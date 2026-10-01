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
instead — an unnamed one fails the census rather than vanishing from it. The
one computed section it does read is a per-kind table: a loop over
`kind_tables` is expanded over the kinds the call itself names.
"""
from __future__ import annotations

import ast
import contextlib
import inspect
import io
import os
import re
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import cli as top_cli  # noqa: E402
from agentic_sdlc.core import config  # noqa: E402
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
COERCERS = frozenset({'flag', 'heading_tuple', 'line_prefixes', 'number',
                      'number_table',
                      'pattern', 'relpath',
                      'relpath_tuple', 'str_tuple', 'str_tuple_table', 'table',
                      'table_array', 'text', 'kind_tables'})
# The one coercer with no default: it reads `[<section>.<key>.<kind>]`, one
# table per kind, and its last argument is the kind list. The census expands
# it over that list and folds each read in the loop over its tables once per
# kind, so a per-kind key is compared to the seed like any other.
PER_KIND = 'kind_tables'
COERCER_HOME = 'core/config.py'
# Each coercer's own signature: a call is bound against it, so a read written
# with keywords is the same read as one written positionally.
SIGNATURES = {name: inspect.signature(getattr(config, name))
              for name in COERCERS}

# A module that reads config through a computed section or key. Static reading
# stops there, so each is named with where its keys ARE held instead. A module
# that starts reading dynamically and is not listed fails the census.
DYNAMIC_MODULES = {
    'repo/belts.py':
        '[adopt] ours — the section is a parameter, and the stock claim set '
        'is empty; the 2.0.0 retired keys are asked only whether present',
    'repo/pm/vocabulary.py':
        '[pm] keys reached through a loop variable in `load` and '
        '`all_config_defects`; every one of them is ALSO read by a literal '
        'call in the other, which is what this census sees. And '
        '`[pm.required.<kind>] lines`, whose section is a local: a WORKFLOW '
        'key with nothing behind it, so the seed shows it as an example',
    'repo/verify/rules.py':
        '[verify] rungs, keyed in a loop — a DECLARATION: nothing is behind '
        'them and `read({})` refuses, which is asserted below',
}

# A read whose fallback is deliberately NOT the stock default: it asks "did the
# project declare anything", and a stock roster would answer yes for a repo
# that declared nothing. The authoritative site is the one left over.
PROBE_READS = {
    ('checks', 'all'): frozenset({'repo/belts.py',
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

SECTION_LINE = re.compile(r'^# \[([a-z_.]+)\]$')
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


def _fold(node, names: dict) -> tuple[bool, object]:
    """(folded, value) for a literal, a name in `names`, a tuple or list of
    those, or an f-string whose every part folds to a string."""
    if node is None:
        return False, None
    try:
        return True, ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        pass
    if isinstance(node, ast.Name) and node.id in names:
        return True, names[node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        parts = [_fold(elt, names) for elt in node.elts]
        if all(got for got, _ in parts):
            values = [value for _, value in parts]
            return True, (tuple(values) if isinstance(node, ast.Tuple)
                          else values)
    if isinstance(node, ast.JoinedStr):
        text = []
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                if part.conversion != -1 or part.format_spec is not None:
                    return False, None
                part = part.value
            got, value = _fold(part, names)
            if not (got and isinstance(value, str)):
                return False, None
            text.append(value)
        return True, ''.join(text)
    return False, None


def _module_constants(tree: ast.Module) -> dict:
    """Module-level names bound to a literal, for folding `SECTION` and friends.

    In source order, so `FLOW_KINDS = (GRAIN_MILESTONE, ...)` folds over the
    names bound above it.
    """
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
        folded, constant = _fold(value, out)
        if not folded:
            continue
        for name in names:
            out[name] = constant
    return out


def _coercer(node) -> str:
    """The coercer a call names, or '' when it is not a call to one."""
    if not isinstance(node, ast.Call):
        return ''
    func = node.func
    name = (func.id if isinstance(func, ast.Name)
            else func.attr if isinstance(func, ast.Attribute) else '')
    return name if name in COERCERS else ''


def _kind_loop(node) -> tuple[ast.Call, str] | None:
    """`(the kind_tables call, the kind variable)` for a loop over one table
    per kind — `for kind, sect in kind_tables(...).items():` or
    `for kind in kind_tables(...):` — else None."""
    if not isinstance(node, ast.For):
        return None
    source, target = node.iter, node.target
    if (isinstance(source, ast.Call) and not source.args
            and isinstance(source.func, ast.Attribute)
            and source.func.attr == 'items'
            and isinstance(target, ast.Tuple) and target.elts):
        source, target = source.func.value, target.elts[0]
    if _coercer(source) == PER_KIND and isinstance(target, ast.Name):
        return source, target.id
    return None


def _bind(name: str, call: ast.Call) -> tuple | None:
    """The call's (section, key, fallback) argument nodes, bound the way
    Python binds them — positional or keyword — against the coercer's OWN
    signature, so a parameter renamed in `core/config.py` is followed rather
    than retyped. A missing argument is `None`. A call that cannot be bound
    (`*args`, `**kwargs`, too many or unknown arguments) is `None` whole.
    """
    if (any(isinstance(arg, ast.Starred) for arg in call.args)
            or any(kw.arg is None for kw in call.keywords)):
        return None
    signature = SIGNATURES[name]
    try:
        bound = signature.bind_partial(
            *call.args, **{kw.arg: kw.value for kw in call.keywords})
    except TypeError:
        return None
    # (sect, section, key, fallback): the first is the table read from.
    params = list(signature.parameters)[1:4]
    return tuple(bound.arguments.get(param) for param in params)


def census(sources) -> tuple[dict, dict, set]:
    """`code_reads` over any `(rel, source text)` pairs, so a planted module
    is graded by the same reader as the real tree."""
    values: dict[tuple[str, str], set] = {}
    dynamic: dict[str, str] = {}
    unfolded: set[tuple[str, str]] = set()
    def read(rel: str, node: ast.Call, names: dict) -> None:
        name = _coercer(node)
        # A call that will not bind, or binds without a section or a key, is
        # still a config read: it goes to the dynamic bookkeeping, where an
        # unnamed module fails, never out of the census.
        bound = _bind(name, node)
        section_node, key_node, fallback_node = bound or (None,) * 3
        got_section, section = _fold(section_node, names)
        got_key, key = _fold(key_node, names)
        if (name == PER_KIND or not (got_section and got_key)
                or not (isinstance(section, str) and isinstance(key, str))):
            dynamic.setdefault(rel, f'{name}(...) at line {node.lineno}')
            return
        if rel in PROBE_READS.get((section, key), ()):
            return
        folded, value = _fold(fallback_node, names)
        if not folded:
            unfolded.add((section, key))
            return
        values.setdefault((section, key), set()).add(repr(_normalise(value)))

    for rel, source in sources:
        tree = ast.parse(source)
        constants = _module_constants(tree)
        expanded: set[int] = set()
        # A per-kind table first: the loop over `kind_tables` binds its kind
        # variable to each kind its kinds argument names, and every read in the
        # loop body is folded once per kind. A kind_tables call this cannot
        # expand is left to the pass below, which names its module dynamic.
        for loop in ast.walk(tree):
            per_kind = _kind_loop(loop)
            if per_kind is None:
                continue
            tables, variable = per_kind
            _, _, kinds_node = _bind(PER_KIND, tables) or (None,) * 3
            got, kinds = _fold(kinds_node, constants)
            if not (got and isinstance(kinds, (tuple, list)) and kinds
                    and all(isinstance(kind, str) for kind in kinds)):
                continue
            inner = [node for stmt in loop.body for node in ast.walk(stmt)
                     if _coercer(node)]
            expanded |= {id(tables)} | {id(node) for node in inner}
            for kind in kinds:
                for node in inner:
                    read(rel, node, {**constants, variable: kind})
        for node in ast.walk(tree):
            if _coercer(node) and id(node) not in expanded:
                read(rel, node, constants)
    return values, dynamic, unfolded


def code_reads() -> tuple[dict, dict, set]:
    """Every `(section, key)` this package reads with a default, the modules
    that read one dynamically, and the keys whose fallback would not fold.

    Values come back as {(section, key): {value}} — a SET, because two call
    sites spelling one default differently is itself the drift this file is
    about.
    """
    return census(
        (rel, path.read_text(encoding='utf-8'))
        for path in sorted(SRC.rglob('*.py'))
        if (rel := path.relative_to(SRC).as_posix()) != COERCER_HOME)


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


_PER_KIND_LOOP = '''\
MILESTONE = 'milestone'
KINDS = (MILESTONE, 'bug')
for kind, kind_sect in kind_tables(sect, 'pm', 'templates', KINDS).items():
    names = heading_tuple(kind_sect, f'pm.templates.{kind}',
                          'extra_sections', ())
'''


class TheCensusCountsEveryCallShape(unittest.TestCase):
    """A coercer call is a config read however its arguments are spelled."""

    PROTECTS = (
        'every call to a core/config.py coercer lands in the census — as a '
        'default, an unfolded fallback, or a dynamic module that must be named '
        '— whether its arguments are positional or keywords, and once per '
        'kind for a per-kind table',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): a '
        'read the census skips is a default the seed is never compared to, '
        'and the comparison stays green over it',
    )

    CORPUS = (
        ("text(sect, 'pm', 'k', 'v')", True),
        ("text(sect, 'pm', key='k', fallback='v')", True),
        ("config.flag(sect, name='pm', key='k', fallback=True)", True),
        # Too few arguments, or arguments the census cannot bind, are still a
        # read: they go to the dynamic bookkeeping, never out of the census.
        ("text(sect, 'pm')", True),
        ('text(sect, *where)', True),
        ('text(sect, **where)', True),
        # Not a coercer, and prose is not a call.
        ("compile(sect, 'pm', 'k', 'v')", False),
        ("HELP = \"text(sect, 'pm', key='k', fallback='v')\"", False),
        # A per-kind table, expanded over its kinds; one it cannot expand is
        # dynamic, never dropped.
        (_PER_KIND_LOOP, True),
        ("tables = kind_tables(sect, 'pm', 'templates', KINDS)", True),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return any(census([('planted.py', planted)]))

    def test_a_keyword_read_folds_to_its_section_key_and_default(self):
        values, dynamic, unfolded = census(
            [('planted.py', "text(sect, 'pm', key='k', fallback='v')")])
        self.assertEqual({('pm', 'k'): {"'v'"}}, values)
        self.assertEqual(({}, set()), (dynamic, unfolded))

    def test_a_per_kind_read_folds_once_for_each_kind(self):
        values, dynamic, unfolded = census([('planted.py', _PER_KIND_LOOP)])
        self.assertEqual({(f'pm.templates.{kind}', 'extra_sections'): {'[]'}
                          for kind in ('milestone', 'bug')}, values)
        self.assertEqual(({}, set()), (dynamic, unfolded))


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
    code = code_defaults()
    # A DECLARATION section may still carry a knob — `[verify]
    # reuse_ignores_status` — and a key the code defaults is held to that
    # default wherever the seed spells it.
    knobs = {pair: value for pair, value in seed.items()
             if not declaration[pair[0]] or pair in code}
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
    A declared section may carry a knob beside its declarations; the case
    above holds that knob to its default.
    """
    seed, declaration, _ = seed_sections()
    marked = {name for name, is_declaration in declaration.items()
              if is_declaration}
    assert marked == {'dispatch', 'integrate', 'verify'}, (
        f'the seed marks {sorted(marked)} as DECLARATION; the commented ones '
        f'are [verify], [integrate] and [dispatch] ([pm.states.*] is marked '
        f'and LIVE)')
    code = code_defaults()
    # The knob in a declared section: `[integrate] prepare` is optional, and
    # the case above holds the seed's line to the code's default.
    assert ('integrate', 'prepare') in code and ('integrate', 'prepare') in seed
    declared = {section for section, key in seed
                if section in marked and (section, key) not in code}
    assert declared == marked, (
        f'{sorted(marked - declared)}: a section the seed calls a DECLARATION '
        f'has a default behind every key it spells — then it is a knob and '
        f'belongs commented at that value')
    # Each declaration's reader is ASKED, so "nothing behind it" is a fact
    # about the code rather than a claim in the seed's comment.
    with pytest.raises(ConfigError):
        verify_rules.read({})
    from agentic_sdlc.repo import dispatch as dispatch_verb
    with pytest.raises(ConfigError):
        dispatch_verb.settings({})
    from agentic_sdlc.repo import integrate
    for absent in (None, {}, {'proof': ['unit']}):
        with pytest.raises(ConfigError):
            integrate.settings(absent)
    assert any(DECLARATION_LINE.match(line) for line in SEED.splitlines()), (
        'the seed marks no DECLARATION at all — the split it states is then '
        'unreadable to anything but a human')
