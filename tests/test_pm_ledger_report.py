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

import pytest
from support.pm import (bug, decision_line, dispatch_line, put_ledger, run_cli,
                        section_of, snapshot, status_line, tree, write)

from agentic_sdlc.repo.pm import ledger

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
    write(root / 'pm/roadmap/0.1-demo/features/alpha/stories/s1.md',
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
grain         size  dispatches    in    out  cache_create  cache_read  tool_calls  duration_s  planning  ready  building  reviewing  accepted  packaging  total_s
0.1/alpha/s0                 2  1200  38500        210000     9100000          37         812         -      -       600        120         -          -      720
  developer                  1  1200  38000        210000     9100000          37         812
  reviewer                   1     -    500             -           -           -           -
0.1/alpha/s1  m              0     -      -             -           -           -           -         -      -         -          -         -          -        -

-- feature (1)
grain        size  dispatches    in    out  cache_create  cache_read  tool_calls  duration_s  planning  ready  building  reviewing  accepted  packaging  total_s
0.1/alpha                   2  1200  38500        210000     9100000          37         812         -      -         -          -         -          -        -
  developer                 1  1200  38000        210000     9100000          37         812
  reviewer                  1     -    500             -           -           -           -

-- bug (1)
grain           size  dispatches  in  out  cache_create  cache_read  tool_calls  duration_s  open  fixed  total_s
0.1/bugs/crash                 0   -    -             -           -           -           -     -     30       30

-- rows naming no grain (1)
dispatches  in  out  cache_create  cache_read  tool_calls  duration_s
         1   5    -             -           -           2           -

[ledger:report] 0.1 — 38500 out / 39 tool calls / 812 s across 3 dispatch row(s)"""

SPEND_TITLE = 'spend per grain'
# Section 1's keys in `--json`, and the one key each later section adds.
SPEND_KEYS = ('milestone', 'section', 'grains', 'unattributed', 'totals')
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


# The state columns and `total_s`, for the ledgers that could produce a number
# nobody measured. Every expectation below is the story's last seven cells:
# planning ready building reviewing accepted packaging total_s.
CLOCKS = [
    # In flight: a running clock is not a duration, so no total.
    (('reviewing', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T10:10:00Z', STORY, 'building', 'reviewing')),
     ['-', '-', '600', '-', '-', '-', '-']),
    # One row is an INSTANT. A span needs two rows, and the `0` a subtraction
    # produces here reads as "this was done in no time at all" — a measurement
    # nobody made, in the one column a reader compares grains by.
    (('done', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'reviewing', 'done'),),
     ['-'] * 7),
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
     ['-', '-', '900', '-', '-', '-', '900']),
    # `merge=union` (D6) interleaves two branches' appends by BRANCH, so the
    # file's order is not the clock's. Read in file order this bills 3600s of
    # `reviewing` backwards and 10800s to a `building` the story spent 7200s in
    # — two numbers that look like measurements and are not.
    (('done', 'ready'),
     (status_line('2026-09-03T12:00:00Z', STORY, 'building', 'reviewing'),
      status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('2026-09-03T13:00:00Z', STORY, 'reviewing', 'done')),
     ['-', '-', '7200', '3600', '-', '-', '10800']),
    # A stamp that will not parse contributes no arithmetic, and no arithmetic
    # is `-`. A `0` would say the story passed through the state instantly.
    (('building', 'ready'),
     (status_line('2026-09-03T10:00:00Z', STORY, 'ready', 'building'),
      status_line('not-a-timestamp', STORY, 'building', 'reviewing')),
     ['-'] * 7),
]


@pytest.mark.parametrize('statuses,lines,expected', CLOCKS)
def test_the_clock_is_a_subtraction_and_never_a_fabricated_interval(
        statuses, lines, expected):
    with tree(story_statuses=statuses) as root:
        put_ledger(root, *lines)
        out = report(root, '0.1')[1]
    line = next(ln for ln in out.splitlines() if ln.startswith(STORY))
    assert line.split()[-7:] == expected


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


# The story/feature dwell columns with nothing measured in any of them.
# Written out rather than derived from the vocabulary — a golden that computes
# itself from the code under test passes whatever that code says, which is how
# the four words of the 0.24.0 deprecation window could have outlived their
# release here unnoticed. Six keys: the lifecycle minus its terminal `done`.
EMPTY_STATES = {'planning': None, 'ready': None, 'building': None,
                'reviewing': None, 'accepted': None, 'packaging': None}


def test_the_seeded_ledger_produces_this_exact_json_object():
    """The same numbers, `null` where the table prints `-` — and `--json` is
    what a consumer parses, so a key that changed shape is a break nobody
    re-derives."""
    full = {'input': 1200, 'output': 38500, 'cache_creation': 210000,
            'cache_read': 9100000}
    dev = {'agent_type': 'developer', 'dispatches': 1,
           'usage': {'input': 1200, 'output': 38000,
                     'cache_creation': 210000, 'cache_read': 9100000},
           'tool_calls': 37, 'duration_s': 812}
    rev = {'agent_type': 'reviewer', 'dispatches': 1,
           'usage': dict(blank_usage(), output=500),
           'tool_calls': None, 'duration_s': None}
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
             'dispatches': 2, 'usage': full, 'tool_calls': 37,
             'duration_s': 812, 'agent_types': [dev, rev],
             'states': {'planning': None, 'ready': None,
                        'building': 600, 'reviewing': 120,
                        'accepted': None, 'packaging': None},
             'total_s': 720},
            {'grain': QUIET, 'kind': 'story', 'size': 'm',
             'dispatches': 0, 'usage': blank_usage(), 'tool_calls': None,
             'duration_s': None, 'agent_types': [],
             'states': EMPTY_STATES,
             'total_s': None},
            {'grain': FEATURE, 'kind': 'feature', 'size': None,
             'dispatches': 2, 'usage': full, 'tool_calls': 37,
             'duration_s': 812, 'agent_types': [dev, rev],
             'states': EMPTY_STATES,
             'total_s': None},
            {'grain': BUG, 'kind': 'bug', 'size': None, 'dispatches': 0,
             'usage': blank_usage(), 'tool_calls': None,
             'duration_s': None, 'agent_types': [],
             'states': {'open': None, 'fixed': 30}, 'total_s': 30},
        ],
        'unattributed': {'dispatches': 1,
                         'usage': dict(blank_usage(), input=5),
                         'tool_calls': 2, 'duration_s': None},
        'totals': {'dispatch_rows': 3, 'status_rows': 5, 'grains': 4,
                   'usage': dict(full, input=1205), 'tool_calls': 39,
                   'duration_s': 812},
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
        'dispatch_rows': 0, 'status_rows': 0, 'grains': 3,
        'usage': blank_usage(), 'tool_calls': None, 'duration_s': None}


def test_which_milestones_ledger_is_read():
    """The building one by default, the one you named when you name it — and
    `no ledger` is exit 0 and ONE line, because "nothing has been recorded
    yet" is a fact about the tree and not an error."""
    with tree(story_statuses=('done', 'ready')) as root:
        seeded(root)
        write(root / 'pm/roadmap/0.2-next/milestone.md',
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
    (('0.1', '0.2'), 'one milestone id'),
    ((FEATURE,), 'not a milestone'),
    ((BUG,), 'not a milestone'),
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


@pytest.mark.parametrize('kwargs,second,needle', [
    (dict(milestone_status='planning'), False, 'is in progress'),
    (dict(), True, '2 milestones are in progress'),
])
def test_a_milestone_this_verb_cannot_choose_is_named(kwargs, second, needle):
    """The one question the verb cannot answer, and it says so rather than
    picking — with the spelling that would have answered it."""
    with tree(**kwargs) as root:
        if second:
            write(root / 'pm/roadmap/0.2-next/milestone.md',
                  {'id': '"0.2"', 'name': 'Next', 'status': 'building'})
        code, out = report(root)
        assert code == 2, out
        assert needle in out
        if second:
            assert '0.1 0.2' in out
            assert 'pm ledger report <milestone-id>' in out
            assert report(root, '0.1')[0] == 0
