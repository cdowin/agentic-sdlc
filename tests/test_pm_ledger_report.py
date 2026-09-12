"""test_pm_ledger_report.py — `pm ledger report <milestone>`: the stamp table.

The ledger records and never judges; the report is the caller D3 and D4 left
the judgement to. What it may do is arithmetic over rows already on disk — sum,
count, subtract, group — and it reads ONLY the rows the milestone owns
(`ft-a-milestone-reports-only-its-own-rows`).

What is pinned here, and why each of these would COST something if it broke:

  * the exact report and the exact JSON for one seeded tree + one seeded
    ledger. The line shapes are a consumer contract (hard rule 6): the units
    table, one column family per claim (a stamp pair, a dispatch unit whose
    start is a subtraction, an open unit, an issue list, an outcome), the
    agents and their share, the clock, and every count line;
  * **absent is not zero.** A unit nobody stopped has no stop and no
    duration; a dispatch that measured only the split has no `tokens`;
  * the clock is a SUBTRACTION and never a fabricated interval: rows in time
    order, an unparseable stamp contributing nothing, a lone row being an
    instant rather than a zero-second total;
  * the refusal matrix (SDLC § 5). Nothing exits non-zero on a NUMBER: the one
    content refusal is a ledger line that will not parse, by line number. No
    ledger at all is exit 0 and one line.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from support.pm import (bug, decision_line, dispatch_line, ledger_lines,
                        put_ledger, run_cli, session_line,
                        snapshot, status_line, write)

from agentic_sdlc.repo.pm import arrive, ledger
from agentic_sdlc.repo.pm import report as pm_report

# THE ALL-SEVEN-SEED FLOW, and why these rows keep the declaration they were
# written under rather than being rewritten: tests/test_pm_ledger.py, beside the
# same `LEGACY_FLOW`.
from support.pm import declaring as _declaring, tree as _seed_tree  # noqa: E402
from agentic_sdlc.repo.pm import vocabulary  # noqa: E402

LEGACY_FLOW = _declaring(feature=vocabulary.DEFAULT_FLOWS['milestone'],
                         story=vocabulary.DEFAULT_FLOWS['milestone'])


def tree(**kwargs):
    """`support.pm.tree` under the all-seven flow these ledgers assume."""
    kwargs.setdefault('config', LEGACY_FLOW)
    return _seed_tree(**kwargs)

STORY = '0.1/alpha/s0'
QUIET = '0.1/alpha/s1'
FEATURE = '0.1/alpha'
BUG = '0.1/bugs/crash'
GONE = '0.1/alpha/gone'


def report(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'report', *argv)


def stamp_line(ts: str, grain: str, edge: str, **fields: object) -> str:
    """A `stamp` row as the 0.10.0 contract writes it — planted as JSON, so
    this reader is proven against the CONTRACT rather than one writer."""
    return json.dumps({'ts': ts, 'kind': 'stamp', 'grain': grain,
                       'edge': edge, **fields})


def seeded(root) -> None:
    """The fixture every shape case reads: one story worked and closed through
    a stamp pair and two dispatches, one story with an OPEN unit, a stop with
    no start, a dispatch on a grain the milestone no longer holds, a session
    row naming nothing, and one closed bug."""
    bug(root, 'crash', 'closed')
    put_ledger(
        root,
        status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
        stamp_line('2026-09-03T10:00:30Z', STORY, 'start', issue=['#41'],
                   agent='developer'),
        dispatch_line('2026-09-03T10:05:00Z', grain=STORY,
                      agent_type='developer', duration_s=300,
                      tokens_total=4000),
        stamp_line('2026-09-03T10:09:00Z', STORY, 'stop', issue=['#41'],
                   agent='developer', tokens=6000, outcome='landed'),
        status_line('2026-09-03T10:10:00Z', STORY, 'building', 'reviewing'),
        # The measured SPLIT is not `tokens`: only a reported total is.
        dispatch_line('2026-09-03T10:11:00Z', grain=STORY,
                      agent_type='reviewer', tokens_total=2500,
                      usage={'output': 500}),
        status_line('2026-09-03T10:12:00Z', STORY, 'reviewing', 'done'),
        status_line('2026-09-03T10:20:00Z', BUG, 'open', 'fixed'),
        status_line('2026-09-03T10:20:30Z', BUG, 'fixed', 'closed'),
        stamp_line('2026-09-03T10:25:00Z', QUIET, 'start',
                   issue=['#42', '#43'], agent='developer'),
        stamp_line('2026-09-03T10:26:00Z', FEATURE, 'stop', tokens=10),
        dispatch_line('2026-09-03T10:30:00Z', grain=GONE,
                      agent_type='developer', tokens_total=700),
        session_line('2026-09-03T10:40:00Z', session_id='sess-1'),
    )


TABLE = """\
[ledger:report] 0.1 — stamp table — 4 unit(s), 1 open unit(s), 12500 token(s)

-- units (4)
unit  grain         issue    agent      start                 stop                  duration  tokens  outcome
   1  0.1/alpha/s0  -        developer  2026-09-03T10:00:00Z  2026-09-03T10:05:00Z       300    4000  -
   2  0.1/alpha/s0  #41      developer  2026-09-03T10:00:30Z  2026-09-03T10:09:00Z       510    6000  landed
   3  0.1/alpha/s0  -        reviewer   -                     2026-09-03T10:11:00Z         -    2500  -
   4  0.1/alpha/s1  #42,#43  developer  2026-09-03T10:25:00Z  -                            -       -  -

-- by agent (2)
agent      units  tokens  duration  share
developer      3   10000       810    80%
reviewer       1    2500         -    20%

-- time per state (5)
grain             building_s  reviewing_s  fixed_s  closed_s  open_s  open_state
0.1                      600          120       30       750       -  -
  0.1/alpha              600          120        -       720       -  -
    0.1/alpha/s0         600          120        -       720       -  -
    0.1/alpha/s1           -            -        -         -       -  -
  0.1/bugs/crash           -            -       30        30       -  -

   11 row(s) this milestone owns: dispatch 2, stamp 4, status 5 — by grain; no `branch:` declared, so no row naming no grain is placed here by branch
   1 stamp row(s) pair with nothing — a stop with no open start on its grain, or an edge that is neither; counted in no unit
   superseded spend: 1 row(s), 700 token(s) in this milestone's ledger naming a grain it does not hold: 0.1/alpha/gone
   1 row(s) in this milestone's ledger name no grain and no branch it declares — counted in no unit
   0 courier/hand pair(s) joined by agent_id — one dispatch each, on the hand row's grain with the courier row's measured spend"""

STAMP_TITLE = pm_report.STAMP_TITLE


def test_the_seeded_ledger_prints_this_exact_table():
    """The whole report, byte for byte — which is also every per-cell claim:
    a stamp pair is one unit, a dispatch's start is `ts - duration_s` and
    blank without one, an open unit prints `-` for its stop and duration, a
    unit's issues are one comma-joined cell, `tokens` is a reported total and
    never the measured split, `share` is of the tokens the units recorded,
    and every row the units do not hold is COUNTED on a named line."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        code, out = report(root, '0.1')
    assert code == 0, out
    assert out.rstrip('\n') == TABLE


def test_the_seeded_ledger_produces_this_exact_json_object():
    """The same rows, `null` where the table prints `-` — and `--json` is
    what a consumer parses, so a key that changed shape is a break nobody
    re-derives."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        code, out = report(root, '0.1', '--json')
    assert code == 0, out
    assert len(out.strip().splitlines()) == 1, out
    data = json.loads(out)
    assert sorted(data) == ['agents', 'branch', 'clock', 'grains', 'joined',
                            'milestone', 'no_grain', 'owned', 'superseded',
                            'units', 'unpaired']
    assert data['units'][1] == {
        'unit': 2, 'grain': STORY, 'issue': ['#41'], 'agent': 'developer',
        'start': '2026-09-03T10:00:30Z', 'stop': '2026-09-03T10:09:00Z',
        'duration': 510, 'tokens': 6000, 'outcome': 'landed', 'kind': 'stamp'}
    assert data['units'][3]['stop'] is None
    assert data['units'][3]['duration'] is None
    assert data['agents'][1] == {'agent': 'reviewer', 'units': 1,
                                 'tokens': 2500, 'duration': None, 'share': 20}
    assert {k: data[k] for k in ('branch', 'grains', 'joined', 'owned',
                                 'unpaired', 'superseded', 'no_grain')} == {
        'branch': None, 'grains': 4, 'joined': 0,
        'owned': {'dispatch': 2, 'stamp': 4, 'status': 5}, 'unpaired': 1,
        'superseded': {'rows': 1, 'tokens': 700, 'grains': [GONE]},
        'no_grain': 1}


def test_json_prints_an_object_even_with_no_ledger_at_all():
    """No units is an empty list and every count a number — a zero, because
    each is a COUNT of rows, and the census of rows read was zero."""
    with tree(story_statuses=('done', 'ready')) as root:
        code, out = report(root, '0.1', '--json')
        assert code == 0, out
        data = json.loads(out)
    assert (data['units'], data['agents'], data['owned']) == ([], [], {})
    assert (data['unpaired'], data['no_grain']) == (0, 0)
    assert data['superseded'] == {'rows': 0, 'tokens': None, 'grains': []}


def test_which_milestones_ledger_is_read():
    """The building one by default, the one you named when you name it — and
    `no ledger` is exit 0 and ONE line, because "nothing has been recorded
    yet" is a fact about the tree and not an error."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        write(root / 'pm/roadmap/milestones/0.2.md',
              {'id': '"0.2"', 'name': 'Next', 'status': 'planning'})
        named = report(root, '0.1')
        default = report(root)
        other = report(root, '0.2')
    assert default[0] == 0, default[1]
    assert default == named
    assert default[1].rstrip('\n') == TABLE
    assert other[0] == 0, other[1]
    assert other[1].strip() == '[ledger:report] 0.2 — no ledger'


def test_a_malformed_ledger_line_names_its_line_number():
    """The one content refusal, in both output modes. A reader that skipped
    the line would print a table with a hole in it and no way to know."""
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(root,
                   status_line('2026-09-03T10:00:00Z', STORY, 'ready',
                               'building'),
                   '{not json',
                   status_line('2026-09-03T10:01:00Z', STORY, 'building',
                               'reviewing'))
        for argv in (('0.1',), ('0.1', '--json')):
            code, out = report(root, *argv)
            assert code == 2, out
            assert 'line 2' in out


# SDLC § 5's matrix. Exit 2 on input, never on a number — one representative
# per refusal rather than per spelling: the id grammar is the shared resolver's
# (`pm get`/`pm set`/`ledger show` use the same one) and cannot answer
# differently here than there.
REFUSALS = [
    (('0.9',), 'no grain resolves'),
    (('--wombat',), 'unknown flag'),
    # Neither spelling is a flag here, and a verb that quietly accepted one
    # would be inventing a grammar its own --help does not print.
    (('--json=1',), 'unknown flag'),
    # Two ids is a COMPARISON, so what refuses here is the SECOND id naming no
    # grain in this tree. The comparison's own matrix is in
    # tests/test_pm_ledger_report_sections.py.
    (('0.1', '0.2'), "no grain resolves from id '0.2'"),
    (('0.1/../0.1',), 'resolves from id'),
    (('/etc/hosts',), 'resolves from id'),
    (('0.*',), 'resolves from id'),
    (('',), 'resolves from id'),
    # The tree's report is about no milestone, so it takes none.
    (('--tree', '0.1'), '--tree reports the rows no milestone owns'),
]


def test_the_refusal_matrix():
    with tree() as root:
        bug(root, 'crash')
        for argv, needle in REFUSALS:
            code, out = report(root, *argv)
            assert code == 2, (argv, out)
            assert needle in out, (argv, out)


# The clock over ledgers that could produce a number nobody measured. Every
# expectation is the story's `state_s`: seconds per state it LEFT, by
# subtraction, and no key for a state it never finished a stint in.
CLOCKS = [
    # In flight: a running clock is not a duration, so only the closed stint.
    (('reviewing', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T10:10:00Z', STORY, 'building', 'reviewing')),
     {'building': 600}),
    # One row is an INSTANT. A span needs two rows, and the `0` a subtraction
    # produces here reads as "this was done in no time at all".
    (('done', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'reviewing', 'done'),),
     {}),
    # R3: a `decision` row NAMES a grain but does not move it, and a dispatch
    # after the terminal row cannot extend the span.
    (('done', 'ready'),
     (decision_line('2026-09-03T09:00:00Z', STORY, 'D1'),
      status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T10:15:00Z', STORY, 'building', 'done'),
      dispatch_line('2026-09-03T11:00:00Z',
                    tree=snapshot(stories_wip=[STORY]))),
     {'building': 900}),
    # `merge=union` (D6) interleaves two branches' appends by BRANCH, so the
    # file's order is not the clock's. Read in file order this bills 3600s of
    # `reviewing` backwards.
    (('done', 'ready'),
     (status_line('2026-09-03T12:00:00Z', STORY, 'building', 'reviewing'),
      status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T13:00:00Z', STORY, 'reviewing', 'done')),
     {'building': 7200, 'reviewing': 3600}),
    # A stamp that will not parse contributes no arithmetic, and no arithmetic
    # is no key. A `0` would say the story passed through the state instantly.
    (('building', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('not-a-timestamp', STORY, 'building', 'reviewing')),
     {}),
    # REOPENED: a grain can leave `done`-side states, and each finished stint
    # is a duration.
    (('done', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'building', 'obe'),
      status_line('2026-09-03T10:30:00Z', STORY, 'obe', 'ready'),
      status_line('2026-09-03T10:40:00Z', STORY, 'ready', 'done')),
     {'obe': 1800, 'ready': 600}),
]


@pytest.mark.parametrize('statuses,lines,expected', CLOCKS)
def test_the_clock_is_a_subtraction_and_never_a_fabricated_interval(
        statuses, lines, expected):
    with tree(story_statuses=statuses) as root:
        put_ledger(root, *lines)
        assert clock_of(root)[STORY]['state_s'] == expected


def test_the_id_names_the_LEVEL_and_a_feature_reports_its_own_subtree(frozen):
    """The criterion's first sentence: *at whatever level the id names*.

    A feature id used to be exit 2 — "the ledger is per milestone" — which is
    true of where the ROWS are and says nothing about which level a reader
    asked for. The ledger stays the milestone's; the table roots at the grain
    the id named, and stops at its own descendants.
    """
    with tree(story_statuses=('done', 'done')) as root:
        put_ledger(
            root,
            status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
            status_line('2026-09-03T10:10:00Z', STORY, 'building', 'done'),
            disposition_line('2026-09-03T10:00:00Z', QUIET, 'building',
                             '--by', 'me'),
            disposition_line('2026-09-03T10:05:00Z', QUIET, 'done'),
        )
        code, out = report(root, FEATURE)
        assert code == 0, out
        data = json.loads(report(root, FEATURE, '--json')[1])
        story_only = json.loads(report(root, STORY, '--json')[1])
    assert data['focus'] == FEATURE and data['milestone'] == '0.1'
    rows = data['clock']['rows']
    # The feature roots the table at depth 0, its two stories hang under it,
    # and the milestone and its other grains are not in it.
    assert [(r['grain'], r['depth']) for r in rows] == [
        (FEATURE, 0), (STORY, 1), (QUIET, 1)]
    assert rows[0]['state_s'] == {'building': 900}
    assert [r['grain'] for r in story_only['clock']['rows']] == [STORY]
    assert f'{FEATURE} — {pm_report.CLOCK_TITLE}' in out


@pytest.mark.parametrize('kwargs,second', [
    (dict(milestone_status='planning'), False),
    (dict(), True),
])
def test_a_bare_report_asks_the_plan_and_never_a_status(kwargs, second):
    """0.4.0/D1 — INVERTED from `…cannot_choose_is_named`, deliberately.

    Both rows used to BE the refusal: "no milestone is in progress" and "2
    milestones are in progress". Neither is a question any more, on any path,
    so the refusal that remains is the PLAN's — there is nothing to file
    against because nothing was scheduled — and the two old sentences must not
    appear, because nothing asked.
    """
    with tree(**kwargs) as root:
        if second:
            write(root / 'pm/roadmap/milestones/0.2.md',
                  {'id': '"0.2"', 'name': 'Next', 'status': 'building'})
        code, out = report(root)
        assert code == 2, out
        assert 'declares no `order`' in out
        assert 'in progress' not in out, 'a status lookup survived'
        assert 'pm ledger report <milestone-id>' in out
        assert report(root, '0.1')[0] == 0


def test_two_milestones_in_progress_is_answered_from_the_plan():
    """The situation that was the loudest refusal, now an answer: `order`
    names the current release and one milestone claims it."""
    with tree() as root:
        write(root / 'pm/roadmap/milestones/0.2.md',
              {'id': '"0.2"', 'name': 'Next', 'status': 'building',
               'version': '0.2.0'})
        write(root / 'pm/roadmap/milestones/0.1.md',
              {'id': '"0.1"', 'name': 'Demo', 'status': 'building',
               'version': '0.1.0'})
        (root / 'pm/roadmap/releases.md').write_text(
            '---\nid: releases\norder:\n  - "0.1"\n  - "0.2"\n---\n\n'
            '# Releases\n', encoding='utf-8')
        code, out = report(root)
        assert code == 0, out
        assert '0.1' in out


# --- the boundary: rows written before the snapshot carried categories --------
OLD_SHAPE = Path(__file__).parent / 'fixtures' / 'ledger-old-shape' / 'ledger.jsonl'


def test_an_old_shape_ledger_is_read_where_it_can_be_and_counted_where_not():
    """A vendored ledger written under the OLD key shape (decision D7).

    An old row that names a grain through the frozen keys is placed as it
    always was — one unit on that story. An old row that names nothing HERE
    is counted on the no-grain line and folded into no unit.
    """
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(root, *OLD_SHAPE.read_text('utf-8').splitlines())
        data = json.loads(report(root, '0.1', '--json')[1])
    assert [(u['grain'], u['agent'], u['duration']) for u in data['units']] \
        == [(STORY, 'developer', 300)]
    assert data['no_grain'] == 2
    assert data['owned'] == {'dispatch': 1, 'status': 3}


# --- the clock, per STATE and rolled up ---------------------------------------
# What is pinned below is the claims the clock makes:
#
#   * the sum is a WALK. A milestone's building time is its features', which is
#     its stories', and each level is the level below PLUS its own;
#   * OPEN time is a CHARGE. A running clock and a finished one are different
#     facts, so no grain gets completed-time credit until it closes, and the
#     charge rolls up so the pressure line has one number to name;
#   * a state a grain never held contributes NO KEY, never a zero;
#   * and all of it comes off ARRIVAL rows alone — the one event (D3) — on a
#     tree where no harness hook has ever fired.
NOW = datetime(2026, 9, 3, 11, 0, 0, tzinfo=timezone.utc)
DASH = pm_report.DASH


def disposition_line(ts: str, grain: str, state: str,
                     answer: str = ledger.NO_DISPOSITION,
                     value: str = '') -> str:
    """The row an ARRIVAL mints (D3/D6) — the half of a move no hook is
    involved in. Built through `ledger.disposition_row`, like every other
    fixture line here, so a shape that drifted from the writer would fail."""
    return ledger.dumps(ledger.disposition_row(
        grain, state, arrive.Said(answer, value), ts=ts))


@pytest.fixture
def frozen(monkeypatch):
    """Read time held still. An open charge is measured against NOW, and a
    case whose expectation moved every second would prove nothing."""
    monkeypatch.setattr(pm_report, '_now', lambda: NOW)
    return NOW


def clock_line(out: str, gid: str) -> str:
    """One grain's row out of the printed clock block. Sliced from the
    block heading, because the units table above names the same grains."""
    block = out.split(f'-- {pm_report.CLOCK_TITLE}')
    return next(ln for ln in block[1].splitlines()
                if ln.strip().startswith(gid))


def clock_of(root, mid: str = '0.1') -> dict:
    """`{grain id: its clock row}` out of `--json`."""
    code, out = report(root, mid, '--json')
    assert code == 0, out
    return {row['grain']: row for row in json.loads(out)['clock']['rows']}


def test_each_levels_time_in_a_state_is_the_level_below_plus_its_own(frozen):
    """Roll-up is the FEATURE, not a view.

    Membership is already a field (0.4.0), so the sum is a walk and not a
    join — and the number a milestone reports for `building` is the one
    somebody actually asks for, rather than its own four minutes of it.
    """
    with tree(story_statuses=('done', 'done')) as root:
        put_ledger(
            root,
            # The milestone's OWN minute, before anything under it moved.
            status_line('2026-09-03T09:59:00Z', '0.1', 'planning', 'building'),
            status_line('2026-09-03T10:00:00Z', '0.1', 'building', 'done'),
            # The feature's own twenty, which no story spent.
            status_line('2026-09-03T10:00:00Z', FEATURE, 'ready', 'building'),
            status_line('2026-09-03T10:20:00Z', FEATURE, 'building', 'done'),
            status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
            status_line('2026-09-03T10:10:00Z', STORY, 'building', 'done'),
            status_line('2026-09-03T10:00:00Z', QUIET, 'ready', 'building'),
            status_line('2026-09-03T10:05:00Z', QUIET, 'building', 'done'),
        )
        rows = clock_of(root)
    assert rows[STORY]['state_s'] == {'building': 600}
    assert rows[QUIET]['state_s'] == {'building': 300}
    # 1200 of its own, plus 600 and 300 from the two stories it owns.
    assert rows[FEATURE]['state_s'] == {'building': 2100}
    assert rows[FEATURE]['closed_s'] == 2100
    # 60 of its own, plus the feature's rolled 2100.
    assert rows['0.1']['state_s'] == {'building': 2160}
    # Nothing here ever held `reviewing`, and an absent key is what says so:
    # a `0` would be a measurement nobody made in the column a reader
    # compares grains by.
    assert 'reviewing' not in rows['0.1']['state_s']


def test_open_time_is_a_charge_and_nothing_gets_credit_until_it_closes(frozen):
    """A grain that has been `building` for an hour with nothing recorded is
    accruing cost, and the number belongs in front of whoever decides next.

    The report used to show a dash there. A dash is not a number (rule 11),
    and folding the hour into `building_s` would say the work is finished
    (rule 4) — so it is a column of its own, named with the state it is
    accruing in, and it rolls up so the pressure line has one number.
    """
    with tree(story_statuses=('building', 'ready')) as root:
        put_ledger(root, status_line('2026-09-03T10:00:00Z', STORY,
                                     'ready', 'building'))
        rows = clock_of(root)
        out = report(root, '0.1')[1]
    assert rows[STORY]['state_s'] == {}
    assert rows[STORY]['closed_s'] is None
    assert rows[STORY]['open_s'] == 3600
    assert rows[STORY]['open_state'] == 'building'
    # The milestone's charge is the sum of its open children's; the milestone
    # itself was never moved, so it sits in no state of its own.
    assert rows['0.1']['open_s'] == 3600
    assert rows['0.1']['open_state'] is None
    # A grain nobody has ever moved is UNMEASURED, never zero.
    assert rows[QUIET]['open_s'] is None
    assert clock_line(out, STORY).split()[-3:] == [DASH, '3600',
                                                   'building']


def test_the_clock_is_complete_on_a_tree_no_hook_has_ever_touched(frozen):
    """The ship criterion's real claim, and this milestone's own condition.

    Time per state, off ARRIVAL rows alone: not one dispatch, session or gate
    row in the ledger, because the tree records
    itself. If this needed a hook-written row to be right, the feature has
    failed — telemetry that depends on something outside the tree is the hole
    the disposition row exists to close.
    """
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(
            root,
            status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
            disposition_line('2026-09-03T10:00:00Z', STORY, 'building',
                             '--by', 'agent developer'),
            status_line('2026-09-03T10:10:00Z', STORY, 'building', 'reviewing'),
            disposition_line('2026-09-03T10:10:00Z', STORY, 'reviewing',
                             '--review', 'agent reviewer'),
            status_line('2026-09-03T10:12:00Z', STORY, 'reviewing', 'done'),
            disposition_line('2026-09-03T10:12:00Z', STORY, 'done'),
        )
        raw = ' '.join(ledger_lines(root))
        rows = clock_of(root)
    assert ledger.KIND_DISPATCH not in raw and ledger.KIND_GATE not in raw
    assert rows[STORY]['state_s'] == {'building': 600, 'reviewing': 120}
    assert rows[FEATURE]['state_s'] == {'building': 600, 'reviewing': 120}


def test_one_move_is_one_arrival_however_many_rows_carry_it(frozen):
    """A move writes a `status` row AND a `disposition` row at one instant,
    and they are ONE event (D3). Walking both would bill the same stint twice
    — so the repeat is folded, and a ledger holding either half alone measures
    the same seconds.
    """
    pair = (status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
            disposition_line('2026-09-03T10:00:00Z', STORY, 'building'),
            status_line('2026-09-03T10:10:00Z', STORY, 'building', 'done'),
            disposition_line('2026-09-03T10:10:00Z', STORY, 'done'))
    measured = []
    for lines in (pair, pair[1::2], pair[0::2]):
        with tree(story_statuses=('done', 'ready')) as root:
            put_ledger(root, *lines)
            measured.append(clock_of(root)[STORY]['state_s'])
    assert measured == [{'building': 600}] * 3
