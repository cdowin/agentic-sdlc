"""test_pm_ledger_record.py — `pm ledger record` and `pm ledger show`.

The contract under test, in Chris's words (2026-09-03): *"the ledger is
actually very very simple. It shouldn't judge or infer or even guard really
anything … It just timestamps transitions and stamps whatever hook data.
Judgement/inference is left to the caller."* So:

  * a transcript's numbers are COPIED — sums, counts, first/last stamp, model —
    and a field the transcript lacks is an absent KEY, never a zero and never a
    label (no `unattributed`, no `?`, no weight, no cost);
  * every row carries D3's `tree` snapshot: the ACTIVE tree's live state at the
    instant of the write, every candidate id verbatim, empty lists when empty;
  * the refusals are input hygiene only (SDLC § 5), and every one of them
    refuses WITHOUT writing — a half-written line in an append-only committed
    file is permanent, and `records_of` then reports a parse defect on a line
    nobody wrote;
  * a transcript with NO assistant record REFUSES (exit 2). A row of zeros is
    indistinguishable afterwards from a cheap dispatch, which is hard rule 4's
    read-side sin with a timestamp on it;
  * the reader never goes red on a row this version did not write: the file is
    `merge=union`, so another branch's rows and a later package's rows arrive
    in shapes this matcher has never emitted;
  * `pm ledger show` is a subtraction over raw rows (D8), and prints a total
    only when the grain actually reached its vocabulary's last state.

THE FIXTURES (tests/fixtures/transcripts/):

  * `subagent-dispatch.jsonl` — the first 60 records of a REAL subagent
    transcript (`~/.claude/projects/…/subagents/agent-*.jsonl`, 2026-08-29),
    scrubbed: every key kept, every string value replaced by `"x"` except the
    ones the parser reads (`type`, `timestamp`, the ids, `message.model`, block
    `type`s and tool `name`s) and the `usage` numbers.
  * `main-session.jsonl` — the Stop shape, written by hand: `isSidechain:
    false`, no `agentId`, two models across the session, one assistant
    record with no `usage` at all, and one `<synthetic>` API-error record.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from support.pm import (ledger_lines, ledger_rows, loaded, run_cli, run_gate,
                        tree, write)

from agentic_sdlc.core import frontmatter
from agentic_sdlc.repo.pm import arrive, ledger, roster
from agentic_sdlc.repo.pm import inventory, vocabulary

# THE ALL-SEVEN-SEED FLOW, and why these rows keep the declaration they were
# written under rather than being rewritten: tests/test_pm_ledger.py, beside the
# same `LEGACY_FLOW`.
from support.pm import declaring as _declaring, tree as _seed_tree  # noqa: E402
from agentic_sdlc.repo.pm import inventory, vocabulary  # noqa: E402

LEGACY_FLOW = _declaring(feature=vocabulary.DEFAULT_FLOWS['milestone'],
                         story=vocabulary.DEFAULT_FLOWS['milestone'])


def tree(**kwargs):
    """`support.pm.tree` under the all-seven flow these ledgers assume."""
    kwargs.setdefault('config', LEGACY_FLOW)
    return _seed_tree(**kwargs)

FIXTURES = Path(__file__).parent / 'fixtures' / 'transcripts'
SUBAGENT = FIXTURES / 'subagent-dispatch.jsonl'
MAIN_SESSION = FIXTURES / 'main-session.jsonl'

STORY = '0.1/alpha/s0'
BUG = '0.1/bugs/b0'
LEDGER_REL = 'pm/roadmap/ledgers/0.1.jsonl'
# 0.4.0/D3: a row naming no grain lands in the TREE's ledger. A
# transcript row carries no grain yet and a `gate` row never will, so
# this is where most of this module's rows arrive.
ROOT_LEDGER_REL = 'pm/roadmap/ledger.jsonl'

# A stamp for the rows a case seeds by hand, and the stock gate-form argv.
TS = '2026-09-03T10:00:00Z'
GATE = ('--gate', 'check', '--verdict', 'PASS', '--duration-ms', '12')

# The tree `support.pm.tree()` builds: one milestone `building`, one feature
# `building`, and whatever story statuses the case asked for. Two key
# families (decision D7): the frozen five, DEPRECATED and matched by the
# seed's words, and the three category keys the report attributes by.
STOCK_TREE = {'milestones_building': ['0.1'], 'features_building': ['0.1/alpha'],
              'features_review': [], 'stories_wip': [], 'stories_review': [],
              'milestones_in_progress': ['0.1'],
              'features_in_progress': ['0.1/alpha'],
              'stories_in_progress': []}


def fresh(**over) -> dict:
    snap = dict(STOCK_TREE)
    snap.update(over)
    return snap


def record(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'record', *argv)


def all_ledger_lines(root) -> dict[str, list[str]]:
    """{relative path: lines} for EVERY ledger in the tree.

    There are two homes since 0.4.0/D3 — `<roadmap>/ledgers/<id>.jsonl` per
    milestone for attributed rows and `<roadmap>/ledger.jsonl` for the rest —
    so "the file was not written" is a claim about the tree, not about one
    path. A refusal that wrote into the other file would pass a single-path
    check.
    """
    found = sorted(root.rglob('ledger.jsonl')) + sorted(root.rglob('ledgers/*.jsonl'))
    return {str(path.relative_to(root)):
            path.read_text(encoding='utf-8').splitlines()
            for path in found}


def only_row(root) -> dict:
    """The one row in the tree, wherever it landed.

    Location-agnostic ON PURPOSE: every case reaching for this is asserting
    what a row CONTAINS — the module's subject — and WHERE it goes is
    `_row_ledger`'s, proven by the routing cases below over fixtures where
    the candidate directories differ. Asserting one row across the whole tree
    is also the stronger claim: a second row written somewhere else fails here
    and would not fail a read of one path.
    """
    rows = [row for lines in all_ledger_lines(root).values()
            for line in lines if line.strip()
            for row in [json.loads(line)]]
    assert len(rows) == 1, f'expected one row, got {rows}'
    return rows[0]


def stamped(row: dict) -> dict:
    """The row minus `ts`, having asserted `ts` is a fresh full-UTC stamp."""
    when = datetime.strptime(row['ts'], ledger.TS_FORMAT).replace(
        tzinfo=timezone.utc)
    assert abs(when - datetime.now(timezone.utc)) < timedelta(minutes=5), row
    return {k: v for k, v in row.items() if k != 'ts'}


def put_ledger(root, *lines: str, rel: str = LEDGER_REL) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(line + '\n' for line in lines), encoding='utf-8')


def status_line(ts: str, grain: str, frm: str, to: str) -> str:
    return ledger.dumps(ledger.status_row(grain, frm, to, ts=ts))


def bug_doc(root, status: str = 'open') -> None:
    write(root / 'pm/roadmap/bugs/b0.md',
          {'id': BUG, 'milestone': '"0.1"', 'name': 'B0', 'status': status})


def assistant(model: str, ts: str = '2026-09-03T10:00:00Z') -> dict:
    return {'type': 'assistant', 'timestamp': ts,
            'message': {'model': model,
                        'usage': {'input_tokens': 1, 'output_tokens': 2}}}


def refuses(root, *argv, needle: str = '') -> str:
    """Exit 2, the message names why, and the file's LINES are unchanged."""
    before = all_ledger_lines(root)
    code, out = record(root, *argv)
    assert code == 2, (argv, out)
    assert all_ledger_lines(root) == before, f'a refusal wrote a row: {argv}'
    if needle:
        assert needle in out, (argv, out)
    return out


# --- one transcript in, one exact row out -------------------------------------

def test_the_subagent_fixture_produces_this_exact_dispatch_row():
    """Every key, every sum, the key ORDER, and one compact line. The row is
    what story 03's report joins on, so a field that quietly changed shape
    would be a wrong number in a table nobody re-derives."""
    with tree(story_statuses=('building',)) as root:
        code, out = record(root, '--from-transcript', str(SUBAGENT),
                           '--event', 'SubagentStop',
                           '--agent-type', 'developer')
        assert code == 0, out
        # This tree has exactly ONE story in progress, so D2's fallback
        # resolves the grain and the row is ATTRIBUTED — which puts it in that
        # grain's milestone ledger, not the tree's.
        lines = ledger_lines(root)
        row = only_row(root)
    assert stamped(row) == {
        'kind': 'dispatch',
        'grain': STORY,
        'session_id': '406aac76-fb60-4d90-9383-5b0af2163067',
        'agent_id': 'a0c097f0217026051',
        'agent_type': 'developer',
        'model': 'claude-sonnet-5',
        'started_at': '2026-08-29T03:38:09Z',
        'ended_at': '2026-08-29T03:39:29Z',
        'duration_s': 80,
        'messages': 36,
        'tool_calls': 23,
        'tools': {'Bash': 22, 'Write': 1},
        'tool_calls_before_first_write': 20,
        'usage': {'input': 72, 'output': 5829, 'cache_creation': 165473,
                  'cache_read': 1820260},
        'tree': fresh(stories_wip=[STORY], stories_in_progress=[STORY]),
    }
    # `ROW_KEYS` order, minus the keys nothing supplied: the durable line's
    # own shape, not just its contents.
    assert list(row) == [
        'ts', 'kind', 'grain', 'session_id', 'agent_id', 'agent_type', 'model',
        'started_at', 'ended_at', 'duration_s', 'messages', 'tool_calls',
        'tools', 'tool_calls_before_first_write', 'usage', 'tree']
    assert len(lines) == 1
    assert lines[0] == json.dumps(json.loads(lines[0]), separators=(',', ':'))


def test_a_field_nothing_supplied_is_an_absent_key_never_a_label():
    """No `--agent-type` and no transcript field for it: no key at all. A
    sentinel here is a value the report would have to learn to disbelieve."""
    with tree() as root:
        assert record(root, '--from-transcript', str(SUBAGENT),
                      '--event', 'SubagentStop')[0] == 0
        row = only_row(root)
    assert 'agent_type' not in row
    assert 'grain' not in row
    assert 'unattributed' not in json.dumps(row)
    assert '?' not in json.dumps(row)


def test_the_flags_win_over_the_transcripts_own_ids():
    """The hook payload names the ids authoritatively; the transcript is the
    fallback for a hand run."""
    with tree() as root:
        assert record(root, '--from-transcript', str(SUBAGENT),
                      '--event', 'SubagentStop',
                      '--session-id', 'S', '--agent-id', 'A')[0] == 0
        row = only_row(root)
    assert (row['session_id'], row['agent_id']) == ('S', 'A')


def test_the_main_session_fixture_produces_a_session_row():
    """The Stop shape, and with it the three transcript oddities that matter:
    two models in one session is a LIST (never a pick), an assistant record
    with no `usage` still counts as a message, and the `<synthetic>` record
    counts everywhere except in `model`. No `agent_id` key: there is none."""
    with tree() as root:
        code, out = record(root, '--from-transcript', str(MAIN_SESSION),
                           '--event', 'Stop')
        assert code == 0, out
        row = only_row(root)
    assert stamped(row) == {
        'kind': 'session',
        'session_id': '11111111-2222-3333-4444-555555555555',
        'model': ['claude-opus-5', 'claude-sonnet-5'],
        'started_at': '2026-09-03T10:00:00Z',
        'ended_at': '2026-09-03T10:07:36Z',
        'duration_s': 456,
        'messages': 4,
        'tool_calls': 3,
        'tools': {'Read': 1, 'Edit': 1, 'Bash': 1},
        'tool_calls_before_first_write': 1,
        'usage': {'input': 15, 'output': 1240, 'cache_creation': 5000,
                  'cache_read': 181000},
        'tree': fresh(),
    }


# `<synthetic>` is Claude Code's marker for an assistant record IT generated,
# not a model identifier (0.23.0/ledger D3) — and the rule is the EXACT token,
# never the `<…>` shape: a census of 734 real transcripts found this value and
# no other bracketed one in this position, so a shape rule would make the NEXT
# pseudo-name vanish from the one field that would have reported it.
@pytest.mark.parametrize('name', [
    'claude-opus-5',      # a real identifier is never dropped
    '<compaction>',       # an unknown bracketed name comes through raw
    '<synthetic',         # near misses a substring/prefix rule would swallow
    '<SYNTHETIC>',
])
def test_only_the_exact_synthetic_token_is_dropped_from_the_model_list(name):
    summary = ledger.transcript_summary(enumerate([
        assistant('<synthetic>'), assistant(name, '2026-09-03T10:00:30Z')], 1))
    assert summary['model'] == name


def test_a_synthetic_record_counts_everywhere_but_the_model_field():
    """Dropped from ONE field, not from the row: the record happened, and a
    summary that stopped counting it would answer "what did this session cost"
    with a number that is quietly short (hard rule 4). A transcript of nothing
    else has NO `model` key at all — the absence rule, not a placeholder."""
    two = ledger.transcript_summary(enumerate([
        assistant('claude-fable-5-1'),
        assistant('<synthetic>', '2026-09-03T10:00:30Z')], 1))
    assert (two['messages'], two['usage']['input'], two['usage']['output']) == (
        2, 2, 4)
    alone = ledger.transcript_summary(enumerate([assistant('<synthetic>')], 1))
    assert alone['model'] is None
    assert alone['messages'] == 1
    assert 'model' not in ledger.usage_row('session', **alone)


def test_a_dispatch_that_never_wrote_reports_its_whole_tool_count():
    """`tool_calls_before_first_write` is the whole count when no write ever
    happened — not zero. A read-only dispatch did all of its work before a
    write that never came, and a 0 there would read as 'wrote immediately'."""
    summary = ledger.transcript_summary(enumerate([
        {'type': 'assistant', 'timestamp': '2026-09-03T10:00:00Z',
         'message': {'content': [{'type': 'tool_use', 'name': 'Read'},
                                 {'type': 'tool_use', 'name': 'Bash'}]}}], 1))
    assert (summary['tool_calls'],
            summary['tool_calls_before_first_write']) == (2, 2)


@pytest.mark.parametrize('raw,expected', [
    # Truncated, never rounded: a rounded `ended_at` can land after the stop
    # that recorded it, and a duration is a subtraction over these strings.
    ('2026-08-29T03:38:09.719Z', '2026-08-29T03:38:09Z'),
    # Converted, never relabelled — reading an offset as UTC shifts every
    # duration by the machine's own.
    ('2026-08-29T05:38:09+02:00', '2026-08-29T03:38:09Z'),
])
def test_a_transcript_stamp_is_normalised_to_full_utc_seconds(raw, expected):
    assert ledger.normalise_ts(raw, 'x') == expected


# --- D3's tree snapshot -------------------------------------------------------

def test_the_tree_snapshot_is_the_live_trees_state_verbatim():
    """Every bucket present, populated ones verbatim and empty ones EMPTY
    rather than absent — the report attributes a dispatch by reading these, so
    a missing bucket is a dispatch silently attributed to nothing.

    Both key families on one row (decision D7): the category keys hold every
    grain in `in_progress` — `accepted` included, a word no frozen key can
    spell — and the frozen keys hold exactly what they always held."""
    with tree(story_statuses=('building', 'done', 'accepted')) as root:
        write(root / 'pm/roadmap/features/beta.md',
              {'id': '0.1/beta', 'kind': 'feature', 'milestone': '"0.1"',
               'name': 'Beta', 'status': 'reviewing', 'reviewed': ''})
        write(root / 'pm/roadmap/stories/b0.md',
              {'id': '0.1/beta/b0', 'kind': 'story', 'feature': '0.1/beta',
               'milestone': '"0.1"', 'name': 'B0', 'status': 'reviewing'})
        assert record(root, '--from-transcript', str(SUBAGENT),
                      '--event', 'SubagentStop')[0] == 0
        snap = only_row(root)['tree']
    assert snap == {
        'milestones_building': ['0.1'],
        'features_building': ['0.1/alpha'],
        'features_review': ['0.1/beta'],
        'stories_wip': [STORY],
        'stories_review': ['0.1/beta/b0'],
        'milestones_in_progress': ['0.1'],
        'features_in_progress': ['0.1/alpha', '0.1/beta'],
        'stories_in_progress': [STORY, '0.1/alpha/s2', '0.1/beta/b0'],
    }


def test_a_renamed_vocabulary_fills_the_category_keys_and_empties_the_frozen():
    """The row shape's honest statement under a renamed vocabulary: the frozen
    keys can spell none of the words, so they are empty — never absent — and
    the category keys carry the tree. An old reader sees an idle tree; the
    report reads the category keys and sees the work."""
    from support.pm import declaring, write_config
    renamed = {'todo': ('queued',), 'in_progress': ('doing',),
               'done': ('shipped',)}
    with tree(milestone_status='doing', feature_status='doing',
              story_statuses=('doing', 'queued')) as root:
        write_config(root, declaring(milestone=renamed, feature=renamed,
                                     story=renamed))
        assert record(root, '--grain', STORY)[0] == 0
        snap = only_row(root)['tree']
    assert snap == {
        'milestones_building': [], 'features_building': [],
        'features_review': [], 'stories_wip': [], 'stories_review': [],
        'milestones_in_progress': ['0.1'],
        'features_in_progress': ['0.1/alpha'],
        'stories_in_progress': [STORY],
    }


def test_the_archived_tree_is_not_the_live_tree():
    """`zz_archive/` is excluded by the same walkers `check pm` uses — a
    snapshot that counted it would put retired grains on every row forever."""
    with tree() as root:
        archived = root / 'pm/roadmap/zz_archive/0.0-old'
        write(archived / 'milestone.md',
              {'id': '"0.0"', 'name': 'Old', 'status': 'building'})
        write(archived / 'features/gamma/feature.md',
              {'id': '0.0/gamma', 'milestone': '"0.0"', 'name': 'G',
               'status': 'building', 'reviewed': ''})
        assert record(root, '--from-transcript', str(SUBAGENT),
                      '--event', 'SubagentStop')[0] == 0
        snap = only_row(root)['tree']
    # Every bucket present and the four empty ones EMPTY, not absent.
    assert snap == fresh()
    assert [k for k, v in snap.items() if v == []] == [
        'features_review', 'stories_wip', 'stories_review',
        'stories_in_progress']


# --- the hand and gate forms: exactly what they were given, and nothing else ---

@pytest.mark.parametrize('kwargs,argv,expected', [
    # Everything given. `cache_creation`/`cache_read` are ABSENT, not 0 —
    # nobody counted them, and a 0 would say they were counted and were none.
    (dict(story_statuses=('building',)),
     ('--grain', STORY, '--agent-type', 'reviewer', '--tokens-in', '1200',
      '--tokens-out', '38000', '--tool-calls', '37', '--duration-s', '812'),
     {'kind': 'dispatch', 'grain': STORY, 'agent_type': 'reviewer',
      'duration_s': 812, 'tool_calls': 37,
      'usage': {'input': 1200, 'output': 38000},
      'tree': STOCK_TREE | {'stories_wip': [STORY],
                            'stories_in_progress': [STORY]}}),
    # Nothing given: every number is a key the row does not carry.
    (dict(), ('--grain', STORY),
     {'kind': 'dispatch', 'grain': STORY, 'tree': STOCK_TREE}),
    # Zero given: recorded, because zero is a measurement.
    (dict(), ('--grain', STORY, '--tool-calls', '0', '--tokens-in', '0'),
     {'kind': 'dispatch', 'grain': STORY, 'tool_calls': 0,
      'usage': {'input': 0}, 'tree': STOCK_TREE}),
    # ONE TOTAL, which is what a subagent completion actually reports: its own
    # key, and no `usage` at all — a total split in half by this verb would be
    # a measurement nobody made.
    (dict(), ('--grain', STORY, '--tokens-total', '1234'),
     {'kind': 'dispatch', 'grain': STORY, 'tokens_total': 1234,
      'tree': STOCK_TREE}),
    # What became of it, as the caller STATED it (#41); never derived.
    (dict(), ('--grain', STORY, '--outcome', 'stopped:re-planned'),
     {'kind': 'dispatch', 'grain': STORY, 'outcome': 'stopped:re-planned',
      'tree': STOCK_TREE}),
    # The grain recorded is the FILE's own id, unquoted — the string every
    # status row spells, or the report joins nothing to it.
    (dict(), ('--grain', '0.1'),
     {'kind': 'dispatch', 'grain': '0.1', 'tree': STOCK_TREE}),
    # `--event` is what makes it a session row; the kind is the EVENT's.
    (dict(), ('--grain', STORY, '--event', 'Stop'),
     {'kind': 'session', 'grain': STORY, 'tree': STOCK_TREE}),
])
def test_a_hand_row_carries_exactly_what_it_was_given(kwargs, argv, expected):
    with tree(**kwargs) as root:
        code, out = record(root, *argv)
        assert code == 0, out
        row = only_row(root)
    assert stamped(row) == expected


@pytest.mark.parametrize('argv,expected', [
    (GATE + ('--census', '228'),
     {'kind': 'gate', 'gate': 'check', 'verdict': 'PASS', 'duration_ms': 12,
      'census': 228}),
    # A census the gate did not report is an absent KEY. A `0` would say it
    # walked nothing, which is the zero-file census rule 4 calls a sin.
    (GATE, {'kind': 'gate', 'gate': 'check', 'verdict': 'PASS',
            'duration_ms': 12}),
    (GATE + ('--census', '0'),
     {'kind': 'gate', 'gate': 'check', 'verdict': 'PASS', 'duration_ms': 12,
      'census': 0}),
    (('--gate', 'z-layer-scan', '--verdict', 'PASS', '--duration-ms', '0'),
     {'kind': 'gate', 'gate': 'z-layer-scan', 'verdict': 'PASS',
      'duration_ms': 0}),
    # `SKIP` is the verdict that must never read as a PASS, so it is the one
    # non-PASS spelling proven to reach the row intact.
    (('--gate', 'check', '--verdict', 'SKIP', '--duration-ms', '3'),
     {'kind': 'gate', 'gate': 'check', 'verdict': 'SKIP', 'duration_ms': 3}),
])
def test_a_gate_row_carries_exactly_what_it_was_given(argv, expected):
    """No `grain` and no `tree`: a gate is not work somebody was dispatched to
    do, and folding it into either would make the spend table bill a story for
    the seconds `make check` spent."""
    with tree(story_statuses=('building',)) as root:
        code, out = record(root, *argv)
        assert code == 0, out
        row = only_row(root)
    assert stamped(row) == expected


# --- it never exits 0 having written nothing (story criterion 3) --------------
# The FAIL-OPEN promise is the shell caller's — story 02 discards this exit
# code so a ledger that cannot be written is never a gate failure. That is
# exactly why this verb must not lie about having recorded: a silent success
# would make the discarded failure unauditable.

# 0.4.0/D3: ONE reason is left, and it is not about the tree's state. A gate
# row is refused when there is nowhere at all to put it — no `pm/roadmap` — and
# `append_row` creates the FILE but never the directory. Every other row this
# roster used to carry ("no milestone is in progress", "several are", "the plan
# declares no `order`") is a write now, each proven above.
# 0.4.0/D3 + 0.3.0 review X1, merged. A gate row names no grain, so it lands in
# the tree's own ledger: there is no plan to consult and no milestone to pick,
# and the ONLY way to have nowhere to file it is to have no PM tree at all.
# That case is INFORMATION, not a refusal — reporting it as one made every gate
# of every run print `the recorder exited 1`, which reads as a broken install.
# One line, exit 0, and still no row, which is the half that must not change.
@pytest.mark.parametrize('kwargs,second_milestone', [
    (dict(), False),
    (dict(milestone_status='planning'), False),
    (dict(), True),
])
def test_a_tree_with_no_roadmap_is_information_not_a_refusal(
        kwargs, second_milestone):
    with tree(**kwargs) as root:
        if second_milestone:
            write(root / 'pm/roadmap/milestones/0.2.md',
                  {'id': '"0.2"', 'name': 'Next', 'status': 'building'})
        shutil.rmtree(root / 'pm')
        got, out = record(root, *GATE)
        assert (got, 'no PM tree' in out) == (0, True), out
        assert list(root.rglob('ledger.jsonl')) == []


# --- D1: a row is routed by its GRAIN, and no status is read ------------------
# The lookup these replace asked which milestone was `in_progress` and refused
# on none and on several. Every case below is a write that used to be REFUSED
# or MISFILED, so each one fails at the commit before this story.
# The second milestone's document and the ledger keyed to its id: one file per
# milestone under `<roadmap>/ledgers/`, which is where an ATTRIBUTED row goes.
SECOND_DOC = 'pm/roadmap/milestones/0.2.md'
SECOND_LEDGER = 'pm/roadmap/ledgers/0.2.jsonl'


def two_milestones(root, other_status: str = 'planning') -> str:
    """A second milestone with a feature of its own, so the milestone that owns
    the GRAIN and the milestone that is BUILDING are two different directories.

    Without that separation a case asserting "the row landed in 0.1" passes for
    the old reason — 0.1 is also the one milestone in progress — and proves
    nothing about what routed it. Returns the second feature's id.
    """
    write(root / SECOND_DOC,
          {'id': '"0.2"', 'kind': 'milestone', 'name': 'Next',
           'status': other_status})
    write(root / 'pm/roadmap/features/beta.md',
          {'id': '0.2/beta', 'kind': 'feature', 'milestone': '"0.2"',
           'name': 'Beta', 'status': 'planning', 'reviewed': ''})
    return '0.2/beta'


def test_a_grain_in_a_planning_milestone_records():
    """Exit 1 with no write until this story: nothing was `in_progress` in
    0.2, so the row that names 0.2's feature had nowhere to go. Design work IS
    the milestone's work, and it is the first thing a milestone does."""
    with tree(milestone_status='planning') as root:
        write(root / 'pm/roadmap/milestones/0.1.md',
              {'id': '"0.1"', 'name': 'Demo', 'status': 'planning'})
        code, out = record(root, '--grain', '0.1/alpha')
        assert code == 0, out
        assert [r['grain'] for r in ledger_rows(root)] == ['0.1/alpha']


def test_two_milestones_in_progress_file_against_the_one_that_owns_the_grain():
    """The refusal that said "which one owns this row is the one thing this
    verb cannot know". The row knows: it names a grain, and the grain's
    document sits under exactly one milestone."""
    with tree() as root:
        other = two_milestones(root, other_status='building')
        assert record(root, '--grain', other)[0] == 0
        assert record(root, '--grain', '0.1/alpha')[0] == 0
        assert [r['grain'] for r in ledger_rows(root, SECOND_LEDGER)] == [other]
        assert [r['grain'] for r in ledger_rows(root)] == ['0.1/alpha']


def test_the_milestone_that_is_building_does_not_collect_another_ones_rows():
    """The inversion of "lands in the building milestone", with the two pulled
    apart: 0.1 is the only milestone in progress and the row still goes to
    0.2, because 0.2 owns the grain. Under the old rule this row landed in
    0.1 — the same file, for the wrong reason."""
    with tree() as root:
        other = two_milestones(root)
        code, out = record(root, '--grain', other, '--event', 'Stop')
        assert code == 0, out
        assert ledger_lines(root) == [], 'the building milestone took the row'
        rows = ledger_rows(root, SECOND_LEDGER)
        assert [(r['kind'], r['grain']) for r in rows] == [('session', other)]


# --- D2's fallback: the orchestrator's path, and the one rule that outranks it -
def transcript(root, *extra):
    return record(root, '--from-transcript', str(SUBAGENT), '--event', 'Stop',
                  *extra)


def second_story(root, status: str = 'building') -> str:
    write(root / 'pm/roadmap/stories/s9.md',
          {'id': '0.1/alpha/s9', 'kind': 'story', 'feature': '0.1/alpha',
           'milestone': '"0.1"', 'name': 'S9', 'status': status, 'owner': ''})
    return '0.1/alpha/s9'


def test_show_reads_the_trees_ledger_too_so_it_cannot_disagree_with_report():
    """Review M1. `ledger show` read the milestone's ledger alone while
    `ledger report` read both, so one root row could be BILLED to a story by
    one verb and invisible to the other.

    The row names no grain and its snapshot names TWO stories, so `report`
    places it on neither (0.9.0 D2) — and `show` must not print it as this
    story's either (0.10.0: `show` attributes as the report does). With one
    story live the snapshot does place it, and both verbs agree again.
    """
    with tree(story_statuses=('building',)) as root:
        second_story(root)  # two live: resolution omits the key
        assert transcript(root)[0] == 0
        assert list(all_ledger_lines(root)) == [ROOT_LEDGER_REL]
        code, out = run_cli(root, 'ledger', 'show', STORY)
        assert code == 0, out
        assert 'session' not in out, out
    assert ledger.row_names({'tree': {'stories_in_progress': [STORY]}}, {STORY})
    assert not ledger.row_names(
        {'tree': {'stories_in_progress': [STORY, '0.1/alpha/s9']}}, {STORY})



# `--grain` given -> use it. Absent and one story live -> use it. Absent and
# zero or several -> OMIT THE KEY, and name the candidates. Never a guess.
def test_one_story_in_progress_resolves_and_routes():
    """The undispatched orchestrator, which is the session type most of a
    milestone's work happens in: no prompt to read a grain out of, and one
    obvious answer in the tree."""
    with tree(story_statuses=('building',)) as root:
        code, out = transcript(root)
        assert code == 0, out
        assert only_row(root)['grain'] == STORY
        # A resolved grain ROUTES as well as names (D1): one rule, whichever
        # way the grain arrived.
        assert list(all_ledger_lines(root)) == [LEDGER_REL], out


def test_no_story_in_progress_omits_the_key_entirely():
    """Asserted on the KEY SET, not with a membership check: a row carrying
    `grain: ""` or `grain: null` has to fail here. A number not given is a key
    the row does not carry, never a zero — and `grain` is no different."""
    with tree(story_statuses=('ready',)) as root:
        code, out = transcript(root)
        assert code == 0, out
        assert 'grain' not in sorted(only_row(root))
        assert list(all_ledger_lines(root)) == [ROOT_LEDGER_REL], out


def test_two_stories_in_progress_omit_the_key_and_name_the_candidates():
    """**The case this story exists for.** Two agents on two stories in one
    milestone is the workflow this package is built for, and it is exactly
    when a lookup has more than one answer. A row filed against the wrong
    story is uncorrectable; a row filed against none is visible in a bucket
    that already exists.

    The candidates go to stderr, which the couriers pass through verbatim, so
    D2's "revisit if ambiguity turns out to be common" is countable rather
    than hopeful."""
    with tree(story_statuses=('building',)) as root:
        other = second_story(root)
        code, out = transcript(root)
        assert code == 0, out
        assert 'grain' not in sorted(only_row(root))
        assert '2 stories are in progress' in out
        assert STORY in out and other in out
        assert 'GDK_LEDGER_GRAIN' in out, 'the fix is not named'


def test_the_flag_wins_over_the_lookup_and_the_lookup_stays_quiet():
    """A caller who said what they meant is never overridden — and the lookup
    must not even RUN, or a dispatch that named its grain still gets a
    complaint about two live stories it was never torn between."""
    with tree(story_statuses=('building',)) as root:
        second_story(root)
        code, out = transcript(root, '--grain', STORY)
        assert code == 0, out
        assert only_row(root)['grain'] == STORY
        assert 'in progress' not in out, out


def test_resolution_never_changes_an_exit_code():
    """The fail-open promise the couriers depend on lives here now: a row that
    could not be attributed is a SUCCESSFUL write with a key absent.

    THREE shapes, and the third is the one that shipped broken: zero live,
    several live, and **two files claiming one id**. `_resolved_grain_file`
    caught `Usage` and the story resolver raised `AmbiguousStory`, a plain
    `Exception` — so a lookup NOBODY ASKED FOR became exit 2 with no row
    written anywhere. The convenience destroyed the row it was meant to label.

    The third shape resolves now rather than raising: a duplicate id keeps the
    first document read (0.4.0/D4 — uniqueness cannot be a runtime lock without
    an allocator, and a git repo has none). So the exit code is what this case
    is about, and the collision itself is graded where a collision belongs —
    `check pm`, by name, which is the assertion at the end.
    """
    with tree(story_statuses=('ready',)) as root:
        second_story(root, 'ready')
        assert transcript(root)[0] == 0
    with tree(story_statuses=('building',)) as root:
        second_story(root)
        assert transcript(root)[0] == 0
    # Two files, ONE id, and only one of them live — so the lookup has exactly
    # one candidate and that candidate will not resolve. The resolver's own
    # refusal, reached from a path the caller never asked to travel.
    with tree(story_statuses=('ready',), config=LEGACY_FLOW) as root:
        for stem, status in (('01-twin', 'building'), ('02-twin', 'ready')):
            write(root / f'pm/roadmap/stories/{stem}.md',
                  {'id': '0.1/alpha/twin', 'kind': 'story',
                   'feature': '0.1/alpha',
                   'milestone': '"0.1"', 'name': 'Twin', 'status': status,
                   'owner': ''})
        code, out = transcript(root)
        assert code == 0, out
        # The row landed, attributed to the id both files claim.
        assert only_row(root)['grain'] == '0.1/alpha/twin'
        # And the collision is a FINDING where findings live — otherwise one
        # of those two files is in the tree and addressable by nothing.
        code, out = run_gate(root)
        assert code == 1, out
        assert "2 documents claim id '0.1/alpha/twin'" in out, out
        assert '01-twin.md' in out and '02-twin.md' in out, out


# --- D2: a dispatch that was TOLD its grain files a row that says so ----------
def test_a_transcript_row_carries_the_grain_it_was_given():
    """The numbers come from the transcript; `--grain` says what they were
    spent ON. The two were exclusive until 0.4.0, which made every automatic
    row unattributed — captured, and saying nothing about the work.

    The `grain` key sits in `ROW_KEYS` position, and the row lands in the
    GRAIN's milestone rather than the tree's, which is the whole point: this is
    what moves a dispatch off the `rows naming no grain` line.
    """
    with tree() as root:
        code, out = record(root, '--from-transcript', str(SUBAGENT),
                           '--event', 'Stop', '--grain', STORY)
        assert code == 0, out
        row = only_row(root)
        assert list(all_ledger_lines(root)) == [LEDGER_REL], out
    assert row['grain'] == STORY
    # Third key, as `ROW_KEYS` declares — a durable line's shape, not just its
    # contents.
    assert list(row)[:4] == ['ts', 'kind', 'grain', 'session_id']
    # And the transcript's own numbers are untouched by the attribution.
    assert row['tool_calls'] == 23 and row['duration_s'] == 80


def test_the_row_carries_the_id_the_grain_declares_not_the_string_typed():
    """Two rows naming one grain must spell it one way, or the report bills
    two lines for one thing. `_ledger_id` is what every other row already
    uses."""
    with tree() as root:
        write(root / 'pm/roadmap/stories/s0.md',
              {'id': STORY, 'feature': '0.1/alpha', 'milestone': '"0.1"',
               'name': 'S0', 'status': 'building', 'owner': ''})
        assert record(root, '--from-transcript', str(SUBAGENT),
                      '--event', 'SubagentStop', '--grain', STORY)[0] == 0
        assert only_row(root)['grain'] == STORY


def test_a_row_naming_no_grain_lands_in_the_trees_own_ledger():
    """D3. A transcript row carries no grain, so it has no milestone to belong
    to — and under the deleted lookup that made it a REFUSAL when nothing was
    in progress, which is how a whole milestone's telemetry went missing. It
    now has a home, created on first write like a milestone's is."""
    with tree(milestone_status='planning') as root:
        assert not (root / ROOT_LEDGER_REL).exists()
        code, out = record(root, '--from-transcript', str(SUBAGENT),
                           '--event', 'SubagentStop')
        assert code == 0, out
        assert ROOT_LEDGER_REL in out, 'the verb did not say where it wrote'
        assert list(all_ledger_lines(root)) == [ROOT_LEDGER_REL]
        assert 'grain' not in only_row(root)


def test_retire_takes_the_milestones_ledger_and_appends_to_the_trees():
    """The `check pm` D6 rule is unchanged by D3: an attributed row still dies
    with its milestone and git is still the archive.

    The tree's own ledger is APPENDED to and never rewritten — every byte that
    was there is still there, in order, and the one new line is the `retire`
    row carrying what the deleted documents held
    (`bg-retire-drops-the-summary-it-accepts`). Retire removing rows that were
    never about this milestone would be the same defect from the other side.
    """
    with tree(milestone_status='done', feature_status='done',
              story_statuses=('done',)) as root:
        put_ledger(root, status_line(TS, STORY, 'building', 'done'))
        assert record(root, *GATE)[0] == 0
        before = (root / ROOT_LEDGER_REL).read_bytes()
        code, out = run_cli(root, 'retire', '0.1', 'the first cut')
        assert code == 0, out
        # The GRAINS go, not the tree — `pm/roadmap/` is the tree itself and a
        # pooled milestone has no directory of its own to remove.
        assert not (root / LEDGER_REL).exists()
        assert inventory.milestones(loaded(root)) == []
        after = (root / ROOT_LEDGER_REL).read_bytes()
        assert after.startswith(before), after
        added = [json.loads(line) for line in
                 after[len(before):].decode('utf-8').splitlines() if line.strip()]
        assert [r['kind'] for r in added] == [ledger.KIND_RETIRE], added
        assert added[0]['grain'] == '0.1' and added[0]['name'] == 'Demo'
        assert added[0]['summary'] == 'the first cut'
        # No version declared, so no `version` key — an absent fact is an
        # absent key, never an empty string.
        assert 'version' not in added[0], added[0]


def test_an_id_no_grain_carries_is_still_refused_and_writes_nothing():
    """Routing by grain must not turn an unknown id into a new place to
    write."""
    with tree() as root:
        refuses(root, '--grain', '0.1/nope', needle='no grain resolves')
        assert all_ledger_lines(root) == {}


def test_a_ledger_that_cannot_be_appended_to_is_reported_not_swallowed():
    """The loud half of the fail-open contract: the courier may discard this,
    but the verb must say it, or a ledger that stopped being written is
    invisible for as long as nobody looks."""
    if os.geteuid() == 0:  # pragma: no cover - root ignores the mode bits
        pytest.skip('running as root: a read-only file is still writable')
    with tree() as root:
        # The ROOT ledger, because that is where a gate row is addressed (D3);
        # locking the milestone's would leave the write path untouched and the
        # case would prove the opposite of what it says.
        put_ledger(root, status_line(TS, STORY, 'ready', 'building'),
                   rel=ROOT_LEDGER_REL)
        path = root / ROOT_LEDGER_REL
        before = path.read_bytes()
        path.chmod(0o444)
        try:
            code, out = record(root, *GATE)
        finally:
            path.chmod(0o644)
        assert code == 2, out
        assert 'could not be appended to' in out
        assert path.read_bytes() == before


# --- the refusal matrix (SDLC § 5) --------------------------------------------
# Every case asserts the file's LINES before and after, not just the exit code:
# a half-written row in an append-only committed file is worse than a missing
# one, because `read_rows` then reports a parse defect on a line nobody wrote.

# One representative per REFUSAL, not per spelling — the make-target grammar
# itself is `gates_extra`'s and is proven there, and the grain grammar is the
# shared resolver's.
GATE_FORM_REFUSALS = [
    # A row naming no gate is unattributable; a name carrying a line breaker
    # would not be one row; a name that is a path is not a make target.
    (('--gate', '', '--verdict', 'PASS', '--duration-ms', '12'),
     'make-target name'),
    (('--gate', 'a\nb', '--verdict', 'PASS', '--duration-ms', '12'),
     'make-target name'),
    # The forged second row: refused as a NAME long before `LINE_BREAKERS`
    # would have had to escape it.
    (('--gate', 'a {"kind":"gate"}', '--verdict', 'PASS',
      '--duration-ms', '12'), 'make-target name'),
    (('--gate', '../../etc/passwd', '--verdict', 'PASS', '--duration-ms', '12'),
     'make-target name'),
    # A flag at the end of argv must not adopt the next token as its value.
    (('--gate', 'check', '--verdict', 'PASS', '--duration-ms', '12', '--census'),
     '--census needs'),
    (('--verdict', 'PASS', '--duration-ms', '12', '--gate'), '--gate needs'),
    # The verdict vocabulary is CLOSED: free text would give one outcome five
    # spellings and nothing could count them.
    (('--gate', 'check', '--verdict', '', '--duration-ms', '12'), '--verdict'),
    (('--gate', 'check', '--verdict', 'pass', '--duration-ms', '12'),
     '--verdict'),
    (('--gate', 'check', '--verdict', 'PASS\n{"kind":"gate"}',
      '--duration-ms', '12'), '--verdict'),
    # The numbers are non-negative decimal integers or they are not measurements.
    (('--gate', 'check', '--verdict', 'PASS', '--duration-ms=-1'),
     'non-negative integer'),
    (('--gate', 'check', '--verdict', 'PASS', '--duration-ms=1.5'),
     'non-negative integer'),
    (GATE + ('--census=1e3',), 'non-negative integer'),
    # A cost row with no cost is a write-only column.
    (('--gate', 'check', '--verdict', 'PASS'), '--duration-ms'),
    (('--gate', 'check', '--duration-ms', '12'), '--verdict'),
    # Two record forms in one call, and a flag from one form on the other:
    # a flag silently dropped is the write-side sin with a shrug on it.
    (GATE + ('--grain', STORY), 'exclusive'),
    (('--grain', STORY, '--verdict', 'PASS'), '--gate'),
    (GATE + ('--tokens-in', '5'), '--tokens-in'),
    (GATE + ('--event', 'Stop'), '--event'),
]


def test_the_gate_form_refuses_and_writes_nothing():
    with tree() as root:
        put_ledger(root, status_line(TS, STORY, 'ready', 'building'))
        for argv, needle in GATE_FORM_REFUSALS:
            refuses(root, *argv, needle=needle)
    # The escape still works for the rows that legitimately carry prose — the
    # gate NAME just never gets there.
    line = ledger.dumps({'k': 'a\u2028b'})
    assert '\u2028' not in line
    assert '\\u2028' in line


RECORD_REFUSALS = [
    (('--from-transcript', str(SUBAGENT), '--event', 'Wombat'),
     'is not a hook event'),
    (('--from-transcript', str(SUBAGENT)), '--event is required'),
    (('--grain', STORY, '--tokens-in=-1'), 'non-negative integer'),
    (('--grain', STORY, '--duration-s=3.5'), 'non-negative integer'),
    # NOT here any more: `--grain` with `--from-transcript` is the courier's
    # own shape since 0.4.0/every-row-names-its-grain. It is a WRITE, proven
    # below.
    # An id that resolves to nothing is refused on the transcript form too —
    # the same bar the hand form applies. A bad grain must never degrade to an
    # omitted key: that is how a typo becomes silent misattribution.
    (('--grain', '0.1/alpha/nope', '--from-transcript', str(SUBAGENT),
      '--event', 'Stop'), 'no grain resolves'),
    (('--agent-type', 'developer'), 'needs --from-transcript'),
    (('--grain', '0.1/alpha/nope'), 'no grain resolves'),
    # The grain grammar, one representative per class: traversal, absolute,
    # glob. The resolver is shared with `pm get`/`pm set`/`ledger show`.
    (('--grain', '0.1/../0.1/alpha/s0'), ''),
    (('--grain', '/etc/hosts'), ''),
    (('--grain', '0.1/alpha/s*'), ''),
    # The hand form's agent type is asked of the roster the case plants — the
    # typo, then one representative per class of the grain grammar above.
    (('--grain', STORY, '--agent-type', 'wombat'), "'wombat' is not an agent"),
    (('--grain', STORY, '--agent-type', '../developer'), 'not an agent type'),
    (('--grain', STORY, '--agent-type', '/developer'), 'not an agent type'),
    (('--grain', STORY, '--agent-type', 'dev*'), 'not an agent type'),
    ((STORY, '--tokens-in', '5'), 'takes flags only'),
    (('--grain', STORY, '--wombat', '5'), 'takes flags only'),
    # A total and a split in one row is a row that can disagree with itself,
    # so both spellings of "I have both" are refused before anything lands —
    # the hand split, and a transcript that MEASURES one.
    (('--grain', STORY, '--tokens-total', '5', '--tokens-in', '1'),
     'exclusive'),
    (('--grain', STORY, '--tokens-total', '5', '--tokens-out', '1'),
     'exclusive'),
    (('--grain', STORY, '--tokens-total', '5', '--from-transcript',
      str(SUBAGENT), '--event', 'Stop'), 'exclusive'),
    (('--grain', STORY, '--tokens-total=-1'), 'non-negative integer'),
    (('--grain', STORY, '--outcome', 'finished'), 'an outcome is landed'),
    (('--grain', STORY, '--outcome', 'stopped: '), 'not a reason'),
    (GATE + ('--outcome', 'landed'), 'the gate form takes'),
]


def test_the_record_flags_refuse_and_write_nothing():
    with tree() as root:
        put_ledger(root, status_line(TS, STORY, 'ready', 'building'))
        outside = root.parent / 'outside.md'
        outside.write_text('---\nid: outside\n---\n', encoding='utf-8')
        agents = root / roster.AGENTS_DIR
        agents.mkdir(parents=True)
        (agents / 'scout.md').write_text('# no frontmatter\n', encoding='utf-8')
        refuses(root, '--from-transcript', str(root / 'nope.jsonl'),
                '--event', 'Stop', needle='is not a file')
        for argv, needle in RECORD_REFUSALS:
            refuses(root, *argv, needle=needle)
        assert outside.read_text(encoding='utf-8') == '---\nid: outside\n---\n'
        # On the roster, by FILENAME when there is no `name:`; and a
        # transcript's type is what the harness spawned, never a typo, so it
        # is carried whatever the roster says rather than lose the spend.
        for argv in (('--grain', STORY, '--agent-type', 'scout'),
                     ('--from-transcript', str(SUBAGENT), '--event',
                      'SubagentStop', '--agent-type', 'general-purpose')):
            assert record(root, *argv)[0] == 0, argv
        assert sorted(row['agent_type']
                      for lines in all_ledger_lines(root).values()
                      for row in map(json.loads, lines)
                      if 'agent_type' in row) == ['general-purpose', 'scout']


def test_a_transcript_this_module_cannot_read_refuses_loudly():
    """The transcript is an interface we READ and do not own (D4), so a shape
    we cannot parse is REPORTED and never skipped: the alternative is a row of
    zeros that reads exactly like a cheap dispatch, and a ledger cannot tell
    the two apart afterwards (hard rule 4)."""
    with tree() as root:
        torn = root / 'torn.jsonl'
        lines = SUBAGENT.read_text(encoding='utf-8').splitlines()[:5]
        lines.insert(3, '{"type": "assistant"')
        torn.write_text('\n'.join(lines) + '\n', encoding='utf-8')

        empty = root / 'empty.jsonl'
        empty.write_text(json.dumps(
            {'type': 'user', 'timestamp': TS,
             'message': {'role': 'user', 'content': 'x'}}) + '\n',
            encoding='utf-8')

        counted = root / 'counted.jsonl'
        counted.write_text(json.dumps(
            {'type': 'assistant', 'timestamp': TS,
             'message': {'model': 'm', 'usage': {'input_tokens': '12'}}}) + '\n',
            encoding='utf-8')

        stampless = root / 'stampless.jsonl'
        stampless.write_text(json.dumps(
            {'type': 'assistant', 'timestamp': 'yesterday',
             'message': {'model': 'm', 'usage': {'input_tokens': 1}}}) + '\n',
            encoding='utf-8')

        for path, needle in (
                (torn, 'line 4'),
                (empty, 'no assistant record — nothing to sum'),
                (counted, 'is not a number'),
                (stampless, 'not ISO-8601')):
            refuses(root, '--from-transcript', str(path), '--event', 'Stop',
                    needle=needle)


def test_an_unknown_ledger_subcommand_and_an_unresolvable_show_id():
    with tree() as root:
        code, out = run_cli(root, 'ledger', 'wombat')
        assert code == 2, out
        assert 'unknown ledger subcommand' in out
        for gid in ('0.1/alpha/nope', '0.1/../outside', '/etc/hosts'):
            assert run_cli(root, 'ledger', 'show', gid)[0] == 2


# --- `pm ledger show` — a subtraction over raw rows, and nothing more ---------

TIMELINE = ('2026-09-03T10:00:00Z', '2026-09-03T10:13:32Z',
            '2026-09-03T10:20:00Z')


def timeline(root, last_to: str = 'done') -> None:
    one, two, three = TIMELINE
    put_ledger(root,
               status_line(one, STORY, 'ready', 'building'),
               status_line(two, STORY, 'building', 'reviewing'),
               status_line(three, STORY, 'reviewing', last_to))


def test_the_human_form_is_one_line_per_row_with_the_gap_after_the_first():
    with tree() as root:
        timeline(root)
        code, out = run_cli(root, 'ledger', 'show', STORY)
    assert code == 0, out
    assert out.strip().splitlines() == [
        '2026-09-03T10:00:00Z  status         ready -> building',
        '2026-09-03T10:13:32Z  status         building -> reviewing  +812s',
        '2026-09-03T10:20:00Z  status         reviewing -> done  +388s',
        # `done` is terminal for a story, so the run ends with the total.
        'first row → terminal row: 1200s',
    ]


def test_a_disposition_prints_its_state_answer_and_every_skipped_check():
    """Rule 11's read side, and a ship criterion of 0.5.0. The row was on disk
    from the first arrival this package recorded, and this verb printed its
    `ts` and `kind` and stopped — so `state`, `answer` and every `skipped`
    entry were held by the tree and invisible at the surface someone stands in
    to ask what a grain cost. Bites: a column dropping back off the line, which
    is indistinguishable from the tree never having recorded it.
    """
    one, two = TIMELINE[0], TIMELINE[1]
    with tree() as root:
        put_ledger(
            root,
            status_line(one, STORY, 'ready', 'building'),
            ledger.dumps(ledger.disposition_row(
                STORY, 'building', arrive.Said('--by', 'agent developer'),
                ts=one)),
            status_line(two, STORY, 'building', 'done'),
            ledger.dumps(ledger.disposition_row(
                STORY, 'done', arrive.NOTHING,
                [('review-recorded', 'read inline'),
                 ('story-verified', 'no code changed')], ts=two)))
        code, out = run_cli(root, 'ledger', 'show', STORY)
    assert code == 0, out
    assert out.strip().splitlines()[:4] == [
        f'{one}  status         ready -> building',
        f'{one}  disposition    building  --by agent developer',
        f'{two}  status         building -> done  +812s',
        f'{two}  disposition    done  none  skipped: review-recorded — '
        f'"read inline", story-verified — "no code changed"',
    ], out


def test_the_three_taps_print_their_payload_and_not_a_bare_kind():
    """D5's finding for `disposition`, carried to the kinds this milestone
    added. A refused run and a passed one rendered as the SAME eight characters
    here, so "there is no rung.exit_failed, the absence is the signal" held on
    the JSONL and failed at the verb the ship criterion names. Bites: a cell
    dropping off, which is indistinguishable from a row that never carried it.
    """
    from agentic_sdlc.repo.conveyor import driver
    from agentic_sdlc.repo.pm import ready_for
    nxt = arrive.Next('feature', 'close feature', '0.1/alpha',
                      ('stories-done', 'findings-landed'))
    minted = [
        ready_for._enter_row('story', STORY,
                             [ready_for.Blocker('evidence-written', 'why')]),
        driver.verdict_row('story', STORY, 'tree-clean',
                           driver.Answer.no('2 file(s) dirty'),
                           'git status --porcelain'),
        ledger.leave_row(STORY, 'done', nxt, (), arrive.NOTHING),
    ]
    with tree() as root:
        put_ledger(root, *[ledger.dumps(dict(row, ts=TIMELINE[0]))
                           for row in minted])
        code, out = run_cli(root, 'ledger', 'show', STORY)
    assert code == 0, out
    printed = out.strip().splitlines()
    assert len(printed) == len(minted), out
    assert printed[0].endswith(
        f'{ledger.NOT_READY}  blocked: evidence-written'), printed[0]
    assert printed[1].endswith(
        'tree-clean  error — 2 file(s) dirty  '
        '(ran: git status --porcelain)'), printed[1]
    assert printed[2].endswith(
        'done  none  next: feature (stories-done, findings-landed)'), printed[2]
    # The kind column fits the widest kind, or the cells above start ragged.
    for line, row in zip(printed, minted):
        assert line.startswith(f'{TIMELINE[0]}  {row["kind"]:<13}  '), line


def test_no_total_line_while_the_grain_is_still_in_flight():
    """A running clock is not a duration, and a `0` here would read as
    "finished in no time at all" — a measurement nobody made."""
    with tree() as root:
        bug_doc(root)
        put_ledger(root, status_line(TS, BUG, 'open', 'fixed'))
        code, out = run_cli(root, 'ledger', 'show', BUG)
    assert code == 0, out
    assert 'terminal row' not in out


def test_done_ends_a_story_and_blocked_does_not():
    """Finished is the `done` CATEGORY, never the last word in a list.

    `blocked` is a word this project never declared, so it is in no category
    and ends nothing; reading a list's last entry would have printed a total
    for a story that STALLED and none for one that finished. The category is
    the one every drift rule asks of `vocabulary`, so `show` agrees with the gate.
    """
    with tree() as root:
        timeline(root, last_to='done')
        done_out = run_cli(root, 'ledger', 'show', STORY)[1]
        timeline(root, last_to='blocked')
        blocked_out = run_cli(root, 'ledger', 'show', STORY)[1]
    assert 'first row → terminal row: 1200s' in done_out
    assert 'terminal row' not in blocked_out


def test_only_status_rows_bound_the_total():
    """R3: a `decision` row and a `dispatch` row both NAME a grain; neither
    MOVES one. Measuring from the first row that merely mentioned the grain
    billed a decision logged before work started — on this repo's own tree
    `0.23.0/ledger` totalled 4222s against 1799s of measured status time, a
    number its own state columns contradicted."""
    with tree() as root:
        put_ledger(root,
                   ledger.dumps(ledger.decision_row(
                       STORY, 'D1', 'why', ts='2026-09-03T09:00:00Z')),
                   status_line('2026-09-03T10:00:00Z', STORY, 'ready',
                               'building'),
                   status_line('2026-09-03T10:15:00Z', STORY, 'building',
                               'done'))
        before = run_cli(root, 'ledger', 'show', STORY)[1]
        # And a dispatch AFTER the terminal row no more extends the span than
        # the decision was able to start it early.
        assert record(root, '--grain', STORY, '--duration-ms', '30')[0] == 0
        after = run_cli(root, 'ledger', 'show', STORY)[1]
    assert 'first row → terminal row: 900s' in before
    assert 'first row → terminal row: 900s' in after
    assert '4500s' not in before


def test_the_finished_rule_lives_in_ledger_py_and_is_the_done_category():
    """One home, because a report that disagreed with `show` about where a
    grain finished would produce two durations for one grain — and it is the
    kind's `done` CATEGORY: `obe` ends a story, a bug's own `closed` ends a
    bug, and a word the project never declared ends nothing."""
    with tree() as root:
        cfg = loaded(root)
    assert ledger.ends_grain(cfg, 'story', 'done')
    assert ledger.ends_grain(cfg, 'story', 'obe')
    assert ledger.ends_grain(cfg, 'feature', 'done')
    assert ledger.ends_grain(cfg, 'milestone', 'done')
    assert ledger.ends_grain(cfg, vocabulary.GRAIN_BUG, 'closed')
    assert not ledger.ends_grain(cfg, vocabulary.GRAIN_BUG, 'fixed')
    assert not ledger.ends_grain(cfg, 'story', 'reviewing')
    assert not ledger.ends_grain(cfg, 'story', 'shut')
    assert not ledger.ends_grain(cfg, 'story', {'to': 'done'})


def test_json_prints_the_raw_lines_and_nothing_else():
    """The bytes on disk, not a re-serialisation — a row written by a future
    version of this package, with keys this one has never heard of, must come
    back out unchanged."""
    with tree() as root:
        timeline(root)
        code, out = run_cli(root, 'ledger', 'show', STORY, '--json')
        expected = ledger_lines(root)
    assert code == 0, out
    assert out.strip().splitlines() == expected


def test_no_rows_is_exit_zero_because_it_is_a_fact():
    with tree() as root:
        bug_doc(root)
        put_ledger(root, status_line(TS, BUG, 'open', 'fixed'))
        code, out = run_cli(root, 'ledger', 'show', STORY)
    assert code == 0, out
    assert f'no rows for {STORY}' in out


def test_a_malformed_ledger_line_refuses_and_names_the_line():
    """A reader that SKIPPED it would print a timeline with a hole in it and
    no way to know — the read-side sin."""
    with tree() as root:
        put_ledger(root,
                   status_line(TS, STORY, 'ready', 'building'),
                   '{not json',
                   status_line('2026-09-03T10:01:00Z', STORY, 'building',
                               'reviewing'))
        code, out = run_cli(root, 'ledger', 'show', STORY)
    assert code == 2, out
    assert 'line 2' in out


# --- rows this version never wrote --------------------------------------------
# `ledger.jsonl` is `merge=union`, so the reader meets shapes it never emitted:
# another milestone branch's rows, a newer package's rows and a hand edit all
# land here without passing through `usage_row`, and `read_rows` deliberately
# accepts any JSON OBJECT as a row. `{} in names` raises `TypeError`; a
# traceback would take out the whole timeline over one line.

def test_a_row_this_version_never_wrote_does_not_crash_the_timeline():
    with tree() as root:
        put_ledger(
            root,
            status_line(TS, STORY, 'ready', 'building'),
            '{"ts":"2026-09-03T10:01:00Z","kind":"dispatch",'
            '"tree":{"stories_wip":[{"id":"' + STORY + '"}]}}',
            '{"ts":"2026-09-03T10:02:00Z","kind":"dispatch",'
            '"tree":{"stories_wip":[null,3,["' + STORY + '"]]}}',
            '{"ts":"2026-09-03T10:03:00Z","kind":"status",'
            '"grain":{"id":"' + STORY + '"},"from":"a","to":"b"}')
        code, out = run_cli(root, 'ledger', 'show', STORY)
    assert code == 0, out
    assert 'ready -> building' in out


def test_such_a_row_does_not_become_this_grains_row():
    """Not crashing is half of it: the match must still be False. A dict whose
    `id` happens to spell the grain is not the grain being NAMED — reading it
    as one would put another row's cost on this timeline."""
    assert not ledger.row_names(
        {'grain': {'id': STORY}, 'tree': {'stories_wip': [{'id': STORY}]}},
        {STORY})
    assert ledger.row_names({'tree': {'stories_wip': [STORY]}}, {STORY})


# --- 0.4.0/D3+D7: a gate row names no grain, so it lands in the TREE's ledger --
# INVERTED from 0.3.0's pair, which proved a gate row followed the current
# RELEASE (`order` plus `version_at`). That was a better answer than the status
# lookup it replaced and still a second routing mechanism reading tree state; a
# binding is a FIELD, and `gate_row` has none. So the plan is not consulted
# either, and a tree with no plan at all records — which the release rule could
# not do.
@pytest.mark.parametrize('kwargs,plan', [
    # THE BUG, in its original shape: two milestones planned, none flipped to
    # `in_progress`, and every gate run of this milestone's design printed
    # "no milestone in pm/roadmap is in progress" and wrote nothing.
    (dict(milestone_status='planning'), False),
    # A tree at rest with a plan: the row does not go to the release's
    # milestone, because it is not about a milestone.
    (dict(milestone_status='planning'), True),
    # Two in progress — "which one owns this row" was the one thing the verb
    # said it could not know. Nothing asks.
    (dict(milestone_status='building'), False),
])
def test_a_gate_row_asks_the_tree_nothing_and_lands_at_the_root(kwargs, plan):
    with tree(**kwargs) as root:
        write(root / 'pm/roadmap/milestones/0.2.md',
              {'id': '"0.2"', 'name': 'Next', 'status': kwargs['milestone_status'],
               'version': '"0.2.0"'})
        if plan:
            frontmatter.set_field(root / 'pm/roadmap/milestones/0.1.md',
                             'version', '"0.1.0"')
            (root / 'pm/roadmap/releases.md').write_text(
                '---\norder:\n  - "0.1.0"\n  - "0.2.0"\n---\n\nThe plan.\n',
                encoding='utf-8')
        code, out = record(root, *GATE)
        assert code == 0, out
        assert only_row(root)['kind'] == 'gate'
        assert list(all_ledger_lines(root)) == [ROOT_LEDGER_REL], out


# --- every row names its branch (ft-a-milestone-reports-only-its-own-rows) ----
@pytest.mark.parametrize('head,worktree,expected', [
    ('ref: refs/heads/milestone/0.1-x\n', False, 'milestone/0.1-x'),
    # A worktree's `.git` is a FILE naming its own gitdir, with its own HEAD.
    ('ref: refs/heads/feat/w\n', True, 'feat/w'),
    # Detached: there is no branch, so there is no key — never the sha.
    ('0123456789abcdef0123456789abcdef01234567\n', False, None),
])
def test_every_appended_row_names_the_checkouts_branch(tmp_path, head,
                                                      worktree, expected):
    gitdir = tmp_path / ('real-gitdir' if worktree else 'repo/.git')
    gitdir.mkdir(parents=True)
    (gitdir / 'HEAD').write_text(head, encoding='utf-8')
    if worktree:
        (tmp_path / 'repo').mkdir()
        (tmp_path / 'repo/.git').write_text(f'gitdir: {gitdir}\n',
                                            encoding='utf-8')
    path = tmp_path / 'repo/pm/roadmap/ledgers/0.1.jsonl'
    ledger.append_to(path, ledger.gate_row('check', 'PASS', 1, ts=TS))
    row = json.loads(path.read_text(encoding='utf-8'))
    assert row.get('branch') == expected, row


# --- the dispatch's own stamp line (ft-a-concurrent-dispatch-attributes-itself)
def stamped_transcript(root, user_content, name='stamped.jsonl') -> str:
    """SUBAGENT's records behind one prompt record carrying `user_content`."""
    path = root / name
    prompt = {'type': 'user', 'timestamp': TS,
              'message': {'role': 'user', 'content': user_content}}
    path.write_text(json.dumps(prompt) + '\n'
                    + SUBAGENT.read_text(encoding='utf-8'), encoding='utf-8')
    return str(path)


@pytest.mark.parametrize('content,extra,grain,issue', [
    # The prompt names it: copied, beating the one-story guess.
    ('brief\nGDK-STAMP grain=0.1/alpha/s9 issue=42 issue=PROJ-7\n', (),
     '0.1/alpha/s9', ['42', 'PROJ-7']),
    # A caller's --grain still wins, and a stamp for another grain lends it
    # no issue.
    ('GDK-STAMP grain=0.1/alpha/s9 issue=42', ('--grain', STORY), STORY, None),
    # Only the prompt's own text is read: a tool's output is not a stamp, so
    # the row falls to today's one-story rule.
    ([{'type': 'tool_result', 'content': 'GDK-STAMP grain=0.1/alpha/s9'}],
     (), STORY, None),
    # A stamp naming nothing resolvable is unattributed, NOT re-guessed.
    ('GDK-STAMP grain=0.1/alpha/gone', (), None, None),
])
def test_a_transcript_stamp_line_is_copied_never_guessed(content, extra,
                                                          grain, issue):
    with tree(story_statuses=('building',)) as root:
        second_story(root, 'ready')  # the guess would say s0; stamps say s9
        code, out = record(root, '--from-transcript',
                           stamped_transcript(root, content),
                           '--event', 'SubagentStop', *extra)
        assert code == 0, out
        row = only_row(root)
    assert (row.get('grain'), row.get('issue')) == (grain, issue), row


# --- `pm ledger stamp` (ft-work-is-stamped-with-its-issue-and-agent) ----------
def stamp(root, *argv) -> tuple[int, str]:
    return run_cli(root, 'ledger', 'stamp', *argv)


def with_roster(root) -> None:
    agents = root / roster.AGENTS_DIR
    agents.mkdir(parents=True)
    (agents / 'scout.md').write_text('# no frontmatter\n', encoding='utf-8')


def test_a_stamped_unit_shows_as_one_line_with_every_column():
    """The ship criterion: start, stop, duration, issue, agent, tokens and
    outcome on ONE line, so `show | grep 42` finds the unit."""
    with tree() as root:
        with_roster(root)
        put_ledger(root, ledger.dumps(ledger.stamp_row(
            STORY, 'start', ['42'], 'developer', ts='2026-09-03T10:00:00Z')))
        code, out = stamp(root, 'stop', STORY, '--tokens', '1200',
                          '--outcome', 'landed')
        assert code == 0, out
        rows = ledger_rows(root)
        assert [r['edge'] for r in rows] == ['start', 'stop']
        assert rows[1]['tokens'] == 1200 and rows[1]['issue'] == []
        code, out = run_cli(root, 'ledger', 'show', STORY)
    assert code == 0, out
    lines = [ln for ln in out.splitlines() if 'stamp' in ln]
    assert len(lines) == 1, out
    cells = lines[0].split()
    assert cells[:2] == ['2026-09-03T10:00:00Z', 'stamp'], lines
    assert cells[-4:] == ['42', 'developer', '1200', 'landed'], lines


def test_the_stamp_verb_refuses_and_writes_nothing():
    """SDLC §5. Pairing is a precondition (exit 1); a bad input is usage
    (exit 2). Every refusal leaves every ledger's lines as they were."""
    with tree() as root:
        with_roster(root)
        for argv, code_, needle in (
                (('stop', STORY), 1, 'no open start'),
                (('start', STORY, '--agent', 'wombat'), 2, 'scout'),
                (('start', STORY, '--tokens', '5'), 2, 'belongs to `stop`'),
                (('stop', STORY, '--outcome', 'done'), 2, 'an outcome is'),
                (('start', STORY, '--issue', '#41'), 2, 'an issue id is'),
                (('start', '0.1/alpha/nope'), 2, 'no grain resolves'),
                (('begin', STORY), 2, 'start|stop'),
                (('start',), 2, 'start|stop')):
            before = all_ledger_lines(root)
            code, out = stamp(root, *argv)
            assert (code, all_ledger_lines(root)) == (code_, before), argv
            assert needle in out, (argv, out)
        assert stamp(root, 'start', STORY, '--issue', '42', '--issue', '43',
                     '--agent', 'scout')[0] == 0
        before = all_ledger_lines(root)
        code, out = stamp(root, 'start', STORY)
        assert (code, all_ledger_lines(root)) == (1, before), out
        assert 'already has an open start' in out
        assert ledger_rows(root)[0]['issue'] == ['42', '43']


def test_an_issue_id_is_the_gate_target_grammar_reused():
    """SDLC §5: the grammar's matrix lives with `[gates] extra`; this proves
    the reuse, value for value."""
    from agentic_sdlc.repo import gates_extra
    for value in ('42', 'PROJ-7', 'a.b+c', '#41', '../x', 'a b', '', 'x=y',
                  '-1', 'a/b', 'é', 'x' * 65, 'ok\n'):
        assert (ledger.issue_defect(value) == '') == bool(
            len(value) <= gates_extra.MAX_LENGTH
            and gates_extra.TARGET.fullmatch(value)), value
