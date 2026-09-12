"""test_pm_ledger_report_sections.py — which rows a report reads, the tree's
own report, the `--help` roster, and milestones side by side.

The one-milestone table is `test_pm_ledger_report.py`. What is pinned here:

  * **ownership** (`ft-a-milestone-reports-only-its-own-rows`). A milestone
    reads a row naming one of its grains, or a row naming no grain stamped
    with its declared `branch:`; an old row carrying neither is placed by its
    snapshot only when that names exactly one of its stories. Everything else
    in the tree's ledger is the TREE's, reported once under `--tree`;
  * **the tree's report** is the gate table: one row per gate, one run per
    row, a delta whose census moved marked, and a row it cannot use NAMED;
  * **the roster**: every block the verb prints is named in `--help` with its
    columns in order, and `--help` names no block that stopped printing;
  * **the comparison**: one golden, the `--json` shape, ORDER read and never
    chosen, and the refusal matrix.
"""
from __future__ import annotations

import json

import pytest
from support.pm import (decision_line, declaring, dispatch_line, put_ledger,
                        run_cli, session_line, snapshot, snapshot_legacy,
                        status_line, write)
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
ROOT_LEDGER = 'pm/roadmap/ledger.jsonl'
LOCAL_LEDGER = 'pm/roadmap/ledger.local.jsonl'
OWN_LEDGER = 'pm/roadmap/ledgers/0.1.jsonl'


def feature(root, fid: str, status: str, stories: tuple = ()) -> None:
    slug = fid.partition('/')[2]
    pools = root / 'pm/roadmap'
    write(pools / 'features' / f'{slug}.md',
          {'id': fid, 'kind': 'feature', 'milestone': '"0.1"',
           'name': slug, 'status': status, 'reviewed': ''})
    for name, sstatus in stories:
        write(pools / 'stories' / f'{slug}-{name}.md',
              {'id': f'{fid}/{name}', 'kind': 'story', 'feature': fid,
               'milestone': '"0.1"', 'name': name, 'status': sstatus})


def stamp_line(ts: str, grain: str, edge: str, **fields: object) -> str:
    """A `stamp` row as the 0.10.0 contract writes it, planted as JSON."""
    return json.dumps({'ts': ts, 'kind': 'stamp', 'grain': grain,
                       'edge': edge, **fields})


def seeded(root) -> None:
    """Four features, three stories, and one ledger: two dispatches placed by
    their snapshot, one on the story's own grain, an open stamp unit, and the
    decision and session rows a unit never holds."""
    feature(root, BETA, 'building', (('s0', 'building'),))
    feature(root, GAMMA, 'planning')
    feature(root, DELTA, 'reviewing')
    put_ledger(
        root,
        status_line('2026-09-03T10:00:00Z', A_S0, 'ready', 'building'),
        dispatch_line('2026-09-03T10:05:00Z', agent_type='developer',
                      duration_s=300, tokens_total=3000,
                      tree=snapshot(stories_wip=[A_S0])),
        status_line('2026-09-03T10:10:00Z', A_S0, 'building', 'reviewing'),
        dispatch_line('2026-09-03T10:11:00Z', agent_type='reviewer',
                      tokens_total=1000,
                      tree=snapshot(stories_review=[A_S0])),
        status_line('2026-09-03T10:12:00Z', A_S0, 'reviewing', 'building'),
        dispatch_line('2026-09-03T10:13:00Z', grain=A_S0,
                      agent_type='developer'),
        status_line('2026-09-03T10:20:00Z', A_S0, 'building', 'done'),
        decision_line('2026-09-03T10:21:00Z', ALPHA, 'D1'),
        decision_line('2026-09-03T10:22:00Z', '0.1', 'D2'),
        status_line('2026-09-03T10:25:00Z', B_S0, 'ready', 'building'),
        stamp_line('2026-09-03T10:26:00Z', B_S0, 'start', issue=['#7'],
                   agent='developer'),
        session_line('2026-09-03T11:00:00Z', session_id='sess-1'),
    )


def report(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'report', *argv)


def block_rows(out: str, block: str) -> list[list[str]]:
    """The data rows of the one `-- <block>` table, split into cells."""
    lines = out.splitlines()
    start = lines.index(f'-- {block}')
    rows = []
    for line in lines[start + 2:]:
        if not line.strip():
            break
        rows.append(line.split())
    return rows


def row_of(out: str, block: str, first: str) -> list[str]:
    rows = [r for r in block_rows(out, block) if r[0] == first]
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


SECOND = '0.2'
SECOND_LEDGER = 'pm/roadmap/ledgers/0.2.jsonl'


def second_milestone(root) -> None:
    """A second milestone with a ledger of its own — what a comparison needs
    two of, and the smallest tree that produces one."""
    write(root / 'pm/roadmap/milestones/0.2.md',
          {'id': f'"{SECOND}"', 'kind': 'milestone', 'name': 'Next',
           'status': 'planning'})
    write(root / 'pm/roadmap/features/omega.md',
          {'id': '0.2/omega', 'kind': 'feature', 'milestone': f'"{SECOND}"',
           'name': 'Omega', 'status': 'building', 'reviewed': ''})
    put_ledger(root,
               status_line('2026-09-04T10:00:00Z', '0.2/omega',
                           'planning', 'building'),
               dispatch_line('2026-09-04T10:05:00Z', grain='0.2/omega',
                             agent_type='developer', duration_s=60,
                             tokens_total=700),
               rel=SECOND_LEDGER)


def test_the_report_never_writes():
    """A read verb that wrote is the write-side cardinal sin, and this is the
    one place it is asserted against every byte in the tree — every form."""
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        second_milestone(root)
        before = {p: p.read_bytes() for p in sorted(root.rglob('*'))
                  if p.is_file()}
        for argv in (('0.1',), ('0.1', '--json'), ('0.1', SECOND),
                     ('0.1', SECOND, '--json'), ('--tree',),
                     ('--tree', '--json')):
            assert report(root, *argv)[0] == 0, argv
        after = {p: p.read_bytes() for p in sorted(root.rglob('*'))
                 if p.is_file()}
    assert after == before


# --- which rows a milestone owns ----------------------------------------------
# One probe dispatch per case, and the question is the only one that matters:
# which grain's unit is it, or is it no unit of this milestone's at all? Each
# row guards a defect that shipped.
PROBE = 'probe'


@pytest.mark.parametrize('fields, rel, placed, superseded', [
    # 0.4.0/every-row-names-its-grain: an EMPTY snapshot, so `grain:` is the
    # only thing that could place the row.
    (dict(grain=A_S1), ROOT_LEDGER, A_S1, 0),
    # The row says s1; the snapshot says s0 was live. Both are true, and only
    # the stated one is what the work was on: it wins, ALONE.
    (dict(grain=A_S1, tree=snapshot(stories_wip=[A_S0])), ROOT_LEDGER, A_S1, 0),
    # 0.4.0/D8, M2: two live stories and no grain is the courier's refusal to
    # guess, and the reader does not un-do it.
    (dict(tree=snapshot(stories_wip=[A_S0, A_S1])), ROOT_LEDGER, None, 0),
    # One story and the feature that owns it are ONE candidate; a feature
    # beside it that does not own it is no candidate either.
    (dict(tree=snapshot(stories_wip=[A_S1], features_building=[ALPHA])),
     ROOT_LEDGER, A_S1, 0),
    (dict(tree=snapshot(stories_wip=[A_S1], features_building=[BETA])),
     ROOT_LEDGER, A_S1, 0),
    # #39: one feature and no story places NOTHING, old shape or new.
    (dict(tree=snapshot(features_building=[ALPHA])), ROOT_LEDGER, None, 0),
    (dict(tree=snapshot_legacy(features_building=[ALPHA])), ROOT_LEDGER,
     None, 0),
    # M3: a stated grain this milestone does not hold never falls through to
    # the snapshot. In the TREE's ledger it is simply not this milestone's...
    (dict(grain='9.9/gone/s0', tree=snapshot(stories_wip=[A_S1])),
     ROOT_LEDGER, None, 0),
    # ...and in the milestone's OWN ledger it is superseded spend, counted.
    (dict(grain='0.1/alpha/renamed-away'), OWN_LEDGER, None, 1),
    # A row naming no grain, stamped with a branch no milestone declares: the
    # snapshot is not consulted, because the stamp already said where it was.
    (dict(branch='feat/x', tree=snapshot(stories_wip=[A_S1])), ROOT_LEDGER,
     None, 0),
], ids=['stated', 'stated-outranks-snapshot', 'ambiguous-snapshot',
        'story-and-owner', 'story-and-stranger', 'feature-only',
        'feature-only-legacy', 'stated-elsewhere-in-the-tree',
        'stated-elsewhere-in-its-own-ledger', 'branch-outranks-snapshot'])
def test_which_unit_a_row_is_on_is_read_off_the_row(fields, rel, placed,
                                                    superseded):
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        row = json.loads(dispatch_line('2026-09-03T12:00:00Z',
                                       agent_type=PROBE, tokens_total=9,
                                       **{k: v for k, v in fields.items()
                                          if k != 'branch'}))
        row.update({k: v for k, v in fields.items() if k == 'branch'})
        with (root / rel).open('a', encoding='utf-8') as out:
            out.write(json.dumps(row) + '\n')
        code, out = report(root, '0.1', '--json')
    assert code == 0, out
    data = json.loads(out)
    assert [u['grain'] for u in data['units'] if u['agent'] == PROBE] == (
        [placed] if placed else [])
    assert data['superseded']['rows'] == superseded, data['superseded']


# --- #39: a hand record naming its courier twin's agent_id is ONE dispatch ----
COURIER = 'agent-7f'


@pytest.mark.parametrize('hand_id, branch, joined, units, elsewhere', [
    # The pair: ONE unit, on the hand row's grain and outcome, with the
    # courier's measured duration and issue — and nowhere else: not the
    # tree's grainless dispatch, which the courier alone would be.
    (COURIER, None, 1, [(A_S1, 60, 'landed', ['#41'])], (0, 0)),
    # The courier on ANOTHER milestone's branch, in the tree's ledger that
    # milestone reads too: still one unit, in the milestone the hand names.
    (COURIER, 'milestone/0.2', 1, [(A_S1, 60, 'landed', ['#41'])], (0, 0)),
    # An id no courier row carries joins nothing: the hand row is a unit on
    # its grain, and the courier — naming no grain — is the tree's.
    ('agent-other', None, 0, [(A_S1, None, 'landed', [])], (0, 1)),
])
def test_a_hand_record_joins_its_courier_twin_by_agent_id(hand_id, branch,
                                                          joined, units,
                                                          elsewhere):
    """The courier files a grainless row when no one story is building, and
    the documented remedy, `pm ledger record --grain`, appended a SECOND.
    Joined on `agent_id` and nothing else — never on matching numbers, which
    is a guess from coincidence (rule 9). The join is over every ledger in
    the tree, so no other report counts the pair a second time."""
    courier = json.loads(dispatch_line(
        '2026-09-03T12:00:00Z', agent_id=COURIER, messages=4, tool_calls=9,
        duration_s=60, usage={'output': 70}, issue=['#41']))
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        write(root / 'pm/roadmap/milestones/0.2.md',
              {'id': f'"{SECOND}"', 'kind': 'milestone', 'name': 'Next',
               'status': 'planning', 'branch': 'milestone/0.2'})
        put_ledger(root, json.dumps({**courier, **({'branch': branch}
                                                   if branch else {})}),
                   rel=ROOT_LEDGER)
        code, said = run_cli(root, 'ledger', 'record', '--grain', A_S1,
                             '--agent-id', hand_id, '--tool-calls', '8',
                             '--tokens-total', '500', '--outcome', 'landed')
        assert code == 0, said
        code, out = report(root, '0.1')
        assert code == 0, out
        data = json.loads(report(root, '0.1', '--json')[1])
        other = json.loads(report(root, SECOND, '--json')[1])
        tree_rows = json.loads(report(root, '--tree', '--json')[1])['rows']
    assert [(u['grain'], u['duration'], u['outcome'], u['issue'])
            for u in data['units']] == units
    # Counted, and a zero is printed as a zero (rule 11).
    assert f'   {joined} courier/hand pair(s) joined by agent_id' in out, out
    assert (len(other['units']), tree_rows.get('dispatch', 0)) == elsewhere


# --- the tree's report: `--tree` ----------------------------------------------
# A gate row names no grain, so 0.4.0/D3 files every one in the tree's ledger.
# Before 0.10.0 every milestone's report printed that same table under its own
# heading; now a milestone claims the runs stamped with its branch, and the
# rest are printed ONCE, headed as the tree's. Pinned: one row per gate, one
# run per row, a gate with ONE run still appears, a delta whose census moved
# is marked, and a row this section cannot use is NAMED.
GATES = 'gate cost'


def gate_line(ts: str, gate: str, verdict: str = 'PASS',
              duration_ms: int | None = 0, census: int | None = None) -> str:
    from agentic_sdlc.repo.pm import ledger as _ledger
    return _ledger.dumps(_ledger.gate_row(gate, verdict, duration_ms,
                                          census=census, ts=ts))


def gates_report(*lines: str, argv: tuple = (), local: tuple = ()) -> str:
    """A tree whose root ledgers are exactly the gate rows a case cares about:
    `lines` in the tracked one, `local` in the gitignored one new gate rows
    land in (#48)."""
    with tree(story_statuses=('done', 'ready')) as root:
        put_ledger(root, *lines, rel=ROOT_LEDGER)
        if local:
            put_ledger(root, *local, rel=LOCAL_LEDGER)
        code, out = report(root, '--tree', *argv)
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
    a gate that costs nothing. Half the rows in each root ledger (#48): the
    committed history and the local file are ONE table."""
    assert gates_report(*THREE_PARSE_ONE_LINT[:2],
                        local=THREE_PARSE_ONE_LINT[2:]).rstrip('\n') == """\
[ledger:report] tree — gate cost — 4 gate row(s), 2 gate(s), 1 delta(s) \
marked * for a census that moved or is absent, 0 row(s) this section could \
not use

-- gate (2)
gate   runs  first_ms  last_ms  delta_ms  census
parse     3      8000    30000   +22000*  -
lint      1      2000     2000         -  -

-- rows this section could not use (0)

   4 tree row(s) no milestone owns, by kind: gate 4; the same rows by branch: - 4
   0 row(s) name a grain no milestone in this tree holds — counted in no report"""


def test_a_gate_that_got_faster_carries_a_signed_negative_delta():
    out = gates_report(
        gate_line('2026-09-03T10:00:00Z', 'pm-shape-scan', duration_ms=34800),
        gate_line('2026-09-03T11:00:00Z', 'pm-shape-scan', duration_ms=900))
    assert row_of(out, 'gate (1)', 'pm-shape-scan') == [
        'pm-shape-scan', '2', '34800', '900', '-33900*', '-']


# A duration without its census invites the wrong conclusion: the same gate is
# legitimately slower on a bigger tree. The number is still printed — it was
# measured — but nothing may present it as a regression.
@pytest.mark.parametrize('first_census,last_census,expected', [
    (120, 120, ['parse', '2', '8000', '9000', '+1000', '120', '→', '120']),
    (120, 900, ['parse', '2', '8000', '30000', '+22000*', '120', '→', '900']),
    # Half a pair is not half an answer.
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
    assert row_of(out, 'gate (1)', 'parse') == expected
    marked = '0' if first_census == last_census else '1'
    assert f'{marked} delta(s) marked' in out.splitlines()[0]


def test_every_unusable_gate_row_is_named_with_why_and_the_good_row_survives():
    """Hard rule 4's read side: a row this section cannot use is NAMED, never
    dropped into silence and never coerced to a zero."""
    out = gates_report(*BROKEN_GATE_ROWS)
    assert block_rows(out, 'rows this section could not use (4)') == [
        ['lint', 'no', 'duration_ms', '2026-09-03T10:01:00Z'],
        ['warnings', 'duration_ms', 'is', 'not', 'an', 'integer',
         '2026-09-03T10:02:00Z'],
        ['unit', 'duration_ms', 'is', 'negative', '2026-09-03T10:03:00Z'],
        ['-', 'no', 'gate', 'name', '2026-09-03T10:04:00Z']]
    assert row_of(out, 'gate (1)', 'parse')[:2] == ['parse', '1']


def test_a_tree_with_no_gate_row_still_prints_the_table():
    """A missing table is indistinguishable from an empty one, and only one
    of those is true."""
    out = gates_report(dispatch_line('2026-09-03T10:05:00Z',
                                     agent_type='developer'))
    assert '-- gate (0)' in out
    assert '   1 tree row(s) no milestone owns, by kind: dispatch 1' in out


def test_the_gate_json_carries_every_field_and_names_what_it_could_not_use():
    """The incomparable mark included, so a caller need not re-derive it."""
    data = json.loads(gates_report(*THREE_PARSE_ONE_LINT, argv=('--json',)))
    assert data['gates'] == {
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
    assert (data['rows'], data['unplaced']) == ({'gate': 4}, 0)


# --- the roster: every block this report prints, named where a reader stands ---
# `bg-a-read-verb-names-three-of-its-thirteen-sections`. THE GATE IS THE SET:
# `--help`'s block titles and the titles the report PRINTS are compared both
# ways, so a new block reddens this the day it lands and a block that retires
# reddens it too.
SECTION_SEPARATOR = ' — '
HEADING_MARK = ' (heading)'
ROSTER_MARK = 'columns IN ORDER:'
TITLE_INDENT, COLUMN_INDENT = 45, 47
KIND_JOIN = ' / '


def help_roster() -> dict[str, tuple[str, ...]]:
    """`pm --help`'s block roster for `ledger report`, PARSED — one title to
    the columns it names, in order."""
    from agentic_sdlc.repo.pm import cli as pm_cli
    entry = (pm_cli.USAGE or '').split('THE TELEMETRY REPORT')[-1]
    roster: dict[str, list[str]] = {}
    titles: list[str] = []
    for line in entry.split(ROSTER_MARK)[-1].split('\n'):
        indent = len(line) - len(line.rstrip('\n').lstrip())
        if not line.strip():
            continue
        if indent < TITLE_INDENT:
            break
        if indent == TITLE_INDENT:
            titles = line.strip().replace(HEADING_MARK, '').split(KIND_JOIN)
            for title in titles:
                roster.setdefault(title, [])
        else:
            for title in titles:
                roster[title].extend(line.split())
    return {title: tuple(columns) for title, columns in roster.items()}


def printed_blocks(out: str) -> dict[str, set[str]]:
    """One report's block titles to the column names it printed under them:
    a three-part `<prefix> <id> — <title> — <census>` heading, or a
    `-- <title> (n)` table."""
    from agentic_sdlc.repo.pm import report as pm_report
    lines = out.splitlines()
    found: dict[str, set[str]] = {}
    for i, line in enumerate(lines):
        if (line.startswith(pm_report.HEADING_PREFIX)
                and line.count(SECTION_SEPARATOR) >= 2):
            found.setdefault(line.split(SECTION_SEPARATOR)[1], set())
        elif line.startswith(f'{pm_report.BLOCK_PREFIX} '):
            title = line[3:].rsplit(' (', 1)[0]
            header = lines[i + 1] if i + 1 < len(lines) else ''
            found.setdefault(title, set()).update(
                header.split() if header.strip() else [])
    return found


def compared_report(*argv) -> str:
    with tree(feature_status='done', story_statuses=('done', 'ready')) as root:
        seeded(root)
        second_milestone(root)
        code, out = report(root, '0.1', SECOND, *argv)
    assert code == 0, out
    return out


def every_block_printed() -> dict[str, set[str]]:
    """Every block the verb has, from the three seeds that between them reach
    all of them: one milestone, the tree's gate rows, and two milestones."""
    found: dict[str, set[str]] = {}
    for out in (seeded_report(), gates_report(*THREE_PARSE_ONE_LINT),
                compared_report()):
        for title, columns in printed_blocks(out).items():
            found.setdefault(title, set()).update(columns)
    return found


class TestTheHelpNamesEveryBlockItPrints:
    """Rule 11's read side, gated in BOTH directions for `ledger report`."""

    def test_the_census_of_blocks_is_not_zero(self):
        """Rule 4: an empty scrape would make both directions below pass over
        nothing."""
        assert len(every_block_printed()) >= 8, sorted(every_block_printed())
        assert len(help_roster()) >= 8, sorted(help_roster())

    def test_every_block_printed_is_named_in_help(self):
        printed, roster = every_block_printed(), help_roster()
        assert set(printed) - set(roster) == set(), (
            f'{sorted(set(printed) - set(roster))} print(s) and `pm --help` '
            f'names {len(roster)} of {len(printed)} blocks — a capability '
            f'nobody can find is a capability you do not have')

    def test_help_names_no_block_that_stopped_printing(self):
        printed, roster = every_block_printed(), help_roster()
        assert set(roster) - set(printed) == set(), (
            f'{sorted(set(roster) - set(printed))} is named in `pm --help` '
            f'and no seed printed it')

    def test_every_column_named_is_a_column_printed(self):
        """A title with the wrong columns beside it is the same defect one
        layer down. `<placeholder>` columns are the clock's per-state ones."""
        printed = every_block_printed()
        for title, columns in help_roster().items():
            if not printed.get(title):
                continue
            named = {c for c in columns if not c.startswith('<')}
            assert named <= printed[title], (
                f'{title}: `--help` names {sorted(named - printed[title])}, '
                f'which is no column of {sorted(printed[title])}')


# --- more than one milestone --------------------------------------------------
# `bg-the-telemetry-verb-cannot-compare-two-milestones`. What is pinned here:
# ONE GOLDEN for the whole compared report; the `--json` SHAPE; ORDER read,
# never chosen (rule 9); a root row in exactly ONE block; the refusal matrix.
PLAN_REL = 'pm/roadmap/releases.md'
COMPARED_TABLE = """\
[ledger:report] 0.1 → 0.2 — milestone comparison — 2 milestone(s) in given \
order, 3 block(s), 3 block(s) marked * for a census that moved or is absent

-- units (2)
milestone  units  open_units  tokens  duration  rows
0.1            4           1    4000       300    11
0.2            1           0     700        60     2
delta         -3         -1*  -3300*     -240*   -9*

-- by agent (2)
milestone  agents  developer  reviewer
0.1             2       3000      1000
0.2             1        700         -
delta          -1     -2300*         -

-- time per state (2)
milestone  grains  building_s  reviewing_s  closed_s   open_s
0.1             7        1080          120      1200    88500
0.2             1           -            -         -     3600
delta          -6           -            -         -  -84900*

[ledger:report] tree — gate cost — 0 gate row(s), 0 gate(s), 0 delta(s) \
marked * for a census that moved or is absent, 0 row(s) this section could \
not use

-- gate (0)

-- rows this section could not use (0)

   0 tree row(s) no milestone owns, by kind: none; the same rows by branch: none
   0 row(s) name a grain no milestone in this tree holds — counted in no report"""


@pytest.fixture
def frozen(monkeypatch):
    """Read time held still. `open_s` is measured against NOW, and a golden
    whose last column moved every second would prove nothing."""
    from datetime import datetime, timezone
    from agentic_sdlc.repo.pm import report as pm_report
    when = datetime(2026, 9, 4, 11, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(pm_report, '_now', lambda: when)
    return when


def compare(root, *argv) -> tuple[int, str]:
    return report(root, '0.1', SECOND, *argv)


def two_milestones(root) -> None:
    seeded(root)
    second_milestone(root)


class TestTwoMilestonesSideBySide:
    """The comparative question, answered by the verb instead of by hand."""

    def test_two_ids_print_this_exact_table(self, frozen):
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            two_milestones(root)
            code, out = compare(root)
        assert code == 0, out
        assert out.rstrip('\n') == COMPARED_TABLE

    def test_the_json_is_one_joined_document_and_not_two_reports(self, frozen):
        """The shape decision, asserted where it is DECIDED — in
        `report.compare_data`'s docstring and here."""
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            two_milestones(root)
            code, out = compare(root, '--json')
        assert code == 0, out
        data = json.loads(out)
        assert sorted(data) == ['blocks', 'milestones', 'order', 'tree']
        assert data['milestones'] == ['0.1', SECOND]
        assert data['order'] == 'given'
        units = data['blocks'][0]
        assert units['census'] == 'units' and units['moved'] is True
        assert [row['milestone'] for row in units['rows']] == ['0.1', SECOND]
        assert units['delta']['units'] == -3
        # Absent stays absent through the subtraction, exactly as in the table.
        agents = data['blocks'][1]
        assert agents['delta']['reviewer'] is None
        assert [b['block'] for b in data['blocks']] == [
            'units', 'by agent', 'time per state']

    def test_the_plan_sequences_the_ids_it_holds_and_says_so(self, frozen):
        """Rule 9's edge. `releases.md` `order` is a DECLARATION, so reading it
        to sequence two ids the caller named is reading; picking WHICH two
        would be deciding, and nothing here does that."""
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            two_milestones(root)
            write(root / PLAN_REL, {'id': 'roadmap', 'kind': 'roadmap',
                                    'order': f'\n  - "{SECOND}"\n  - "0.1"'})
            code, out = compare(root)
        assert code == 0, out
        assert out.splitlines()[0].startswith(
            f'[ledger:report] {SECOND} → 0.1 — milestone comparison — '
            f'2 milestone(s) in plan order')

    def test_an_id_the_plan_does_not_hold_leaves_the_order_given(self, frozen):
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            two_milestones(root)
            write(root / PLAN_REL, {'id': 'roadmap', 'kind': 'roadmap',
                                    'order': f'\n  - "{SECOND}"'})
            code, out = compare(root)
        assert code == 0, out
        assert '2 milestone(s) in given order' in out.splitlines()[0]

    def test_a_milestone_with_no_ledger_of_its_own_says_so(self, frozen):
        """Rule 11: a column of zeros with no reason beside it reads as work
        that cost nothing. The line names the milestone, under the heading,
        before the numbers."""
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            two_milestones(root)
            (root / SECOND_LEDGER).unlink()
            code, out = compare(root)
        assert code == 0, out
        assert out.splitlines()[1] == f'   {SECOND} — no ledger'

    def test_a_root_row_lands_in_exactly_one_block(self, frozen):
        """`ft-a-milestone-reports-only-its-own-rows`: a milestone reads only
        rows it OWNS — its grain, or its declared `branch:` on a row naming no
        grain. Every other root row is the TREE's, printed once under its own
        heading and never under either milestone. Shipped, every root row
        landed under EVERY milestone, and the delta read 0 over the lie."""
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            two_milestones(root)
            write(root / 'pm/roadmap/milestones/0.1.md',
                  {'id': '"0.1"', 'kind': 'milestone', 'name': 'Demo',
                   'status': 'building', 'branch': 'milestone/0.1'})
            put_ledger(root, *(json.dumps(row) for row in (
                {'ts': '2026-09-05T10:00:00Z', 'kind': 'gate', 'gate': 'unit',
                 'verdict': 'PASS', 'duration_ms': 10, 'branch': 'main'},
                {'ts': '2026-09-05T10:01:00Z', 'kind': 'gate', 'gate': 'lint',
                 'verdict': 'PASS', 'duration_ms': 20,
                 'branch': 'milestone/0.1'},
                {'ts': '2026-09-05T10:02:00Z', 'kind': 'dispatch',
                 'agent_type': 'scout', 'tokens_total': 900})),
                rel=ROOT_LEDGER)
            code, out = compare(root, '--json')
            own = json.loads(report(root, '0.1', '--json')[1])
        assert code == 0, out
        data = json.loads(out)
        tree_gates = [g['gate'] for g in data['tree']['gates']['gates']]
        # The row on `main` is the tree's; the row on 0.1's branch is 0.1's,
        # in 0.1's own gate table — every gate row in exactly one table.
        assert tree_gates == ['unit'], data['tree']
        assert [g['gate'] for g in own['gates']['gates']] == ['lint'], own
        units = next(b for b in data['blocks'] if b['block'] == 'units')
        rows = {r['milestone']: r['rows'] for r in units['rows']}
        # The seeded 0.1 ledger's 11 placed rows (its session row names no
        # grain and is counted apart), plus the gate on its branch.
        assert rows == {'0.1': 12, SECOND: 2}, units
        # The grainless dispatch names no grain and no branch: the tree's.
        agents = next(b for b in data['blocks'] if b['block'] == 'by agent')
        assert 'scout' not in agents['columns'], agents
        assert data['tree']['rows'] == {'dispatch': 1, 'gate': 1}, data['tree']

    @pytest.mark.parametrize('argv, says', [
        # An id that resolves to nothing: the ONE sentence every verb gives a
        # bad id, not a second wording invented for this path.
        (('0.1', 'no-such-milestone'),
         "no grain resolves from id 'no-such-milestone'"),
        # A LEVEL is a single-id question; two of them are one ledger read
        # twice.
        (('0.1', '0.1/alpha'), 'is a feature and a comparison is between'),
        (('0.1', A_S0), 'is a story and a comparison is between'),
        # A milestone against itself is a delta of zero by construction.
        (('0.1', '0.1'), "'0.1' was named twice"),
        # One rev cannot say which moment each milestone should be read at.
        (('0.1', SECOND, '--from', 'HEAD'),
         '--from reads ONE rev and 2 milestone ids were named'),
    ])
    def test_every_refusal_exits_2_and_names_what_it_refused(self, argv, says):
        with tree(feature_status='done',
                  story_statuses=('done', 'ready')) as root:
            two_milestones(root)
            before = {p: p.read_bytes() for p in sorted(root.rglob('*'))
                      if p.is_file()}
            code, out = report(root, *argv)
            after = {p: p.read_bytes() for p in sorted(root.rglob('*'))
                     if p.is_file()}
        assert code == 2, out
        assert says in out, out
        # A refusal writes nothing, which is the half an exit code cannot say.
        assert after == before
