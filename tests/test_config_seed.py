"""test_config_seed.py — the seed is printable, and it cannot drift from the code.

`pm config --seed` is the surface a BUMPING consumer reads; `init` serves a new
repo once. The case that earns this module is the second one: every value the
seed carries commented is compared to the default the code actually holds, in
both directions, so a key added to `[pm]` without a line here fails by name
instead of reaching consumers as a capability nobody can find (hard rule 11).

**Why it is not one more per-key assertion.** Every individual default is
already covered one key at a time by the gate that reads it — `check doc` proves
its own scope, `check pm` its own rule list. What nothing covered is the SEED
against those defaults, and that is the pair that drifted: 0.4.0 added five
`[pm]` pool keys and `breadcrumbs` and the seed never learned about any of them.

The code side is a CENSUS, not a restatement: `core/config.py`'s coercers are
the one door every value goes through, so the calls to them are the surface.
A call whose section or key is computed cannot be read statically, and those
modules are named in `DYNAMIC_MODULES` with where their keys are covered
instead — an unnamed one fails the census rather than vanishing from it.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import sys
import tempfile
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import cli as top_cli  # noqa: E402
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import init  # noqa: E402
from agentic_sdlc.repo.checks import grain_shape  # noqa: E402
from agentic_sdlc.repo.pm import (cli as pm_cli, skills,  # noqa: E402
                                  vocabulary)
from agentic_sdlc.repo.verify import rules as verify_rules  # noqa: E402

SEED = init.seed_body(init.SEED_CONFIG[0])

SRC = REPO_ROOT / 'src' / 'agentic_sdlc'
# The one door: `core/config.py` decides what a config VALUE may be, so a call
# to one of these IS a config read. The module that defines them is not a read.
COERCERS = frozenset({'flag', 'number', 'number_table', 'pattern', 'relpath',
                      'relpath_tuple', 'str_tuple', 'str_tuple_table', 'table',
                      'table_array', 'text'})
COERCER_HOME = 'core/config.py'

# A module that reads config through a computed section or key. Static reading
# stops there, so each is named with where its keys ARE held instead. A module
# that starts reading dynamically and is not listed fails the census.
DYNAMIC_MODULES = {
    'repo/checks/budget.py':
        '[tests] budget/cases/floor, keyed in a loop — the gate ships NO '
        'ceiling (a number is the project\'s, not this package\'s), so there '
        'is no stock value for the seed to carry',
    'repo/conveyor/steps.py':
        '[<belt>] ours — the section IS the belt\'s name, and the stock claim '
        'set is empty',
    'repo/pm/vocabulary.py':
        '[pm] keys reached through a loop variable in `load` and '
        '`all_config_defects`; every one of them is ALSO read by a literal '
        'call in the other, which is what this census sees',
    'repo/verify/rules.py':
        '[verify] rungs, keyed in a loop — a DECLARATION: nothing is behind '
        'them and `read({})` refuses, which is asserted below',
}

# A read whose fallback is deliberately NOT the stock default: it asks "did the
# project declare anything", and a stock roster would answer yes for a repo
# that declared nothing. The authoritative site is the one left over.
PROBE_READS = {
    ('checks', 'all'): frozenset({'repo/conveyor/steps.py',
                                  'repo/verify/main.py'}),
}

# The fallback is an expression this census cannot fold — a local, or a table
# whose keys are named constants. The value is asked of the CODE anyway, never
# retyped. Held to the census below, so an entry cannot rot into a restatement.
VALUE_FROM_CODE = {
    ('checks', 'all'):
        lambda: tuple(name for name, on in top_cli.KNOWN_GATES.items() if on),
    ('grain_shape', 'caps'): lambda: dict(grain_shape.DEFAULT_CAPS),
    # Keyed and valued by the grain vocabulary's constants, which do not fold.
    ('pm', 'contains'): lambda: dict(vocabulary.DEFAULT_CONTAINS),
}

SECTION_LINE = re.compile(r'^# \[([a-z_]+)\]$')
KEY_LINE = re.compile(r'^# ([a-z_][a-z0-9_]*)[ \t]*=[ \t]*(\S.*)$')
DECLARATION_LINE = re.compile(r'^# DECLARATION\b')


def _normalise(value):
    """Tuples and TOML arrays are the same value; dicts compare by content."""
    if isinstance(value, (list, tuple)):
        return [_normalise(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items()}
    return value


def seed_sections() -> tuple[dict, dict, list]:
    """The seed's commented surface: {(section, key): value}, {section: is a
    DECLARATION}, and the key lines that would not parse as TOML.

    A section is one contiguous run of comment lines; a blank or live line ends
    it. The run leading up to a `# [section]` header is its preamble, and a
    `# DECLARATION` line in that preamble marks the whole block.
    """
    defaults: dict[tuple[str, str], object] = {}
    declaration: dict[str, bool] = {}
    unparsed: list[str] = []
    current: str | None = None
    preamble: list[str] = []
    for line in SEED.splitlines():
        if not line.startswith('#'):
            current, preamble = None, []
            continue
        header = SECTION_LINE.match(line)
        if header:
            current = header.group(1)
            declaration[current] = any(DECLARATION_LINE.match(p)
                                       for p in preamble)
            preamble = []
            continue
        preamble.append(line)
        pair = KEY_LINE.match(line)
        if not pair or current is None:
            continue
        key, raw = pair.group(1), pair.group(2)
        try:
            defaults[(current, key)] = tomllib.loads(f'{key} = {raw}')[key]
        except tomllib.TOMLDecodeError:
            unparsed.append(f'[{current}] {line}')
    return defaults, declaration, unparsed


def _module_constants(tree: ast.Module) -> dict:
    """Module-level names bound to a literal, for folding `SECTION` and friends."""
    out: dict[str, object] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            names = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            value = stmt.value
        elif (isinstance(stmt, ast.AnnAssign) and stmt.value
              and isinstance(stmt.target, ast.Name)):
            names, value = [stmt.target.id], stmt.value
        else:
            continue
        try:
            folded = ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError):
            continue
        for name in names:
            out[name] = folded
    return out


def code_reads() -> tuple[dict, dict, set]:
    """Every `(section, key)` this package reads with a default, the modules
    that read one dynamically, and the keys whose fallback would not fold.

    Values come back as {(section, key): {value}} — a SET, because two call
    sites spelling one default differently is itself the drift this file is
    about.
    """
    values: dict[tuple[str, str], set] = {}
    dynamic: dict[str, str] = {}
    unfolded: set[tuple[str, str]] = set()
    for path in sorted(SRC.rglob('*.py')):
        rel = path.relative_to(SRC).as_posix()
        if rel == COERCER_HOME:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        constants = _module_constants(tree)

        def fold(node):
            try:
                return True, ast.literal_eval(node)
            except (ValueError, SyntaxError, TypeError):
                pass
            if isinstance(node, ast.Name) and node.id in constants:
                return True, constants[node.id]
            return False, None

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or len(node.args) < 3:
                continue
            func = node.func
            name = (func.id if isinstance(func, ast.Name)
                    else func.attr if isinstance(func, ast.Attribute) else '')
            if name not in COERCERS:
                continue
            got_section, section = fold(node.args[1])
            got_key, key = fold(node.args[2])
            if not (got_section and got_key
                    and isinstance(section, str) and isinstance(key, str)):
                dynamic.setdefault(rel, f'{name}(...) at line {node.lineno}')
                continue
            if rel in PROBE_READS.get((section, key), ()):
                continue
            if len(node.args) > 3:
                folded, value = fold(node.args[3])
            else:
                folded, value = False, None
            if not folded:
                unfolded.add((section, key))
                continue
            values.setdefault((section, key), set()).add(
                repr(_normalise(value)))
    return values, dynamic, unfolded


def code_defaults() -> dict[tuple[str, str], object]:
    """One default per `(section, key)`, asked of the code."""
    values, _, unfolded = code_reads()
    out: dict[tuple[str, str], object] = {}
    for pair, spellings in values.items():
        assert len(spellings) == 1, (
            f'[{pair[0]}] {pair[1]} is defaulted TWO ways in this package — '
            f'{sorted(spellings)}. One of them is the one consumers get and '
            f'nobody can tell which; single-source it before seeding it.')
        out[pair] = _normalise(ast.literal_eval(next(iter(spellings))))
    for pair in unfolded:
        out[pair] = _normalise(VALUE_FROM_CODE[pair]())
    return out


@contextlib.contextmanager
def tree(config: str):
    """A throwaway root with a devkit.toml; `.git` is a MARKER, not a repo."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        (root / 'devkit.toml').write_text(config, encoding='utf-8')
        (root / '.git').mkdir()
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file under `root`, by content — what `git status --porcelain`
    would answer, without spawning git (hard rule 10, unit tier)."""
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob('*')) if p.is_file()}


# --- criterion 1: the seed is printable ---------------------------------------

def test_pm_config_seed_prints_the_seed_and_writes_nothing():
    """Exit 0, the seed byte for byte, and the tree untouched."""
    from agentic_sdlc.repo.pm import vocabulary
    with tree(SEED) as root:
        before = snapshot(root)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = skills.cmd_config(vocabulary.load(), ['--seed'])
        after = snapshot(root)
    assert code == 0
    assert out.getvalue() == SEED, 'stdout is not the seed byte for byte'
    assert after == before, 'a read verb wrote to the tree'


def test_pm_config_is_reachable_from_the_cli():
    """Rule 11: a capability nobody can find is a capability you do not have.

    `cmd_config` is written and tested above; until `pm/cli.py` routes it, no
    consumer can reach it. This case is the handshake, and its message is the
    diff that closes it.
    """
    routed = set()
    source = ast.parse((SRC / 'repo/pm/cli.py').read_text(encoding='utf-8'))
    for node in ast.walk(source):
        if isinstance(node, ast.Dict):
            routed |= {k.value for k in node.keys
                       if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    assert 'config' in routed, (
        "pm/cli.py does not route `config`. Add to the table in `main`:\n"
        "        'config': skills.cmd_config,\n"
        "and one line to USAGE naming what it prints:\n"
        "  config --seed                           (the seed devkit.toml this\n"
        "                                           pinned tool ships — every\n"
        "                                           gate key at its real\n"
        "                                           default. Writes nothing)")
    assert 'config --seed' in pm_cli.USAGE, (
        '`pm --help` does not name `config --seed` — see the USAGE lines above')


# --- criterion 2: the seed cannot drift from the code -------------------------

def test_the_census_reads_every_module_that_reads_config():
    """The floor criterion 2 stands on (hard rule 4): a census that folded to
    nothing would compare an empty set of keys and pass over everything.
    """
    values, dynamic, unfolded = code_reads()
    assert values, 'the census found no config read at all — it proves nothing'
    assert set(dynamic) == set(DYNAMIC_MODULES), (
        f'dynamic-read drift: {sorted(set(dynamic) ^ set(DYNAMIC_MODULES))} — '
        f'a module reading config through a computed key is invisible to this '
        f'census, so it is named here with where its keys ARE held, or the '
        f'key is made literal')
    assert unfolded == set(VALUE_FROM_CODE), (
        f'fallback-folding drift: {sorted(unfolded ^ set(VALUE_FROM_CODE))} — '
        f'a fallback this census cannot fold needs an entry in '
        f'VALUE_FROM_CODE that ASKS the code, and one that folds again needs '
        f'its entry removed')


def test_every_commented_default_in_the_seed_is_the_codes_own_default():
    """The feature. Both directions, because both have bitten:

    a value that drifted (`[checks] all` shipped two gates while the code ran
    three) and a key the seed never learned about (0.4.0 added five `[pm]`
    pool keys and `breadcrumbs`). A consumer reads the seed to find out what a
    version can do; a key missing from it is a capability nobody can find.
    """
    seed, declaration, unparsed = seed_sections()
    assert not unparsed, (
        f'{len(unparsed)} commented line(s) in the seed look like a setting '
        f'and are not valid TOML — they would be invisible to this case:\n  '
        + '\n  '.join(unparsed))
    knobs = {pair: value for pair, value in seed.items()
             if not declaration[pair[0]]}
    code = code_defaults()
    assert knobs, 'the seed parser found no commented default at all'
    assert code, 'the census found no default at all'

    missing = sorted(set(code) - set(knobs))
    assert not missing, (
        f'the code defaults {len(missing)} key(s) the seed never mentions: '
        + ', '.join(f'[{s}] {k} = {code[(s, k)]!r}' for s, k in missing)
        + ' — add each to the seed, commented at exactly that value')
    extra = sorted(set(knobs) - set(code))
    assert not extra, (
        f'the seed offers {len(extra)} key(s) nothing reads: '
        + ', '.join(f'[{s}] {k}' for s, k in extra)
        + ' — a key that does nothing is worse than one that errors')

    for section, key in sorted(knobs):
        assert knobs[(section, key)] == code[(section, key)], (
            f'[{section}] {key} has DRIFTED: the seed says '
            f'{knobs[(section, key)]!r}, the code defaults '
            f'{code[(section, key)]!r}. A repo with no devkit.toml would not '
            f'run byte-identically to one that uncommented this line.')


# --- criterion 3: the split is stated in the seed, and it decides -------------

def test_the_seeds_declarations_are_the_keys_with_nothing_behind_them():
    """A knob has a default and stays commented at it; a declaration has none,
    refuses by name, and is spelled out with its argument. The classification
    is machine-readable in the seed, and the CODE is asked whether it is true.
    """
    _, declaration, _ = seed_sections()
    marked = {name for name, is_declaration in declaration.items()
              if is_declaration}
    assert marked == {'dispatch', 'verify'}, (
        f'the seed marks {sorted(marked)} as DECLARATION; the commented ones '
        f'are [verify] and [dispatch] ([pm.states.*] is marked and LIVE)')
    code = code_defaults()
    assert not [pair for pair in code if pair[0] in marked], (
        f'a section the seed calls a DECLARATION has a default behind it — '
        f'then it is a knob and belongs commented at that value')
    # Each declaration's reader is ASKED, so "nothing behind it" is a fact
    # about the code rather than a claim in the seed's comment.
    with pytest.raises(ConfigError):
        verify_rules.read({})
    from agentic_sdlc.repo import dispatch as dispatch_verb
    with pytest.raises(ConfigError):
        dispatch_verb.settings({})
    assert any(DECLARATION_LINE.match(line) for line in SEED.splitlines()), (
        'the seed marks no DECLARATION at all — the split it states is then '
        'unreadable to anything but a human')


# --- criterion 4: the arrival a dispatch starts at names the courier ----------
# The one `GDK_LEDGER_*` value no hook payload carries, so nothing exports it.
LEDGER_GRAIN_ENV = 'GDK_LEDGER_GRAIN'


def test_the_arrival_that_starts_a_dispatch_names_the_ledger_courier():
    """Rule 11, in the surface somebody is standing in: `pm feature|story
    building <id> --by agent <type>` already records WHO, so it is where the
    courier and the env var it needs get named. Measured before this line
    existed: six dispatches, zero dispatch rows, on a tree whose couriers were
    wired. The SEED's example and this repo's own declaration are one change,
    never two — a consumer reads the seed to find out what a version can do.
    """
    live = tomllib.loads((REPO_ROOT / 'devkit.toml').read_text(encoding='utf-8'))
    for kind in (vocabulary.GRAIN_FEATURE, vocabulary.GRAIN_STORY):
        node = live['pm'][vocabulary.ARRIVE_KEY][kind]['building']
        named = {path: why for path, why in node[vocabulary.HAVE_KEY].items()
                 if any(courier in path for courier in vocabulary.LEDGER_COURIERS)}
        assert named, (
            f'[pm.arrive.{kind}.building] have names no ledger courier; a '
            f'dispatch starts here and nothing tells the operator it can be '
            f'recorded: {sorted(node[vocabulary.HAVE_KEY])}')
        for path, why in named.items():
            assert (REPO_ROOT / path).is_file(), (
                f'[pm.arrive.{kind}.building] have names {path}, which is not '
                f'in this checkout — the line would read "DECLARED and not '
                f'installed" forever')
            assert LEDGER_GRAIN_ENV in why, (
                f'[pm.arrive.{kind}.building] have.{path} does not name '
                f'{LEDGER_GRAIN_ENV}: the courier reads it from its own '
                f'environment and no hook event carries it, so a line naming '
                f'the script without the variable names half the capability')
    assert LEDGER_GRAIN_ENV in SEED, (
        f'the seed\'s [pm.arrive.…] example does not name {LEDGER_GRAIN_ENV} '
        f'while this repo\'s own declaration does — a consumer reads the seed '
        f'to find out what a version can do')
