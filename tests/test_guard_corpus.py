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
zero replays a finding. Here a guard declares three names:

    PROTECTS — (the property this guard holds, the judgement on it). The
               judgement opens `load-bearing` and names which of rule 4's two
               sins it stands against, or opens `second scoreboard` and names
               the case that already covers the property.
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

**Why `PROTECTS` is a declared name and not the class docstring's first line.**
Every guard already has a docstring, so a rule reading one would have had an
empty offender list on the day it was written and would keep having one as new
guards arrive with ordinary prose in it — a gate nobody can fail, inside the
module that exists because an empty offender list is also what a reader that
stopped reading produces. A name is a DECISION: `PROTECTS` exists for one
reason, it is read from the class body by the same `_assigned` scan that finds
`CORPUS` (no import, no second parse), and a string assignment is code rather
than prose, so the answer does not land on the wrong side of a census. The cost
is stated rather than hidden: the contract every guard must satisfy is now
three names wide, and a guard that is a bare FUNCTION can satisfy none of them
— which is not a new exemption but the finding `_guards` already records about
`CORPUS`, and all thirteen of them are already named on `UNCOVERED`.

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
import functools
import importlib
import unittest
from pathlib import Path
from typing import NamedTuple

from support import REPO_ROOT

TESTS = REPO_ROOT / 'tests'
MODULE_GLOB = 'test_*.py'

# The three names a guard declares. All are required: a table nothing runs
# proves nothing, a replay with no table is a hook that names `--self-test` and
# has no cases behind it, and a guard nobody can ask what it protects is a cost
# nobody can price — which is the whole of this census when it is the ANSWER
# rather than the population.
PROTECTS_ATTR = 'PROTECTS'
CORPUS_ATTR = 'CORPUS'
REPLAY_ATTR = 'catches'

# The two verdicts a judgement may open with, and what each then owes. Rule 4's
# two sins are the only things `load-bearing` can be load-bearing AGAINST, so
# the judgement names one of them by number; `second scoreboard` owes the id of
# the case that already covers the property, and that id has to resolve in the
# roster — a judgement pointing at a case that moved is the same dangling name
# `UNCOVERED` fails on in both directions.
LOAD_BEARING = 'load-bearing'
SECOND_SCOREBOARD = 'second scoreboard'
SINS = ('sin 1', 'sin 2')
ID_MARK = '.py::'
ID_TRAILERS = ',.;:)`'

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
# well under what is really there and well over zero.
#
# THE READING BESIDE THEM WAS HAND-WRITTEN AND WENT STALE, which is the defect
# `bg-the-brief-undercounts-the-coupling-it-argues-from` records one file over.
# This comment said "56 modules, 30 AST-shaped guards, 155 replayed cases at
# the time of writing" with the reader that answers the same question directly
# below it; asked on 2026-09-11 that reader said 59, 35 and 202.
#
# NO NUMBER HERE IS MAINTAINED, and that is the correction rather than the
# refresh. A quote refreshed is a quote that goes stale again on the next
# commit — it went stale by 3 modules and 5 guards in four days. So the reading
# above is DATED and is evidence about the defect, not a description of now:
# `shaped_roster()` is the call that answers it, and each assertion below prints
# the live count in its own failure message.
#
# The floors do not move to meet any of it. A floor raised to match a census
# stops being a floor and becomes a ratchet on growth; these exist to catch a
# broken root, and 30/20/40 is still far under and far over zero.
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
# THIRTEEN OF THE SIXTEEN ARE BARE FUNCTIONS, which is why this roster also
# carries their JUDGEMENT. A class fixes its line by growing a `CORPUS`, a
# `catches` and a `PROTECTS`; a bare function has nowhere to hang any of the
# three, so the judgement `PROTECTS` would have held is written here beside the
# name instead. Every one of the thirteen is load-bearing against rule 4's
# FIRST sin (a gate that misses drift and prints PASS) unless the line says
# otherwise, and the reason is the same shape each time: what they grade is a
# second spelling, an absent route or a folded census, and none of those
# changes any behaviour a behaviour test could observe.
UNCOVERED = frozenset((
    # The seed is what a consumer reads to find out what a pinned version can
    # do, so a default that drifted from the code is a lie with no symptom.
    'test_config_seed.py::test_every_commented_default_in_the_seed_is_the_codes_own_default',
    # Rule 11's handshake: `cmd_config` is written and tested, and unreachable
    # until the router names it. Nothing that RUNS notices an unrouted verb.
    'test_config_seed.py::test_pm_config_is_reachable_from_the_cli',
    # The zero-file floor under the two above — a census that folded to nothing
    # compares an empty set of keys and passes over everything.
    'test_config_seed.py::test_the_census_reads_every_module_that_reads_config',
    # Rule 5's GATE/WORKFLOW split: a knob misfiled as a declaration stops
    # refusing by name, and a tree with no section gets a default it never set.
    'test_config_seed.py::test_the_seeds_declarations_are_the_keys_with_nothing_behind_them',
    # Rule 9, express never infer. The counter-example is a `frequency` nobody
    # increments, which pins confidence at 0.1 forever and still reads as rank.
    'test_conveyor_lessons.py::test_every_match_prints_in_recorded_order_and_nothing_ranks_them',
    # The classifier the census above stands on, and it says so itself.
    'test_conveyor_lessons.py::test_the_ranking_reader_tells_a_stamp_from_a_ranking',
    # A kind read from a literal in one module and a constant in another
    # diverges with no error anywhere — six spellings is where it started.
    'test_grain_shape.py::test_the_slot_names_have_one_source',
    # SIN 2 (a write that looks legitimate and is not): a second refusal after
    # the first byte is a half-written tree. The case above observes one tree;
    # this one asks the code whether a third refusal is waiting.
    'test_init_verb.py::test_the_preflight_carries_exactly_one_refusal',
    # The same family as `NoVocabularyLiteralSurvivesOutsideItsHome` beside it,
    # on the state words rather than the kinds and fields.
    'test_pm_flow.py::test_no_state_literal_survives_outside_the_seed',
    # A belt that spells a state word has stopped reading what the project
    # declared (rule 9), and writes the wrong word without raising.
    'test_pm_flow.py::test_the_belts_spell_no_state_word',
    # A new silent reader of a seed word is a second place the vocabulary gets
    # decided, which is the condition every drift above grew out of.
    'test_pm_flow.py::test_the_seeds_exported_words_have_exactly_the_named_readers',
    # The census itself, for one root. Its module is `st-the-tests-ceiling-is-
    # declared-and-argued`'s, so the ceiling argument is judged there.
    'test_prose_census.py::test_comments_and_docstrings_are_under_a_third_of_the_code',
    # Its sibling, on the same reader and uncovered the same way: a bare
    # function has nowhere to hang a corpus, and `prose_and_code` sums over a
    # fixed node set rather than classifying which node it is looking at — the
    # blindness this census narrows to. Its own arithmetic is probed in
    # 0.6.0/D7 instead: withdraw the printing and the exclusion drops from 9
    # modules to 2. Load-bearing INVERTED: it is the only thing that can fail
    # when a ceiling is met by trimming a file that was not the one that grew.
    'test_prose_census.py::test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling',
    # The three classes below declare `PROTECTS` and owe only a corpus.
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
    klass: bool = False
    protects: object = None

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


def _protects(node: ast.ClassDef) -> object:
    """The `PROTECTS` value, read from source and never imported.

    A literal, so `ast.literal_eval` answers without running the module — the
    same reason the roster is read rather than imported. Anything that is not a
    literal comes back as `()`, which `_judged` then names: a value computed at
    import is a judgement no reader can quote.
    """
    for stmt in node.body:
        if PROTECTS_ATTR not in _assigned(stmt):
            continue
        try:
            return ast.literal_eval(stmt.value)
        except (ValueError, TypeError):
            return ()
    return None


def _judged(value: object, ids: frozenset[str]) -> str:
    """Why this `PROTECTS` is not a judgement yet, or `''` when it is one.

    The SHAPE is graded and the truth is not. Whether `OneApply` is really
    load-bearing is a reading of the suite, and asserting it here would be the
    second scoreboard this census exists to find — so what is gated is that a
    verdict was reached, that it names what it stands against, and that any case
    it points at still exists.
    """
    if value is None:
        return f'declares no {PROTECTS_ATTR}'
    if not (isinstance(value, tuple) and len(value) == 2
            and all(isinstance(part, str) and part.strip() for part in value)):
        return (f'{PROTECTS_ATTR} is not (the property, the judgement) with '
                f'both spelled out')
    verdict = value[1]
    if verdict.startswith(LOAD_BEARING):
        if not any(sin in verdict for sin in SINS):
            return (f'load-bearing against WHICH of rule 4 two sins? name '
                    f'{" or ".join(SINS)}')
    elif verdict.startswith(SECOND_SCOREBOARD):
        if ID_MARK not in verdict:
            return (f'a {SECOND_SCOREBOARD} names the case that already covers '
                    f'the property, by id')
    else:
        return (f'the judgement opens with neither {LOAD_BEARING!r} nor '
                f'{SECOND_SCOREBOARD!r}')
    dangling = sorted(cited for cited in _cited(verdict) if cited not in ids)
    if dangling:
        return f'names a guard that is not in the roster: {", ".join(dangling)}'
    return ''


def _cited(verdict: str) -> set[str]:
    """Every `module.py::name` the judgement points at."""
    return {word.rstrip(ID_TRAILERS) for word in verdict.split()
            if ID_MARK in word}


def _undeclared(guards: tuple[Guard, ...]) -> list[str]:
    """Every AST-shaped guard that COULD declare what it protects and has not.

    The population is the AST-shaped CLASSES. A bare function has nowhere to
    hang a declaration, which is the same finding `_guards` records about
    `CORPUS` and the reason all thirteen of them are already on `UNCOVERED` —
    so the absence carries a name either way and there is no second roster.
    """
    ids = frozenset(guard.id for guard in guards)
    return sorted(f'{guard.id}: {why}' for guard in guards
                  if guard.shaped and guard.klass
                  and (why := _judged(guard.protects, ids)))


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
        klass = isinstance(node, ast.ClassDef)
        protects = None
        if klass:
            corpus = any(CORPUS_ATTR in _assigned(s) for s in node.body)
            replay = any(isinstance(s, ast.FunctionDef)
                         and s.name == REPLAY_ATTR for s in node.body)
            protects = _protects(node)
        out.append(Guard(module, node.name, node.lineno,
                         _parses(node) or bool(_named(node) & readers),
                         corpus, replay, klass, protects))
    return out


@functools.cache
def _modules() -> tuple[Path, ...]:
    return tuple(sorted(TESTS.glob(MODULE_GLOB)))


@functools.cache
def _roster() -> tuple[Guard, ...]:
    """Every guard under `tests/`, read from source and never imported.

    Cached for the same reason `conftest.module_spawns` is: every case below
    asks for the whole roster, and a file does not change under a running
    session. Reading 33k lines of `tests/` four times cost the inner loop four
    seconds, and a tier that got slower is a finding (rule 10).
    """
    return tuple(guard for path in _modules()
                 for guard in _guards(path.name,
                                      ast.parse(path.read_text(encoding='utf-8'))))


def shaped_roster() -> tuple[Guard, ...]:
    """THE ASK: every AST-shaped guard, with the property it protects.

    One call, derived from source, never hand-listed — `guard.protects` is the
    pair the class declared and `guard.id` is where it lives. This is the
    question the feature brief could only answer with a grep, and a grep cannot
    tell a `parse` three helpers down from the word in a docstring.
    """
    return tuple(guard for guard in _roster() if guard.shaped)


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
    PROTECTS = ('the tree is clean', 'load-bearing - sin 1: nothing else looks')
    CORPUS = (('x', True),)

    @staticmethod
    def catches(planted):
        return bool(_sites(planted))

    def test_the_tree_is_clean(self):
        assert _sites('x') == []
'''
_A_GUARD_WITH_NO_JUDGEMENT = '''\
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
_A_JUDGEMENT_THAT_IS_A_BARE_STRING = '''\
import ast


class Guard(unittest.TestCase):
    PROTECTS = 'the tree is clean'
    CORPUS = (('x', True),)

    @staticmethod
    def catches(planted):
        return bool(ast.parse(planted).body)

    def test_the_tree_is_clean(self):
        assert ast.parse('x').body == []
'''
_A_JUDGEMENT_WITH_NO_VERDICT = '''\
import ast


class Guard(unittest.TestCase):
    PROTECTS = ('the tree is clean', 'it matters a great deal to all of us')
    CORPUS = (('x', True),)

    @staticmethod
    def catches(planted):
        return bool(ast.parse(planted).body)

    def test_the_tree_is_clean(self):
        assert ast.parse('x').body == []
'''
_A_JUDGEMENT_NAMING_NO_SIN = '''\
import ast


class Guard(unittest.TestCase):
    PROTECTS = ('the tree is clean', 'load-bearing - it matters a great deal')
    CORPUS = (('x', True),)

    @staticmethod
    def catches(planted):
        return bool(ast.parse(planted).body)

    def test_the_tree_is_clean(self):
        assert ast.parse('x').body == []
'''
_A_SECOND_SCOREBOARD_POINTING_NOWHERE = '''\
import ast


class Guard(unittest.TestCase):
    PROTECTS = ('the tree is clean',
                'second scoreboard - test_renamed_away.py::test_the_tree')
    CORPUS = (('x', True),)

    @staticmethod
    def catches(planted):
        return bool(ast.parse(planted).body)

    def test_the_tree_is_clean(self):
        assert ast.parse('x').body == []
'''
_A_SECOND_SCOREBOARD_THAT_RESOLVES = '''\
import ast


class Guard(unittest.TestCase):
    PROTECTS = ('the tree is clean',
                'second scoreboard - planted_guard.py::Guard asks it first')
    CORPUS = (('x', True),)

    @staticmethod
    def catches(planted):
        return bool(ast.parse(planted).body)

    def test_the_tree_is_clean(self):
        assert ast.parse('x').body == []
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

    PROTECTS = (
        'every AST-shaped guard declares what it protects, the violations it '
        'must catch, and a classifier answering over one of them — or is named '
        'as an absence, in both directions',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): the '
        'thing that counts corpora carries one. It found four hollow gates at '
        'the close of 0.6.0, and the 0.5.0 guard that reported 4-of-4 while '
        'blind to the field it existed to catch is why it exists at all',
    )

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
        # The third declaration, probed the way the first two are: a corpus
        # and a replay with no judgement on them is a cost nobody can price,
        # and every malformed judgement is a judgement nobody reached.
        (_A_GUARD_WITH_NO_JUDGEMENT, True),
        (_A_JUDGEMENT_THAT_IS_A_BARE_STRING, True),
        (_A_JUDGEMENT_WITH_NO_VERDICT, True),
        (_A_JUDGEMENT_NAMING_NO_SIN, True),
        # A judgement pointing at a case that moved is `UNCOVERED`'s dangling
        # entry one declaration over, and it fails the same way.
        (_A_SECOND_SCOREBOARD_POINTING_NOWHERE, True),
        (_A_SECOND_SCOREBOARD_THAT_RESOLVES, False),
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
        """Does the roster reader report an AST-shaped guard that under-declares?

        All three names, because the contract is one contract: a guard with a
        corpus and no judgement and a guard with a judgement and no corpus are
        both half-declared, and a reader that can only see one of the two halves
        is the blindness this module was written about.
        """
        guards = _guards(PLANTED_MODULE, ast.parse(planted))
        return bool(_undeclared(guards)
                    or any(guard.shaped and not guard.covered
                           for guard in guards))

    def test_every_ast_shaped_guard_declares_a_corpus_or_is_named(self):
        """Three declarations, one roster, and both directions on the absences.

        One case rather than three, because all three questions are asked of the
        same roster read and the suite has no case headroom under
        `[tests] cases` — a second pass over 58 modules to assert a second
        attribute would buy nothing the assertions below do not already say by
        name.
        """
        roster = _roster()
        undeclared = _undeclared(roster)
        self.assertEqual(
            [], undeclared,
            f'an AST-shaped guard that cannot say what it protects. The roster '
            f'is the answer to "what does the self-policing cost and which of '
            f'it is load-bearing", and a guard with no judgement on it is a '
            f'line item nobody can price. Give it `{PROTECTS_ATTR}` — (the '
            f'property it holds, the judgement) — where the judgement opens '
            f'{LOAD_BEARING!r} and names the sin it stands against, or '
            f'{SECOND_SCOREBOARD!r} and names the case that already covers '
            f'it:\n  ' + '\n  '.join(undeclared))
        uncovered = {guard.id for guard in shaped_roster()
                     if not guard.covered}
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
        shaped = shaped_roster()
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
