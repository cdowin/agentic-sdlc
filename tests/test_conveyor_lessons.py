"""test_conveyor_lessons.py — a recorded lesson, read back where you stand.

D1's whole argument in four cases: the namesake package captures patterns
faithfully, never reads them back in any way that changes an outcome, and
nothing in its architecture reports that. So what is proven here is the read
BACK — the three surfaces a belt has, the exactness that keeps it from being a
nag, and the assembly half of the claim the feature lives or dies on:

  **a lesson changes no verdict and no exit code**, present or absent.

The BELT half of that claim is not here and cannot be: it needs a check that
reads the filesystem the surfacer writes to, which means git, which means the
shell tier. It is `test_conveyor_steps.py`'s
`test_a_recorded_lesson_changes_no_verdict_no_exit_code_and_no_write`, over the
real `tree-clean`. Keeping these four cases in the unit tier is the point of
the split; keeping the pointer is the point of rule 11.

The reader is in the belts because the `lesson` row kind is
`ft-a-lesson-is-a-row-bound-to-a-grain`'s; `lessons.paths` belongs in
`ledger.py` beside the other row readers once it lands, and these cases move to
`tests/test_pm_ledger.py` with it.
"""
from __future__ import annotations

import ast
import contextlib
import io
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable, NamedTuple

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import (LEDGER_REL, bug, cfg_for, ledger_rows,  # noqa: E402
                        run_cli, tree, write, write_config)

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.repo.conveyor import driver, lessons, steps  # noqa: E402
from agentic_sdlc.repo.pm import ledger, ready_for  # noqa: E402

MILESTONE = '0.1'
FEATURE = '0.1/alpha'
STORY = '0.1/alpha/s0'
GRAINLESS_REL = 'pm/roadmap/ledger.jsonl'
RECORD = 'docs/reviews/alpha.md'
TS = '2026-09-07T00:00:00Z'

# The check names the belts already ship, so the rule surface is asked of a
# real rule rather than of a word invented for a test.
RULE = 'evidence-written'
OTHER_RULE = 'tree-clean'


def lesson_row(grain: str = '', rule: str = '', source: str = RECORD,
               text: str = 'the fixture is copied, never edited in place',
               ts: str = TS) -> dict:
    """One `lesson` row, keyed off the MINTER's own list so a renamed column
    goes red here. Built rather than minted because several cases below need a
    DEGENERATE row — no source, no text — which `ledger.lesson_row` refuses to
    write and the reader must still survive reading."""
    values = {'ts': ts, 'kind': lessons.KIND, 'grain': grain, 'rule': rule,
              'source': source, 'text': text}
    return {name: values[name] for name in ledger.LESSON_KEYS}


def record(root: Path, *rows: dict, rel: str = LEDGER_REL) -> None:
    """Append rows to a ledger through the ledger's own writer."""
    for row in rows:
        ledger.append_to(root / rel, row)


class Run(NamedTuple):
    """What one belt run did: its EXIT CODE, its stdout, and every write."""

    code: int
    lines: list[str]
    writes: list[str]

    @property
    def taught(self) -> list[str]:
        return [line for line in self.lines if f'] {lessons.WORD}' in line]

    @property
    def verdicts(self) -> list[str]:
        return [line for line in self.lines if f'] {lessons.WORD}' not in line]


def check(name: str, answer: driver.Answer) -> driver.Check:
    return driver.Check(name, lambda ctx: answer)


def belt(root: Path, checks, *argv: str) -> Run:
    """One belt run through the VERB, over scripted checks, on a scratch tree.

    Through `driver.main` rather than `driver.run`, so the wiring the surfacing
    hangs on — which grain this run is standing on, and the config the sink is
    read from — is what the case exercises. The write is stubbed: what a belt
    writes is `test_conveyor_close.py`'s claim, not this module's.
    """
    cfg_for(root)  # the config caches a moved cwd invalidates
    registry = {c.name: c for c in checks}
    writes: list[str] = []
    out = io.StringIO()

    def write(ctx: driver.Context, state: str,
              skipped: tuple = ()) -> tuple[bool, str]:
        writes.append(state)
        return True, f'wrote {state}'

    with contextlib.redirect_stdout(out):
        code = driver.main(list(argv or ('close', 'feature', FEATURE)),
                           root=root, registry=registry,
                           steps=tuple(registry), write=write)
    return Run(code, out.getvalue().splitlines(), writes)


# --- 1: what a lesson is, and how exactly it is matched -----------------------

def test_a_lesson_is_read_back_only_for_the_exact_grain_or_rule_it_names():
    """The nag guard. Scope is EXACT — a prefix, a suffix, a different case and
    a substring all match nothing, because "related" is the inference edge this
    package does not have (rule 9). And one damaged ledger is NAMED rather than
    read as a tree with nothing recorded (rule 11).
    """
    with tree() as root:
        record(root,
               lesson_row(grain=STORY),
               lesson_row(rule=RULE),
               lesson_row(grain=FEATURE, rule=RULE),
               # Not a lesson: another row kind, and a row whose fields are of
               # the wrong shape (rows arrive from other branches and versions).
               ledger.status_row(STORY, 'ready', 'building'),
               {'ts': TS, 'kind': lessons.KIND, 'grain': 3, 'rule': None})
        record(root, lesson_row(grain=STORY, text='in the tree ledger'),
               rel=GRAINLESS_REL)
        (root / GRAINLESS_REL).open('a', encoding='utf-8').write('torn{\n')

        store = lessons.read(cfg_for(root))

        assert [(les.grain, les.rule) for les in store.lessons] == [
            (STORY, ''), ('', RULE), (FEATURE, RULE), ('', '')], (
            'the store is not the lesson rows of every ledger in recorded '
            'order, typed field by field')
        assert len(store.unreadable) == 1 and GRAINLESS_REL.split('/')[-1] \
            in store.unreadable[0], (
            'a ledger that would not parse was read as silence — one damaged '
            'file must not make a recording tree look empty')

        assert len(store.against_grain(STORY)) == 1
        assert len(store.against_rule(RULE)) == 2
        for near in (STORY[:-1], STORY + '1', STORY.upper(), 'alpha/s0', ''):
            assert store.against_grain(near) == (), (
                f'{near!r} matched the grain {STORY!r} — the scope is exact, '
                f'and a lesson on every neighbouring id is the nag that gets '
                f'rule 11\'s surfaces muted')
        for near in (RULE[:-1], RULE.upper(), 'evidence', ''):
            assert store.against_rule(near) == (), f'{near!r} matched {RULE!r}'


# --- 2: the three places, and no others ---------------------------------------

def test_a_lesson_surfaces_at_the_three_places_a_belt_stands_and_nowhere_else():
    """The move it touches, the rule it runs, and the blocker `ready-for`
    named — each printed with its `source` and emitted on the sink."""
    with tree(story_statuses=('building',)) as root:
        code, said = run_cli(root, 'ready-for', 'feature', FEATURE)
        # What the belt actually holds is the verb's output flattened to one
        # line, which is where the marker has to survive being read.
        said = ' '.join(said.split())
        assert code == 1, said
        assert lessons.blockers_named(said) == (STORY,), (
            f'the blockers were not read off `pm ready-for`\'s own marker: '
            f'{said}')

        mine = (lesson_row(grain=FEATURE, text='the move surface'),
                lesson_row(rule=RULE, text='the rule surface'),
                lesson_row(grain=STORY, text='the blocker surface'))
        theirs = (lesson_row(grain='0.1/beta', text='another grain'),
                  lesson_row(rule=OTHER_RULE, text='another rule'))
        record(root, *mine, *theirs)

        # Emission is OPT-IN: declaring the section is what turns the sink on
        # (0.5.0/D1, `emit.emit`), and this case is about what lands on it.
        write_config(root, '[emit]\n')

        run = belt(root, [
            check('stories-done', replace(driver.Answer.no(said),
                                          names=lessons.blockers_named(said))),
            check(RULE, driver.Answer.yes('the story carries a done: line')),
            check('review-recorded', driver.Answer.yes(RECORD)),
        ])

        assert run.taught == [
            f'[feature] lesson: grain {FEATURE} — the move surface '
            f'(source: {RECORD})',
            f'[feature] lesson: grain {STORY} — the blocker surface '
            f'(source: {RECORD})',
            f'[feature] lesson: rule {RULE} — the rule surface '
            f'(source: {RECORD})',
        ], ('the three surfaces are not the entry grain, the blocker the '
            'ready-for check named, and the rule that ran — in that order')
        assert 'another' not in ' '.join(run.taught), (
            'a lesson against another grain or another rule surfaced on an '
            'unrelated run — that is the nag rule 11 warns about')

        # Each line sits BESIDE the verdict it belongs to, never inside it:
        # the check's own line is untouched (rule 6).
        assert run.lines.index(run.taught[1]) == \
            run.lines.index('[feature] error: stories-done: ' + said) + 1

        emitted = [row for row in ledger_rows(root)
                   if str(row.get('kind', '')).startswith(f'{lessons.KIND}.')]
        assert [row['kind'] for row in emitted] == [
            'lesson.enter', 'lesson.verdict', 'lesson.verdict']
        assert [row['matched'] for row in emitted] == [FEATURE, STORY, RULE]
        assert [row.get('check', '') for row in emitted] == [
            '', 'stories-done', RULE]
        assert {row['grain'] for row in emitted} == {FEATURE}, (
            'the events are not routed by the grain the belt is standing on')
        assert emitted[0]['lesson'] == mine[0], (
            'the event restates the lesson instead of carrying the recorded '
            'row verbatim')

        # The outer belt stands on a VERSION, and the grain it touches is the
        # milestone claiming it — one resolver, so the surface and the write
        # cannot disagree about what is being moved.
        record(root, lesson_row(grain=MILESTONE, text='the milestone surface'))
        outer = belt(root, [check('gate', driver.Answer.yes('green'))],
                     'release', MILESTONE)
        assert outer.taught == [
            f'[release] lesson: grain {MILESTONE} — the milestone surface '
            f'(source: {RECORD})']


# --- 3: the case that must exist ----------------------------------------------

def test_a_lesson_changes_no_verdict_and_no_exit_code():
    """**A lesson is never a gate**, at the ASSEMBLY altitude: `driver.run`'s
    lines, its exit code and its write decision are the same with a lesson
    against every check and with none, on the passing path and the refusing
    one. An unreachable sink and a malformed `[emit]` are lines too.

    **What this case cannot see, and where that lives.** Every check here is a
    closure returning a constant, and `tree()` is not a git repository — so no
    check here READS the filesystem the surfacer writes to, and the shape that
    actually broke `release` (an emission before a cleanliness check) is
    invisible from this tier by construction. The check that can see it spawns
    git, so it belongs to the shell tier and it is
    `test_conveyor_steps.py::test_a_recorded_lesson_changes_no_verdict_no_exit_code_and_no_write`
    — the real `steps.check_tree_clean`, two committed-clean trees. Named here
    rather than assumed: a claim proven somewhere else is still a claim, and a
    reader of this module has to be able to find it.

    Two trees, built fresh, rather than one tree run twice: run over the same
    tree, `bare`'s own emitted rows are already on disk when `taught` reads it.
    """
    passing = [check('a', driver.Answer.yes('a holds')),
               check(RULE, driver.Answer.yes('the done: line is there'))]
    failing = [check('a', driver.Answer.no('a fails')),
               check(RULE, driver.Answer.unverifiable('cannot tell'))]

    for checks, expected in ((passing, 0), (failing, 1)):
        with tree() as root:
            bare = belt(root, checks)
        with tree() as root:
            record(root, lesson_row(grain=FEATURE), lesson_row(rule='a'),
                   lesson_row(rule=RULE))
            taught = belt(root, checks)

        assert taught.taught, 'nothing surfaced; the case is vacuous'
        assert taught.code == bare.code == expected
        assert taught.writes == bare.writes
        assert taught.verdicts == bare.lines, (
            'a lesson reshaped the belt\'s own lines; it is only ever a '
            'line BESIDE a verdict (rule 6)')

    # A sink that cannot be reached is the emit seam's business and never the
    # belt's; a section that will not PARSE is the belt's, at exit 2. That
    # split is deliberate: the sink is never load-bearing, the declaration is
    # read like every other declaration.
    with tree() as root:
        record(root, lesson_row(grain=FEATURE))
        write_config(root, '[emit]\nsink = "events.jsonl"\n')
        (root / 'events.jsonl').mkdir()
        unreachable = belt(root, passing)
        assert unreachable.code == 0 and unreachable.writes == ['done']
        assert unreachable.taught, 'the lesson was not printed either'

        write_config(root, '[emit]\nkinds = "verdict"\n')
        malformed = belt(root, passing)
        assert malformed.code == 2 and malformed.writes == [], (
            f'a malformed [emit] is a DECLARATION this run could not read, so '
            f'it is exit 2 before the first check and nothing is written '
            f'(rule 9) — not a mid-belt warning over a sink that will stay '
            f'silent forever: {malformed.taught}')


# --- 4: several match, and nothing chooses ------------------------------------

# D1's rule is that nothing is inferred, scored or ranked — no ordering by
# VALUE. Ordering by TIME is not ranking, it is the order they were recorded,
# so this is NOT a ban on the word `sort`: it is a ban on any sort key that is
# not the row's own stamp, plus the vocabulary of choosing.
STAMP = 'ts'
ORDERING = ('sorted', 'sort')
# Each of these picks one row over another. `[:3]` and `[-1]` do too and are
# NOT held here: a slice of a lesson list and `_clip`'s `text[:limit]` are the
# same node without types. Named rather than implied — issue #14.
CHOOSING = ('min', 'max', 'nlargest', 'nsmallest', 'most_common', 'reverse')
# Matched against the whole identifier AND each `_`-separated part, lowered, so
# `confidence_derived` — D1's own counter-example, one suffix away — is caught
# while `stop` is not `top`.
RANKING = ('rank', 'ranked', 'score', 'scored', 'confidence', 'frequency',
           'similarity', 'best', 'top', 'weight', 'priority')


def _spelt(name: str) -> str:
    return name.id if isinstance(name, ast.Name) else getattr(name, 'attr', '')


def _keyed_on_the_stamp(call: ast.Call) -> bool:
    """Is this ordering call keyed on the recorded stamp and nothing else? A
    bare `sorted(x)` orders by the tuple's first field, which is a VALUE."""
    if len(call.keywords) != 1 or call.keywords[0].arg != 'key':
        return False
    key = call.keywords[0].value
    bound = {arg.arg for node in ast.walk(key)
             if isinstance(node, ast.Lambda) for arg in node.args.args}
    read = {_spelt(node) for node in ast.walk(key)
            if isinstance(node, (ast.Name, ast.Attribute))}
    return read - bound == {STAMP}


def _chooses(source: ast.AST) -> list[str]:
    """Every identifier or field NAME here that ranks, scores or chooses, and
    every ordering call whose key is something other than the stamp. String
    constants are graded too: `row['confidence_derived']` is D1's own
    counter-example and it is not an identifier."""
    found: list[str] = []
    for node in ast.walk(source):
        name = ''
        if isinstance(node, (ast.Name, ast.Attribute)):
            name = _spelt(node)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            name = node.value
        if name and (set(name.lower().split('_')) | {name.lower()}) & (
                set(RANKING) | set(CHOOSING)):
            found.append(name)
        if (isinstance(node, ast.Call) and _spelt(node.func) in ORDERING
                and not _keyed_on_the_stamp(node)):
            found.append(f'{_spelt(node.func)}(…) not keyed on {STAMP!r}')
    return sorted(set(found))

LESSON_MODULE = 'src/agentic_sdlc/repo/conveyor/lessons.py'
# The ROW MINTER lives among minters that legitimately sort, so the ledger is
# scanned by FUNCTION: everything the lesson word owns there is named `lesson`.
MINTER_MODULE = 'src/agentic_sdlc/repo/pm/ledger.py'


def lesson_sources() -> list[tuple[str, ast.AST]]:
    """Every piece of source the lesson word owns — the reader and the verb
    whole, plus the minter's own functions."""
    read = ast.parse((REPO_ROOT / LESSON_MODULE).read_text(encoding='utf-8'))
    found = [(LESSON_MODULE, read)]
    minters = ast.parse((REPO_ROOT / MINTER_MODULE).read_text(encoding='utf-8'))
    found += [(f'{MINTER_MODULE}::{node.name}', node)
              for node in ast.walk(minters)
              if isinstance(node, ast.FunctionDef)
              and lessons.KIND in node.name]
    assert len(found) > 1, 'the minter left the census — nothing is scanned'
    return found


# The reader is probed before it grades: a guard that quietly stopped catching
# things passes forever, which is rule 4's first sin (issue #14's class).
CHOOSING_SPELLINGS = (
    ('found.sort(key=lambda one: one.ts)', False),
    ('sorted(found, key=lambda one: one.ts)', False),
    ('sorted(found)', True),
    ('found.sort()', True),
    ('sorted(found, key=lambda l: len(l.text))', True),
    ('found.sort(key=lambda one: one.ts, reverse=True)', True),
    ('max(found, key=lambda l: len(l.text))', True),
    ('min(found, key=lambda l: l.ts)', True),
    ('heapq.nlargest(3, found)', True),
    ('Counter(x).most_common(3)', True),
    ('found.reverse()', True),
    ("row['confidence_derived'] = 0.1", True),
    ('weight = {}', True),
    ('priority = []', True),
    # NOT held, and said out loud: a slice of a lesson list and `_clip`'s
    # `text[:limit]` are the same node without types — issue #14.
    ('found[:3]', False),
    ('text[:limit]', False),
    # `stop` is not `top`, or the guard reddens on prose.
    ('stopped = True', False),
)


@pytest.mark.parametrize('source,chosen', CHOOSING_SPELLINGS)
def test_the_ranking_reader_tells_a_stamp_from_a_ranking(source, chosen):
    """The census below is only worth its line if this holds."""
    assert bool(_chooses(ast.parse(source))) is chosen, source


def test_lessons_read_from_two_ledgers_print_oldest_first():
    """`--help` promises "the order they were recorded" and `read()` walked
    `ledger_paths` — grainless first, then one file per milestone — extending
    per file. Across two ledgers that printed NEWEST before OLDEST, and the
    operator could not tell, because `ts` is the last column."""
    with tree() as root:
        # `ledger_paths` reads the grainless file FIRST, so the NEWEST row goes
        # there: file order and recorded order have to disagree, or the case
        # passes over an unsorted reader (issue #14's class).
        record(root, lesson_row(grain=FEATURE, text='OLDEST',
                                ts='2020-01-01T00:00:00Z'))
        grainless = ledger.grainless_path(cfg_for(root).roadmap)
        ledger.append_to(grainless, ledger.lesson_row(
            FEATURE, RULE, RECORD, 'NEWEST', ts='2026-09-07T00:00:00Z'))
        code, out = run_lesson(root, lessons.SHOW)
    assert code == 0, out
    assert [line.split('\t')[3] for line in out.splitlines()] == [
        'OLDEST', 'NEWEST'], out


def test_every_match_prints_in_recorded_order_and_nothing_ranks_them():
    """Choosing is inference and the caller has the source paths (rule 9). The
    counter-example is specific: the namesake package's `Learner` ranks by a
    `frequency` it never increments, pinning confidence at 0.1 forever (D1).
    """
    with tree() as root:
        record(root,
               lesson_row(grain=FEATURE, text='first', source='docs/a.md'),
               lesson_row(grain=FEATURE, text='second', source='docs/b.md'),
               lesson_row(grain=FEATURE, text='', source=''),
               lesson_row(grain=FEATURE, text='x' * (lessons.TEXT_LIMIT + 50)))
        printed = belt(root, [check('a', driver.Answer.yes('ok'))]).taught
        assert len(printed) == 4, 'a match was dropped, folded or ranked away'
        assert [line.split(' — ')[1] for line in printed[:2]] == [
            'first (source: docs/a.md)', 'second (source: docs/b.md)'], (
            'the matches are not printed in the order they were recorded')
        assert printed[2].endswith(
            f'{lessons.NO_TEXT} (source: {lessons.NO_SOURCE})'), (
            'a lesson pointing at nothing must SAY it points at nothing')
        assert f'… (source: {RECORD})' in printed[3] and \
            len(printed[3]) < lessons.TEXT_LIMIT + 100, (
            'an unbounded row made an unbounded line — the text is clipped '
            'and the source, which is where the reader goes next, is not')

    # The WRITE half joins the guard the read half already carried: a lesson
    # ranked at the moment it is recorded is ranked just as permanently.
    for where, source in lesson_sources():
        chosen = _chooses(source)
        assert not chosen, (
            f'{chosen} in {where} — nothing here may rank, score, weigh or '
            f'pick one lesson over another: anything inferred needs a feedback '
            f'edge and a reader/writer has nowhere to put one (D1). Ordering '
            f'by {STAMP!r} is NOT ranking — it is the order they were '
            f'recorded, which is what `lesson show --help` promises. NOT held '
            f'by this census: a slice of a lesson collection — issue #14')


# --- 5: the coupling to `pm ready-for`'s printed blockers ---------------------
# The third surface reads grains off ANOTHER verb's sentences, and until this
# census exactly one of the eleven shapes that verb constructs had a case. The
# rest failed the way rule 4 forbids: quietly. Every shape below is produced by
# running the REAL verb, so a reworded sentence turns one of these red.

FEATURE_DOC = 'pm/roadmap/features/alpha.md'
STORY_DOC = 'pm/roadmap/stories/s0.md'
GONE = 'docs/reviews/gone.md'
BUG = '0.1/bugs/crash'
OVER_CAP = ready_for.MAX_NAMED + 5
HOLD_RECORD = ('A record.\n\n```\nverdict: HOLD\n'
               '| id | severity | disposition |\n| E1 | BLOCKER | open |\n```\n')


def no_features(root: Path) -> None:
    (root / FEATURE_DOC).unlink()
    (root / STORY_DOC).unlink()


def open_bug(root: Path) -> None:
    bug(root, 'crash', 'open', fix_milestone=f'"{MILESTONE}"')


def pointer_to_nothing(root: Path) -> None:
    path = root / FEATURE_DOC
    path.write_text(path.read_text(encoding='utf-8')
                    .replace('reviewed:', f'reviewed: {GONE}'), encoding='utf-8')


def open_finding(root: Path) -> None:
    (root / RECORD).write_text(HOLD_RECORD, encoding='utf-8')


class Shape(NamedTuple):
    """One blocker sentence `pm ready-for` constructs, and what it NAMES.

    `named` is asserted exactly, `grain` is the id the sentence is ABOUT — ''
    when the sentence names none, which is a fact about the verb's wording and
    not a miss: a lesson against the RULE still surfaces on the same check.
    """

    why: str
    build: dict
    edit: Callable[[Path], None] | None
    argv: tuple[str, ...]
    named: tuple[str, ...]
    grain: str


SHAPES = (
    Shape('feature: a story not in done — `<sid> is <status>`',
          {'story_statuses': ('building',)}, None,
          ('ready-for', 'feature', FEATURE), (STORY,), STORY),
    Shape('feature: no stories at all — vacuously READY, no blocker',
          {'story_statuses': ()}, None,
          ('ready-for', 'feature', FEATURE), (), ''),
    Shape('milestone: a feature not in done — `<fid> is <status>`',
          {'feature_status': 'building'}, None,
          ('ready-for', 'milestone', MILESTONE), (FEATURE,), FEATURE),
    Shape('milestone: done with a record defect — `<fid> is done, <defect>`',
          {'feature_status': 'done', 'with_record': False}, None,
          ('ready-for', 'milestone', MILESTONE), (FEATURE,), FEATURE),
    Shape('milestone: no features — `<mid> has no features …`',
          {}, no_features,
          ('ready-for', 'milestone', MILESTONE), (MILESTONE,), MILESTONE),
    Shape('milestone: an open bug — `<bid> is <status> — a bug whose …`',
          {'feature_status': 'done'}, open_bug,
          ('ready-for', 'milestone', MILESTONE), (BUG,), BUG),
    # The shape M1 was raised on: the id carries the sentence's colon, and
    # taking the token verbatim yielded `0.1/alpha:`, which matches no lesson.
    Shape('tag: a record pointer defect — `<owner>: <defect>`',
          {'feature_status': 'done', 'with_record': False}, pointer_to_nothing,
          ('ready-for', 'tag', MILESTONE), (FEATURE, MILESTONE), FEATURE),
    Shape('tag: a record that will not parse — `UNVERIFIABLE <rel>: …`',
          {'feature_status': 'done'}, None,
          ('ready-for', 'tag', MILESTONE), (RECORD,), ''),
    Shape('tag: open blocking findings — `E1, E2 open in <rel>`',
          {'feature_status': 'done'}, open_finding,
          ('ready-for', 'tag', MILESTONE), ('E1',), ''),
    Shape('tag: no records — `<mid> points at no review record …`',
          {'feature_status': 'done', 'with_record': False}, None,
          ('ready-for', 'tag', MILESTONE), (MILESTONE,), MILESTONE),
    Shape('story: nothing decidable before the work — `nothing was asked — …`',
          {'story_statuses': ('building',),
           'config': '[story]\nsteps = ["story-verified"]\n'}, None,
          ('ready-for', 'story', STORY), ('nothing',), ''),
)


@pytest.mark.parametrize('shape', SHAPES, ids=[s.why.split(':')[0] + '-'
                                               + str(i) for i, s
                                               in enumerate(SHAPES)])
def test_every_blocker_shape_the_verb_prints_is_read_the_same_way(shape: Shape):
    """Bites: `pm ready-for` rewording a sentence and this surface going dark
    with no line — the silent miss M1 named, one case per shape.

    Three shapes name no grain (a record path, a finding id, the word
    `nothing`). Those are asserted too: the reader hands them on, `against_grain`
    is `==`, and they match nothing — so the miss is bounded and visible rather
    than a surprise the next reader has to re-derive.
    """
    with tree(**shape.build) as root:
        if shape.edit is not None:
            shape.edit(root)
        code, said = run_cli(root, *shape.argv)
        assert code in (0, 1), f'{shape.why}: usage or config error — {said}'
        assert lessons.blockers_named(said) == shape.named, (
            f'{shape.why}: the verb printed {" ".join(said.split())!r}')
        if shape.grain:
            assert shape.grain in shape.named, (
                f'{shape.why}: the sentence is ABOUT {shape.grain} and the '
                f'reader did not name it')
        else:
            # A store holding a lesson against every grain this tree HAS: a
            # token the sentence led with that is not one of them must match
            # nothing, which is what keeps a non-grain harmless rather than a
            # lesson surfacing under a word nobody recorded.
            store = lessons.Store(tuple(
                lessons.lesson_of(lesson_row(grain=gid))
                for gid in (MILESTONE, FEATURE, STORY)))
            for name in shape.named:
                assert store.against_grain(name) == (), (
                    f'{shape.why}: {name!r} names no grain and matched one')


def test_the_blocked_marker_is_the_verbs_own_and_the_cap_line_names_nothing():
    """Bites the two ways the coupling breaks without a line anywhere.

    The MARKER: this reader imports `ready_for.BLOCKED` rather than spelling it,
    and reads it with sentence punctuation trimmed — so the `BLOCKED:` /
    `BLOCKED (…)` spelling every other guard in this repo uses would still be
    found. Asserted against the verb's real output, not against the constant
    alone, because the constant surviving a flatten is the actual claim.

    The CAP: past `MAX_NAMED` the verb prints one `...` line instead of the
    rest. That line must contribute NO name — a `...` read as a grain would be
    a lesson surfacing under a token nobody recorded.
    """
    with tree(story_statuses=tuple('building' for _ in range(OVER_CAP))) as root:
        code, said = run_cli(root, 'ready-for', 'feature', FEATURE)
        assert code == 1
        flat = ' '.join(said.split())
        assert ready_for.BLOCKED.strip() in flat.split(), (
            f'the marker did not survive the verb\'s own printing: {flat[:200]}')
        named = lessons.blockers_named(said)
        assert len(named) == ready_for.MAX_NAMED, (
            f'{len(named)} named off a run the verb capped at '
            f'{ready_for.MAX_NAMED}; the over-cap line added one')
        assert all(name.startswith(f'{FEATURE}/s') for name in named), named


def test_a_blocker_is_read_from_the_whole_output_not_the_clipped_detail():
    """Bites a silent miss the belt owned rather than the verb: `steps._clip`
    bounds a check's DETAIL to one line (rule 6) by keeping only the lines that
    look like a failure — so a run where ONE blocker sentence happens to contain
    `error:` dropped every other blocker before the reader saw it, and their
    lessons with them. The detail stays clipped; the blockers are read whole.
    """
    with tree(feature_status='error: it broke') as root:
        write(root / 'pm/roadmap/features/beta.md',
              {'id': '0.1/beta', 'kind': 'feature', 'milestone': f'"{MILESTONE}"',
               'name': 'Beta', 'status': 'building', 'reviewed': ''})
        cfg_for(root)  # the config caches a moved cwd invalidates
        ctx = driver.Context(root=root, operation='release',
                             version=MILESTONE)
        answer = steps.ready_for(ctx, 'milestone')

        assert not answer.is_true
        assert '0.1/beta' not in answer.detail, (
            'the fixture no longer clips — this case probes nothing')
        assert answer.names == (FEATURE, '0.1/beta'), (
            f'a blocker was dropped with the clipped line: {answer.names}')


# --- 6: the WRITE half — `agentic-sdlc lesson record|show` --------------------
# Until this feature, nothing in the package could write the row the four cases
# above read: the store was a reader of a file no verb produced. What is proven
# here is the pair D1 says has to exist together — a row lands, and it lands
# routed by grain like every other row — plus the two refusals that keep the
# store honest, both of them the ones `--review-record` already makes.

def run_lesson(root: Path, *argv: str) -> tuple[int, str]:
    """The verb through `cli.main`, so what is exercised is the surface a
    caller types rather than a function this file reached for."""
    from agentic_sdlc import cli
    cfg_for(root)  # the config caches a moved cwd invalidates
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main([cli.LESSON_VERB, *argv])
    return code, out.getvalue() + err.getvalue()


TEXT = 'a NIT that blocks is a NIT nobody writes down'


def test_a_recorded_lesson_lands_routed_by_grain_and_reads_back_verbatim():
    """The ship criterion, end to end and through the CLI: one row, in the
    ledger of the milestone that owns the grain, with the four fields the
    caller stated and nothing else — then read back by the verb beside it,
    which is the half D1 says capture is decoration without."""
    with tree() as root:
        code, out = run_lesson(root, lessons.RECORD,
                               lessons.GRAIN_FLAG, FEATURE,
                               lessons.RULE_FLAG, RULE,
                               lessons.SOURCE_FLAG, RECORD, TEXT)
        assert code == 0, out
        rows = [r for r in ledger_rows(root) if r['kind'] == lessons.KIND]
        assert len(rows) == 1, rows
        assert rows[0] == {'ts': rows[0]['ts'], 'kind': lessons.KIND,
                           'grain': FEATURE, 'rule': RULE, 'source': RECORD,
                           'text': TEXT}
        assert ledger.parse_ts(rows[0]['ts']) is not None, (
            'the stamp is `ts` and parses — a row spelled `at` sorts as the '
            'empty string and files at the beginning of time')

        code, shown = run_lesson(root, lessons.SHOW)
        assert code == 0, shown
        assert shown.splitlines()[0].split('\t') == [
            FEATURE, RULE, RECORD, TEXT, rows[0]['ts']], shown


@pytest.mark.parametrize('flags,why', [
    ((lessons.SOURCE_FLAG, 'docs/reviews/nowhere.md'),
     'a source resolving to nothing'),
    ((lessons.GRAIN_FLAG, '0.9/nobody'), 'a grain no milestone owns'),
    # A pointer that resolves on ONE machine. This ledger is committed and
    # `append_to` appends, so the row cannot be edited back out afterwards —
    # and hard rule 8 says no file here reads a path outside the checkout.
    ((lessons.SOURCE_FLAG, '../outside.md'), 'a source above the checkout'),
    ((lessons.SOURCE_FLAG, '/etc/hosts'), 'an absolute source'),
])
def test_a_pointer_resolving_to_nothing_is_refused_and_nothing_is_written(
        flags, why):
    """Exactly as `--review-record` refuses one (exit 1, nothing stamped). A
    lesson whose `source` names no file is the paraphrase D1 forbids, and one
    whose grain no ledger owns would surface at no move ever. The last two
    RESOLVE — `/etc/hosts` is a real file — and are refused anyway."""
    with tree() as root:
        argv = [lessons.RECORD, lessons.GRAIN_FLAG, FEATURE,
                lessons.RULE_FLAG, RULE, lessons.SOURCE_FLAG, RECORD, TEXT]
        argv[argv.index(flags[0]) + 1] = flags[1]
        code, out = run_lesson(root, *argv)
        assert code == 1, out
        assert 'nothing was recorded' in out, out
        assert [r for r in ledger_rows(root) if r['kind'] == lessons.KIND] \
            == [], why


@pytest.mark.parametrize('argv', [
    (lessons.RECORD,),
    (lessons.RECORD, lessons.GRAIN_FLAG, FEATURE, RULE, RECORD, TEXT),
    (lessons.RECORD, lessons.GRAIN_FLAG, FEATURE, lessons.RULE_FLAG, RULE,
     lessons.SOURCE_FLAG, RECORD),
    (lessons.RECORD, lessons.GRAIN_FLAG, FEATURE, lessons.RULE_FLAG, RULE,
     lessons.SOURCE_FLAG, RECORD, TEXT, 'and one more'),
    (lessons.RECORD, lessons.GRAIN_FLAG),
    (lessons.SHOW, FEATURE),
    (lessons.SHOW, lessons.GRAIN_FLAG, FEATURE, lessons.RULE_FLAG, RULE),
    ('learn',),
])
def test_an_incomplete_or_invented_invocation_is_exit_2_and_writes_nothing(
        argv):
    """Rule 6: usage is 2, never 1. Both filters at once is here because a
    lesson matches one column or the other EXACTLY — an implicit AND would be
    the tool deciding what the caller meant."""
    with tree() as root:
        code, out = run_lesson(root, *argv)
        assert code == 2, out
        assert [r for r in ledger_rows(root) if r['kind'] == lessons.KIND] == []


def test_show_filters_by_one_column_exactly_and_says_when_nothing_matched():
    """Rule 11's read side: `--grain` and `--rule` are the store's own two
    filters, `=` is the whole match, and nothing recorded is a LINE rather than
    a blank — a reader who cannot tell "none" from "broken" has been told
    nothing."""
    with tree() as root:
        record(root, lesson_row(grain=FEATURE, rule=RULE, text='first'),
               lesson_row(grain=STORY, rule=OTHER_RULE, text='second'))
        for flag, value, expected in (
                (lessons.GRAIN_FLAG, FEATURE, ['first']),
                (lessons.RULE_FLAG, OTHER_RULE, ['second']),
                (lessons.GRAIN_FLAG, '0.1/alph', []),
                (lessons.RULE_FLAG, RULE.upper(), [])):
            code, out = run_lesson(root, lessons.SHOW, flag, value)
            assert code == 0, out
            texts = [line.split('\t')[3] for line in out.splitlines()
                     if '\t' in line]
            assert texts == expected, out
            if not expected:
                assert f'no {lessons.WORD} recorded' in out, out
        code, out = run_lesson(root, lessons.SHOW)
        assert len([ln for ln in out.splitlines() if '\t' in ln]) == 2, out


def test_the_help_names_its_columns_in_order_and_the_reader_agrees():
    """Rule 11's read side again, and the third copy of the column list: the
    rows and the filters are one tuple, the `--help` line is prose and can
    drift, which is what this holds. The FIELDS are the minter's keys, so a
    column renamed in `ledger.py` reddens here too."""
    columns = lessons.USAGE.split('columns IN ORDER:')[1].split('\n')[0]
    assert tuple(columns.split()) == lessons.COLUMNS
    assert set(lessons.COLUMNS) == set(ledger.LESSON_KEYS) - {'kind'}
    assert 'ts' in lessons.COLUMNS and 'at' not in lessons.COLUMNS, (
        'every reader in this package keys the stamp as `ts`')
