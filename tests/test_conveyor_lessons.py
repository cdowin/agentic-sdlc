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
               at: str = TS) -> dict:
    """One `lesson` row as `ft-a-lesson-is-a-row-bound-to-a-grain` writes it —
    `{kind, grain, rule, source, text, at}` and nothing derived."""
    return {'ts': TS, 'kind': lessons.KIND, 'grain': grain, 'rule': rule,
            'source': source, 'text': text, 'at': at}


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

    def write(ctx: driver.Context, state: str) -> tuple[bool, str]:
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

    # A sink that cannot be reached, and a section that will not parse: both
    # are the emit seam's business and neither is the belt's.
    with tree() as root:
        record(root, lesson_row(grain=FEATURE))
        write_config(root, '[emit]\nsink = "events.jsonl"\n')
        (root / 'events.jsonl').mkdir()
        unreachable = belt(root, passing)
        assert unreachable.code == 0 and unreachable.writes == ['done']
        assert unreachable.taught, 'the lesson was not printed either'

        write_config(root, '[emit]\nkinds = "verdict"\n')
        malformed = belt(root, passing)
        assert malformed.code == 0 and malformed.writes == ['done']
        warnings = [line for line in malformed.taught if 'WARNING' in line]
        assert len(warnings) == 1 and 'NOT emitted' in warnings[0], (
            f'a malformed [emit] must be one named line here and never a '
            f'refused belt: {malformed.taught}')


# --- 4: several match, and nothing chooses ------------------------------------

RANKING = ('sorted', 'sort', 'rank', 'ranked', 'score', 'scored', 'confidence',
           'frequency', 'similarity', 'best', 'top')


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

    module = REPO_ROOT / 'src/agentic_sdlc/repo/conveyor/lessons.py'
    names = {node.attr if isinstance(node, ast.Attribute) else node.id
             for node in ast.walk(ast.parse(module.read_text(encoding='utf-8')))
             if isinstance(node, (ast.Name, ast.Attribute))}
    assert not names & set(RANKING), (
        f'{sorted(names & set(RANKING))} in the lesson reader — anything '
        f'inferred needs a feedback edge, and a reader/writer has nowhere to '
        f'put one (D1)')


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
