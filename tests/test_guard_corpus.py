"""test_guard_corpus.py — a guard declares the violations it must catch, and
this replays them.

`tests/test_boundaries.py` and its peers police this package's own source by
walking an AST: one walk, one apply, config through the guards, layers pointing
downward, the tool emits and never executes, every event field derived, no
`git` pointed at this checkout. Every one of them asserts an EMPTY offender
list — and an empty list is also what a reader that stopped reading produces.

0.5.0 shipped exactly that. A derived-field guard walked `ast.Return` in a
function whose only return is a bare name, so a planted `suggested_action` was
invisible while the guard reported 4-of-4, and the count was handed to the
orchestrator as proof the property held. Rule 4's first cardinal sin, running
green, inside the file that exists to prevent it.

**The shape is the hook corpus's, one layer over.** `tools/hooks/prepare-commit-msg`
declares its own cases behind `--self-test`; `check hooks` derives from each
hook's TEXT which ones declare a corpus, replays them, counts them, and calls
zero replays a finding. Here a guard declares two names:

    CORPUS   — ((planted, must this guard catch it), ...). `planted` is
               whatever that guard's own reader takes: usually a source
               snippet, sometimes a pair of them.
    catches  — the guard's REAL classifier over one planted input, answering
               the one question that matters when a reader goes blind: did it
               see this.

and this module derives the roster from source, replays every declared corpus
case by case, and holds the guards that declare nothing as a named roster that
can only shrink. A corpus with no violation case is the analogue of a hook that
names `--self-test` and never prints `SELF-TEST OK`: it cannot fail when the
guard stops grading, which is the whole defect.

**The population is AST-SHAPED guards, and that narrowing is deliberate.** A
guard whose grading reaches `ast.parse` classifies syntax, and a classifier can
visit the wrong node type while still reporting a count. A guard that compares
bytes or greps a shipped file either matches or does not. Guards that read
shipped text without parsing it are outside this census and are not counted
here; so is a guard reaching a reader in ANOTHER module, which source in this
file cannot resolve. Both are the honest limit of a single-module AST walk,
stated rather than implied.
"""
from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path
from typing import NamedTuple

from support import REPO_ROOT

TESTS = REPO_ROOT / 'tests'
MODULE_GLOB = 'test_*.py'

# The two names a guard declares. Both are required: a table nothing runs
# proves nothing, and a replay with no table is a hook that names `--self-test`
# and has no cases behind it.
CORPUS_ATTR = 'CORPUS'
REPLAY_ATTR = 'catches'

# What makes a guard AST-shaped. `ast.parse` on the receiver, so a docstring
# that says the words is not a call — the same distinction the guards below are
# built on.
PARSE_OWNER = 'ast'
PARSE_CALL = 'parse'
TEST_PREFIX = 'test'

# The module name a planted corpus case is graded as. Not a real module: the
# gate is being MUTATED here, not observed.
PLANTED_MODULE = 'planted_guard.py'

# Floors in the spirit of `MIN_SOURCES`: every case below asserts an EMPTY
# offender list, and empty is what a moved `tests/` produces too. All three sit
# well under what is really there (56 modules, 30 AST-shaped guards, 155
# replayed cases at the time of writing) and well over zero.
MIN_MODULES = 30
MIN_GUARDS = 20
MIN_CASES = 40

# AST-shaped guards that declare no corpus, exactly. Two directions, because a
# roster that only grows is a TODO list and a roster that only shrinks is a
# tripwire: a guard missing from here breaks the build until it brings a
# corpus, and a guard listed here that has since gained one breaks it until the
# line is deleted. Every entry is an absence with a name on it (rule 11), and
# the list is the work queue.
#
# The fifteen below live in test modules this feature did not own. Each is
# fixed the same way: give the class a `CORPUS` and a `catches`, and delete its
# line from here.
UNCOVERED = frozenset((
    'test_config_seed.py::test_every_commented_default_in_the_seed_is_the_codes_own_default',
    'test_config_seed.py::test_pm_config_is_reachable_from_the_cli',
    'test_config_seed.py::test_the_census_reads_every_module_that_reads_config',
    'test_config_seed.py::test_the_seeds_declarations_are_the_keys_with_nothing_behind_them',
    'test_conveyor_lessons.py::test_every_match_prints_in_recorded_order_and_nothing_ranks_them',
    'test_conveyor_lessons.py::test_the_ranking_reader_tells_a_stamp_from_a_ranking',
    'test_grain_shape.py::test_the_slot_names_have_one_source',
    'test_init_verb.py::test_the_preflight_carries_exactly_one_refusal',
    'test_pm_flow.py::test_no_state_literal_survives_outside_the_seed',
    'test_pm_flow.py::test_the_belts_spell_no_state_word',
    'test_pm_flow.py::test_the_seeds_exported_words_have_exactly_the_named_readers',
    'test_prose_census.py::test_comments_and_docstrings_are_under_a_third_of_the_code',
    'test_shell_mark.py::Census',
    'test_shell_mark.py::NoUnreadSpawnSpelling',
    'test_verify_rules.py::TheModuleReadsNoFileAndSpawnsNothing',
))


class Guard(NamedTuple):
    """One test class or module-level test function, and what it declares."""

    module: str
    name: str
    lineno: int
    shaped: bool
    corpus: bool
    replay: bool

    @property
    def id(self) -> str:
        return f'{self.module}::{self.name}'

    @property
    def covered(self) -> bool:
        return self.corpus and self.replay


def _parses(node: ast.AST) -> bool:
    """Does anything under `node` call `ast.parse`?"""
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == PARSE_CALL
               and isinstance(n.func.value, ast.Name)
               and n.func.value.id == PARSE_OWNER
               for n in ast.walk(node))


def _named(node: ast.AST) -> set[str]:
    """Every bare name under `node` — how a guard reaches its helpers."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _readers(tree: ast.Module) -> set[str]:
    """The module-level helpers whose grading reaches `ast.parse`.

    A fixpoint, because `_graded` calls `_minted_by` calls `_row_values`: the
    guard names the outermost one and the parse is three hops down.
    """
    helpers = {node.name: node for node in tree.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    readers = {name for name, node in helpers.items() if _parses(node)}
    while True:
        grown = readers | {name for name, node in helpers.items()
                           if _named(node) & readers}
        if grown == readers:
            return readers
        readers = grown


def _assigned(stmt: ast.stmt) -> set[str]:
    if isinstance(stmt, ast.Assign):
        return {t.id for t in stmt.targets if isinstance(t, ast.Name)}
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return {stmt.target.id}
    return set()


def _holds_tests(node: ast.ClassDef) -> bool:
    return any(isinstance(s, ast.FunctionDef) and s.name.startswith(TEST_PREFIX)
               for s in node.body)


def _guards(module: str, tree: ast.Module) -> list[Guard]:
    """Every guard in one test module, with what it declares.

    A guard is a top-level test CLASS or a top-level `test_*` function. It is
    AST-shaped when its own text calls `ast.parse` or names a helper that
    reaches one. Only a class can declare — a bare function has nowhere to hang
    a corpus, which is itself the finding.
    """
    readers = _readers(tree)
    out: list[Guard] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not _holds_tests(node):
                continue
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith(TEST_PREFIX):
                continue
        else:
            continue
        corpus = replay = False
        if isinstance(node, ast.ClassDef):
            corpus = any(CORPUS_ATTR in _assigned(s) for s in node.body)
            replay = any(isinstance(s, ast.FunctionDef)
                         and s.name == REPLAY_ATTR for s in node.body)
        out.append(Guard(module, node.name, node.lineno,
                         _parses(node) or bool(_named(node) & readers),
                         corpus, replay))
    return out


def _modules() -> list[Path]:
    return sorted(TESTS.glob(MODULE_GLOB))


def _roster() -> list[Guard]:
    """Every guard under `tests/`, read from source and never imported."""
    return [guard for path in _modules()
            for guard in _guards(path.name,
                                 ast.parse(path.read_text(encoding='utf-8')))]


def _declared(guard: Guard) -> tuple[tuple, object]:
    """One guard's corpus and its replay, imported.

    The only import this module does, and only for a guard that declares both —
    the roster itself is read from source, so a module that declares nothing is
    never loaded to find that out.
    """
    owner = getattr(importlib.import_module(Path(guard.module).stem), guard.name)
    return getattr(owner, CORPUS_ATTR), getattr(owner, REPLAY_ATTR)


# Planted test modules, as (source, does the roster reader report an AST-shaped
# guard with no corpus). This gate is a guard too, and the way a roster reader
# dies is by quietly reporting nobody — so every shape it has to get right is
# probed before anything above is believed.
_A_BARE_GUARD = '''\
import ast


def _sites(source):
    return [n for n in ast.walk(ast.parse(source))]


class Guard(unittest.TestCase):
    def test_the_tree_is_clean(self):
        assert _sites('x') == []
'''
_A_DECLARED_GUARD = '''\
import ast


def _sites(source):
    return [n for n in ast.walk(ast.parse(source))]


class Guard(unittest.TestCase):
    CORPUS = (('x', True),)

    @staticmethod
    def catches(planted):
        return bool(_sites(planted))

    def test_the_tree_is_clean(self):
        assert _sites('x') == []
'''
_A_TABLE_NOTHING_REPLAYS = '''\
import ast


class Guard(unittest.TestCase):
    CORPUS = (('x', True),)

    def test_the_tree_is_clean(self):
        assert ast.parse('x').body == []
'''
_A_REPLAY_WITH_NO_TABLE = '''\
import ast


class Guard(unittest.TestCase):
    @staticmethod
    def catches(planted):
        return bool(ast.parse(planted).body)

    def test_the_tree_is_clean(self):
        assert ast.parse('x').body == []
'''
_A_GUARD_THAT_PARSES_NOTHING = '''\
class Guard(unittest.TestCase):
    def test_the_file_says_so(self):
        assert 'wombat' not in (SRC / 'cli.py').read_text()
'''
_A_PARSE_THREE_HOPS_DOWN = '''\
import ast


def _tree(path):
    return ast.parse(path.read_text())


def _sites(path):
    return _tree(path).body


def _graded(path):
    return sorted(_sites(path))


class Guard(unittest.TestCase):
    def test_the_tree_is_clean(self):
        assert _graded(p) == []
'''
_A_BARE_FUNCTION_GUARD = '''\
import ast


def _sites(source):
    return ast.parse(source).body


def test_the_tree_is_clean():
    assert _sites('x') == []
'''
_A_HELPER_CLASS_THAT_PARSES = '''\
import ast


class Helper:
    def parsed(self, source):
        return ast.parse(source)
'''
_A_DOCSTRING_THAT_SAYS_PARSE = '''\
class Guard(unittest.TestCase):
    """Decided by ast.parse in the module next door, not here."""

    def test_the_roster_is_the_roster(self):
        assert ROSTER == ('a', 'b')
'''


class EveryGuardDeclaresWhatItMustCatch(unittest.TestCase):
    """The roster, the replay, and the absences with names on them.

    This class is itself an AST-shaped guard, so it is in its own census and
    its own corpus is replayed by the case below it — which is the property
    `check hooks` has and the reason the hook precedent was worth copying:
    the thing that counts corpora carries one.
    """

    CORPUS = (
        (_A_BARE_GUARD, True),
        (_A_TABLE_NOTHING_REPLAYS, True),
        (_A_REPLAY_WITH_NO_TABLE, True),
        # The parse is three hops down a chain of helpers, which is how the
        # real ones are written — `_graded` -> `_minted_by` -> `_row_values`.
        (_A_PARSE_THREE_HOPS_DOWN, True),
        # A bare function is AST-shaped and can declare nothing, so it is
        # uncovered by construction and has to be reported as such.
        (_A_BARE_FUNCTION_GUARD, True),
        (_A_DECLARED_GUARD, False),
        # Not AST-shaped: it greps a shipped file. Outside this census, and
        # the docstring says why.
        (_A_GUARD_THAT_PARSES_NOTHING, False),
        # A class with no test methods is scaffolding, not a guard.
        (_A_HELPER_CLASS_THAT_PARSES, False),
        # The distinction the guards themselves are built on: prose naming a
        # call is not the call.
        (_A_DOCSTRING_THAT_SAYS_PARSE, False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        """Does the roster reader report an AST-shaped guard with no corpus?"""
        return any(guard.shaped and not guard.covered
                   for guard in _guards(PLANTED_MODULE, ast.parse(planted)))

    def test_every_ast_shaped_guard_declares_a_corpus_or_is_named(self):
        roster = _roster()
        uncovered = {guard.id for guard in roster
                     if guard.shaped and not guard.covered}
        unnamed = sorted(uncovered - UNCOVERED)
        self.assertEqual(
            [], unnamed,
            'an AST-shaped guard that declares no violation corpus. It asserts '
            'an empty offender list, and a reader that stopped reading returns '
            'one too — 0.5.0 shipped a guard reporting 4-of-4 while blind to '
            f'the field it existed to catch. Give it `{CORPUS_ATTR}` (planted '
            f'input, must it be caught) and `{REPLAY_ATTR}()` (its own '
            'classifier over one planted input), or add it to UNCOVERED with '
            'a reason:\n  ' + '\n  '.join(unnamed))
        gained = sorted(UNCOVERED - uncovered)
        self.assertEqual(
            [], gained,
            'UNCOVERED names a guard that is covered now, or one that moved or '
            'was renamed. Either way the roster has stopped describing the '
            'suite, and an entry nothing matches is a hole waiting for a guard '
            'to move into it — delete the line:\n  ' + '\n  '.join(gained))

    def test_every_declared_corpus_is_replayed_case_by_case(self):
        replayed = 0
        for guard in _roster():
            if not (guard.corpus or guard.replay):
                continue
            self.assertTrue(
                guard.covered,
                f'{guard.id} declares {CORPUS_ATTR if guard.corpus else REPLAY_ATTR} '
                f'and not {REPLAY_ATTR if guard.corpus else CORPUS_ATTR} — a '
                f'table nothing runs and a runner with no table are the same '
                f'silence, and both read as a corpus from outside')
            corpus, catches = _declared(guard)
            for planted, caught in corpus:
                with self.subTest(guard=guard.id, planted=planted):
                    self.assertEqual(
                        caught, bool(catches(planted)),
                        f'{guard.id} classified a planted case as '
                        f'{"clean" if caught else "a violation"}. The guard is '
                        f'only worth what it can still see:\n{planted!r}')
                replayed += 1
        self.assertGreaterEqual(
            replayed, MIN_CASES,
            f'{replayed} corpus case(s) replayed — expected at least '
            f'{MIN_CASES}. A replay over nothing is the silence this module '
            f'exists to end.')

    def test_every_corpus_holds_a_violation_and_a_clean_case(self):
        thin: list[str] = []
        for guard in _roster():
            if not guard.covered:
                continue
            said = {bool(caught) for _, caught in _declared(guard)[0]}
            if said != {False, True}:
                thin.append(f'{guard.id}: every case says '
                            f'{"caught" if said == {True} else "clean"}')
        self.assertEqual(
            [], thin,
            'a corpus that cannot fail. All-clean cases pass over a guard that '
            'went blind, which is the defect; all-caught cases pass over a '
            'guard that flags everything, which is the next one. This is the '
            'hook rule one layer over: an unhandled `--self-test` also exits 0, '
            'so the marker matters as much as the code:\n  ' + '\n  '.join(thin))

    def test_the_census_is_the_real_suite(self):
        modules, roster = _modules(), _roster()
        shaped = [guard for guard in roster if guard.shaped]
        self.assertGreaterEqual(
            len(modules), MIN_MODULES,
            f'{len(modules)} test module(s) under {TESTS} — expected at least '
            f'{MIN_MODULES}. Every case above asserts an EMPTY offender list, '
            f'and a moved `tests/` produces one.')
        self.assertGreaterEqual(
            len(shaped), MIN_GUARDS,
            f'{len(shaped)} AST-shaped guard(s) across {len(roster)} guard(s) '
            f'— expected at least {MIN_GUARDS}. The roster reader stopped '
            f'seeing them, and a coverage rule over nobody is satisfied by '
            f'everybody.')


if __name__ == '__main__':
    unittest.main()
