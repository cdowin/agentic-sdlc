"""test_pm_ledger_report.py — `pm ledger report`, section 1 (spend per grain).

The ledger records and never judges; the report is the caller D3 and D4 left
the judgement to. What it may do is arithmetic over rows already on disk — sum,
count, subtract, group. What it may NOT do is D5: `size:` is a column and never
a divisor, there is no dollar figure, no score and no label.

What is pinned here, and why each of these would COST something if it broke:

  * the exact table and the exact JSON for one seeded tree + one seeded ledger.
    The line shapes are a consumer contract (hard rule 6), and one golden per
    section subsumes every per-cell assertion that reads the same section;
  * **absent is not zero.** A row that carried no `cache_creation` contributes
    NOTHING to that column, and a column no row carried prints `-`. A grain no
    row names prints dashes across, because the tree is walked and not the
    ledger. A misaligned column costs nobody anything; an absent key read as a
    `0` is a wrong decision that nothing downstream can undo;
  * the clock is a SUBTRACTION and never a fabricated interval: rows in time
    order, an unparseable stamp contributing nothing, a lone row being an
    instant rather than a zero-second total, and only STATUS rows bounding it;
  * the refusal matrix (SDLC § 5). Nothing exits non-zero on a NUMBER: the one
    content refusal is a ledger line that will not parse, by line number. No
    ledger at all is exit 0 and one line, because "nothing has been recorded
    yet" is a fact about the tree.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from support.pm import (bug, decision_line, dispatch_line, ledger_lines,
                        put_ledger, run_cli, section_of, snapshot,
                        status_line, tree, write)

from agentic_sdlc.repo.pm import arrive, ledger
from agentic_sdlc.repo.pm import report as pm_report

# THE ALL-SEVEN-SEED FLOW, and why these rows keep the declaration they were
# written under rather than being rewritten: tests/test_pm_ledger.py, beside the
# same `LEGACY_FLOW`.
from support.pm import declaring as _declaring, tree as _seed_tree  # noqa: E402
from agentic_sdlc.repo.pm import model as _model  # noqa: E402

LEGACY_FLOW = _declaring(feature=_model.DEFAULT_FLOWS['milestone'],
                         story=_model.DEFAULT_FLOWS['milestone'])


def tree(**kwargs):
    """`support.pm.tree` under the all-seven flow these ledgers assume."""
    kwargs.setdefault('config', LEGACY_FLOW)
    return _seed_tree(**kwargs)

STORY = '0.1/alpha/s0'
QUIET = '0.1/alpha/s1'
FEATURE = '0.1/alpha'
BUG = '0.1/bugs/crash'


def report(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'report', *argv)


def seeded(root) -> None:
    """The fixture every shape case reads: one story worked and closed, one
    story nothing ever touched, the feature that owns them, one closed bug, and
    three dispatch rows — two agent types on the story, one naming no grain."""
    write(root / 'pm/roadmap/stories/s1.md',
          {'id': QUIET, 'feature': FEATURE, 'milestone': '"0.1"', 'name': 'S1',
           'status': 'ready', 'size': 'm'})
    bug(root, 'crash', 'closed')
    put_ledger(
        root,
        status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
        dispatch_line('2026-09-03T10:05:00Z', agent_type='developer',
                      tool_calls=37, duration_s=812,
                      usage={'input': 1200, 'output': 38000,
                             'cache_creation': 210000, 'cache_read': 9100000},
                      tree=snapshot(stories_wip=[STORY],
                                    features_building=[FEATURE])),
        status_line('2026-09-03T10:10:00Z', STORY, 'building', 'reviewing'),
        # No `tool_calls`, no `duration_s`, and one usage key only: absent is
        # not zero, and this row is what proves the columns say so.
        dispatch_line('2026-09-03T10:11:00Z', agent_type='reviewer',
                      usage={'output': 500},
                      tree=snapshot(stories_review=[STORY])),
        status_line('2026-09-03T10:12:00Z', STORY, 'reviewing', 'done'),
        status_line('2026-09-03T10:20:00Z', BUG, 'open', 'fixed'),
        status_line('2026-09-03T10:20:30Z', BUG, 'fixed', 'closed'),
        # Nothing was `wip` when this one stopped. A true statement about
        # process discipline (D3's cost note), never a dropped row.
        dispatch_line('2026-09-03T10:30:00Z', usage={'input': 5}, tool_calls=2),
    )


TABLE = """\
[ledger:report] 0.1 — spend per grain — 3 dispatch row(s), 5 status row(s), 4 grain(s)

-- story (2)
grain         size  dispatches    in    out  cache_create  cache_read  tokens_total  tool_calls  duration_s  todo  in_progress  done  total_s
0.1/alpha/s0                 2  1200  38500        210000     9100000             -          37         812     -          720     -      720
  developer                  1  1200  38000        210000     9100000             -          37         812
  reviewer                   1     -    500             -           -             -           -           -
0.1/alpha/s1  m              0     -      -             -           -             -           -           -     -            -     -        -

-- feature (1)
grain        size  dispatches    in    out  cache_create  cache_read  tokens_total  tool_calls  duration_s  todo  in_progress  done  total_s
0.1/alpha                   2  1200  38500        210000     9100000             -          37         812     -            -     -        -
  developer                 1  1200  38000        210000     9100000             -          37         812
  reviewer                  1     -    500             -           -             -           -           -

-- bug (1)
grain           size  dispatches  in  out  cache_create  cache_read  tokens_total  tool_calls  duration_s  todo  in_progress  done  total_s
0.1/bugs/crash                 0   -    -             -           -             -           -           -     -           30     -       30

-- time per state (5)
grain             building_s  reviewing_s  fixed_s  closed_s  open_s  open_state
0.1                      600          120       30       750       -  -
  0.1/alpha              600          120        -       720       -  -
    0.1/alpha/s0         600          120        -       720       -  -
    0.1/alpha/s1           -            -        -         -       -  -
  0.1/bugs/crash           -            -       30        30       -  -

-- time per actor (0)

-- rows naming no grain (1)
dispatches  in  out  cache_create  cache_read  tokens_total  tool_calls  duration_s
         1   5    -             -           -             -           2           -

[ledger:report] 0.1 — 38500 out / 39 tool calls / 812 s across 3 dispatch row(s)"""

SPEND_TITLE = 'spend per grain'
# Section 1's keys in `--json`, and the one key each later section adds.
# `legacy` landed with the category keys (decision D7): how many dispatch rows
# predate them, and how many of those named nothing.
SPEND_KEYS = ('milestone', 'section', 'grains',
              # 0.5.0/time-is-measured-per-state-and-rolls-up: the same rows
              # again, per STATE rather than per category, rolled up the
              # membership tree, with the OPEN charge beside the closed time.
              'clock',
              # 0.4.0/every-grain-is-on-a-stopwatch: per kind, how many
              # grains have not reached a terminal state and how long
              # they have been in flight. A report; nothing gates on it.
              'in_flight',
              # ...and how many status rows it could NOT place, so an empty
              # distribution can never read as a calm zero (0.4.0/C1).
              'in_flight_unplaceable',
              'unattributed',
              # 0.4.0/D8: a row STATING a grain this milestone does not
              # hold, counted apart from the ones naming none — the
              # tree's shared ledger is read by every milestone's
              # report, so this is the ordinary case, not an error.
              'stated_elsewhere', 'legacy',
              'totals')
SECTION_KEYS = ('yield', 'rework', 'escapes', 'overhead', 'gates')


def blank_usage() -> dict:
    return {key: None for key, _ in ledger.USAGE_FIELDS}


def test_the_seeded_ledger_prints_this_exact_table():
    """The whole of section 1, byte for byte — which is also every per-cell
    claim this section used to make in its own case: a grain no row names
    present and dashed, an absent usage key printing `-` and never `0`, two
    agent types split into sub-rows, and a bug's columns coming from the bug
    vocabulary. Sections 2-6 follow and are pinned in
    test_pm_ledger_report_sections.py."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        code, out = report(root, '0.1')
    assert code == 0, out
    assert section_of(out, SPEND_TITLE) == TABLE


def test_a_reported_total_is_summed_apart_from_the_split_and_says_so():
    """The half the golden above cannot show: a hand-recorded dispatch that
    reported ONE number.

    Two rows on one grain, one of each kind. The claim is subtraction as much
    as addition — `in`/`out` carry the measured split ALONE, `tokens_total`
    carries the reported one alone, and neither cell moved when the other row
    landed. Then the summary says which of the two its `out` came from and how
    many rows it therefore does not cover: a reader who takes `out` for the
    whole spend is the lie the flag exists to avoid.
    """
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(
            root,
            dispatch_line('2026-09-03T10:05:00Z', grain=STORY,
                          usage={'input': 10, 'output': 20}),
            dispatch_line('2026-09-03T10:06:00Z', grain=STORY,
                          tokens_total=1234))
        code, out = report(root, '0.1')
    assert code == 0, out
    row = [ln for ln in out.splitlines() if ln.startswith(STORY)][0].split()
    # dispatches in out cache_create cache_read tokens_total …
    assert row[1:7] == ['2', '10', '20', '-', '-', '1234'], row
    assert '1 of those row(s) reported ONE total' in out
    assert '1234 token(s)' in out
    assert '`tokens_total`' in out
    # The summary itself is unchanged: it still sums the split, and the total
    # is disclosed beside it rather than folded into it.
    assert '— 20 out / ' in out


def test_the_report_prints_every_section_in_the_milestones_order():
    """The five questions of milestone.md, then what the gates cost.

    Gate cost is SIXTH and last on purpose: the five above it are the
    milestone's own questions, in the order that document asks them, and a new
    section wedged among them would move every heading a consumer already
    slices on (hard rule 6).
    """
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        out = report(root, '0.1')[1]
    heads = [line for line in out.splitlines()
             if line.startswith('[ledger:report] 0.1 — ')
             and line.count(' — ') >= 2]
    assert [h.split(' — ')[1] for h in heads] == [
        SPEND_TITLE, 'yield per review pass', 'rework', 'escapes',
        'overhead shape', 'gate cost']


# The category columns and `total_s`, for the ledgers that could produce a
# number nobody measured. Every expectation below is the story's last four
# cells: todo in_progress done total_s. Three columns whatever the vocabulary
# (ship criterion 3 of `the-ledger-rows-carry-categories`): a stint in
# `building` and a stint in `reviewing` are one `in_progress` number.
CLOCKS = [
    # In flight: a running clock is not a duration, so no total.
    (('reviewing', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T10:10:00Z', STORY, 'building', 'reviewing')),
     ['-', '600', '-', '-']),
    # One row is an INSTANT. A span needs two rows, and the `0` a subtraction
    # produces here reads as "this was done in no time at all" — a measurement
    # nobody made, in the one column a reader compares grains by.
    (('done', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'reviewing', 'done'),),
     ['-'] * 4),
    # R3: a `decision` row NAMES a grain but does not move it, and a dispatch
    # after the terminal row cannot extend the span. Measuring from "the first
    # row that mentions it" read 4222s against 1799s of measured status time on
    # this repo's own tree — a number the state columns contradict.
    (('done', 'ready'),
     (decision_line('2026-09-03T09:00:00Z', STORY, 'D1'),
      status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T10:15:00Z', STORY, 'building', 'done'),
      dispatch_line('2026-09-03T11:00:00Z',
                    tree=snapshot(stories_wip=[STORY]))),
     ['-', '900', '-', '900']),
    # `merge=union` (D6) interleaves two branches' appends by BRANCH, so the
    # file's order is not the clock's. Read in file order this bills 3600s of
    # `reviewing` backwards and 10800s to a `building` the story spent 7200s in
    # — two numbers that look like measurements and are not. Both stints are
    # `in_progress`, so the one column sums them.
    (('done', 'ready'),
     (status_line('2026-09-03T12:00:00Z', STORY, 'building', 'reviewing'),
      status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T13:00:00Z', STORY, 'reviewing', 'done')),
     ['-', '10800', '-', '10800']),
    # A stamp that will not parse contributes no arithmetic, and no arithmetic
    # is `-`. A `0` would say the story passed through the state instantly.
    (('building', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('not-a-timestamp', STORY, 'building', 'reviewing')),
     ['-'] * 4),
    # REOPENED: `done` has a column because a grain can leave it. The stint
    # it spent finished before the reopen is a duration; the running clock
    # after its last row is not, and `obe` sits in `done` with it.
    (('done', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'building', 'obe'),
      status_line('2026-09-03T10:30:00Z', STORY, 'obe', 'ready'),
      status_line('2026-09-03T10:40:00Z', STORY, 'ready', 'done')),
     ['600', '-', '1800', '2400']),
]


@pytest.mark.parametrize('statuses,lines,expected', CLOCKS)
def test_the_clock_is_a_subtraction_and_never_a_fabricated_interval(
        statuses, lines, expected):
    with tree(story_statuses=statuses) as root:
        put_ledger(root, *lines)
        out = report(root, '0.1')[1]
    line = next(ln for ln in out.splitlines() if ln.startswith(STORY))
    assert line.split()[-4:] == expected


def test_a_snapshot_id_from_another_milestone_names_nothing_here():
    """D3 puts every live candidate on the row; the rule that reads it is this
    module's. An id that is not a grain of THIS milestone attributes to no
    grain, and the row lands in the trailing block rather than being dropped or
    silently billed to whichever grain happened to be nearby."""
    with tree(story_statuses=('building', 'ready')) as root:
        put_ledger(root, dispatch_line(
            '2026-09-03T10:00:00Z',
            tree=snapshot(stories_wip=['0.9/other/s0'],
                          features_building=['0.9/other']),
            usage={'input': 7}, tool_calls=1))
        out = report(root, '0.1')[1]
    line = next(ln for ln in out.splitlines() if ln.startswith(STORY))
    # dispatches, then the four token sums — nothing was attributed here.
    assert line.split()[1:6] == ['0', '-', '-', '-', '-']
    assert '-- rows naming no grain (1)' in out
    assert '0.9/other' not in out


def test_no_ledger_still_reports_what_the_ledger_never_held():
    """Sections 2 and 4 read the review records and the bug frontmatter —
    documents `ledger.jsonl` has nothing to do with. Saying `no ledger` and
    stopping there hides a yield of real findings and a real escape behind a
    line about a different file, which is the read-side sin: the reader is told
    there is nothing and there is something."""
    with tree() as root:
        bug(root, 'esc', caused_by=FEATURE)
        (root / 'docs/reviews/alpha.md').write_text(
            'x\n\n```text\nverdict: SHIP-WITH-FIXES\n'
            '| id | severity | disposition |\n'
            '| W1 | WARNING | landed in-place |\n```\n', encoding='utf-8')
        code, out = report(root, '0.1')
    assert code == 0, out
    assert '[ledger:report] 0.1 — no ledger' in out
    assert 'SHIP-WITH-FIXES' in out
    assert '0.1/bugs/esc' in out


def test_an_empty_no_grain_block_still_says_zero():
    """A census that saw nothing says so; silence reads as never scanned."""
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(root, status_line('2026-09-03T10:00:00Z', STORY, 'ready',
                                     'building'))
        out = report(root, '0.1')[1]
    assert '-- rows naming no grain (0)' in out


# The dwell columns with nothing measured in any of them. Written out rather
# than derived from the code under test — a golden that computes itself passes
# whatever that code says. Three keys, one per CATEGORY, for every grain kind.
EMPTY_STATES = {'todo': None, 'in_progress': None, 'done': None}


def test_the_seeded_ledger_produces_this_exact_json_object():
    """The same numbers, `null` where the table prints `-` — and `--json` is
    what a consumer parses, so a key that changed shape is a break nobody
    re-derives."""
    full = {'input': 1200, 'output': 38500, 'cache_creation': 210000,
            'cache_read': 9100000}
    dev = {'agent_type': 'developer', 'dispatches': 1,
           'usage': {'input': 1200, 'output': 38000,
                     'cache_creation': 210000, 'cache_read': 9100000},
           'tokens_total': None, 'tool_calls': 37, 'duration_s': 812}
    rev = {'agent_type': 'reviewer', 'dispatches': 1,
           'usage': dict(blank_usage(), output=500),
           'tokens_total': None, 'tool_calls': None, 'duration_s': None}
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        code, out = report(root, '0.1', '--json')
        assert code == 0, out
        assert len(out.strip().splitlines()) == 1, out
        data = json.loads(out)
    # Section 1's own keys, exactly — sections 2-6 add one key each and are
    # pinned in test_pm_ledger_report_sections.py. Compared as a SLICE rather
    # than by deleting keys, so a key section 1 stopped emitting still fails.
    assert {k: data[k] for k in SPEND_KEYS if k in data} == {
        'milestone': '0.1',
        'section': 'spend',
        'grains': [
            {'grain': STORY, 'kind': 'story', 'size': None,
             'dispatches': 2, 'usage': full, 'tokens_total': None,
             'tool_calls': 37,
             'duration_s': 812, 'agent_types': [dev, rev],
             'states': {'todo': None, 'in_progress': 720, 'done': None},
             'unplaced_s': None, 'frozen_only': None,
             'total_s': 720},
            {'grain': QUIET, 'kind': 'story', 'size': 'm',
             'dispatches': 0, 'usage': blank_usage(), 'tokens_total': None,
             'tool_calls': None,
             'duration_s': None, 'agent_types': [],
             'states': EMPTY_STATES, 'unplaced_s': None, 'frozen_only': None,
             'total_s': None},
            {'grain': FEATURE, 'kind': 'feature', 'size': None,
             'dispatches': 2, 'usage': full, 'tokens_total': None,
             'tool_calls': 37,
             'duration_s': 812, 'agent_types': [dev, rev],
             'states': EMPTY_STATES, 'unplaced_s': None, 'frozen_only': None,
             'total_s': None},
            {'grain': BUG, 'kind': 'bug', 'size': None, 'dispatches': 0,
             'usage': blank_usage(), 'tokens_total': None, 'tool_calls': None,
             'duration_s': None, 'agent_types': [],
             'states': {'todo': None, 'in_progress': 30, 'done': None},
             'unplaced_s': None, 'frozen_only': None, 'total_s': 30},
        ],
        # The clock, keyed by STATE NAME (the ship criterion's `--json`
        # clause) and rolled up: the milestone's `building` is its features',
        # which is its stories'. A state a grain never held is an ABSENT KEY
        # and never a zero, which is why `0.1/alpha/s1` carries `{}`.
        'clock': {
            'rows': [
                {'grain': '0.1', 'kind': 'milestone', 'depth': 0,
                 'state_s': {'building': 600, 'reviewing': 120, 'fixed': 30},
                 'closed_s': 750, 'open_s': None, 'open_state': None},
                {'grain': FEATURE, 'kind': 'feature', 'depth': 1,
                 'state_s': {'building': 600, 'reviewing': 120},
                 'closed_s': 720, 'open_s': None, 'open_state': None},
                {'grain': STORY, 'kind': 'story', 'depth': 2,
                 'state_s': {'building': 600, 'reviewing': 120},
                 'closed_s': 720, 'open_s': None, 'open_state': None},
                {'grain': QUIET, 'kind': 'story', 'depth': 2, 'state_s': {},
                 'closed_s': None, 'open_s': None, 'open_state': None},
                {'grain': BUG, 'kind': 'bug', 'depth': 1,
                 'state_s': {'fixed': 30}, 'closed_s': 30, 'open_s': None,
                 'open_state': None},
            ],
            'actors': []},
        'unattributed': {'dispatches': 1,
                         'usage': dict(blank_usage(), input=5),
                         'tokens_total': None,
                         'tool_calls': 2, 'duration_s': None},
        'legacy': {'rows': 0, 'unattributed': 0},
        'stated_elsewhere': 0,
        # Everything the seeded fixture touches is closed, so nothing is in
        # flight — and an EMPTY list rather than an absent key, because "none
        # in flight" is an answer and a missing key is not. It is only an
        # answer BESIDE the second number: zero rows this could not place, so
        # the emptiness is measured rather than merely reported.
        'in_flight': [],
        'in_flight_unplaceable': 0,
        # `total_rows` is 0 and `tokens_total` is null on the same object:
        # nothing here reported a total, and the summary's `out` is therefore
        # the whole of what these rows say.
        'totals': {'dispatch_rows': 3, 'status_rows': 5, 'grains': 4,
                   'total_rows': 0,
                   'usage': dict(full, input=1205), 'tokens_total': None,
                   'tool_calls': 39, 'duration_s': 812},
    }
    assert sorted(data) == sorted(SPEND_KEYS + SECTION_KEYS)


def test_json_prints_an_object_even_with_no_ledger_at_all():
    """And the totals are `null`, never `0`: a machine reader that saw zeros
    would report a milestone that measured nothing as a milestone that cost
    nothing."""
    with tree(story_statuses=('done', 'ready')) as root:
        code, out = report(root, '0.1', '--json')
        assert code == 0, out
        data = json.loads(out)
    assert data['totals'] == {
        'dispatch_rows': 0, 'status_rows': 0, 'grains': 3, 'total_rows': 0,
        'usage': blank_usage(), 'tokens_total': None, 'tool_calls': None,
        'duration_s': None}


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
    assert section_of(default[1], SPEND_TITLE) == TABLE
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
    (('0.1', '0.2'), 'one grain id'),
    (('0.1/../0.1',), 'resolves from id'),
    (('/etc/hosts',), 'resolves from id'),
    (('0.*',), 'resolves from id'),
    (('',), 'resolves from id'),
]


def test_the_refusal_matrix():
    with tree() as root:
        bug(root, 'crash')
        for argv, needle in REFUSALS:
            code, out = report(root, *argv)
            assert code == 2, (argv, out)
            assert needle in out, (argv, out)


def test_a_dropped_ARRIVAL_row_is_disclosed_whichever_kind_carries_it(frozen):
    """Rule 4, reopened by the new row kind and closed again.

    The clock reads two kinds of arrival and its discard census counted one,
    so a ledger whose arrivals are DISPOSITIONS alone — the configuration this
    feature's own criterion asserts — dropped every row naming a renamed grain
    with nothing at all saying it had.

    THE DISTRIBUTION BESIDE IT WAS DRIVEN BY NOTHING. `in_flight` was
    asserted only as `[]` over a fixture where every grain is closed, so
    `median_s`, `worst_s` and the line that renders them never executed in
    either tier: swapping the median for the worst, or mangling the printed
    sentence, stayed green across 1486 cases (0.4.0/every-grain-is-on-a-
    stopwatch M3, `bg-a-proof-row-names-a-case-that-proves-half`). Both
    numbers are one answer — a discard census over an empty distribution says
    nothing about either — so the same trees now carry three OPEN stories an
    hour apart, which is the cheapest fixture that tells a median from a
    worst: with two, `found[len // 2]` and `found[-1]` are the same row.

    Those ages are measured against the real clock rather than `frozen`'s, so
    what is pinned is the SPACING this fixture chose, which no wall clock
    moves.
    """
    gone = '0.1/alpha/renamed-away'
    ages = ('2026-09-03T10:00:00Z', '2026-09-03T09:00:00Z',
            '2026-09-03T08:00:00Z')
    open_rows = [status_line(ts, f'0.1/alpha/s{i}', 'ready', 'building')
                 for i, ts in enumerate(ages)]
    for carrier in (status_line('2026-09-03T10:00:00Z', gone, 'ready',
                                'building'),
                    disposition_line('2026-09-03T10:00:00Z', gone,
                                     'building')):
        with tree(story_statuses=('building',) * len(ages)) as root:
            put_ledger(root, carrier, *open_rows)
            data = json.loads(report(root, '0.1', '--json')[1])
            out = report(root, '0.1')[1]
        assert data['in_flight_unplaceable'] == 1, carrier
        assert f'1 arrival row(s) {pm_report.IN_FLIGHT_UNPLACEABLE}' in out
        # The placeable half: three open stories, measured and rendered.
        assert [row['kind'] for row in data['in_flight']] == ['story'], data
        entry = data['in_flight'][0]
        assert entry['in_flight'] == len(ages), entry
        # The median is the MIDDLE row and the worst the oldest, an hour
        # apart — so reading one for the other cannot render the same number
        # by accident.
        assert entry['worst_s'] - entry['median_s'] == 3600, entry
        assert f'{len(ages)} story(s) in flight — median ' \
               f'{ledger.human_duration(entry["median_s"])}, worst ' \
               f'{ledger.human_duration(entry["worst_s"])}' in out, out


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
    # The actor table narrows with the rows, or two tables under one heading
    # would answer two different questions.
    assert [a['actor'] for a in data['clock']['actors']] == ['--by me', 'none']
    assert [r['grain'] for r in story_only['clock']['rows']] == [STORY]
    assert story_only['clock']['actors'] == []
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
    appear, because nothing asked. Asserting their ABSENCE is the case: a
    status lookup left behind on this path would still refuse here, with the
    same exit code, and a needle-only assertion would pass over it.
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
    """The situation that was the loudest refusal, now an answer.

    Two milestones building is the workflow this package exists for, and the
    bare report used to call it "the one thing this verb cannot know". The
    plan knows: `order` names the current release and one milestone claims it.
    """
    with tree() as root:
        write(root / 'pm/roadmap/milestones/0.2.md',
              {'id': '"0.2"', 'name': 'Next', 'status': 'building',
               'version': '0.2.0'})
        write(root / 'pm/roadmap/milestones/0.1.md',
              {'id': '"0.1"', 'name': 'Demo', 'status': 'building',
               'version': '0.1.0'})
        # The plan lists MILESTONE IDS (0.4.0); each milestone's own
        # `version:` says which release it is.
        (root / 'pm/roadmap/releases.md').write_text(
            '---\nid: releases\norder:\n  - "0.1"\n  - "0.2"\n---\n\n'
            '# Releases\n', encoding='utf-8')
        code, out = report(root)
        assert code == 0, out
        assert '0.1' in out


# --- the boundary: rows written before the snapshot carried categories --------
OLD_SHAPE = Path(__file__).parent / 'fixtures' / 'ledger-old-shape' / 'ledger.jsonl'


def test_an_old_shape_ledger_is_read_where_it_can_be_and_disclosed_where_not():
    """Ship criteria 2 and 4 of `the-ledger-rows-carry-categories`, on a
    vendored ledger written under the OLD key shape (decision D7).

    An old row that names a grain through the frozen keys is attributed as it
    always was. An old row that names nothing HERE is a dispatch over an idle
    tree, over another milestone's work, or over a tree whose words the old
    shape could not spell — so the report says how many such rows there are,
    in the table and in `--json`, and never counts them as empty.
    A stint in a word the declaration does not name lands in no category
    column and is disclosed by grain.

    Why here and not amended into the seeded golden: the golden pins the
    CURRENT shape, and a case about the boundary has to read rows this
    package no longer writes — which is exactly what a vendored fixture is
    for (hard rule 8).
    """
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(root, *OLD_SHAPE.read_text('utf-8').splitlines())
        code, out = report(root, '0.1')
        assert code == 0, out
        data = json.loads(report(root, '0.1', '--json')[1])
    story = next(e for e in data['grains'] if e['grain'] == STORY)
    # Readable: the `stories_wip` row is the story's, as it always was.
    assert story['dispatches'] == 1
    assert story['usage']['output'] == 2000
    # Disclosed: two of the three dispatch rows predate categories and name
    # nothing; the third predates them too and is readable.
    assert data['legacy'] == {'rows': 3, 'unattributed': 2}
    assert data['unattributed']['dispatches'] == 2
    assert '-- rows naming no grain (2)' in out
    assert ('   2 of these predate category keys and name no grain of this '
            "milestone — an idle tree, another milestone's work, or words "
            'that shape could not spell; not counted as empty' in out)
    # The stint at `review` — a word the seed does not declare — is in no
    # column, and it is said so rather than summed into `in_progress`.
    assert story['states'] == {'todo': None, 'in_progress': 600, 'done': None}
    assert story['unplaced_s'] == 1200
    assert (f'   {STORY} spent time in a state this declaration does not name '
            f'— seconds in no category column, not zero: 1200 s' in out)
    assert story['total_s'] == 1800


def test_a_current_shape_ledger_discloses_no_boundary():
    """The disclosure line is for the boundary and nothing else: a ledger
    whose every dispatch row carries the category keys prints no such line,
    and `legacy` reports zero rows — a number, never an absent key.

    And the one thing a current-shape row CAN drop is disclosed the same way.
    A new row carries both key families; under the stock seed a story at
    `reviewing` — a word its kind no longer declares — is in `stories_review`
    and not in `stories_in_progress`, and the report reads the category key.
    The number is right (nothing was in progress under this declaration) and
    the silence was not: before this case the story printed `dispatches 0`
    and nothing said a row had named it. Built on `support.pm.tree` directly
    because this module's `tree` declares `reviewing` for stories, and the
    two families only disagree when the declaration cannot place the word.
    """
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        code, out = report(root, '0.1')
        data = json.loads(report(root, '0.1', '--json')[1])
    assert code == 0, out
    assert 'predate category keys' not in out
    assert 'deprecated key' not in out
    assert data['legacy'] == {'rows': 0, 'unattributed': 0}
    assert all(e['frozen_only'] is None for e in data['grains'])
    with _seed_tree(story_statuses=('reviewing',)) as root:
        put_ledger(root, dispatch_line(
            '2026-09-03T10:05:00Z', usage={'output': 700}, tool_calls=3,
            tree=snapshot(stories_review=[STORY], stories_in_progress=[],
                          features_in_progress=[FEATURE])))
        code, out = report(root, '0.1')
        data = json.loads(report(root, '0.1', '--json')[1])
    assert code == 0, out
    story = next(e for e in data['grains'] if e['grain'] == STORY)
    # Not attributed — the category key is the declaration's answer — and
    # not silent: the drop is a number beside the column it is missing from.
    assert story['dispatches'] == 0
    assert story['frozen_only'] == 1
    assert (f'   {STORY} named only through a deprecated key — at a word this '
            'declaration does not place in in_progress, so counted in no '
            'column above: 1 dispatch row(s)' in out)
    # The feature named itself through its own category key, so nothing was
    # dropped there; and this is not the old-shape boundary.
    feature = next(e for e in data['grains'] if e['grain'] == FEATURE)
    assert feature['dispatches'] == 1 and feature['frozen_only'] is None
    assert data['legacy'] == {'rows': 0, 'unattributed': 0}


# --- the clock, per STATE and rolled up ---------------------------------------
# `pm ledger report` summed seconds per CATEGORY, and `building` and `reviewing`
# are both `in_progress` — so the tool collapsed exactly the distinction anyone
# asks about. What is pinned below is the four claims the feature makes that the
# category columns above cannot make:
#
#   * the sum is a WALK. A milestone's building time is its features', which is
#     its stories', and each level is the level below PLUS its own;
#   * OPEN time is a CHARGE. A running clock and a finished one are different
#     facts, so no grain gets completed-time credit until it closes, and the
#     charge rolls up so the pressure line has one number to name;
#   * a state a grain never held contributes NO KEY, never a zero;
#   * and all of it comes off ARRIVAL rows alone — the one event (D3) — on a
#     tree where no harness hook has ever fired, which is this repo's own
#     condition and the claim the ship criterion actually makes.
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
    block heading, because the spend tables above name the same grains."""
    block = section_of(out, SPEND_TITLE).split(f'-- {pm_report.CLOCK_TITLE}')
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

    Time per state and spend per actor, off ARRIVAL rows alone: not one
    dispatch, session or gate row in the ledger, because the tree records
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
        data = json.loads(report(root, '0.1', '--json')[1])
    assert ledger.KIND_DISPATCH not in raw and ledger.KIND_GATE not in raw
    assert rows[STORY]['state_s'] == {'building': 600, 'reviewing': 120}
    assert rows[FEATURE]['state_s'] == {'building': 600, 'reviewing': 120}
    # Spend per actor, from the same rows: the answer AS TYPED, the arrivals
    # it opened, and the seconds those stints ran. A move nobody answered is
    # `none` — named, because that is what `check pm`'s U5 counts — and it
    # opened no stint, so it is charged no seconds rather than a zero.
    assert data['clock']['actors'] == [
        {'actor': '--by agent developer', 'arrivals': 1, 'grains': 1,
         'seconds': 600},
        {'actor': '--review agent reviewer', 'arrivals': 1, 'grains': 1,
         'seconds': 120},
        {'actor': 'none', 'arrivals': 1, 'grains': 1, 'seconds': None},
    ]


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
