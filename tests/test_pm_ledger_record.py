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
from support.pm import ledger_lines, ledger_rows, loaded, run_cli, tree, write

from agentic_sdlc.repo.pm import ledger

# THESE LEDGERS WERE WRITTEN UNDER THE 0.2.0 ALL-SEVEN SEED, where a story and
# a feature walked `reviewing`, `accepted` and `packaging` too. The seed now
# gives each kind the states its belt writes (a story: `building`, `done`), and
# what these cases prove is CATEGORY arithmetic — a stint in `reviewing` is one
# `in_progress` number whatever the word — so the tree keeps the declaration
# the rows were written under rather than rewriting every row to a word that
# proves nothing different. `support.pm.tree` is the builder; this only fixes
# its `config`.
from support.pm import declaring as _declaring, tree as _seed_tree  # noqa: E402
from agentic_sdlc.repo.pm import model as _model  # noqa: E402

LEGACY_FLOW = _declaring(feature=_model.DEFAULT_FLOWS['milestone'],
                         story=_model.DEFAULT_FLOWS['milestone'])


def tree(**kwargs):
    """`support.pm.tree` under the all-seven flow these ledgers assume."""
    kwargs.setdefault('config', LEGACY_FLOW)
    return _seed_tree(**kwargs)

FIXTURES = Path(__file__).parent / 'fixtures' / 'transcripts'
SUBAGENT = FIXTURES / 'subagent-dispatch.jsonl'
MAIN_SESSION = FIXTURES / 'main-session.jsonl'

STORY = '0.1/alpha/s0'
BUG = '0.1/bugs/b0'
LEDGER_REL = 'pm/roadmap/0.1-demo/ledger.jsonl'

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


def only_row(root) -> dict:
    rows = ledger_rows(root)
    assert len(rows) == 1, f'expected one row, got {rows}'
    return rows[0]


def stamped(row: dict) -> dict:
    """The row minus `ts`, having asserted `ts` is a fresh full-UTC stamp."""
    when = datetime.strptime(row['ts'], ledger.TS_FORMAT).replace(
        tzinfo=timezone.utc)
    assert abs(when - datetime.now(timezone.utc)) < timedelta(minutes=5), row
    return {k: v for k, v in row.items() if k != 'ts'}


def put_ledger(root, *lines: str) -> None:
    path = root / LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(line + '\n' for line in lines), encoding='utf-8')


def status_line(ts: str, grain: str, frm: str, to: str) -> str:
    return ledger.dumps(ledger.status_row(grain, frm, to, ts=ts))


def bug_doc(root, status: str = 'open') -> None:
    write(root / 'pm/roadmap/0.1-demo/bugs/b0.md',
          {'id': BUG, 'milestone': '"0.1"', 'name': 'B0', 'status': status})


def assistant(model: str, ts: str = '2026-09-03T10:00:00Z') -> dict:
    return {'type': 'assistant', 'timestamp': ts,
            'message': {'model': model,
                        'usage': {'input_tokens': 1, 'output_tokens': 2}}}


def refuses(root, *argv, needle: str = '') -> str:
    """Exit 2, the message names why, and the file's LINES are unchanged."""
    before = ledger_lines(root)
    code, out = record(root, *argv)
    assert code == 2, (argv, out)
    assert ledger_lines(root) == before, f'a refusal wrote a row: {argv}'
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
        lines = ledger_lines(root)
        row = only_row(root)
    assert stamped(row) == {
        'kind': 'dispatch',
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
        'ts', 'kind', 'session_id', 'agent_id', 'agent_type', 'model',
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
        beta = root / 'pm/roadmap/0.1-demo/features/beta'
        write(beta / 'feature.md',
              {'id': '0.1/beta', 'milestone': '"0.1"', 'name': 'Beta',
               'status': 'reviewing', 'reviewed': ''})
        write(beta / 'stories/b0.md',
              {'id': '0.1/beta/b0', 'feature': '0.1/beta', 'milestone': '"0.1"',
               'name': 'B0', 'status': 'reviewing'})
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

# 0.3.0: the ledger binds to the CURRENT RELEASE, not to a status flag. "No
# milestone is in progress" stopped being a reason to refuse a cost row — gate
# cost is a fact about a RUN, and the run happened whether or not anybody had
# flipped a status. The one honest reason left is that the tree has no plan.
# 0.3.0, review X1: having nowhere to file a gate row is a TRUE and
# unremarkable fact — a fresh adoption has no plan and no milestone in progress
# — and reporting it as a REFUSAL made every gate of every run print `the
# recorder exited 1`, which reads as a broken install. It is INFORMATION now:
# one line, exit 0, and still no row, which is the half that must not change.
@pytest.mark.parametrize('kwargs,remove_pm,second_milestone,code,needle', [
    (dict(), True, False, 0, 'no PM tree'),
    (dict(milestone_status='planning'), False, False, 0, 'declares no `order`'),
    (dict(), False, True, 0, 'declares no `order`'),
])
def test_the_verb_names_what_it_cannot_answer_and_writes_nothing(
        kwargs, remove_pm, second_milestone, code, needle):
    with tree(**kwargs) as root:
        if remove_pm:
            shutil.rmtree(root / 'pm')
        if second_milestone:
            write(root / 'pm/roadmap/0.2-next/milestone.md',
                  {'id': '"0.2"', 'name': 'Next', 'status': 'building'})
        got, out = record(root, *GATE)
        assert (got, needle in out) == (code, True), out
        assert list(root.rglob('ledger.jsonl')) == []


def test_a_ledger_that_cannot_be_appended_to_is_reported_not_swallowed():
    """The loud half of the fail-open contract: the courier may discard this,
    but the verb must say it, or a ledger that stopped being written is
    invisible for as long as nobody looks."""
    if os.geteuid() == 0:  # pragma: no cover - root ignores the mode bits
        pytest.skip('running as root: a read-only file is still writable')
    with tree() as root:
        put_ledger(root, status_line(TS, STORY, 'ready', 'building'))
        path = root / LEDGER_REL
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
    (('--grain', STORY, '--from-transcript', str(SUBAGENT), '--event', 'Stop'),
     'are exclusive'),
    (('--agent-type', 'developer'), 'needs --from-transcript'),
    (('--grain', '0.1/alpha/nope'), 'no grain resolves'),
    # The grain grammar, one representative per class: traversal, absolute,
    # glob. The resolver is shared with `pm get`/`pm set`/`ledger show`.
    (('--grain', '0.1/../0.1/alpha/s0'), ''),
    (('--grain', '/etc/hosts'), ''),
    (('--grain', '0.1/alpha/s*'), ''),
    ((STORY, '--tokens-in', '5'), 'takes flags only'),
    (('--grain', STORY, '--wombat', '5'), 'takes flags only'),
]


def test_the_record_flags_refuse_and_write_nothing():
    with tree() as root:
        put_ledger(root, status_line(TS, STORY, 'ready', 'building'))
        outside = root.parent / 'outside.md'
        outside.write_text('---\nid: outside\n---\n', encoding='utf-8')
        refuses(root, '--from-transcript', str(root / 'nope.jsonl'),
                '--event', 'Stop', needle='is not a file')
        for argv, needle in RECORD_REFUSALS:
            refuses(root, *argv, needle=needle)
        assert outside.read_text(encoding='utf-8') == '---\nid: outside\n---\n'


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
        '2026-09-03T10:00:00Z  status    ready -> building',
        '2026-09-03T10:13:32Z  status    building -> reviewing  +812s',
        '2026-09-03T10:20:00Z  status    reviewing -> done  +388s',
        # `done` is terminal for a story, so the run ends with the total.
        'first row → terminal row: 1200s',
    ]


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
    the one every drift rule in model.py asks, so `show` agrees with the gate.
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
    assert ledger.ends_grain(cfg, ledger.GRAIN_BUG, 'closed')
    assert not ledger.ends_grain(cfg, ledger.GRAIN_BUG, 'fixed')
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


# --- 0.3.0: the release is what the ledger binds to ---------------------------
def test_a_tree_at_rest_with_a_plan_files_the_row(tmp_path):
    """THE BUG. Every gate run during this milestone's design printed

        [pm] REFUSED — no milestone in pm/roadmap is in progress, so there is
        no ledger this gate row belongs to; no row was written

    over a tree that was planning two milestones with none flipped to
    `in_progress`. The refusal was on the wrong axis: gate cost is a fact about
    a RUN. `order` plus `version_at` answer with exactly one by construction,
    and read no status field to do it.
    """
    with tree(milestone_status='planning') as root:
        _model.set_field(root / 'pm/roadmap/0.1-demo/milestone.md',
                        'version', '"0.1.0"')
        (root / 'pm/roadmap/releases.md').write_text(
            '---\norder:\n  - "0.1.0"\n---\n\nThe plan.\n', encoding='utf-8')
        code, out = record(root, *GATE)
        assert code == 0, out
        assert only_row(root)['kind'] == 'gate'


def test_several_milestones_in_progress_is_no_longer_a_question(tmp_path):
    """"Which one owns this row" was the one thing the verb could not know. A
    position in `order` is one place, so it is not asked."""
    with tree(milestone_status='building') as root:
        write(root / 'pm/roadmap/0.2-next/milestone.md',
              {'id': '"0.2"', 'name': 'Next', 'status': 'building',
               'version': '"0.2.0"'})
        _model.set_field(root / 'pm/roadmap/0.1-demo/milestone.md',
                        'version', '"0.1.0"')
        (root / 'pm/roadmap/releases.md').write_text(
            '---\norder:\n  - "0.1.0"\n  - "0.2.0"\n---\n', encoding='utf-8')
        code, out = record(root, *GATE)
        assert code == 0, out
        # `start`: the first unshipped entry is 0.1.0, so its milestone holds it.
        assert (root / 'pm/roadmap/0.1-demo/ledger.jsonl').is_file(), out
        assert not (root / 'pm/roadmap/0.2-next/ledger.jsonl').exists()
