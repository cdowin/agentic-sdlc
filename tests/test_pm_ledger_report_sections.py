"""test_pm_ledger_report_sections.py — `pm ledger report`, sections 2-6.

Section 1 (spend per grain) is `test_pm_ledger_report.py`. The sections here
read the same ledger plus two documents section 1 never opens — the review
records and the bug frontmatter — and each keeps the same three rules:

  * **it counts, and never judges.** Findings are counted per severity and per
    `disposition_kind` — never per the SHAPE of the disposition's value, so
    `landed <hash>` and `landed in-place` are one column, which is the whole
    reason a reviewer who fixes in place and never commits (SDLC § 2) is not
    counted as having landed nothing;
  * **absent is not zero, and no data is not a table of zeros.** A story with
    no status rows has no reopen count, not a count of 0; a rule that cannot
    SEE a transition prints `-`, never `0`; a section with nothing in it prints
    ONE line and still says what it counted;
  * **the one refusal on content is a document that will not parse.** A review
    record whose verdict block exists and cannot be read is exit 2, by record
    and by line. A record with NO block is not that: it is a row saying so.

ONE GOLDEN PER SECTION carries the per-cell claims. A case beyond the golden
earns its place by reaching a state the fixture cannot hold — a legacy ledger
spelling, a cause that resolves to nothing, a gate row this section cannot use
— or by guarding a defect that shipped: the `Vocabulary` cases below are all
four of the second kind.
"""
from __future__ import annotations

import json

import pytest
from support.pm import (bug, declaring, decision_line, dispatch_line,
                        put_ledger, run_cli, section_of, session_line, snapshot,
                        status_line, write, write_config)
from support.pm import tree as _seed_tree

from agentic_sdlc.repo.pm import vocabulary

# THE ALL-SEVEN-SEED FLOW, and why these rows keep the declaration they were
# written under rather than being rewritten: tests/test_pm_ledger.py, beside the
# same `LEGACY_FLOW`.
LEGACY_FLOW = declaring(feature=vocabulary.DEFAULT_FLOWS['milestone'],
                        story=vocabulary.DEFAULT_FLOWS['milestone'])


def tree(**kwargs):
    """`support.pm.tree` under the all-seven flow these ledgers assume."""
    kwargs.setdefault('config', LEGACY_FLOW)
    return _seed_tree(**kwargs)

ALPHA, BETA, GAMMA, DELTA = ('0.1/alpha', '0.1/beta', '0.1/gamma', '0.1/delta')
A_S0, A_S1, B_S0 = '0.1/alpha/s0', '0.1/alpha/s1', '0.1/beta/s0'
ALPHA_RECORD = 'docs/reviews/alpha.md'
BETA_RECORD = 'pm/roadmap/features/beta-review.md'
DELTA_RECORD = 'pm/roadmap/features/delta-review.md'

YIELD, REWORK, ESCAPES, OVERHEAD, GATES = (
    'yield per review pass', 'rework', 'escapes', 'overhead shape',
    'gate cost')

# A record as the installed agents write it: a fenced block, the header row,
# one row per finding. Both `landed` forms are here on purpose — the column
# counts `disposition_kind`, so a fix landed in place counts exactly like a
# fix landed as a commit.
ALPHA_BLOCK = """\
The pass, in prose.

```text
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| A1 | MAJOR | landed 0badc0f |
| A2 | MINOR | landed in-place |
| A3 | NIT | rejected: a surface decision, not a local correction |
| A4 | QUESTION | deferred: 0.1/beta |
```
"""
BETA_BLOCK = """\
```text
verdict: HOLD
| id | severity | disposition |
| B1 | CRITICAL | deferred: 0.1/beta |
| B2 | WARNING | deferred: 0.1/gamma |
| B3 | MAJOR | open: the landing pass has not run |
```
"""
# A real review, written before the block existed. A FACT about the pass.
NO_BLOCK = 'LGTM. Ship it.\n'
# A block that exists and cannot be read: `WOMBAT` is not in the closed set.
BAD_BLOCK = """\
```text
verdict: SHIP
| X1 | WOMBAT | rejected: no such severity |
```
"""


def feature(root, fid: str, status: str, record: str = '',
            stories: tuple = ()) -> None:
    slug = fid.partition('/')[2]
    pools = root / 'pm/roadmap'
    write(pools / 'features' / f'{slug}.md',
          {'id': fid, 'kind': 'feature', 'milestone': '"0.1"',
           'name': slug, 'status': status, 'reviewed': ''})
    if record:
        # Beside the grain, under its own name: a pool is flat, so a bare
        # `review.md` would be one file for every feature.
        (pools / 'features' / f'{slug}-review.md').write_text(
            record, encoding='utf-8')
    for name, sstatus in stories:
        write(pools / 'stories' / f'{slug}-{name}.md',
              {'id': f'{fid}/{name}', 'kind': 'story', 'feature': fid,
               'milestone': '"0.1"', 'name': name, 'status': sstatus})


def seeded(root) -> None:
    """Four features, three stories, three bugs, and one ledger.

    `alpha` points at its record through `reviewed:` and `beta`/`delta` are
    read from the slot beside the feature document — the two ways a record is
    found, both exercised, and both printed as the path that answered.
    """
    (root / ALPHA_RECORD).write_text(ALPHA_BLOCK, encoding='utf-8')
    feature(root, BETA, 'building', BETA_BLOCK, (('s0', 'building'),))
    feature(root, GAMMA, 'planning')
    feature(root, DELTA, 'reviewing', NO_BLOCK)
    bug(root, 'crash', 'open', caused_by=ALPHA)
    bug(root, 'wobble', 'closed', caused_by=BETA)
    bug(root, 'quiet', 'open')
    put_ledger(
        root,
        status_line('2026-09-03T10:00:00Z', A_S0, 'ready', 'building'),
        dispatch_line('2026-09-03T10:05:00Z', agent_type='developer',
                      tool_calls=37, tool_calls_before_first_write=12,
                      tree=snapshot(stories_wip=[A_S0])),
        status_line('2026-09-03T10:10:00Z', A_S0, 'building', 'reviewing'),
        dispatch_line('2026-09-03T10:11:00Z', agent_type='reviewer',
                      tool_calls_before_first_write=3,
                      tree=snapshot(stories_review=[A_S0])),
        # The reopen: `review` back to `wip`, one row, nothing inferred.
        status_line('2026-09-03T10:12:00Z', A_S0, 'reviewing', 'building'),
        # No `tool_calls_before_first_write`: absent, so it is neither in the
        # sum nor in the list.
        dispatch_line('2026-09-03T10:13:00Z', agent_type='developer',
                      tree=snapshot(stories_wip=[A_S0])),
        status_line('2026-09-03T10:20:00Z', A_S0, 'building', 'done'),
        # A feature-grained decision with no status row of alpha's after it,
        # and a milestone-grained one whose scope is every grain here.
        decision_line('2026-09-03T10:21:00Z', ALPHA, 'D1'),
        decision_line('2026-09-03T10:22:00Z', '0.1', 'D2'),
        status_line('2026-09-03T10:25:00Z', B_S0, 'ready', 'building'),
        session_line('2026-09-03T11:00:00Z', session_id='sess-1',
                     tool_calls=10, usage={'output': 1000}),
        session_line('2026-09-03T11:05:00Z', session_id='sess-1',
                     tool_calls=26, usage={'output': 2500}),
    )


def report(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'report', *argv)


def block_rows(out: str, title: str, block: str) -> list[list[str]]:
    """The data rows of ONE block of ONE section, split into cells.

    Scoped twice on purpose: `0.1/alpha/s0` heads a row in three different
    sections, and a case that grepped the whole report for it would assert
    against whichever section happened to print first.
    """
    lines = section_of(out, title).splitlines()
    start = lines.index(f'-- {block}')
    rows = []
    for line in lines[start + 2:]:
        if not line.strip():
            break
        rows.append(line.split())
    return rows


def row_of(out: str, title: str, block: str, first: str) -> list[str]:
    rows = [r for r in block_rows(out, title, block) if r[0] == first]
    if len(rows) != 1:
        raise AssertionError(f'{len(rows)} rows start with {first!r} in '
                             f'{block!r} — the fixture is not what it claims')
    return rows[0]


def seeded_report(*argv) -> str:
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        code, out = report(root, '0.1', *argv)
    assert code == 0, out
    return out


YIELD_TABLE = """\
[ledger:report] 0.1 — yield per review pass — 3 record(s), 2 pass(es), 7 finding(s)

-- verdict (3)
feature    record                               pass  verdict           findings  landed  rejected  deferred  open
0.1/alpha  docs/reviews/alpha.md                   1  SHIP-WITH-FIXES          4       2         1         1     0
0.1/beta   pm/roadmap/features/beta-review.md      1  HOLD                     3       0         0         2     1
0.1/delta  pm/roadmap/features/delta-review.md     -  no verdict block         -       -         -         -     -

-- findings by severity (7)
feature    pass  severity  findings
0.1/alpha     1  MAJOR            1
0.1/alpha     1  MINOR            1
0.1/alpha     1  NIT              1
0.1/alpha     1  QUESTION         1
0.1/beta      1  CRITICAL         1
0.1/beta      1  MAJOR            1
0.1/beta      1  WARNING          1

-- deferred to (3)
target     feature    pass  findings
0.1/beta   0.1/alpha     1         1
0.1/beta   0.1/beta      1         1
0.1/gamma  0.1/beta      1         1"""

REWORK_TABLE = """\
[ledger:report] 0.1 — rework — 2 pass(es) with a verdict

-- verdict distribution (2)
verdict          passes
SHIP-WITH-FIXES       1
HOLD                  1"""

ESCAPES_TABLE = """\
[ledger:report] 0.1 — escapes — 2 bug(s) naming a cause, 2 feature(s)

-- bugs naming a cause (2)
caused_by  bug              status  feature_status
0.1/alpha  0.1/bugs/crash   open    done
0.1/beta   0.1/bugs/wobble  closed  building"""

OVERHEAD_TABLE = """\
[ledger:report] 0.1 — overhead shape — 3 dispatch row(s), 2 decision row(s), 2 session row(s)

-- story (3)
story         dispatches  before_first_write  calls
0.1/alpha/s0           3                  15  12,3
0.1/alpha/s1           0                   -  -
0.1/beta/s0            0                   -  -

-- decisions per grain (5)
grain      decisions
0.1                1
0.1/alpha          1
0.1/beta           0
0.1/delta          0
0.1/gamma          0

-- decision to next status row (2)
grain      entry  ts                    next_status_s
0.1/alpha  D1     2026-09-03T10:21:00Z              -
0.1        D2     2026-09-03T10:22:00Z            180

-- session deltas (1)
session_id  ts                     out  tool_calls
sess-1      2026-09-03T11:05:00Z  1500          16"""


def test_the_seeded_ledger_prints_these_exact_tables():
    """Rule 6: the shape is the API — and one golden per section carries every
    per-cell claim these sections used to assert one case at a time. Both
    `landed` forms in one column, `open` as its own column, a record with no
    block listed and never counted as zero, a feature with no record absent
    entirely, deferrals grouped by target, both record-discovery paths printed,
    the reopen and the dispatches after it, a cause's status verbatim, the
    before-first-write sum beside its own list, the decision gap inside its own
    grain's scope, and the session delta per session."""
    out = seeded_report()
    for title, table in ((YIELD, YIELD_TABLE), (REWORK, REWORK_TABLE),
                         (ESCAPES, ESCAPES_TABLE), (OVERHEAD, OVERHEAD_TABLE)):
        assert section_of(out, title) == table


def test_the_report_never_writes():
    """A read verb that wrote is the write-side cardinal sin, and this is the
    one place it is asserted against every byte in the tree."""
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        before = {p: p.read_bytes() for p in sorted(root.rglob('*'))
                  if p.is_file()}
        assert report(root, '0.1')[0] == 0
        assert report(root, '0.1', '--json')[0] == 0
        after = {p: p.read_bytes() for p in sorted(root.rglob('*'))
                 if p.is_file()}
    assert after == before


# --- three passes over one record ---------------------------------------------
# The record this package's own SDLC produces, end to end. The re-ordered
# protocol runs three review passes over one feature record, each appending its
# block. Before M2 the second block was `MalformedVerdict`, `parsed_records`
# mapped that to `RecordError`, and `pm ledger report` exited 2 on a
# well-formed record — which is why 0.24.0 carried a second review file whose
# header said it existed to work around this. So the first assertion is the
# exit code, and nothing is collapsed into one answer: `C1` was raised open in
# pass 1 and landed in pass 2, and a merged view would lose the transition,
# which is the only thing three passes are evidence of.

THREE_PASSES = '''# alpha — reviewed three times

```text
verdict: RELEASE-WITH-FIXES
| id | severity | disposition |
| C1 | CRITICAL | open |
| m1 | MINOR | deferred: 0.1/beta |
```

Prose between the passes, which is where the fixes went in.

```text
verdict: RELEASE-WITH-FIXES
| id | severity | disposition |
| C1 | CRITICAL | landed 3a42f19ad |
```

```text
verdict: RELEASE-SAFE
| id | severity | disposition |
```
'''


def three_pass_report(*argv) -> str:
    with tree(feature_status='done', story_statuses=('done',)) as root:
        (root / ALPHA_RECORD).write_text(THREE_PASSES, encoding='utf-8')
        put_ledger(root, status_line('2026-09-03T10:00:00Z', A_S0,
                                     'building', 'done'))
        code, out = report(root, '0.1', *argv)
    assert code == 0, out
    return out


def test_each_pass_of_one_record_is_its_own_row_in_document_order():
    out = three_pass_report()
    rows = block_rows(out, YIELD, 'verdict (3)')
    assert [r[2] for r in rows] == ['1', '2', '3']
    assert [r[3] for r in rows] == ['RELEASE-WITH-FIXES',
                                    'RELEASE-WITH-FIXES', 'RELEASE-SAFE']
    # findings landed rejected deferred open, per pass: the second pass landed
    # the CRITICAL the first one raised, and the third raised none.
    assert [r[-5:] for r in rows] == [['2', '0', '0', '1', '1'],
                                      ['1', '1', '0', '0', '0'],
                                      ['0', '0', '0', '0', '0']]
    # Records and passes are counted separately, and the distribution counts
    # PASSES — counting records would have to pick one of the three verdicts.
    assert ('yield per review pass — 1 record(s), 3 pass(es), '
            '3 finding(s)') in out
    assert '3 pass(es) with a verdict' in out
    assert block_rows(out, REWORK, 'verdict distribution (2)') == [
        ['RELEASE-SAFE', '1'], ['RELEASE-WITH-FIXES', '2']]
    # Severities and deferrals carry the pass that raised them.
    assert block_rows(out, YIELD, 'findings by severity (3)') == [
        [ALPHA, '1', 'CRITICAL', '1'], [ALPHA, '1', 'MINOR', '1'],
        [ALPHA, '2', 'CRITICAL', '1']]
    assert block_rows(out, YIELD, 'deferred to (1)') == [[BETA, ALPHA, '1', '1']]


def test_the_json_nests_the_passes_under_the_one_record():
    data = json.loads(three_pass_report('--json'))['yield']
    assert len(data['records']) == 1
    passes = data['records'][0]['passes']
    assert [one['pass'] for one in passes] == [1, 2, 3]
    assert passes[0]['dispositions']['open'] == 1
    assert passes[1]['dispositions']['landed'] == 1
    assert data['totals'] == {'records': 1, 'passes': 3, 'findings': 3}


# --- section 4: the cause the tree cannot resolve -----------------------------

def test_a_cause_that_resolves_to_nothing_still_gets_its_row():
    """A retired or mistyped cause is a fact `pm validate` reports; the report
    prints the row with `-` rather than dropping the bug — a dropped escape is
    an escape nobody counts."""
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        bug(root, 'ghost', 'open', caused_by='0.9/vanished')
        out = report(root, '0.1')[1]
    assert row_of(out, ESCAPES, 'bugs naming a cause (3)', '0.9/vanished') == [
        '0.9/vanished', '0.1/bugs/ghost', 'open', '-']
    assert '3 bug(s) naming a cause, 3 feature(s)' in out


# --- section 5: a delta needs both ends ---------------------------------------

def test_one_session_row_alone_is_a_count_and_no_delta():
    """A cumulative total with nothing to subtract from it is not a delta, and
    the census still says the row is there — silence would read as a section
    that never ran."""
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        put_ledger(root, session_line('2026-09-03T11:00:00Z',
                                      session_id='sess-1', tool_calls=10,
                                      usage={'output': 1000}))
        out = section_of(report(root, '0.1')[1], OVERHEAD)
    assert '0 dispatch row(s), 0 decision row(s), 1 session row(s)' in out
    assert '-- session deltas (0)' in out


def test_a_delta_needs_both_ends_measured():
    """One end absent is not a delta of the other end minus zero."""
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        put_ledger(
            root,
            session_line('2026-09-03T11:00:00Z', session_id='sess-1',
                         usage={'output': 1000}),
            session_line('2026-09-03T11:05:00Z', session_id='sess-1',
                         tool_calls=26, usage={'output': 2500}))
        out = report(root, '0.1')[1]
    assert row_of(out, OVERHEAD, 'session deltas (1)', 'sess-1')[-2:] == [
        '1500', '-']


# Section 3's per-story table left (0.2.0): `reopens` counted
# `reviewing -> building` by name, `after_review` counted dispatches after the
# first move into `reviewing` by name, and the story seed no longer holds the
# word, so neither had a tree left to be a number on. What remains is the
# verdict distribution the REWORK golden above holds.


# --- nothing to report --------------------------------------------------------

def test_a_row_that_names_its_grain_is_on_that_grains_line():
    """0.4.0/every-row-names-its-grain, read side. Until the couriers passed
    `--grain`, every automatic row reached the report with nothing but a tree
    SNAPSHOT to be attributed by — which works for a status flip and not for a
    session, so the per-grain table showed 0 dispatches against every story in
    the milestone. The numbers were captured; nothing said what they bought.

    The snapshot is deliberately EMPTY here, so `grain:` is the only thing that
    could attribute the row.
    """
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        put_ledger(root,
                   dispatch_line('2026-09-03T12:00:00Z', grain=A_S1,
                                 tool_calls=9),
                   rel='pm/roadmap/ledger.jsonl')
        code, out = report(root, '0.1')
    assert code == 0, out
    assert '9' in row_of(out, 'spend per grain', 'story (3)', A_S1), out
    assert '-- rows naming no grain (0)' in out, out


def test_a_stated_grain_outranks_the_snapshot_and_bills_nobody_else():
    """The row says `0.1/alpha/s1`; the snapshot says `0.1/alpha/s0` was live.

    Both are true — the OTHER story was in progress at that instant — and only
    one of them is what the dispatch was doing. Adding the snapshot's grains on
    top would bill s0 for nine tool calls it never spent, which is rule 4 on
    the read side. The stated grain wins, and it wins ALONE.
    """
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        was = row_of(seeded_report(), 'spend per grain', 'story (3)', A_S0)
        put_ledger(root,
                   dispatch_line('2026-09-03T12:00:00Z', grain=A_S1,
                                 tool_calls=9, tree=snapshot(stories_wip=[A_S0])),
                   rel='pm/roadmap/ledger.jsonl')
        code, out = report(root, '0.1')
    assert code == 0, out
    assert '9' in row_of(out, 'spend per grain', 'story (3)', A_S1), out
    assert row_of(out, 'spend per grain', 'story (3)', A_S0) == was, out
    # And it is not a silent drop: `frozen_only` exists to disclose a snapshot
    # the report read past, and a STATED grain is not that.
    assert 'dispatch row(s)' in out


# --- 0.4.0/D8: the reader does not un-do the writer's refusal ------------------
def test_an_ambiguous_snapshot_places_nothing_and_stays_in_the_bucket():
    """M2. `pm ledger record` omits the `grain` key when two stories are live,
    because a row filed against the wrong one is uncorrectable. The reader was
    then attributing that same row through its snapshot — to BOTH stories and
    to their feature — so the decision was un-done on the way out and the
    bucket the feature exists to fill printed `(0)`.

    The snapshot here names two live stories and no grain, which is exactly
    what the courier writes in the case this milestone was built for.
    """
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        was_s0 = row_of(seeded_report(), 'spend per grain', 'story (3)', A_S0)
        put_ledger(root,
                   dispatch_line('2026-09-03T12:00:00Z', tool_calls=9,
                                 tree=snapshot(stories_wip=[A_S0, A_S1])),
                   rel='pm/roadmap/ledger.jsonl')
        code, out = report(root, '0.1')
    assert code == 0, out
    stray = block_rows(out, 'spend per grain', 'rows naming no grain (1)')
    assert stray and '9' in stray[0], out
    assert row_of(out, 'spend per grain', 'story (3)', A_S0) == was_s0, out


def test_one_story_and_its_feature_is_ONE_candidate_not_two():
    """The rule's edge, and getting it wrong would empty the whole table: a
    snapshot naming a story AND the feature that owns it names one thing, and
    the feature is a roll-up `_named_through` added. Ambiguity is judged at
    the finest kind the snapshot names."""
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        put_ledger(root,
                   dispatch_line('2026-09-03T12:00:00Z', tool_calls=9,
                                 tree=snapshot(stories_wip=[A_S1],
                                               features_building=[ALPHA])),
                   rel='pm/roadmap/ledger.jsonl')
        code, out = report(root, '0.1')
    assert code == 0, out
    assert '9' in row_of(out, 'spend per grain', 'story (3)', A_S1), out
    assert '-- rows naming no grain (0)' in out, out


def test_a_stated_grain_this_milestone_cannot_place_never_falls_through():
    """M3. `stated in kinds` fell THROUGH to the snapshot, so a row naming a
    story that had since been renamed away was billed to whichever other story
    happened to be live — and `frozen_only` disclosed nothing, under a
    docstring promising a stated grain is attributed by it and nothing else.

    It gets its own counted line rather than joining `rows naming no grain`:
    the two are opposites, and since D3 every milestone's report reads the
    tree's shared ledger, so another milestone's rows are the ordinary case.
    """
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        was_s1 = row_of(seeded_report(), 'spend per grain', 'story (3)', A_S1)
        put_ledger(root,
                   dispatch_line('2026-09-03T12:00:00Z', grain='9.9/gone/s0',
                                 tool_calls=9,
                                 tree=snapshot(stories_wip=[A_S1])),
                   rel='pm/roadmap/ledger.jsonl')
        code, out = report(root, '0.1')
    assert code == 0, out
    assert row_of(out, 'spend per grain', 'story (3)', A_S1) == was_s1, out
    assert '-- rows naming no grain (0)' in out, out
    assert 'does not hold' in out, out


# --- 0.4.0/D3: the report reads BOTH ledgers -----------------------------------
def test_the_trees_own_rows_are_counted_and_never_folded_into_a_grain():
    """A milestone's report reads its own ledger AND `<roadmap>/ledger.jsonl`,
    where every row that names no grain now lives.

    Two claims, and the second is the one that could go wrong silently: the
    root rows must appear in `rows naming no grain`, and they must not be added
    to any grain's line. Reading only the milestone's file would empty that
    bucket for every tree; folding the rows into a grain would bill a story for
    seconds nobody spent on it.
    """
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        before = row_of(seeded_report(), 'spend per grain', 'story (3)', A_S0)
        # An empty tree snapshot and no `grain`: nothing to attribute it to,
        # which is exactly the row D3 gave a home to. A `gate` row beside it,
        # because that one can never be attributed at all.
        put_ledger(root,
                   dispatch_line('2026-09-03T12:00:00Z', tool_calls=9),
                   gate_line('2026-09-03T12:01:00Z', 'check'),
                   rel='pm/roadmap/ledger.jsonl')
        code, out = report(root, '0.1')
    assert code == 0, out
    # The block's own title carries the count, so the number is asserted where
    # a reader reads it. It is `(0)` without this story — every seeded dispatch
    # row is attributed through its tree snapshot — so the count IS the case.
    stray = block_rows(out, 'spend per grain', 'rows naming no grain (1)')
    assert stray and stray[0][0] == '1' and '9' in stray[0], out
    # And not folded into a grain: the busiest story's row is unchanged from
    # the same report over a tree with no root ledger.
    assert row_of(out, 'spend per grain', 'story (3)', A_S0) == before
    assert 'check' in section_of(out, 'gate cost'), out


def test_a_section_with_nothing_in_it_prints_one_line_and_says_what_it_counted():
    """Never a table of zeros — and never silence either: a census that saw
    nothing has to say so, or `no data` is indistinguishable from `not run`."""
    with tree(feature_status='building', story_statuses=(),
              with_record=False) as root:
        put_ledger(root, status_line('2026-09-03T10:00:00Z', ALPHA,
                                     'ready', 'building'))
        code, out = report(root, '0.1')
        assert code == 0, out
        data = json.loads(report(root, '0.1', '--json')[1])
    for title in (YIELD, REWORK, ESCAPES, OVERHEAD):
        section = section_of(out, title)
        assert len(section.splitlines()) == 2, section
        assert section.splitlines()[1] == 'no data'
    assert ('yield per review pass — 0 record(s), 0 pass(es), '
            '0 finding(s)') in out
    assert 'rework — 0 pass(es) with a verdict' in out
    assert 'escapes — 0 bug(s) naming a cause, 0 feature(s)' in out
    assert ('overhead shape — 0 dispatch row(s), 0 decision row(s), '
            '0 session row(s)') in out
    # The keys stay, with empty lists behind them: a consumer that has to
    # branch on a missing key is a consumer this report broke.
    assert data['yield']['records'] == []
    assert data['rework']['verdicts'] == []
    assert data['escapes']['bugs'] == []
    assert data['overhead']['sessions'] == []


# --- the JSON for the same fixture --------------------------------------------

def test_the_seeded_ledger_produces_this_exact_json():
    """The same numbers, `null` where the table prints `-`, and the nesting is
    the shape of the fact: a record is a file, a pass is a review, and a record
    reviewed three times has one path and three verdicts."""
    data = json.loads(seeded_report('--json'))
    assert data['yield'] == {
        'records': [
            {'feature': ALPHA, 'record': ALPHA_RECORD, 'passes': [
                {'pass': 1, 'verdict': 'SHIP-WITH-FIXES', 'findings': 4,
                 'severities': {'MAJOR': 1, 'MINOR': 1, 'NIT': 1,
                                'QUESTION': 1},
                 'deferred': [{'target': BETA, 'findings': 1}],
                 'dispositions': {'landed': 2, 'rejected': 1,
                                  'deferred': 1, 'open': 0}}]},
            {'feature': BETA, 'record': BETA_RECORD, 'passes': [
                {'pass': 1, 'verdict': 'HOLD', 'findings': 3,
                 'severities': {'CRITICAL': 1, 'MAJOR': 1, 'WARNING': 1},
                 'deferred': [{'target': BETA, 'findings': 1},
                              {'target': GAMMA, 'findings': 1}],
                 'dispositions': {'landed': 0, 'rejected': 0,
                                  'deferred': 2, 'open': 1}}]},
            # No block at all: an empty `passes` list, never a pass numbered 1
            # with nothing in it.
            {'feature': DELTA, 'record': DELTA_RECORD, 'passes': []},
        ],
        'totals': {'records': 3, 'passes': 2, 'findings': 7}}
    assert data['rework'] == {
        'verdicts': [{'verdict': 'SHIP-WITH-FIXES', 'passes': 1},
                     {'verdict': 'HOLD', 'passes': 1}],
        'totals': {'passes': 2}}
    assert data['escapes'] == {
        'bugs': [
            {'caused_by': ALPHA, 'bug': '0.1/bugs/crash', 'status': 'open',
             'feature_status': 'done', 'feature_done': True},
            {'caused_by': BETA, 'bug': '0.1/bugs/wobble', 'status': 'closed',
             'feature_status': 'building', 'feature_done': False},
        ],
        'totals': {'bugs': 2, 'features': 2}}
    assert data['overhead'] == {
        'stories': [
            {'grain': A_S0, 'dispatches': 3, 'before_first_write': 15,
             'calls': [12, 3]},
            {'grain': A_S1, 'dispatches': 0, 'before_first_write': None,
             'calls': []},
            {'grain': B_S0, 'dispatches': 0, 'before_first_write': None,
             'calls': []},
        ],
        'decisions': [{'grain': '0.1', 'decisions': 1},
                      {'grain': ALPHA, 'decisions': 1},
                      {'grain': BETA, 'decisions': 0},
                      {'grain': DELTA, 'decisions': 0},
                      {'grain': GAMMA, 'decisions': 0}],
        'gaps': [
            {'grain': ALPHA, 'entry': 'D1', 'title': 'why',
             'ts': '2026-09-03T10:21:00Z', 'next_status_s': None},
            {'grain': '0.1', 'entry': 'D2', 'title': 'why',
             'ts': '2026-09-03T10:22:00Z', 'next_status_s': 180},
        ],
        'sessions': [{'session_id': 'sess-1', 'ts': '2026-09-03T11:05:00Z',
                      'output': 1500, 'tool_calls': 16}],
        'totals': {'dispatch_rows': 3, 'decision_rows': 2, 'session_rows': 2}}


def test_a_malformed_verdict_block_refuses_whole():
    """The one refusal on content, and it refuses WHOLE: section 1's table
    would otherwise be on stdout with a broken section 2 behind it, and a
    report half-printed reads as a report."""
    for argv in ((), ('--json',)):
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            seeded(root)
            (root / ALPHA_RECORD).write_text(BAD_BLOCK, encoding='utf-8')
            code, out = report(root, '0.1', *argv)
        assert code == 2, out
        assert '-- story (' not in out
        assert '"milestone"' not in out
        if not argv:
            assert ALPHA_RECORD in out
            assert 'line 3' in out
            assert 'WOMBAT' in out


# --- section 6: gate cost -----------------------------------------------------
# The feature's own risk 3 is that telemetry nobody reads is cost with no
# benefit, which is why this section is the feature's ship blocker rather than
# its garnish. So the cases below pin the two ways the table could lie — a gate
# omitted for having only one run, and a delta whose corpus moved presented as
# a regression — and hard rule 4's read side: a row this section cannot use is
# NAMED, never dropped into silence.

def gate_line(ts: str, gate: str, verdict: str = 'PASS',
              duration_ms: int | None = 0, census: int | None = None) -> str:
    from agentic_sdlc.repo.pm import ledger as _ledger
    return _ledger.dumps(_ledger.gate_row(gate, verdict, duration_ms,
                                          census=census, ts=ts))


def gates_report(*lines: str, argv: tuple = ()) -> str:
    """A tree whose ledger is exactly the gate rows a case cares about."""
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(root, *lines)
        code, out = report(root, '0.1', *argv)
    assert code == 0, out
    return out


THREE_PARSE_ONE_LINT = (
    gate_line('2026-09-03T10:00:00Z', 'parse', duration_ms=8000),
    gate_line('2026-09-03T10:05:00Z', 'lint', duration_ms=2000),
    gate_line('2026-09-03T11:00:00Z', 'parse', duration_ms=12000),
    gate_line('2026-09-03T12:00:00Z', 'parse', duration_ms=30000),
)

BROKEN_GATE_ROWS = (
    gate_line('2026-09-03T10:00:00Z', 'parse', duration_ms=8000),
    # No duration at all — the CLI refuses to write one, so this is a row some
    # other hand appended.
    gate_line('2026-09-03T10:01:00Z', 'lint', duration_ms=None),
    json.dumps({'ts': '2026-09-03T10:02:00Z', 'kind': 'gate',
                'gate': 'warnings', 'verdict': 'PASS',
                'duration_ms': '900'}),
    json.dumps({'ts': '2026-09-03T10:03:00Z', 'kind': 'gate',
                'gate': 'unit', 'verdict': 'PASS', 'duration_ms': -5}),
    json.dumps({'ts': '2026-09-03T10:04:00Z', 'kind': 'gate',
                'verdict': 'PASS', 'duration_ms': 400}),
)


def test_the_seeded_gate_rows_print_this_exact_table():
    """One row per gate, slowest-latest first, and a gate with ONE run still
    appears with no delta — a gate omitted for having too little data reads as
    a gate that costs nothing, and the measurement that started this feature
    found the gate suspected by NAME costing 0.2 s."""
    assert section_of(gates_report(*THREE_PARSE_ONE_LINT), GATES) == """\
[ledger:report] 0.1 — gate cost — 4 gate row(s), 2 gate(s), \
across the whole tree, not this milestone: a gate row names no grain, so every one lands in the tree's ledger; 1 delta(s) marked \
* for a census that moved or is absent, 0 row(s) this section could not use

-- gate (2)
gate   runs  first_ms  last_ms  delta_ms  census
parse     3      8000    30000   +22000*  -
lint      1      2000     2000         -  -

-- rows this section could not use (0)"""


def test_a_gate_that_got_faster_carries_a_signed_negative_delta():
    out = gates_report(
        gate_line('2026-09-03T10:00:00Z', 'pm-shape-scan', duration_ms=34800),
        gate_line('2026-09-03T11:00:00Z', 'pm-shape-scan', duration_ms=900))
    assert row_of(out, GATES, 'gate (1)', 'pm-shape-scan') == [
        'pm-shape-scan', '2', '34800', '900', '-33900*', '-']


# A duration without its census invites the wrong conclusion (risk 2): the same
# gate is legitimately slower on a bigger tree. The number is still printed —
# it was measured — but nothing may present it as a regression.
@pytest.mark.parametrize('first_census,last_census,expected', [
    # Held still: comparable, so no mark.
    (120, 120, ['parse', '2', '8000', '9000', '+1000', '120', '→', '120']),
    # Moved: the delta is marked and the heading counts it.
    (120, 900, ['parse', '2', '8000', '30000', '+22000*', '120', '→', '900']),
    # Half a pair is not half an answer: `120 → -` would read as a corpus that
    # shrank to nothing, and an unqualified delta reads as a fact.
    (120, None, ['parse', '2', '8000', '30000', '+22000*', '-']),
])
def test_a_delta_whose_census_moved_or_is_absent_is_marked(
        first_census, last_census, expected):
    last_ms = 9000 if (first_census == last_census) else 30000
    out = gates_report(
        gate_line('2026-09-03T10:00:00Z', 'parse', duration_ms=8000,
                  census=first_census),
        gate_line('2026-09-03T11:00:00Z', 'parse', duration_ms=last_ms,
                  census=last_census))
    assert row_of(out, GATES, 'gate (1)', 'parse') == expected
    marked = '0' if first_census == last_census else '1'
    assert f'{marked} delta(s) marked' in section_of(out, GATES)


def test_every_unusable_gate_row_is_named_with_why_and_the_good_row_survives():
    """Hard rule 4's read side: a row this section cannot use is NAMED, never
    dropped into silence and never coerced to a zero."""
    assert section_of(gates_report(*BROKEN_GATE_ROWS), GATES) == """\
[ledger:report] 0.1 — gate cost — 5 gate row(s), 1 gate(s), \
across the whole tree, not this milestone: a gate row names no grain, so every one lands in the tree's ledger; 0 delta(s) marked \
* for a census that moved or is absent, 4 row(s) this section could not use

-- gate (1)
gate   runs  first_ms  last_ms  delta_ms  census
parse     1      8000     8000         -  -

-- rows this section could not use (4)
gate      why                            ts
lint      no duration_ms                 2026-09-03T10:01:00Z
warnings  duration_ms is not an integer  2026-09-03T10:02:00Z
unit      duration_ms is negative        2026-09-03T10:03:00Z
-         no gate name                   2026-09-03T10:04:00Z"""


def test_the_gate_section_says_it_is_the_trees_and_two_milestones_agree():
    """Review M2. `gate` rows name no grain, so 0.4.0/D3 files every one at the
    tree's root and every milestone's report reads the same set — which makes
    `runs` and `delta_ms` lifetime-of-TREE numbers under a MILESTONE heading.

    Two claims, and the second is the one that would have been a silent lie:
    the section states its own scope, and two different milestones' reports
    print the identical gate line. Windowing by the milestone's timestamps was
    the alternative and it loses — a milestone declares no time range, so the
    window would be inferred and then quoted as if somebody had stated it.
    """
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        write(root / 'pm/roadmap/milestones/0.2.md',
              {'id': '"0.2"', 'name': 'Next', 'status': 'building'})
        put_ledger(root,
                   gate_line('2026-01-01T00:00:00Z', 'unit'),
                   gate_line('2026-07-01T00:00:00Z', 'unit'),
                   rel='pm/roadmap/ledger.jsonl')
        one = section_of(report(root, '0.1')[1], GATES)
        two = section_of(report(root, '0.2')[1], GATES)
    assert 'across the whole tree, not this milestone' in one, one
    assert one.replace('0.1', 'X') == two.replace('0.2', 'X'), (one, two)


def test_a_ledger_with_no_gate_row_still_prints_the_section():
    """A missing section is indistinguishable from an empty one, and only one
    of those is true."""
    out = gates_report(
        status_line('2026-09-03T10:00:00Z', A_S0, 'ready', 'building'),
        dispatch_line('2026-09-03T10:05:00Z', agent_type='developer'))
    assert section_of(out, GATES) == """\
[ledger:report] 0.1 — gate cost — 0 gate row(s), 0 gate(s), \
across the whole tree, not this milestone: a gate row names no grain, so every one lands in the tree's ledger; 0 delta(s) marked \
* for a census that moved or is absent, 0 row(s) this section could not use
no data"""


def test_the_gate_json_carries_every_field_and_names_what_it_could_not_use():
    """The incomparable mark included, so a caller need not re-derive it."""
    assert json.loads(gates_report(*THREE_PARSE_ONE_LINT,
                                   argv=('--json',)))['gates'] == {
        'gates': [
            {'gate': 'parse', 'runs': 3, 'first_ms': 8000, 'last_ms': 30000,
             'delta_ms': 22000, 'first_census': None, 'last_census': None,
             'comparable': False},
            {'gate': 'lint', 'runs': 1, 'first_ms': 2000, 'last_ms': 2000,
             'delta_ms': None, 'first_census': None, 'last_census': None,
             'comparable': None},
        ],
        'unusable': [],
        'totals': {'rows': 4, 'gates': 2, 'incomparable': 1, 'unusable': 0}}
    broken = json.loads(gates_report(*BROKEN_GATE_ROWS,
                                     argv=('--json',)))['gates']
    assert broken['unusable'] == [
        {'gate': 'lint', 'why': 'no duration_ms',
         'ts': '2026-09-03T10:01:00Z'},
        {'gate': 'warnings', 'why': 'duration_ms is not an integer',
         'ts': '2026-09-03T10:02:00Z'},
        {'gate': 'unit', 'why': 'duration_ms is negative',
         'ts': '2026-09-03T10:03:00Z'},
        {'gate': None, 'why': 'no gate name', 'ts': '2026-09-03T10:04:00Z'}]
