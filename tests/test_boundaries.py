"""test_boundaries.py — the two primitives, enforced by AST rather than by memory.

A day of review found ~25 defects in this package that were three bugs in
eighteen places. Two of the three are shapes, not incidents:

  * something silently leaves a census (~6x), and
  * a write is not all-or-nothing (~6x).

Every fix before this file was an INSTANCE — one filter taught to report
itself, one writer given a pre-pass — so the next feature reintroduced the
shape somewhere new. Fixing grain detection literally created a new narrowing
via dotted names, because the fix was a filter and nothing made filters
disclose.

`core/walk.py` and `core/apply.py` make each shape impossible to express. THIS
FILE makes them impossible to route around. Both tests are exact module
ALLOWLISTS, not patterns: a new gate that enumerates directly, or a new verb
that writes directly, breaks the build and is named by `file:line`.

Deliberately AST, not grep: `subprocess.run(['git', 'mv', ...])` is not a
`Path.rename`, a string `'rglob'` in a docstring is not a call, and a grep
cannot tell those apart. An AST walk decides from the syntax, with no inference
and nothing to tune.

**Every guard here declares `CORPUS` and `catches()`, and a new one must.**
`tests/test_guard_corpus.py` replays each corpus and names any AST-shaped guard
that declares none: the classifiers below all assert an EMPTY offender list,
and a reader that stopped reading returns one too.
"""
from __future__ import annotations

import ast
import re
import tomllib
import unittest
from pathlib import Path

# The derivation that puts the `shell` mark on a spawning module. Imported
# rather than re-implemented: primitive 5 below holds `repo/emit.py` to the
# SAME no-subprocess question the tier definition is built on, and two
# spellings of one question is how they drift apart.
from conftest import module_spawns
from support import REPO_ROOT

SRC = REPO_ROOT / 'src' / 'agentic_sdlc'
# Both allowlists assert an EMPTY offender list, so both pass perfectly on a
# census of zero files — which is what a moved/renamed SRC produces. Rule 4 says
# a gate scanning nothing must say so, and these are gates. The floor is well
# under the real count (48 at the time of writing) and well over zero: it is
# there to catch a broken root, not to track the module count.
MIN_SOURCES = 20

# --- primitive 1: one walk ----------------------------------------------------
# The exact module that owns filesystem ENUMERATION. Not a package, not a
# prefix — one file.
WALK_MODULE = 'core/walk.py'
# Attribute calls that ENUMERATE. `Path.walk` is 3.12+, banned here so the two
# spellings of `os.walk` cannot split the ownership between interpreters.
ENUMERATORS = ('glob', 'rglob', 'iterdir', 'walk', 'scandir', 'listdir')
# --- primitive 2: one apply ---------------------------------------------------
APPLY_MODULE = 'core/apply.py'
# Path methods that mutate and CANNOT be anything else at the syntax level.
# `.replace()` is absent on purpose: `str.replace` is the same syntax, and no
# amount of staring at an AST distinguishes them by name. It is caught by ARITY
# instead — see `_replace_is_a_path_replace`.
PATH_MUTATORS = ('write_text', 'write_bytes', 'unlink', 'rmdir', 'mkdir',
                 'rename', 'touch', 'symlink_to', 'hardlink_to', 'chmod')
# Module-qualified mutators. The receiver is right there in the syntax, so
# these need no disambiguation at all.
MODULE_MUTATORS = {
    'os': ('rename', 'replace', 'remove', 'unlink', 'rmdir', 'mkdir',
           'makedirs', 'removedirs', 'symlink', 'link', 'truncate', 'chmod'),
    'shutil': ('rmtree', 'copy', 'copy2', 'copyfile', 'copytree', 'move'),
}
# Modes that make `open()` a mutation. A read-mode `open()` is not a write and
# stays anybody's to call.
WRITE_MODES = ('w', 'a', 'x', '+')
# Where the mode SITS, per spelling. The builtin carries the path first, so its
# mode is the second argument; the bound method already has the path in the
# receiver, so its mode is the FIRST. Reading `args[1]` for both was this gate's
# blind spot: every `p.open('w')` in `src/` classified as a read and passed.
BUILTIN_OPEN_MODE_ARG = 1
METHOD_OPEN_MODE_ARG = 0
# `mode=` outranks the positional slot in either spelling, because that is what
# Python itself does; an absent mode is a read, because that is the default.
OPEN_MODE_KEYWORD = 'mode'
DEFAULT_OPEN_MODE = 'r'
# The ONE sanctioned writer outside APPLY_MODULE, pinned by PATH **and** MODE
# rather than by a blanket allowlist. `ledger.append_row` opens its file in
# append mode deliberately (0.22.0/ledger decision D1): a read-modify-write
# drops rows when two appenders collide and rewrites the bytes `merge=union`
# depends on nobody rewriting. Append is a different primitive, not a variant of
# overwrite — so a `'w'` in THIS file is still a finding, and an `'a'` in any
# other module is too.
APPEND_ONLY_MODULE = 'repo/pm/ledger.py'
APPEND_MODES = ('a', 'ab')


def _sources() -> list[tuple[str, Path]]:
    """(module-relative posix path, file) for every shipped module.

    Enumerated through `core.walk`, because a test that hand-rolled its own
    `rglob` to police `rglob` would be the joke that writes itself.
    """
    from agentic_sdlc.core import walk as walkmod
    from agentic_sdlc.core.walk import Kind
    found = walkmod.descendants(SRC, Kind.FILE, suffix='.py')
    out = [(p.relative_to(SRC).as_posix(), p) for p in found.kept]
    # The census floor, at the one place every caller goes through, so no
    # allowlist can be satisfied by having scanned nothing.
    assert len(out) >= MIN_SOURCES, (
        f'{len(out)} shipped module(s) under {SRC} — expected at least '
        f'{MIN_SOURCES}. The allowlists below assert an EMPTY offender list, '
        f'so a census this small passes them while checking nothing.')
    return out


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))


def _is_an_open_call(node: ast.Call) -> bool:
    """True for both spellings of `open` — the builtin and the bound method."""
    func = node.func
    return ((isinstance(func, ast.Attribute) and func.attr == 'open')
            or (isinstance(func, ast.Name) and func.id == 'open'))


def _open_mode(node: ast.Call) -> str | None:
    """The literal mode of this `open(...)`, or None when it is not a literal.

    The positional slot depends on the SPELLING: `open(path, 'w')` puts the mode
    where `p.open('w')` puts nothing at all. `mode=` wins over the positional in
    either form, and an absent mode is `DEFAULT_OPEN_MODE` — `open(p)` reads.
    """
    index = (METHOD_OPEN_MODE_ARG if isinstance(node.func, ast.Attribute)
             else BUILTIN_OPEN_MODE_ARG)
    mode: ast.expr | None = node.args[index] if len(node.args) > index else None
    for kw in node.keywords:
        if kw.arg == OPEN_MODE_KEYWORD:
            mode = kw.value
    if mode is None:
        return DEFAULT_OPEN_MODE
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return mode.value
    return None


def _is_write_open(node: ast.Call) -> bool:
    """True when this `open(...)` call names a WRITE mode.

    The mode is a literal in every call in this package. A non-literal mode is
    treated as a write: an unreadable mode is exactly the case a guard must not
    wave through.
    """
    mode = _open_mode(node)
    if mode is None:
        return True
    return any(ch in mode for ch in WRITE_MODES)


def _is_sanctioned_append(rel: str, node: ast.Call) -> bool:
    """True for the one append `APPEND_ONLY_MODULE` is allowed to make.

    By path AND by mode: a `'w'` in that same file is not sanctioned, and an
    `'a'` anywhere else is not either. A non-literal mode (None) matches no
    entry in `APPEND_MODES`, so an unreadable mode cannot buy the exception.
    """
    return rel == APPEND_ONLY_MODULE and _open_mode(node) in APPEND_MODES


def _is_unsanctioned_write_open(rel: str, node: ast.Call) -> bool:
    """A write-mode `open(...)` that is not the ledger's sanctioned append."""
    return _is_write_open(node) and not _is_sanctioned_append(rel, node)


def _calls(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def _enumeration_sites(rel: str, tree: ast.Module) -> list[str]:
    out = []
    for node in _calls(tree):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in ENUMERATORS:
            # `ast.walk` / `os.walk` / `path.walk` — the receiver decides
            # whether `walk` is an enumeration or this package's own module.
            if func.attr == 'walk' and isinstance(func.value, ast.Name) \
                    and func.value.id in ('ast', 'walk'):
                continue
            out.append(f'{rel}:{node.lineno}: {func.attr}()')
        elif isinstance(func, ast.Name) and func.id in ('scandir', 'listdir'):
            out.append(f'{rel}:{node.lineno}: {func.id}()')
    return out


def _replace_is_a_path_replace(node: ast.Call) -> bool:
    """True when this `.replace(...)` is `Path.replace`, decided by ARITY.

    `str.replace` needs at least TWO arguments — `s.replace(old)` is a
    TypeError, so it cannot appear in code that runs. `Path.replace(target)`
    takes exactly one. That is a syntactic fact, not a guess about types, and it
    is the only honest way to tell the two apart from an AST.
    """
    return len(node.args) == 1 and not node.keywords


def _mutation_sites(rel: str, tree: ast.Module) -> list[str]:
    out = []
    for node in _calls(tree):
        func = node.func
        if isinstance(func, ast.Name):
            if func.id == 'open' and _is_unsanctioned_write_open(rel, node):
                out.append(f'{rel}:{node.lineno}: open(..., write mode)')
            continue
        if not isinstance(func, ast.Attribute):
            continue
        receiver = func.value.id if isinstance(func.value, ast.Name) else None
        if receiver in MODULE_MUTATORS and func.attr in MODULE_MUTATORS[receiver]:
            out.append(f'{rel}:{node.lineno}: {receiver}.{func.attr}()')
        elif func.attr in PATH_MUTATORS:
            out.append(f'{rel}:{node.lineno}: {func.attr}()')
        elif func.attr == 'replace' and _replace_is_a_path_replace(node):
            out.append(f'{rel}:{node.lineno}: replace() (one arg — Path.replace)')
        elif func.attr == 'open' and _is_unsanctioned_write_open(rel, node):
            out.append(f'{rel}:{node.lineno}: .open(..., write mode)')
    return out


class TheCensusIsTheRealTree(unittest.TestCase):
    """Before either allowlist means anything, it has to have scanned the tree.

    The floor itself is asserted inside `_sources()`, which every case below
    goes through — so the case that restated it here was the same assertion
    twice. What is NOT derivable from that is whether the floor ever fires, and
    that is what stayed.
    """

    def test_a_moved_SRC_breaks_the_build_instead_of_passing(self):
        import tempfile
        import unittest.mock
        with tempfile.TemporaryDirectory() as empty:
            with unittest.mock.patch(f'{__name__}.SRC', Path(empty)):
                with self.assertRaises(AssertionError):
                    _sources()


class OneWalk(unittest.TestCase):
    """PRIMITIVE 1 — filesystem enumeration lives in exactly one module."""

    CORPUS = (
        ("for path in root.rglob('*.py'):\n    pass", True),
        ("names = sorted(root.glob('*.md'))", True),
        ('for child in root.iterdir():\n    pass', True),
        ('for base, dirs, files in os.walk(root):\n    pass', True),
        ('names = os.listdir(root)', True),
        ('with os.scandir(root) as entries:\n    pass', True),
        # The receiver is what decides: `ast.walk` and this package's own
        # `walk` module are not enumerations, and neither is prose.
        ('for node in ast.walk(tree):\n    pass', False),
        ('found = walk.descendants(root, Kind.FILE)', False),
        ("HELP = 'rglob and iterdir and listdir'", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_enumeration_sites(SCRATCH_MODULE, ast.parse(planted)))

    def test_only_the_walk_module_enumerates(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == WALK_MODULE:
                continue
            offenders.extend(_enumeration_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'filesystem enumeration outside ' + WALK_MODULE + '. A walk that '
            'returns one list has nowhere to put what it dropped, which is how '
            'six censuses came to narrow in silence. Route it through '
            '`core.walk`, whose result carries both halves:\n  '
            + '\n  '.join(offenders))

    def test_the_walk_module_does_enumerate(self):
        """The allowlist must not be vacuously satisfiable by a module that
        stopped enumerating — then every offender would move somewhere else and
        the test would still pass."""
        sites = _enumeration_sites(WALK_MODULE, _tree(SRC / WALK_MODULE))
        self.assertGreaterEqual(len(sites), 4, sites)


class OneApply(unittest.TestCase):
    """PRIMITIVE 2 — filesystem mutation lives in exactly one module."""

    CORPUS = (
        ('target.write_text(payload)', True),
        ('target.write_bytes(payload)', True),
        ('target.unlink()', True),
        ('target.mkdir(parents=True)', True),
        ('os.replace(source, target)', True),
        ('shutil.rmtree(scratch)', True),
        # `Path.replace` takes ONE argument and `str.replace` needs two, which
        # is the only honest way an AST tells them apart.
        ('target.replace(other)', True),
        ("line.replace('a', 'b')", False),
        ('target.read_text()', False),
        ('apply.plan(steps).apply()', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_sites_for(planted))

    def test_only_the_apply_module_writes(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == APPLY_MODULE:
                continue
            offenders.extend(_mutation_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'filesystem mutation outside ' + APPLY_MODULE + '. A writer that '
            'decides as it goes lands half a plan when step three refuses, '
            'which is how the scaffolder, install-agents and `pm collapse` each '
            'left a tree neither before nor after. Route it through '
            '`core.apply`, which decides the whole plan and then applies it:\n  '
            + '\n  '.join(offenders))

    def test_the_apply_module_does_write(self):
        sites = _mutation_sites(APPLY_MODULE, _tree(SRC / APPLY_MODULE))
        self.assertGreaterEqual(len(sites), 4, sites)


# Every spelling of `open` the classifier has to get right, as
# (source, is a write). The mode MOVES between argument slots with the
# spelling — `p.open('w')` puts it where `open(p, 'w')` puts the path — and
# that is the whole of the defect this table exists to hold shut. A scratch
# module, not a real one: the gate is being MUTATED here, not observed.
OPEN_SPELLINGS = (
    # bound method — the mode is the FIRST argument.
    ("p.open('w')", True),
    ("p.open(mode='w')", True),
    ("Path(x).open('a')", True),
    ("p.open('x')", True),
    ("p.open('w+')", True),
    ("p.open('r+')", True),
    ("p.open('wb')", True),
    ("p.open('ab')", True),
    ("p.open('a', encoding='utf-8', newline='\\n')", True),
    ("p.open()", False),
    ("p.open('r')", False),
    ("p.open('rb')", False),
    ("p.open(encoding='utf-8')", False),
    # builtin — the mode is the SECOND argument, after the path.
    ("open(p, 'w')", True),
    ("open(p, mode='w')", True),
    ("open(p, 'a')", True),
    ("open(p, 'x')", True),
    ("open(p, 'w+')", True),
    ("open(p, 'r+')", True),
    ("open(p, 'wb')", True),
    ("open(p, 'ab')", True),
    ("open(p)", False),
    ("open(p, 'r')", False),
    ("open(p, 'rb')", False),
    ("open(p, encoding='utf-8')", False),
    # An unreadable mode is a write in both spellings: a guard that cannot read
    # the mode must refuse rather than wave the call through (rule 4).
    ("open(p, mode)", True),
    ("p.open(mode)", True),
)
# A module path that is emphatically NOT the ledger, for proving the exception
# is pinned to one file rather than granted to append mode generally.
SCRATCH_MODULE = 'repo/pm/scratch_not_the_ledger.py'
# The floor under the `open` census, in the same spirit as MIN_SOURCES: well
# under the real count (7 at the time of writing) and well over zero, so the
# classifier cannot be declared correct over a tree it never read.
MIN_OPEN_CALLS = 4


def _sites_for(source: str, rel: str = SCRATCH_MODULE) -> list[str]:
    """The real classifier, run over a source snippet as if it were `rel`."""
    return _mutation_sites(rel, ast.parse(source))


class TheOpenModeIsReadFromTheRightArgument(unittest.TestCase):
    """`Path.open('w')` is a write, and this gate used to say otherwise.

    `_is_write_open` read the mode from `args[1]` — correct for the builtin
    `open(path, 'w')`, and wrong for `p.open('w')`, whose `args[1]` is not the
    mode and is usually nothing at all. Every `p.open('w')` and `p.open('a')`
    under `src/` therefore classified as a READ and passed the one-writer
    boundary: a gate that missed real drift and printed PASS, which CLAUDE.md
    rule 4 calls the cardinal sin.
    """

    # Already (planted, must it be caught) — the table this feature generalised.
    CORPUS = OPEN_SPELLINGS

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_sites_for(planted))

    def test_every_spelling_of_open_is_classified_by_its_real_mode(self):
        for source, is_write in OPEN_SPELLINGS:
            with self.subTest(source=source):
                sites = _sites_for(source)
                self.assertEqual(
                    is_write, bool(sites),
                    f'{source!r} classified as a '
                    f'{"read" if is_write else "write"}. The mode is the first '
                    'argument for the bound method and the second for the '
                    f'builtin; sites={sites}')

    def test_a_scratch_module_writing_by_Path_open_is_caught(self):
        """End to end, through the same path the gate walks: a real file on
        disk, parsed by `_tree`, classified by `_mutation_sites`."""
        import tempfile
        with tempfile.TemporaryDirectory() as scratch:
            module = Path(scratch) / 'scratch.py'
            module.write_text(
                'from pathlib import Path\n'
                '\n'
                '\n'
                'def sneak(target: Path, payload: str) -> None:\n'
                "    with target.open('w', encoding='utf-8') as handle:\n"
                '        handle.write(payload)\n',
                encoding='utf-8')
            sites = _mutation_sites(SCRATCH_MODULE, _tree(module))
        self.assertEqual([f'{SCRATCH_MODULE}:5: .open(..., write mode)'], sites)

    def test_the_open_census_is_not_empty(self):
        """The classifier above is only worth anything over a tree it read."""
        census = sum(1 for _, path in _sources()
                     for node in _calls(_tree(path)) if _is_an_open_call(node))
        self.assertGreaterEqual(
            census, MIN_OPEN_CALLS,
            f'{census} open() call(s) under {SRC} — expected at least '
            f'{MIN_OPEN_CALLS}. A correct mode classifier over nothing is '
            'still a gate that checks nothing.')


class TheLedgerAppendIsTheOneException(unittest.TestCase):
    """PRIMITIVE 2, continued — the single sanctioned writer outside apply.

    Decision D1 of `0.22.0/ledger`: `ledger.append_row` owns append as a
    PRIMITIVE, because a read-modify-write drops rows when two appenders
    collide. The exception it earns is one file in one mode — not an allowlist
    entry that would also excuse an overwrite, a `mkdir`, or a `write_text`.
    """

    # Graded AS the ledger, so every case asks what the exception admits.
    # Append is what it was granted for; an overwrite there rewrites the bytes
    # `merge=union` relies on nobody rewriting, which is the defect D1 exists
    # to prevent; and the exception is by MODE, so it excuses no other
    # mutation of that same file.
    CORPUS = (
        ("p.open('a')", False),
        ("p.open('ab')", False),
        ("p.open(mode='a')", False),
        ("p.open('a', encoding='utf-8', newline='\\n')", False),
        ("p.open('w')", True),
        ("open(p, 'w')", True),
        ("p.open('w+')", True),
        ("p.open(mode='w')", True),
        ("p.open('x')", True),
        ('p.write_text(x)', True),
        ('p.mkdir()', True),
        ('p.unlink()', True),
        ('os.remove(p)', True),
        # A mode this file cannot read matches no entry in APPEND_MODES, so it
        # cannot buy the exception either.
        ('p.open(mode)', True),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_sites_for(planted, APPEND_ONLY_MODULE))

    def test_append_anywhere_else_is_a_finding(self):
        for rel in (SCRATCH_MODULE, 'cli.py', 'repo/pm/model.py'):
            for source in ("p.open('a')", "open(p, 'a')", "p.open('ab')"):
                with self.subTest(rel=rel, source=source):
                    self.assertNotEqual([], _sites_for(source, rel))

    def test_the_ledger_really_does_append(self):
        """The exception must not outlive the append it was granted for.

        An allowlist entry nothing matches is a hole waiting for a file to move
        into it — the same reasoning `CONFIG_IMPORT_ALLOWLIST` prunes for.
        """
        tree = _tree(SRC / APPEND_ONLY_MODULE)
        appends = [f'{APPEND_ONLY_MODULE}:{node.lineno}'
                   for node in _calls(tree)
                   if _is_an_open_call(node)
                   and _is_sanctioned_append(APPEND_ONLY_MODULE, node)]
        self.assertEqual(
            1, len(appends),
            f'{APPEND_ONLY_MODULE} should hold exactly ONE sanctioned append; '
            f'found {appends}. If the append is gone, delete the exception.')


class TheResolversCollapsed(unittest.TestCase):
    """0.4.0 — the addressing layer that existed BECAUSE the path was schema.

    Twenty functions that were one function with a kind baked in: `story_file`
    knew one three-segment shape, `milestone_dir` worked for milestones and
    nothing else, and a fifth kind meant writing four more. They are
    `grain_file(cfg, gid, kind)`, `children(cfg, kind, parent)` and
    `pool_walk(cfg, kind)` now.

    **Both halves are pinned, and the second is the one that rots.** Twelve are
    GONE, and a name coming back means somebody re-derived an id from a path.
    Eight SURVIVE as the nested reader, reachable only when `is_pooled(cfg)` is
    False — that is a deliberate compat layer with a stated retirement
    condition (D3 on `identity-lives-in-frontmatter`), and pinning the roster
    is what stops it becoming permanent by accident: delete the last nested
    tree and this case is what tells you the eight can go.
    """

    # Gone. Each answered a question about a PATH or a grain DIRECTORY, and a
    # pooled tree has neither.
    GONE = ('orphan_dirs', 'milestone_dir_of', '_building_ledger_dir')

    # Kept, and only for the nested layout. Shrinking this list is the goal;
    # GROWING it means a new path-shaped resolver got written, which is the
    # thing 0.4.0 deleted.
    NESTED_ONLY = ('_nested_index', '_nested_feature_files',
                   '_nested_story_files', 'milestone_dir', 'feature_dir',
                   'milestone_walk', 'milestone_dirs', 'AmbiguousStory')

    def test_the_path_shaped_resolvers_are_gone(self):
        model = SRC / 'repo' / 'pm' / 'model.py'
        source = model.read_text(encoding='utf-8')
        for name in self.GONE:
            self.assertNotIn(f'def {name}(', source,
                             f'{name} is back in model.py. An id names no '
                             f'location in 0.4.0, so nothing derives one from '
                             f'a path.')

    def test_the_nested_reader_is_exactly_this_roster(self):
        model = SRC / 'repo' / 'pm' / 'model.py'
        source = model.read_text(encoding='utf-8')
        for name in self.NESTED_ONLY:
            opener = f'class {name}(' if name[0].isupper() else f'def {name}('
            self.assertIn(opener, source,
                          f'{name} left without this roster being updated — '
                          f'if the nested reader is going, the whole of it '
                          f'goes together and D3 gets closed.')

    def test_the_three_general_resolvers_take_a_kind(self):
        from agentic_sdlc.repo.pm import model as pm_model
        import inspect
        for name, arg in (('grain_file', 'kind'), ('children', 'kind'),
                          ('pool_walk', 'kind')):
            fn = getattr(pm_model, name)
            self.assertIn(arg, inspect.signature(fn).parameters, name)


class OneRuleRoutesALedgerRow(unittest.TestCase):
    """0.4.0/D1 — a row is filed against the milestone that owns its GRAIN, and
    no write path reads a status to decide where bytes go.

    The deleted lookup (`_building_ledger_dir`) asked which milestone was
    `in_progress`: it refused when none was, which lost every row a tree wrote
    while it was still planning, and refused when two were, which is the
    workflow this package exists for. It was a SECOND answer to a question
    `_stamp` had always answered from the grain.

    A name test rather than a behaviour test, because the behaviour cases in
    `test_pm_ledger_record.py` prove where a row lands and cannot prove that
    the old mechanism is not sitting beside the new one, reachable from a path
    nobody thought to cover.
    """

    # Spelled as a string so grepping for the retired name finds this case:
    # the one hit in `src/` a reader gets is the gate that removed it.
    RETIRED = '_building_ledger_dir'

    def test_the_in_progress_lookup_is_not_in_the_source(self):
        offenders, scanned = [], 0
        for rel, path in _sources():
            scanned += 1
            if self.RETIRED in path.read_text(encoding='utf-8'):
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         f'{self.RETIRED} is back. A row is routed by its '
                         f'grain (D1); a milestone status decides nothing '
                         f'about where a row is written.')
        self.assertGreaterEqual(scanned, MIN_SOURCES)


# The two halves a `Walk` carries. A count taken off either one is a number
# with its disclosures dropped, which is the shape `census(label)` exists for.
WALK_HALVES = ('kept', 'skipped')


def _half_length_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every `len(...)` in this module taken over one half of a `Walk`."""
    out: list[str] = []
    for node in _calls(tree):
        if not (isinstance(node.func, ast.Name) and node.func.id == 'len'):
            continue
        out.extend(f'{rel}:{node.lineno}: len(...{arg.attr})'
                   for arg in node.args
                   if isinstance(arg, ast.Attribute) and arg.attr in WALK_HALVES)
    return out


class WalkHasNoLength(unittest.TestCase):
    """A census must not be able to reach a number without its narrowings.

    `Walk.__len__` raises, and `len(x.kept)` is the way around it — so the way
    around it is a build break too. The counting API is `Walk.census(label)`,
    which renders the number and the disclosures as ONE string.
    """

    CORPUS = (
        ('total = len(found.kept)', True),
        ('total = len(found.skipped)', True),
        ('total = len(walk.descendants(root, Kind.FILE).kept)', True),
        ('total = len(entries)', False),
        ('total = len(found.census(label))', False),
        ("said = found.census('module(s)')", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_half_length_sites(SCRATCH_MODULE, ast.parse(planted)))

    def test_len_of_a_walk_half_is_never_taken(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == WALK_MODULE:
                continue
            offenders.extend(_half_length_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a count taken off half a Walk. Call `.census(label)` so the number '
            'and what it left out render together:\n  ' + '\n  '.join(offenders))

    def test_len_of_a_walk_raises(self):
        from agentic_sdlc.core.walk import Walk
        with self.assertRaises(TypeError):
            len(Walk((Path('a'),)))


# --- primitive 3: config through the guards -----------------------------------
# The exact modules that may IMPORT a raw config read (`config_section` /
# `load_config`). Every one of them routes each VALUE through the guards in
# `core/config.py` (`str_tuple`, `str_tuple_table`, `pattern`, `text`) — that
# is what the reviewer checks when a file joins this list. A closed list, not a
# pattern: a new module reading config either goes through a guard and gets
# named here, or it breaks the build. `tuple(cfg.get(...))` over a bare string
# is ('a','d','d','o','n','s','/') — the shape that shipped seven silently
# empty censuses in v0.9.0.
CONFIG_READERS = ('config_section', 'load_config')
CONFIG_OWNER = 'core/config.py'
CONFIG_IMPORT_ALLOWLIST = frozenset((
    CONFIG_OWNER,                 # the guard module itself
    'cli.py',
    'repo/pm/model.py',
    'repo/checks/doc.py',
    'repo/checks/grain_shape.py',
    'repo/checks/repo_hygiene.py',
    'repo/checks/shell.py',
    # `[tests] budget` — a table of tier ceilings, read through `number_table`,
    # which is the guard for exactly this shape. A bare `cfg.get('budget')`
    # would hand back whatever TOML held, and a ceiling that is a STRING
    # compares against a float in a way this gate would report as "under
    # budget" forever: the read-side cardinal sin, in the gate whose whole job
    # is to notice a number getting worse.
    'repo/checks/budget.py',
    # `[checks] all` — the roster `verify --plan` joins against the ledger's
    # gate rows, to say which named gate has never produced a cost. Read
    # through `str_tuple`, which is the guard for a list-of-strings, and NOT
    # through `cli.all_roster`: this package's layers point downward, so
    # `verify` reaching up into the router is the import next door refuses.
    # Validating the NAMES stays the router's job.
    'repo/verify/main.py',
    'repo/gates_extra.py',
    # `[dispatch] project` and `contracts`, read through `text` and
    # `relpath_tuple`. The preamble it renders is the only carrier a dispatched
    # agent's contracts have, so a value that arrived unguarded would be a
    # contract pointer nobody validated — and `contracts` is exactly the
    # list-of-strings a bare read would iterate one CHARACTER at a time.
    'repo/dispatch.py',
    # The conveyor reads `[release] steps`, `[release.commands]` and
    # `[<op>.version_files]`, and every one of those values goes through a
    # refusal before it is used: a step name through `name_defect`, a command
    # through the table check, a version file through the non-empty-table
    # check. A step list silently narrowed by a bad value would be a release
    # protocol that walked past what it was asked to prove — the same shape as
    # a gate roster narrowed by a typo, one altitude up.
    'repo/conveyor/steps.py',
    # `[emit] sink` and `[emit] kinds`, read through `relpath` and `str_tuple`.
    # The sink is the value with the sharpest edge in this package: a string a
    # consumer wrote, one `import_module` away from being a plugin system
    # (0.5.0/D1). It goes through a guard and then it is a PATH and nothing
    # else — `TheToolEmitsAndNeverExecutes` below holds that shut by AST.
    'repo/emit.py',
))
# Calls that build a collection straight from an unguarded value.
COLLECTORS = ('tuple', 'set', 'list', 'frozenset')
# --- primitive 4: import layering ----------------------------------------------
# (directory prefix, module prefixes it must NEVER import, census floor).
# `core/` is the floor — the walk, the writer, the config guards, the markdown
# reader — and it knows about nothing above it; `repo/` sits on `core/` and is
# reached only from the CLI, never the other way round. Two rows because the
# package is two layers deep: an upward import is the architecture running
# backwards, however locally convenient.
LAYER_RULES = (
    ('core/', ('agentic_sdlc.repo', 'agentic_sdlc.cli'), 4),
    ('repo/', ('agentic_sdlc.cli',), 4),
)
PACKAGE = 'agentic_sdlc'
# --- primitive 5: the tool EMITS, and never EXECUTES ---------------------------
# 0.5.0/D1. `repo/emit.py` takes a string a CONSUMER wrote and opens a file with
# it — the one value in this package that is a single `import_module` away from
# being a plugin system, which is the design D1 rejects and the package that
# owns our name on PyPI is the worked example of.
#
# Hard rule 2 — boots nothing, safe anywhere, any time, in parallel — is what
# makes every gate here runnable from a git hook and from CI without a sandbox,
# and ONE verb that spawns a consumer-named command ends that for every verb,
# because a caller can no longer tell which ones are safe.
#
# The pressure it has to survive is one sentence: *"just let the config name a
# command to run."* It is one commit and it will sound reasonable, so it breaks
# the BUILD here rather than resting on a reviewer noticing.
EMIT_MODULE = 'repo/emit.py'
# The closed set of modules the emit path may import. An allowlist rather than a
# ban list, because "imports a module named in config" is not a name you can
# enumerate: what makes it impossible is that the ONLY importable things here
# are five modules written down in this file.
EMIT_IMPORTS = frozenset((
    'sys', 'pathlib', 'typing',
    f'{PACKAGE}.core.config',      # the guards every config value crosses
    f'{PACKAGE}.repo.pm.ledger',   # `dumps`, `append_to`, and the row routing
))
# Calls that turn a STRING into behaviour. `import_module`/`__import__` import
# what a config value named, `eval`/`exec`/`compile` run it, `entry_points` is
# the discovery half of the rejected plugin design, and `getattr`/`setattr` are
# how an imported module becomes a callable.
EXECUTORS = ('eval', 'exec', 'compile', '__import__', 'import_module',
             'entry_points', 'getattr', 'setattr')
# `sys` is on the allowlist for `print(file=sys.stderr)` and nothing else, so a
# SUBSCRIPT on it — `sys.modules['subprocess'].run(...)` — reaches an already
# imported module with no import statement for the allowlist to see. Banned by
# name, because "impossible to route around" has to be literal.
MODULE_MAP_OWNER, MODULE_MAP_ATTR = 'sys', 'modules'
# The `os.<name>` spellings that start a process WITHOUT importing `subprocess`
# — invisible to the `shell` derivation, because none of them imports it.
OS_SPAWNERS = ('system', 'popen', 'execv', 'execve', 'execvp', 'execvpe',
               'execl', 'execle', 'execlp', 'execlpe', 'spawnv', 'spawnve',
               'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'posix_spawn',
               'posix_spawnp', 'fork', 'forkpty', 'startfile')
# What the emit path must still BE, so this class cannot pass over a file that
# was emptied or moved: it appends to a sink and it reads its own section.
EMIT_MUST_CALL = ('append_to', 'config_section')
# (source, is it a route to behaviour) — the classifier graded on what it
# CATCHES rather than on the shipped file being empty, since three assertions
# of emptiness pass perfectly over a guard that stopped seeing anything. The
# last row is the legitimate `sys` use the allowlist exists to keep legal.
EMIT_EXECUTION_SPELLINGS = (
    ("sys.modules['subprocess'].run(cmd)", True),
    ("importlib.import_module(sink).write(row)", True),
    ("entry_points(group=sink)", True),
    ("getattr(mod, sink)()", True),
    ("os.system(cmd)", True),
    ("print(line, file=sys.stderr)", False),
)


def _import_bindings(rel: str, tree: ast.Module) -> list[tuple[str, str, int]]:
    """(bound name, imported dotted source, lineno) for every import.

    `import a.b.c` binds `a`; `from m import x as y` binds `y` from `m.x`. A
    relative import is resolved against the module's own package, so a
    hypothetical `from ..godot import x` cannot dodge the layering rules by
    spelling the target without its prefix.
    """
    package_parts = [PACKAGE] + rel.split('/')[:-1]
    out: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split('.')[0]
                out.append((bound, alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[:len(package_parts) - (node.level - 1)]
                module = '.'.join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ''
            if module == '__future__':
                continue
            for alias in node.names:
                bound = alias.asname or alias.name
                out.append((bound, f'{module}.{alias.name}', node.lineno))
    return out


def _names_config_is_bound_to(tree: ast.Module) -> set[str]:
    """Every name assigned from a bare `config_section(...)`/`load_config(...)`
    call anywhere in the module — `_CFG = config_section('doc')` makes `_CFG`
    an unguarded section, and `tuple(_CFG.get(...))` the same defect one
    statement later."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                and value.func.id in CONFIG_READERS):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        bound.update(t.id for t in targets if isinstance(t, ast.Name))
    return bound


def _is_config_lookup(node: ast.expr, section_names: set[str]) -> bool:
    """True for `config_section(...)`, `load_config(...)`, and a `.get(...)`
    on either of those or on a name bound to one."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id in CONFIG_READERS:
        return True
    if isinstance(func, ast.Attribute) and func.attr == 'get':
        receiver = func.value
        if isinstance(receiver, ast.Name) and receiver.id in section_names:
            return True
        return _is_config_lookup(receiver, section_names)
    return False


def _raw_config_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every import of a RAW config read in this module."""
    return [f'{rel}:{lineno}: imports {bound}'
            for bound, source, lineno in _import_bindings(rel, tree)
            if source.rsplit('.', 1)[-1] in CONFIG_READERS
            and source.startswith(f'{PACKAGE}.core.')]


def _unguarded_collection_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every collection built straight from a config lookup, guard skipped."""
    section_names = _names_config_is_bound_to(tree)
    out: list[str] = []
    for node in _calls(tree):
        if not (isinstance(node.func, ast.Name)
                and node.func.id in COLLECTORS):
            continue
        if any(_is_config_lookup(arg, section_names) for arg in node.args):
            out.append(f'{rel}:{node.lineno}: {node.func.id}(<config lookup>)')
    return out


class ConfigGoesThroughTheGuards(unittest.TestCase):
    """PRIMITIVE 3 — every config VALUE crosses `core/config.py` on its way in."""

    # Graded as a module that is NOT on the allowlist, which is what every
    # module written after this one is.
    CORPUS = (
        ('from agentic_sdlc.core.project import load_config', True),
        ('from agentic_sdlc.core.config import config_section', True),
        ("names = tuple(config_section('doc').get('scope'))", True),
        ("_CFG = config_section('doc')\nnames = tuple(_CFG.get('scope'))", True),
        ("names = set(load_config().get('doc', {}).get('scope'))", True),
        ('from agentic_sdlc.core.config import str_tuple', False),
        ("names = str_tuple(section, 'scope', ())", False),
        ('names = tuple(sorted(found))', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        tree = ast.parse(planted)
        return bool(_raw_config_imports(SCRATCH_MODULE, tree)
                    or _unguarded_collection_sites(SCRATCH_MODULE, tree))

    def test_raw_config_imports_are_allowlisted(self):
        census = {rel for rel, _ in _sources()}
        stale = sorted(CONFIG_IMPORT_ALLOWLIST - census)
        self.assertEqual([], stale,
                         'allowlisted module(s) that no longer exist — an entry '
                         'nothing can match is a hole waiting for a file to '
                         'move into it. Prune:\n  ' + '\n  '.join(stale))
        offenders: list[str] = []
        importers = 0
        for rel, path in _sources():
            hits = _raw_config_imports(rel, _tree(path))
            if hits and rel in CONFIG_IMPORT_ALLOWLIST:
                importers += 1
            elif hits:
                offenders.extend(hits)
        self.assertEqual(
            [], offenders,
            'a raw config read imported outside the allowlist. Config comes in '
            'through the guards in ' + CONFIG_OWNER + ' (`str_tuple` & co) — a '
            'bare `cfg.get` hands back whatever TOML holds, and a string is '
            'iterable:\n  ' + '\n  '.join(offenders))
        # The allowlist must not be vacuously satisfied: most of its members
        # really do import a config read today.
        self.assertGreaterEqual(importers, 6, 'config-importer census collapsed')

    def test_no_collection_is_built_from_an_unguarded_lookup(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == CONFIG_OWNER:
                continue  # the guards themselves collect, AFTER validating
            offenders.extend(_unguarded_collection_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a collection built straight from a config lookup. `tuple(...)` of '
            'a bare string is a tuple of its CHARACTERS — seven gates shipped '
            'a silent PASS that way in v0.9.0. Route the value through a '
            + CONFIG_OWNER + ' guard:\n  ' + '\n  '.join(offenders))


def _dead_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every name this module imports and never reads."""
    # An import binds via `alias` nodes, never `ast.Name` — so every Name in
    # the tree is a READ (or a rebind, which also keeps the import from being
    # deletable without a look).
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == '__all__'
                        for t in node.targets)
                and isinstance(node.value, (ast.List, ast.Tuple))):
            used.update(c.value for c in node.value.elts
                        if isinstance(c, ast.Constant)
                        and isinstance(c.value, str))
    return [f'{rel}:{lineno}: {bound} (from {source})'
            for bound, source, lineno in _import_bindings(rel, tree)
            if bound not in used]


class NoImportIsDead(unittest.TestCase):
    """PRIMITIVE 4a — an import nobody reads is a claim nobody checked.

    Eight dead `load_config` imports survived an extraction because nothing
    made them fail. A name counts as read when it appears as any `ast.Name`
    in the module (annotations included — `from __future__ import annotations`
    keeps them unquoted) or in `__all__` (the `__init__.py` re-export form).
    """

    CORPUS = (
        ('import os', True),
        ('from agentic_sdlc.core.config import str_tuple', True),
        # A name inside a STRING is prose, not a read.
        ("import os\nHELP = 'call os.getcwd()'", True),
        ('import os\nHERE = os.getcwd()', False),
        ('import os.path as osp\nHERE = osp.dirname(x)', False),
        ("from x import y\n__all__ = ['y']", False),
        # Annotations are reads, which is what `from __future__ import
        # annotations` keeps true without quoting them.
        ('from pathlib import Path\n\n\ndef f(p: Path) -> None:\n    pass',
         False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_dead_imports(SCRATCH_MODULE, ast.parse(planted)))

    def test_every_import_is_read(self):
        offenders: list[str] = []
        bindings_seen = 0
        for rel, path in _sources():
            tree = _tree(path)
            bindings_seen += len(_import_bindings(rel, tree))
            offenders.extend(_dead_imports(rel, tree))
        self.assertGreaterEqual(bindings_seen, 100,
                                'import census collapsed — this gate is '
                                'asserting emptiness over nothing')
        self.assertEqual(
            [], offenders,
            'imported and never read. Delete it — or read it, in this same '
            'change:\n  ' + '\n  '.join(offenders))


# A module in the bottom layer, for grading a planted import as `core/` sees it.
CORE_SCRATCH = 'core/scratch_not_a_layer.py'


def _upward_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every import this module makes against the layering."""
    banned = tuple(name for prefix, names, _ in LAYER_RULES
                   if rel.startswith(prefix) for name in names)
    return [f'{rel}:{lineno}: {source}'
            for _, source, lineno in _import_bindings(rel, tree)
            if any(source == b or source.startswith(b + '.') for b in banned)]


class LayersPointDownward(unittest.TestCase):
    """PRIMITIVE 4b — core/ -> repo/ -> cli.py, downward only. An upward
    import is the architecture running backwards, however locally
    convenient."""

    CORPUS = (
        ('from agentic_sdlc.repo import emit', True),
        ('import agentic_sdlc.cli', True),
        ('from agentic_sdlc.repo.pm import model', True),
        # Relative, and resolved against the module's own package — spelling
        # the target without its prefix dodges nothing.
        ('from ..repo import emit', True),
        ('from agentic_sdlc.core import walk', False),
        ('from agentic_sdlc.core.config import str_tuple', False),
        ('import tomllib', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_upward_imports(CORE_SCRATCH, ast.parse(planted)))

    def test_no_layer_imports_upward(self):
        sources = _sources()
        offenders: list[str] = []
        for prefix, banned, floor in LAYER_RULES:
            in_layer = [(rel, path) for rel, path in sources
                        if rel.startswith(prefix)]
            self.assertGreaterEqual(
                len(in_layer), floor,
                f'{prefix} census too small ({len(in_layer)}) — a moved layer '
                'passes this rule by not being scanned')
            for rel, path in in_layer:
                offenders.extend(_upward_imports(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'an import against the layering. A layer imports DOWNWARD only '
            '(core/ -> repo/ -> cli.py; nothing below reaches up):\n  '
            + '\n  '.join(offenders))


def _imported_modules(tree: ast.Module) -> list[tuple[str, str, int]]:
    """(module, module.name, lineno) for every import in the file.

    Two spellings because `from a.b import c` is ambiguous in the syntax: `c`
    is a module in `from agentic_sdlc.repo.pm import ledger` and a function in
    `from agentic_sdlc.core.config import str_tuple`. An allowlist matches
    EITHER, so it can name a package's public face (`agentic_sdlc.core.config`)
    or one module inside it (`agentic_sdlc.repo.pm.ledger`) and mean exactly
    what it says.

    `ast.walk`, not `tree.body`: a deferred `import x` inside a function is
    still an import, and "we only do it lazily" is exactly how a spawn would
    arrive here.
    """
    out: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend((alias.name, alias.name, node.lineno)
                       for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != '__future__':
            module = '.' * node.level + (node.module or '')
            out.extend((module, f'{module}.{alias.name}', node.lineno)
                       for alias in node.names)
    return out


def _execution_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every call in this module that could turn a string into behaviour."""
    out: list[str] = []
    for node in _calls(tree):
        func = node.func
        name = (func.id if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute) else '')
        if name in EXECUTORS:
            out.append(f'{rel}:{node.lineno}: {name}()')
        elif (isinstance(func, ast.Attribute)
              and isinstance(func.value, ast.Name) and func.value.id == 'os'
              and func.attr in OS_SPAWNERS):
            out.append(f'{rel}:{node.lineno}: os.{func.attr}()')
    for node in ast.walk(tree):
        owner = node.value if isinstance(node, ast.Subscript) else None
        if (isinstance(owner, ast.Attribute) and owner.attr == MODULE_MAP_ATTR
                and isinstance(owner.value, ast.Name)
                and owner.value.id == MODULE_MAP_OWNER):
            out.append(f'{rel}:{node.lineno}: '
                       f'{MODULE_MAP_OWNER}.{MODULE_MAP_ATTR}[...]')
    return out


class TheToolEmitsAndNeverExecutes(unittest.TestCase):
    """PRIMITIVE 5 — the emit path writes a sink and does nothing else.

    A sink is opened, appended to, closed. Nothing on this path spawns a
    process, imports a module named in config, or resolves a config string to a
    callable — and that is asserted rather than reviewed, because the change
    that would break it is one line long and reads as a convenience.
    """

    CORPUS = EMIT_EXECUTION_SPELLINGS

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_execution_sites(EMIT_MODULE, ast.parse(planted)))

    def test_the_emit_path_never_spawns_a_process(self):
        """The same question `tests/conftest.py` derives the `shell` mark
        from, asked of a SHIPPED module — plus the `os` spellings that
        derivation cannot see, because none of them imports `subprocess`."""
        self.assertFalse(
            module_spawns(SRC / EMIT_MODULE),
            f'{EMIT_MODULE} reaches `subprocess`. An event is WRITTEN here, '
            f'never run (0.5.0/D1): the moment one verb spawns a '
            f'consumer-named command, no caller can tell which verbs are safe '
            f'to run from a git hook, and hard rule 2 is gone for all of them.')

    def test_the_emit_path_resolves_no_string_to_a_callable(self):
        for source, is_execution in EMIT_EXECUTION_SPELLINGS:
            with self.subTest(source=source):
                sites = _execution_sites(EMIT_MODULE, ast.parse(source))
                self.assertEqual(
                    is_execution, bool(sites),
                    f'{source!r} classified as '
                    f'{"harmless" if is_execution else "a route to behaviour"} '
                    f'— the guard below is only worth what it can still see')
        offenders = _execution_sites(EMIT_MODULE, _tree(SRC / EMIT_MODULE))
        self.assertEqual(
            [], offenders,
            'the emit path can turn a value into behaviour. `[emit] sink` is a '
            'string a CONSUMER wrote; imported, evaluated or looked up in an '
            'entry-point group, it is the plugin system D1 rejected — and the '
            'tool has stopped being a reader/writer and become a runtime that '
            'owns lifecycle, timeouts and error isolation:\n  '
            + '\n  '.join(offenders))

    def test_the_emit_path_imports_only_the_allowlist(self):
        offenders = [f'{EMIT_MODULE}:{lineno}: {dotted}'
                     for module, dotted, lineno in
                     _imported_modules(_tree(SRC / EMIT_MODULE))
                     if module not in EMIT_IMPORTS
                     and dotted not in EMIT_IMPORTS]
        self.assertEqual(
            [], offenders,
            'an import the emit path does not need. The allowlist is the '
            'mechanism: "imports a module named in config" cannot be '
            'enumerated as a ban list, so the only importable things here are '
            'the five written down in EMIT_IMPORTS. Widening it is a '
            'DECISION:\n  ' + '\n  '.join(offenders))

    def test_the_emit_path_is_the_real_one(self):
        """Rule 4's floor: three assertions of emptiness above pass perfectly
        over a file that was emptied, renamed or never written."""
        self.assertIn(EMIT_MODULE, {rel for rel, _ in _sources()},
                      f'{EMIT_MODULE} is not in the census — the class above '
                      f'is asserting emptiness over a module that moved')
        tree = _tree(SRC / EMIT_MODULE)
        called = {func.attr if isinstance(func, ast.Attribute) else
                  func.id if isinstance(func, ast.Name) else ''
                  for func in (node.func for node in _calls(tree))}
        missing = sorted(set(EMIT_MUST_CALL) - called)
        self.assertEqual(
            [], missing,
            f'{EMIT_MODULE} no longer {" or ".join(missing)}s — it is not '
            f'reading a sink out of config and appending to it, so this class '
            f'is policing something that does not happen')


# --- primitive 6: every field of an emitted event is DERIVED -------------------
# 0.5.0/ft-one-event-shape-serves-three-readers. Three taps carry the belts'
# events, and the line the feature is written against is one sentence:
# `next_checks: ["stories-done", "findings-landed"]` is the engine reading its
# own registry back; `suggested_action: "run a review"` is the engine deciding,
# and rule 9 forbids it. The two are indistinguishable in a review of the row
# and trivially distinguishable in the source that mints it, which is why this
# is here rather than in a checklist.
#
# THE RULE: in a minter, a field's VALUE may not be a string this file wrote.
# It comes from a parameter, from the kind constant, or from the clock —
# `''` is admitted because it spells "the tree did not say", never a sentence.
# Keys are excluded (they are the schema); values are not.
EVENT_MINTERS = (
    ('repo/pm/ready_for.py', '_enter_row'),
    ('repo/conveyor/driver.py', 'verdict_row'),
    ('repo/pm/ledger.py', 'leave_row'),
    ('repo/pm/ledger.py', 'lesson_row'),
)

# The guard is a reader, and the way a reader dies is silently, so every shape
# a minter is written in is probed before anything is graded — whole FUNCTIONS,
# because the shape that defeated the first version of this rule was the
# function-level one (E1).
MINTER_SPELLINGS = (
    ("def m():\n return {'kind': KIND, 'rung': rung}", []),
    ("def m():\n return dict(zip(KEYS, (utc_now(), KIND, rung,"
     " nxt.belt if nxt else '')))", []),
    ("def m():\n return [{'path': c.path, 'why': c.why} for c in have]", []),
    ("def m():\n return {'kind': KIND, 'suggested_action': 'run a review'}",
     ['run a review']),
    ("def m():\n return dict(zip(KEYS, (KIND, 'stories-done')))",
     ['stories-done']),
    # `leave_row`'s own shape: built, subscripted, returned by NAME. Graded on
    # the RETURN VALUE these two are indistinguishable and both invisible.
    ("def m():\n row = dict(zip(KEYS, (a, b)))\n row['value'] = said.value"
     "\n return row", []),
    ("def m():\n row = dict(zip(KEYS, (a, b)))"
     "\n row['suggested_action'] = 'run a review'\n return row",
     ['run a review']),
    # A docstring and a refusal are not fields the row carries.
    ('def m():\n """Mint a row."""\n raise ValueError(\'refusing to mint\')',
     []),
    # A module constant is a sentence this file wrote with a name on it (E6).
    ("SUGGESTED = 'run a review'\ndef m():\n"
     " return dict(zip(KEYS, (KIND, SUGGESTED)))", ['run a review']),
    ("KIND_LEAVE = 'rung.leave'\ndef m():\n"
     " return dict(zip(KEYS, (KIND_LEAVE, rung)))", []),
)

# The ONE string source a minter may name: the kind, which IS the schema. Any
# other module constant reaching a value position is a sentence this file
# wrote, so a new kind has to be admitted here BY NAME.
ADMITTED_CONSTANTS = ('KIND_ENTER', 'KIND_VERDICT', 'KIND_LEAVE',
                      'KIND_LESSON')


def _module_strings(tree: ast.AST) -> dict[str, str]:
    """Top-level `NAME = '…'`, minus the kinds: what a bare `Name` in a value
    position resolves to. A dotted `mod.NAME` is another module's schema and is
    not resolved here."""
    found: dict[str, str] = {}
    for node in getattr(tree, 'body', []):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str) and node.value.value):
            continue
        if node.targets[0].id not in ADMITTED_CONSTANTS:
            found[node.targets[0].id] = node.value.value
    return found


def _zip_values(node: ast.AST) -> list[ast.AST] | None:
    """`zip(KEYS, (…))`'s VALUE arguments, or None: the first argument is the
    schema, exactly as a `Dict`'s keys are."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'zip' and len(node.args) > 1):
        return list(node.args[1:])
    return None


def _minted_strings(node: ast.AST, constants: dict[str, str]) -> list[str]:
    """Every string a row's VALUES resolve to. A `Dict`'s keys and a `zip`'s
    key tuple are the schema and are skipped; everything else is walked, so a
    hardcoded sentence inside a comprehension, a conditional or a module
    constant is still seen."""
    found: list[str] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, ast.Dict):
            stack.extend(current.values)
            continue
        keyed = _zip_values(current)
        if keyed is not None:
            stack.extend(keyed)
            continue
        if isinstance(current, ast.Constant):
            if isinstance(current.value, str) and current.value:
                found.append(current.value)
            continue
        if isinstance(current, ast.Name) and current.id in constants:
            found.append(constants[current.id])
            continue
        stack.extend(ast.iter_child_nodes(current))
    return found


def _row_values(func: ast.AST) -> list[ast.AST]:
    """Every expression a minter puts in a VALUE position, anywhere in its
    body: a dict literal's values, `dict(zip(KEYS, …))`'s value tuple, and a
    later `row[key] = …`.

    The BODY, never `ast.Return`'s value — that is E1. `leave_row`'s only
    return is `return row`, a bare Name, so grading return VALUES graded
    nothing in the one minter carrying the next-step fields, and a planted
    `row['suggested_action'] = 'run a review'` was invisible. A docstring and a
    `raise`'s message are in no value position and stay ungraded."""
    found: list[ast.AST] = []
    stack: list[ast.AST] = [func]
    while stack:
        current = stack.pop()
        if isinstance(current, ast.Dict):
            found.extend(current.values)
            continue
        keyed = _zip_values(current)
        if keyed is not None:
            found.extend(keyed)
            continue
        if (isinstance(current, ast.Assign)
                and any(isinstance(t, ast.Subscript)
                        for t in current.targets)):
            found.append(current.value)
            continue
        stack.extend(ast.iter_child_nodes(current))
    return found


def _minted_by(func: ast.AST, constants: dict[str, str]) -> list[str]:
    """What one minter WROTE into its row, sorted: the readers, composed."""
    return sorted(word for value in _row_values(func)
                  for word in _minted_strings(value, constants))


def _graded(source: str) -> list[str]:
    """The whole reader over one module — its constants, then its minter."""
    module = ast.parse(source)
    minter = [n for n in ast.walk(module) if isinstance(n, ast.FunctionDef)][-1]
    return _minted_by(minter, _module_strings(module))


class EveryEventFieldIsDerived(unittest.TestCase):
    """PRIMITIVE 6 — a payload holds what the tree said, never what the tool
    thinks. The same shape as the breadcrumb's guard: assert the TRACE, not the
    sentence, because a hardcoded next-step passes every substring check."""

    # The table above says WHICH words a minter wrote; the corpus asks the one
    # question a blind reader fails — did it see anything at all.
    CORPUS = tuple((source, bool(expected))
                   for source, expected in MINTER_SPELLINGS)

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_graded(planted))

    def test_the_reader_can_still_tell_a_derived_field_from_a_written_one(self):
        for source, expected in MINTER_SPELLINGS:
            with self.subTest(source=source):
                self.assertEqual(expected, _graded(source))

    def test_no_minter_writes_a_field_this_package_decided(self):
        seen = 0
        offenders: list[str] = []
        for rel, name in EVENT_MINTERS:
            tree = _tree(SRC / rel)
            constants = _module_strings(tree)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.FunctionDef)
                        and node.name == name):
                    continue
                seen += 1
                offenders.extend(f'{rel}::{name}: {word!r}'
                                 for word in _minted_by(node, constants))
        self.assertEqual(
            len(EVENT_MINTERS), seen,
            f'{seen} of {len(EVENT_MINTERS)} minters found — one was renamed '
            f'or moved, and this rule is grading what is left')
        self.assertEqual(
            [], offenders,
            'a field an emitted row carries that nothing in the tree said. '
            'Every key must resolve to `[pm.states.*]`, to '
            '`registry_for(operation)` or to a frontmatter field — a value '
            'written here is the engine deciding what should happen next, '
            'which rule 9 forbids and a review would pass:\n  '
            + '\n  '.join(offenders))


# --- primitive 6: config is read PER RUN, never at import ---------------------
# Found 2026-09-05: `repo/checks/doc.py` bound `[doc] scope` and `[doc]
# ephemeral` into module-level constants at import. Once the module was in
# `sys.modules` — which `check all` does, and which any test touching the gate
# roster does — a later run in a repo whose `[doc]` section was MALFORMED used
# the first repo's values and never raised. The gate reported findings, or
# none, where the contract says exit 2.
#
# It passed alone and failed after a peer imported first, which is the worst
# shape a defect can have: the suite's answer depended on its own order.
CONFIG_CALLS = ('config_section', 'load_config')


def _import_time_config_reads(label: str, tree: ast.Module) -> list[str]:
    """`config_section(...)` / `load_config(...)` called at module scope."""
    hits = []
    # TOP LEVEL ONLY. A `def`/`class` body is where these calls BELONG, so a
    # walk that descends into one reports the fix as the defect.
    executable = [n for n in tree.body
                  if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef))]
    for node in executable:
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            name = getattr(inner.func, 'id', None) or getattr(
                inner.func, 'attr', None)
            if name in CONFIG_CALLS:
                hits.append(f'{label}:{inner.lineno}: {name}() at import')
    return hits


def module_level_config_reads(path: Path) -> list[str]:
    """The same reader over a file, with the one thing a snippet cannot have."""
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (OSError, SyntaxError, UnicodeDecodeError):
        # A module this walk cannot READ is a module it cannot clear, so it is
        # reported rather than skipped. (`UNREADABLE` was a name that did not
        # exist: the one branch here that could not itself be exercised raised
        # NameError instead of naming the file.)
        return [f'{path.name}: unreadable — not parsed, so not cleared']
    return _import_time_config_reads(path.name, tree)


class ConfigIsReadPerRunNeverAtImport(unittest.TestCase):
    """PRIMITIVE 6b — nothing binds a config value while it is being imported."""

    CORPUS = (
        ("SCOPE = config_section('doc')", True),
        ("SCOPE = tuple(load_config().get('doc', {}))", True),
        ("if True:\n    SCOPE = config_section('doc')", True),
        # Where these calls BELONG. A walk that descends into a body reports
        # the fix as the defect, so both spellings are probed.
        ("def scope():\n    return config_section('doc')", False),
        ("class C:\n    def scope(self):\n        return load_config()", False),
        ("SCOPE = ('doc', 'ephemeral')", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_import_time_config_reads(SCRATCH_MODULE,
                                              ast.parse(planted)))

    def test_no_module_reads_its_config_at_import_time(self):
        """A config value bound at import is a refusal that fires once per
        process.

        The cwd does not move mid-run in production, and `config_section` is
        `lru_cache`d — so reading inside the function that needs it costs one
        cached lookup and buys the exit-2 contract being true every time rather
        than the first time.
        """
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / 'src').rglob('*.py')):
            if '__pycache__' in path.parts:
                continue
            offenders.extend(module_level_config_reads(path))
        self.assertEqual(
            [], offenders,
            'config read at import — the value is bound to whichever repo '
            'imported the module FIRST, and a malformed section in any later '
            'one stops raising:\n  ' + '\n  '.join(offenders))


# Everything that turns a version string into something ordered or numeric.
VERSION_PARSERS = (
    'packaging', 'pkg_resources', 'distutils', 'LooseVersion',
    'StrictVersion', 'parse_version', 'version_tuple', 'VERSION_RE',
)
# Splitting a version on its SEPARATOR is the shape a comparator grows back
# as; splitting a file on newlines is how you read one, so the ARGUMENT is
# what decides.
VERSION_SEPARATORS = ('.', '-', '+')
ORDERING_CALLS = ('int', 'float', 'sorted', 'max', 'min')


def _version_comparator_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every import in this module of something that orders a version."""
    out: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or '']
        out.extend(f'{rel}: imports {name}' for name in names
                   if name.split('.')[0] in VERSION_PARSERS)
    return out


def _version_split_sites(label: str, func: ast.AST) -> list[str]:
    """Every place inside one function that takes a version APART."""
    out: list[str] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == 'split'
                and any(isinstance(a, ast.Constant)
                        and a.value in VERSION_SEPARATORS for a in node.args)):
            out.append(f'{label} splits on a version separator')
        if (isinstance(node.func, ast.Name)
                and node.func.id in ORDERING_CALLS):
            out.append(f'{label} calls {node.func.id}()')
    return out


class NoCodePathParsesAVersion(unittest.TestCase):
    """0.3.0: order is a DECLARED list, so the engine never reads a version
    string as a structure.

    The claim `a-milestone-declares-its-version` makes to consumers is that
    `"1.1.1"` and `"cow"` are equally valid — scheme-agnosticism as a
    consequence of ordering by position rather than as a promise. A comparator
    creeping back in would break every tree whose versions are not semver
    (`0.90.3.2` is the real one that motivated this), and it would do it
    silently, by sorting wrong rather than by raising.

    This is a source-shaped gate because the behaviour it protects is an
    ABSENCE, and an absence has no call site to assert against.
    """

    CORPUS = (
        ('import packaging', True),
        ('from distutils.version import LooseVersion', True),
        ('from packaging.version import parse as parse_version', True),
        ("def bumped(v):\n    return v.split('.')[0]", True),
        ('def bumped(v):\n    return int(v)', True),
        ('def bumped(order):\n    return sorted(order)[-1]', True),
        ('import re', False),
        ("def read(text):\n    return text.splitlines()", False),
        ("def read(text):\n    return text.split('\\n')", False),
        ('def bumped(order, v):\n    return order.index(v) + 1', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        tree = ast.parse(planted)
        return bool(_version_comparator_imports(SCRATCH_MODULE, tree)
                    or any(_version_split_sites(SCRATCH_MODULE, node)
                           for node in ast.walk(tree)
                           if isinstance(node, (ast.FunctionDef,
                                                ast.AsyncFunctionDef))))

    def test_no_module_imports_a_version_comparator(self):
        offenders = []
        for rel, path in _sources():
            offenders.extend(_version_comparator_imports(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a version comparator was imported — order is a POSITION in '
            '`order`, and a comparator cannot sort `0.90.3.2` anyway')

    def test_the_release_helpers_never_split_a_version_into_components(self):
        """The modules that HANDLE versions do not take one apart.

        Scoped to the release surface rather than to all of `src`: `.split('.')`
        is how every module reads a dotted grain id, and a repo-wide ban would
        be a gate nobody could keep green. The census floor below is what keeps
        the narrowing honest.
        """
        surface = {
            'repo/pm/model.py': ('releases_file', 'declared_order',
                                 'milestone_version', 'version_claims',
                                 'milestone_of_version', 'entry_is_shipped',
                                 'entry_is_dangling', 'current_release',
                                 'current_milestone',
                                 # Review F4: the two likeliest regrowth sites.
                                 # Both READ a version out of a file, which is
                                 # one step from taking one apart.
                                 'shipped_version'),
            'repo/checks/pm.py': ('_release_findings',),
            'repo/conveyor/steps.py': ('check_version_sync', '_version_in'),
        }
        by_rel = {rel: path for rel, path in _sources()}
        offenders, scanned = [], 0
        for rel, wanted in surface.items():
            self.assertIn(rel, by_rel, f'{rel} moved — this gate now scans nothing')
            found = {n.name: n for n in ast.walk(_tree(by_rel[rel]))
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for name in wanted:
                self.assertIn(name, found,
                              f'{rel}:{name} is gone — rename it here too, or '
                              f'this gate silently stops checking it')
                scanned += 1
                # The argument is what decides, not the call — otherwise the
                # gate could not cover `shipped_version`, which is exactly
                # where a parser would reappear.
                offenders.extend(_version_split_sites(f'{rel}:{name}',
                                                      found[name]))
        # Rule 4: a gate scanning nothing FAILS rather than passing quietly.
        self.assertGreaterEqual(scanned, 11,
                                'the release surface collapsed — this gate is '
                                'asserting emptiness over almost nothing')
        self.assertEqual([], offenders,
                         'a release helper took a version apart — "did it '
                         'increase" is a position in `order`, never a parse')


# --- primitive 7: one project, said the same way in both files -----------------
# `bg-the-package-docstring-names-another-project`. `src/agentic_sdlc/__init__.py`
# is two lines, and the first one was about a different project: headless scene
# introspection for a game engine, copied from the sibling repo this package was
# extracted from and shipped in every release since. It is the MODULE docstring,
# so it is what `help(agentic_sdlc)` prints and the first thing a reader opening
# the package sees.
#
# `[project] description` held the true sentence the whole time — one fact stored
# twice, in disagreement, with nothing that could say so out loud. That is hard
# rule 7's shape one altitude up: `__version__` and `version` move together
# because a gate makes them, and these two do now as well.
#
# THE RULE, both directions, with neither sentence written down in this file:
#   * the docstring NAMES this package — every word of `[project] name` is in it;
#   * and it names nothing else — every word IT uses is a word `[project] name`
#     or `[project] description` already uses.
#
# A subset rather than a ban list, for the reason `EMIT_IMPORTS` is one: "a
# sentence about somebody else's project" is not a vocabulary anybody can
# enumerate, and a roster of foreign project names would be this package knowing
# about a repo that is not it (rule 8). What makes the drift impossible is that
# the only words admitted here are the ones the description already chose —
# widening the docstring means widening the description in the same change,
# which is the two sites moving together, which is the whole point.
PYPROJECT = REPO_ROOT / 'pyproject.toml'
PROJECT_TABLE = 'project'
NAME_FIELD = 'name'
DESCRIPTION_FIELD = 'description'
PACKAGE_INIT = '__init__.py'
# Floors, in the spirit of MIN_SOURCES: a subset test passes perfectly over an
# empty docstring, and over a description nobody wrote. Both sit well under what
# is really there (20 and 40 distinct words) and well over zero.
MIN_DOCSTRING_WORDS = 10
MIN_DESCRIPTION_WORDS = 20
# (sentence, vocabulary, the words the vocabulary never used). Graded against a
# SYNTHETIC vocabulary, so the reader is proven on what it CATCHES without
# pinning the probe to whatever `[project] description` happens to say. The
# foreign sentence names a SHAPE and never a repo (rule 8).
DOCSTRING_SPELLINGS = (
    ('gizmo — a tracker and its gate.', 'gizmo a tracker and its gate', []),
    ('gizmo — headless scene introspection for a game engine.',
     'gizmo a tracker and its gate',
     ['engine', 'for', 'game', 'headless', 'introspection', 'scene']),
    # Case is not a hiding place, and neither is a hyphen: a compound word is
    # its parts, so `markdown-and-frontmatter` cannot carry a foreign name past
    # the comparison by being punctuated into one token.
    ('GIZMO — a TRACKER, and its gate.', 'gizmo a tracker and its gate', []),
    ('a markdown-and-frontmatter tracker.',
     'a markdown and frontmatter tracker', []),
    ('gizmo — a tracker, 4.x.', 'gizmo a tracker', ['x']),
)


def _words(text: str) -> set[str]:
    """The alphabetic words of a sentence, case-folded."""
    return set(re.findall(r'[a-z]+', text.lower()))


def _foreign_words(sentence: str, vocabulary: str) -> list[str]:
    """Every word `sentence` uses that `vocabulary` never does, sorted."""
    return sorted(_words(sentence) - _words(vocabulary))


def _package_docstring() -> str | None:
    """What `help(agentic_sdlc)` prints, read from the shipped file.

    By AST rather than by import, like everything else here: the docstring is a
    literal in the source, so reading it this way boots nothing (rule 2) and is
    exactly the sentence a reader opening the file gets.
    """
    return ast.get_docstring(_tree(SRC / PACKAGE_INIT))


def _project_naming_fields() -> tuple[str, str]:
    """(`[project] name`, `[project] description`) from the real pyproject.toml.

    READ, never restated. A copy of either sentence in this file would be the
    THIRD copy, and a third copy drifts exactly the way the second one did.
    """
    with PYPROJECT.open('rb') as handle:
        table = tomllib.load(handle)[PROJECT_TABLE]
    return table[NAME_FIELD], table[DESCRIPTION_FIELD]


class TheDocstringAndTheDescriptionNameOneProject(unittest.TestCase):
    """PRIMITIVE 7 — the package describes itself the same way in both files.

    The sentence was wrong for four releases and no gate could have said so:
    `check doc` holds this repo's prose to its make-target and file-path claims,
    and its scope is markdown, while a docstring is prose making a claim about
    what the package IS from inside a `.py` file. Nothing was pointed at it.
    """

    # This reader takes TWO strings, so a planted case is the pair. The gate
    # replaying it hands `catches` whatever the guard put here and reads
    # nothing into it.
    CORPUS = tuple(((sentence, vocabulary), bool(expected))
                   for sentence, vocabulary, expected in DOCSTRING_SPELLINGS)

    @staticmethod
    def catches(planted: tuple[str, str]) -> bool:
        sentence, vocabulary = planted
        return bool(_foreign_words(sentence, vocabulary))

    def test_the_reader_names_the_words_a_vocabulary_never_used(self):
        """The comparison is only worth what it can still see: three assertions
        of emptiness pass perfectly over a reader that stopped comparing."""
        for sentence, vocabulary, expected in DOCSTRING_SPELLINGS:
            with self.subTest(sentence=sentence):
                self.assertEqual(expected, _foreign_words(sentence, vocabulary))

    def test_the_docstring_names_this_package_and_no_other(self):
        docstring = _package_docstring()
        name, description = _project_naming_fields()
        self.assertIsNotNone(
            docstring,
            f'{PACKAGE_INIT} has no module docstring — `help(agentic_sdlc)` '
            f'prints nothing, and an absence is a finding (rule 11)')
        self.assertGreaterEqual(
            len(_words(docstring)), MIN_DOCSTRING_WORDS,
            f'{len(_words(docstring))} distinct word(s) in the docstring — a '
            f'subset check over a sentence this short is a gate that checks '
            f'nothing')
        self.assertGreaterEqual(
            len(_words(description)), MIN_DESCRIPTION_WORDS,
            f'{len(_words(description))} distinct word(s) in [project] '
            f'description — the vocabulary below would admit almost anything')
        self.assertEqual(
            [], _foreign_words(name, docstring),
            'the module docstring does not name this package. `help()` opens '
            'with it, so it says what the thing IS, starting with what it is '
            'called')
        self.assertEqual(
            [], _foreign_words(docstring, f'{name} {description}'),
            'the module docstring uses words [project] description never does. '
            'One fact, two files: a sentence here that pyproject.toml does not '
            'support is the second copy drifting — this one shipped four '
            'releases describing a different project. Say it in the '
            "description's words, or widen the description in this same change")


# --- primitive 8: no test points `git` at THIS checkout ------------------------
# `bg-the-suite-can-flip-the-host-repo-to-bare`. Twice on 2026-09-06 a full-suite
# run left the real checkout's `.git/config` holding `bare = true`, after which
# every git command in the worktree failed with *fatal: this operation must be
# run in a work tree*. No commits were lost and no module reproduced it alone:
# each git-spawning module was run on its own against this checkout with
# `.git/config` hashed either side, and all six left it unchanged. All three
# occurrences happened while subagents ran their own test processes against this
# same worktree.
#
# THIS GATE NAMES NO CAUSE, and the bug is filed unresolved on purpose. It
# removes the PRECONDITION instead: whatever rewrites `.git/config`, it is a
# `git` process pointed at this repository, and a suite that never points one
# here cannot be the writer however the race is shaped. That is assertable from
# source, which a race is not.
#
# A spawn reaches this checkout in four ways and every one of them is visible in
# the syntax:
#   * no `cwd=` at all — the call runs wherever pytest was started, which is the
#     repo root. That was the one real offender: `git init -q --bare <path>`,
#     a verb whose whole job is writing a `.git/config`, spawned loose;
#   * a `cwd=` rooted at this file tree;
#   * `GIT_DIR`/`GIT_WORK_TREE` in `env=`, and `-C`/`--git-dir`/`--work-tree` in
#     the argv. Both OUTRANK `cwd=`, so neither can be read as a confinement —
#     they are banned outright rather than checked against a target this file
#     cannot resolve. `cwd=` already says where a git command runs, and one
#     mechanism is the point.
TESTS_DIR = REPO_ROOT / 'tests'
# Floors in the spirit of MIN_SOURCES: this gate asserts an EMPTY offender list,
# and an empty list is what a moved `tests/` produces too. Both sit well under
# what is really there (56 modules and 48 `git` call sites at the time of
# writing) and well over zero.
MIN_TEST_MODULES = 30
MIN_GIT_SPAWNS = 20
# The one module a spawn crosses, and the constructors that reach it. Spelled
# the way `tests/conftest.py` derives the `shell` mark — `subprocess.<attr>` —
# so the tier definition and this boundary police one chokepoint.
SPAWN_MODULE = 'subprocess'
SPAWNERS = ('run', 'Popen', 'call', 'check_output', 'check_call')
GIT = 'git'
# What `tests/support` calls a path inside this checkout. A `cwd=` naming any of
# them is the host repository: git discovers upward, so `tests/fixtures` is this
# repository exactly as the root is.
SUPPORT_ROOTS = ('REPO_ROOT', 'TESTS', 'FIXTURES', 'SUPPORT')
SUPPORT_PACKAGES = ('support', 'conftest')
# The other way a module names itself: anything derived from its own `__file__`
# is under `tests/`, whatever it is called locally (`REPO`, `ROOT`, …). Derived
# rather than rostered, because a roster of variable NAMES goes stale silently
# and the next spelling would walk straight past it.
FILE_ANCHOR = '__file__'
GIT_LOCATION_ENV = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR',
                    'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY')
GIT_LOCATION_FLAGS = ('-C', '--git-dir', '--work-tree')
NO_CWD = 'no cwd='
HOST_CWD = 'cwd= names this checkout'


def _test_sources() -> list[tuple[str, Path]]:
    """(repo-relative posix path, file) for every module under `tests/`.

    Through `core.walk` for the reason `_sources()` is: a gate that hand-rolled
    an `rglob` to police the suite would be policing itself with the thing it
    bans one directory over.
    """
    from agentic_sdlc.core import walk as walkmod
    from agentic_sdlc.core.walk import Kind
    found = walkmod.descendants(TESTS_DIR, Kind.FILE, suffix='.py')
    out = [(p.relative_to(REPO_ROOT).as_posix(), p) for p in found.kept]
    assert len(out) >= MIN_TEST_MODULES, (
        f'{len(out)} test module(s) under {TESTS_DIR} — expected at least '
        f'{MIN_TEST_MODULES}. The gate below asserts an EMPTY offender list, so '
        f'a census this small passes it while checking nothing.')
    return out


def _argv0(node: ast.Call) -> str | None:
    """The program a spawn runs, when the syntax says so.

    `['git', …]` and `('git', …)` are the list forms; a bare `'git status'` is
    the `shell=True` one. Anything else — `[sys.executable, …]`, `[exe, *argv]`
    — is not a `git` call this file can identify, and is not counted as one.
    """
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
        head = first.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
        return None
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        words = first.value.split()
        return words[0] if words else None
    return None


def _own_scope(node: ast.AST):
    """Every node under `node` that belongs to `node`'s OWN scope.

    Descent stops at a nested `def`/`class`, because its names are its own. A
    walk that did not stop there put every `other = parent / name` in the module
    into one namespace, and one function's `source = REPO_ROOT / …` then made
    `cwd=other` in an unrelated helper read as this checkout — a gate reporting
    a call that was already correct, which is rule 4's other half.
    """
    stack = list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        yield current
        if not isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(current))


def _host_rooted_names(scope: ast.AST, inherited: frozenset[str]) -> set[str]:
    """`inherited`, plus the names THIS scope roots in the checkout.

    Two seeds and a fixpoint, the shape `support_spawn_names()` uses in
    `tests/conftest.py`: a `SUPPORT_ROOTS` name imported from `support`, and an
    assignment whose value mentions `__file__`. Then repeat, so
    `SRC = REPO_ROOT / 'src'` joins on the pass after `REPO_ROOT` does.
    """
    names = set(inherited)
    assignments: list[ast.Assign | ast.AnnAssign] = []
    for node in _own_scope(scope):
        if isinstance(node, ast.ImportFrom) and (
                (node.module or '').split('.')[0] in SUPPORT_PACKAGES):
            names.update(alias.asname or alias.name for alias in node.names
                         if alias.name in SUPPORT_ROOTS)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value:
            assignments.append(node)
    changed = True
    while changed:
        changed = False
        for node in assignments:
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            bound = {t.id for t in targets if isinstance(t, ast.Name)}
            if bound <= names or not _is_host_rooted(node.value, names):
                continue
            names |= bound
            changed = True
    return names


def _is_host_rooted(node: ast.expr, names: set[str]) -> bool:
    """True when this expression is built from this module's own file or from a
    name already known to hold a path inside the checkout."""
    return any(isinstance(inner, ast.Name)
               and (inner.id == FILE_ANCHOR or inner.id in names)
               for inner in ast.walk(node))


def _leading_literal(node: ast.expr) -> str | None:
    """The literal an argv element STARTS with, through the two spellings a
    computed one takes: `'--git-dir=' + d` and `f'--git-dir={d}'`. The flag is
    what decides, and it is a constant in all three."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _leading_literal(node.left)
    if isinstance(node, ast.JoinedStr) and node.values:
        return _leading_literal(node.values[0])
    return None


def _reaches_the_host(node: ast.Call, names: set[str]) -> list[str]:
    """Why this `git` spawn is pointed at this checkout; empty when it is not.

    All four reasons are collected rather than the first one returned: a call
    fixed by adding `cwd=` while it still exports `GIT_DIR` has moved the
    problem, and a reader has to see both lines to know that.
    """
    keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
    why: list[str] = []
    cwd = keywords.get('cwd')
    if cwd is None:
        why.append(NO_CWD)
    elif _is_host_rooted(cwd, names):
        why.append(HOST_CWD)
    env = keywords.get('env')
    if isinstance(env, ast.Dict):
        why.extend(f'env= sets {key.value}' for key in env.keys
                   if isinstance(key, ast.Constant)
                   and key.value in GIT_LOCATION_ENV)
    argv = node.args[0] if node.args else None
    if isinstance(argv, (ast.List, ast.Tuple)):
        for element in argv.elts:
            literal = _leading_literal(element)
            flag = literal.split('=')[0] if literal else None
            if flag in GIT_LOCATION_FLAGS:
                why.append(f'argv carries {flag}')
    return why


def _is_a_git_spawn(node: ast.Call) -> bool:
    """`subprocess.<spawner>(['git', …])` — the module spelled the way
    `tests/conftest.py` derives the `shell` mark from, so the tier and this
    boundary read one mechanism rather than two."""
    func = node.func
    return (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
            and func.value.id == SPAWN_MODULE and func.attr in SPAWNERS
            and _argv0(node) == GIT)


def _git_spawn_sites(tree: ast.Module) -> list[tuple[int, list[str]]]:
    """(lineno, reasons) for every `git` spawn in one module, scope by scope.

    Both halves matter and both are graded: what this counts as a `git` spawn at
    all, and which of those it says reach the host. A classifier that stopped
    seeing `git` would report an empty offender list forever.
    """
    out: list[tuple[int, list[str]]] = []

    def visit(scope: ast.AST, inherited: frozenset[str]) -> None:
        names = _host_rooted_names(scope, inherited)
        for node in _own_scope(scope):
            if isinstance(node, ast.Call) and _is_a_git_spawn(node):
                out.append((node.lineno, _reaches_the_host(node, names)))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)):
                visit(node, frozenset(names))

    visit(tree, frozenset())
    return sorted(out)


# (source, what the classifier must say) — the confined spellings this suite is
# already written in, the four ways a spawn reaches this checkout, and the
# spawns that are not `git` at all and must stay uncounted. `[[]]` is one git
# call with nothing against it; `[]` is no git call found.
GIT_SPAWN_SPELLINGS = (
    # Confined: a directory this file can see is not the checkout.
    ("subprocess.run(['git', 'init', '-q'], cwd=root, check=True)", [[]]),
    ("subprocess.run(['git', 'status'], cwd=tmp_path / 'x')", [[]]),
    ("subprocess.check_output(['git', 'log'], cwd=repo.root)", [[]]),
    ("subprocess.run(('git', 'add', '-A'), cwd=other, check=True)", [[]]),
    # Loose: the pytest process stands in the repo root, so this IS the host.
    ("subprocess.run(['git', 'status'])", [[NO_CWD]]),
    ("subprocess.run(['git', 'init', '-q', '--bare', str(o)], check=True)",
     [[NO_CWD]]),
    ("subprocess.Popen(['git', 'gc'])", [[NO_CWD]]),
    ("subprocess.run('git status', shell=True)", [[NO_CWD]]),
    # Named, and the name is this checkout — by import or by `__file__`.
    ("from support import REPO_ROOT\nsubprocess.run(['git', 'gc'],"
     " cwd=REPO_ROOT)", [[HOST_CWD]]),
    ("REPO = Path(__file__).resolve().parents[1]\n"
     "subprocess.run(['git', 'gc'], cwd=REPO)", [[HOST_CWD]]),
    # One hop further out: a name built from a name built from `__file__`.
    ("REPO = Path(__file__).parent\nWORK = REPO / 'sub'\n"
     "subprocess.run(['git', 'gc'], cwd=WORK)", [[HOST_CWD]]),
    # The overrides, which outrank `cwd=` and so cannot be excused by one.
    ("subprocess.run(['git', 'gc'], cwd=tmp, env={'GIT_DIR': str(tmp)})",
     [['env= sets GIT_DIR']]),
    ("subprocess.run(['git', 'gc'], cwd=tmp,"
     " env={'GIT_WORK_TREE': str(tmp)})", [['env= sets GIT_WORK_TREE']]),
    ("subprocess.run(['git', '-C', str(tmp), 'status'], cwd=tmp)",
     [['argv carries -C']]),
    ("subprocess.run(['git', '--git-dir=' + d, 'status'], cwd=tmp)",
     [['argv carries --git-dir']]),
    ("subprocess.run(['git', f'--work-tree={d}', 'status'], cwd=tmp)",
     [['argv carries --work-tree']]),
    # Every reason at once, and every one of them named: a call fixed halfway
    # is a call still pointed here.
    ("from support import REPO_ROOT\n"
     "subprocess.run(['git', '-C', d, 'gc'], cwd=REPO_ROOT,"
     " env={'GIT_DIR': d})",
     [[HOST_CWD, 'env= sets GIT_DIR', 'argv carries -C']]),
    # Not `git`, and this gate does not widen into the rest of the suite:
    # `make` against REPO_ROOT is what test_makefile_gates.py IS.
    ("subprocess.run(['make', 'check'], cwd=REPO_ROOT)", []),
    ("subprocess.run([sys.executable, '-m', 'agentic_sdlc.cli'])", []),
    ("subprocess.run(['bash', str(hook)], input=event)", []),
    # An argv this file cannot read is not a `git` call it can name. Stated
    # rather than implied: it is the honest limit of an AST, the same one
    # `_replace_is_a_path_replace` runs into.
    ("subprocess.run([exe, 'status'])", []),
)


class NoTestSpawnsGitAgainstThisCheckout(unittest.TestCase):
    """PRIMITIVE 8 — every `git` in this suite runs in a scratch tree.

    Not "no test corrupts the repo", which is a hope. The assertion is
    syntactic and total: a `git` spawn either names a directory that is not this
    checkout, or it is a finding by `file:line`.
    """

    # `[[]]` is one git call with nothing against it — a CLEAN case that is
    # not an empty result, which is why "caught" is the guard's own word here
    # rather than the truthiness of what its reader returned.
    CORPUS = tuple((source, any(reasons for reasons in expected))
                   for source, expected in GIT_SPAWN_SPELLINGS)

    @staticmethod
    def catches(planted: str) -> bool:
        return any(reasons for _, reasons
                   in _git_spawn_sites(ast.parse(planted)))

    def test_the_classifier_can_still_tell_a_confined_spawn_from_a_loose_one(self):
        for source, expected in GIT_SPAWN_SPELLINGS:
            with self.subTest(source=source):
                graded = [reasons for _, reasons in
                          _git_spawn_sites(ast.parse(source))]
                self.assertEqual(expected, graded)

    def test_no_test_module_spawns_git_against_this_checkout(self):
        offenders: list[str] = []
        for rel, path in _test_sources():
            offenders.extend(
                f'{rel}:{lineno}: {reason}'
                for lineno, reasons in _git_spawn_sites(_tree(path))
                for reason in reasons)
        self.assertEqual(
            [], offenders,
            'a `git` spawn pointed at THIS checkout. A full-suite run twice '
            'left `.git/config` holding `bare = true`, and the cause was never '
            'established — so the precondition goes instead: every `git` in '
            'this suite names a scratch directory with `cwd=`, and none of them '
            'inherits this repository, exports GIT_DIR at it, or reaches it '
            'with `-C`:\n  ' + '\n  '.join(offenders))

    def test_the_git_census_is_the_real_suite(self):
        """Rule 4's floor. The case above asserts an EMPTY list, and empty is
        also what a renamed `tests/`, a moved `subprocess` spelling or a
        classifier that stopped recognising `git` all produce."""
        modules = _test_sources()
        spawns = [(rel, lineno) for rel, path in modules
                  for lineno, _ in _git_spawn_sites(_tree(path))]
        self.assertGreaterEqual(
            len(spawns), MIN_GIT_SPAWNS,
            f'{len(spawns)} `git` spawn(s) across {len(modules)} test '
            f'module(s) — expected at least {MIN_GIT_SPAWNS}. A boundary over '
            f'calls nobody makes is a boundary that holds nothing shut.')
        self.assertGreaterEqual(
            len({rel for rel, _ in spawns}), 5,
            f'{len({rel for rel, _ in spawns})} module(s) spawn `git` — the '
            f'integration tier collapsed, or the census stopped seeing it')
