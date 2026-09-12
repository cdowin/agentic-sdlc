"""test_pm_ledger.py — every status flip and every decision leaves a row.

The contract under test (D6 + D8), and what each case here is FOR. The file is
APPEND-ONLY, COMMITTED and read back by `pm ledger report`, `check budget` and
`verify --plan`, so the cases that earn their place are the ones guarding a
permanent defect:

  * a status verb appends `{ts, kind, grain, from, to}` to
    `pm/roadmap/<ms>/ledger.jsonl` — the grain's OWN milestone directory —
    AFTER its frontmatter write landed;
  * a REFUSED or failed flip appends nothing: a row is a record of a write
    that happened, and a ledger that claims a flip nobody made is rule 4's
    cardinal sin with a timestamp on it;
  * one row is one LINE and round-trips: U+2028 and friends must not split one
    row into two, because the second half is invalid JSON forever after;
  * an ABSENT measurement is an absent KEY, never a `0` — a `0` census reads as
    "this gate walked nothing";
  * `append_row` never joins a line it did not write, and never rewrites a byte
    another branch or a later version of this package put there;
  * `ledger.jsonl` is not a grain doc: `pm validate`, `check pm` and
    `pm status` are byte-identical with and without it;
  * `pm init` ships the `merge=union` attribute that makes two branches' rows
    one file rather than one conflict.

The shared tree/run_cli/run_gate harness is tests/support/pm.py, and the ledger
is read back through `ledger_rows`/`ledger_lines` there — the raw LINES as well
as the parse, because compactness and key order are half the shape.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from support.pm import LEDGER_REL, cfg_for, put_ledger  # noqa: F401
from support.pm import (
    damage,
    declaring,
    ledger_lines,
    ledger_rows,
    run_cli,
    run_gate,
    tree,
    write,
    write_config,
)

from agentic_sdlc.repo.pm import arrive, ledger

# THESE LEDGERS WERE WRITTEN UNDER THE 0.2.0 ALL-SEVEN SEED, where a story and
# a feature walked `reviewing`, `accepted` and `packaging` too. The seed now
# gives each kind the states its belt writes (a story: `building`, `done`), and
# what these cases prove is CATEGORY arithmetic — a stint in `reviewing` is one
# `in_progress` number whatever the word — so the tree keeps the declaration
# the rows were written under rather than rewriting every row to a word that
# proves nothing different. `support.pm.tree` is the builder; this only fixes
# its `config`.
from support.pm import declaring as _declaring, tree as _seed_tree  # noqa: E402
from agentic_sdlc.repo.pm import vocabulary  # noqa: E402

LEGACY_FLOW = _declaring(feature=vocabulary.DEFAULT_FLOWS['milestone'],
                         story=vocabulary.DEFAULT_FLOWS['milestone'])


def tree(**kwargs):
    """`support.pm.tree` under the all-seven flow these ledgers assume."""
    kwargs.setdefault('config', LEGACY_FLOW)
    return _seed_tree(**kwargs)

BUG_ID = '0.1/bugs/b0'
STORY = '0.1/alpha/s0'

# A fixed stamp for the row-shape cases: `gate_row`'s own `ts` is asserted by
# the CLI cases, and pinning it here keeps a key-set assertion from depending
# on the clock.
GATE_TS = '2026-09-05T14:02:11Z'


def status_rows(root) -> list[dict]:
    """The `status` rows alone. Read by KIND, never by count: ONE arrival
    mints the flip and the `disposition` that answers it (0.5.0/D3, folded by
    D6), so a length over the whole file counts two things."""
    return [r for r in ledger_rows(root) if r['kind'] == ledger.KIND_STATUS]


def only_row(root, kind: str = ledger.KIND_STATUS) -> dict:
    rows = [r for r in ledger_rows(root) if r['kind'] == kind]
    assert len(rows) == 1, f'expected one {kind} row, got {ledger_rows(root)}'
    return rows[0]


def bug(root, status: str = 'open') -> None:
    write(root / 'pm/roadmap/bugs/b0.md',
          {'id': BUG_ID, 'milestone': '"0.1"', 'name': 'B0',
           'status': status})


def skills_attribute_line() -> str:
    from agentic_sdlc.repo.pm import skills
    return skills.attribute_line('pm/roadmap')


# --- the row, and the line it is written as -----------------------------------

def test_a_story_flip_writes_one_compact_line_with_the_five_keys():
    """Keys, order, values, compactness and a fresh UTC stamp, in one pass.

    A local-time stamp in a durable log is undetectable later; against `now` in
    UTC it is detectable NOW, anywhere but UTC itself. The stdout assertion is
    here too (hard rule 6): the ledger is a side effect on disk and never a
    line a consumer's hook has to learn to skip.
    """
    with tree(story_statuses=('ready',)) as root:
        # STDOUT ONLY: the breadcrumb 0.4.0 added is on stderr, which is what
        # keeps this assertion the contract it was written to be.
        code, out = run_cli(root, 'story', 'building', STORY, stdout_only=True)
        assert code == 0, out
        assert out == '[pm] story 0.1/alpha/s0: ready -> building\n'
        lines = ledger_lines(root)
    # ONE ARRIVAL, TWO ROWS: the flip, and the disposition that answers the
    # state it reached. The second is D3's, and it is asserted here rather
    # than counted around, because a flip that stopped minting it would
    # otherwise look exactly like this case passing.
    assert len(lines) == 2, lines
    row, answer = (json.loads(ln) for ln in lines)
    assert list(row) == ['ts', 'kind', 'grain', 'from', 'to']
    assert (row['kind'], row['grain'], row['from'], row['to']) == (
        'status', STORY, 'ready', 'building')
    assert list(answer) == ['ts', 'kind', 'grain', 'state', 'answer']
    assert (answer['kind'], answer['grain'], answer['state']) == (
        ledger.KIND_DISPOSITION, STORY, 'building')
    # A report reads these with `wc -l` and `readline`, so one row is one line
    # and there are no spaces after the separators.
    assert lines[0] == json.dumps(row, separators=(',', ':'))
    stamped = datetime.strptime(row['ts'], ledger.TS_FORMAT).replace(
        tzinfo=timezone.utc)
    assert len(row['ts']) == len('2026-09-03T21:40:12Z')
    assert abs(stamped - datetime.now(timezone.utc)) < timedelta(minutes=5)


def test_rows_land_in_order_and_earlier_bytes_are_never_rewritten():
    with tree() as root:
        assert run_cli(root, 'story', 'building', STORY)[0] == 0
        first = ledger_lines(root)[0]
        assert run_cli(root, 'story', 'reviewing', STORY)[0] == 0
        assert run_cli(root, 'story', 'done', STORY)[0] == 0
        lines = ledger_lines(root)
        moves = status_rows(root)
    assert len(lines) == 6, lines
    assert lines[0] == first, 'an earlier row was rewritten'
    assert [r['to'] for r in moves] == ['building', 'reviewing', 'done']
    assert [r['from'] for r in moves] == ['ready', 'building', 'reviewing']


# One case per VERB rather than per verb-and-state: each of these is a distinct
# route in cli.py, and a route that stopped appending loses rows silently.
STATUS_VERBS = [
    (dict(story_statuses=('ready',)), False,
     ('story', 'reviewing', STORY), (STORY, 'ready', 'reviewing')),
    (dict(), True, ('bug', 'fixed', BUG_ID), (BUG_ID, 'open', 'fixed')),
    (dict(feature_status='ready'), False,
     ('feature', 'building', '0.1/alpha'), ('0.1/alpha', 'ready', 'building')),
    (dict(feature_status='reviewing'), False,
     ('feature', 'done', '0.1/alpha'), ('0.1/alpha', 'reviewing', 'done')),
    (dict(milestone_status='ready'), False,
     ('milestone', 'building', '0.1'), ('0.1', 'ready', 'building')),
]


@pytest.mark.parametrize('kwargs,needs_bug,argv,expected', STATUS_VERBS)
def test_every_status_verb_writes_the_grains_row(kwargs, needs_bug, argv,
                                                 expected):
    with tree(**kwargs) as root:
        if needs_bug:
            bug(root, 'open')
        code, out = run_cli(root, *argv)
        assert code == 0, out
        row = only_row(root)
    assert (row['kind'], row['grain'], row['from'], row['to']) == (
        'status',) + expected


def test_the_row_lands_in_the_grains_OWN_milestone_directory():
    """A story two milestones deep in the tree stamps ITS milestone, not the
    first one the walker finds."""
    with tree() as root:
        other = root / 'pm/roadmap/milestones'
        write(other / 'milestone.md',
              {'id': '"0.2"', 'name': 'Next', 'status': 'planning'})
        assert run_cli(root, 'story', 'building', STORY)[0] == 0
        assert len(status_rows(root)) == 1
        assert not (other / ledger.LEDGER_FILE_NAME).exists()


# `feature done` is its own route with its own early exits, so the no-op rule
# (0.5.0/D3) is proven on it as well as on the generic one.
@pytest.mark.parametrize('kwargs,argv', [
    (dict(story_statuses=('building',)), ('story', 'building', STORY)),
    (dict(feature_status='done'), ('feature', 'done', '0.1/alpha')),
])
def test_a_no_op_mints_no_flip_and_never_shadows_an_answer(kwargs, argv):
    """A no-op is not an arrival. It used to append `from == to`, which every
    reader of the clock takes for a second arrival at a state the grain never
    left — so the stint it is still IN got billed as a closed one.

    The disposition half STAYS, because re-running the move is how a fork
    somebody skipped gets answered; what it may not do is answer `none` over
    an answer already recorded, since every reader takes the LAST row per
    (grain, state).
    """
    _kind, state, gid = argv
    with tree(**kwargs) as root:
        # An unanswered state: the bare re-run records `none`, which is what
        # puts the grain on the census until somebody answers.
        assert run_cli(root, *argv)[0] == 0
        assert status_rows(root) == []
        assert only_row(root, ledger.KIND_DISPOSITION)['answer'] == (
            ledger.NO_DISPOSITION)
        put_ledger(root, ledger.dumps(ledger.disposition_row(
            gid, state, arrive.Said('--by', 'me'),
            ts='2026-09-07T00:00:00Z')))
        code, out = run_cli(root, *argv)
        assert code == 0, out
        assert '(no-op)' in out
        assert status_rows(root) == []
        answers = [r['answer'] for r in ledger_rows(root)
                   if r['kind'] == ledger.KIND_DISPOSITION]
    assert answers == ['--by'], (
        'the answer was shadowed by a re-run that recorded nothing new')


# --- a feature close touches one grain, so it writes one row ------------------

def test_a_feature_close_writes_the_feature_row_and_no_story_row():
    """Three grains in the tree, one closed, exactly one row. The `--cascade`
    that used to add a story row per `reviewing` story is gone — the story
    belt closes stories by name — so a story row here would be a write the
    caller never asked for."""
    with tree(feature_status='reviewing',
              story_statuses=('reviewing', 'reviewing', 'ready')) as root:
        code, out = run_cli(root, 'feature', 'done', '0.1/alpha')
        assert code == 0, out
        rows = status_rows(root)
    assert [(r['grain'], r['from'], r['to']) for r in rows] == [
        ('0.1/alpha', 'reviewing', 'done')]


# --- a refused flip appends nothing -------------------------------------------
# The row records a write that LANDED. No write, no row — ever.

def test_a_refused_flip_appends_nothing():
    """Every refusal shape this verb has, against ONE tree: a review record
    naming no file, a status outside the vocabulary, and an id that resolves to
    nothing on each of the four grain kinds."""
    with tree(feature_status='reviewing', with_record=False) as root:
        refusals = (
            (1, ('feature', 'done', '0.1/alpha',
                 '--review-record', 'docs/reviews/nope.md')),
            (2, ('story', 'wombat', STORY)),
            (2, ('story', 'building', '0.1/alpha/ghost')),
            (2, ('feature', 'done', '0.1/ghost')),
            (2, ('milestone', 'done', '9.9')),
            (2, ('bug', 'fixed', '0.1/bugs/ghost')),
        )
        for expected, argv in refusals:
            code, out = run_cli(root, *argv)
            assert code == expected, (argv, out)
            assert ledger_lines(root) == [], f'a refusal wrote a row: {argv}'


def test_a_frontmatter_write_that_FAILS_writes_no_row():
    """The one ordering that matters: the row is written after the write
    succeeded. Damaged frontmatter is where `set_field` returns False — the
    file is untouched, so the ledger must be too."""
    with tree() as root:
        damage(root / 'pm/roadmap/stories/s0.md',
               'no-closing-fence')
        code, out = run_cli(root, 'story', 'building', STORY)
        assert code == 2, out
        assert ledger_lines(root) == []


def test_a_ledger_that_cannot_be_written_never_fails_the_verb_that_wrote():
    """FAIL OPEN, and it is the whole reason the row is a side effect.

    These verbs run under the installed hooks, inside a commit — and a hook
    that blocks a commit because telemetry could not be written is the
    expensive defect, far more expensive than a missing row. The flip LANDED,
    so the verb reports it and exits 0. Loudly, though: the warning names the
    file on stderr, because a ledger that quietly stopped being written is the
    one failure nothing downstream would ever notice.

    Nothing covered this before the cut — the loud half (`pm ledger record`
    exiting 2) was proven and this half was not.
    """
    if os.geteuid() == 0:  # pragma: no cover - root ignores the mode bits
        pytest.skip('running as root: a read-only file is still writable')
    story = 'pm/roadmap/stories/s0.md'
    with tree(story_statuses=('ready',)) as root:
        # The MILESTONE's ledger, in its pool — where a story's status row
        # goes since 0.4.0. `<roadmap>/ledger.jsonl` is the grainless home and
        # a story's row never lands there.
        path = root / LEDGER_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('', encoding='utf-8')
        path.chmod(0o444)
        try:
            code, out = run_cli(root, 'story', 'building', STORY)
        finally:
            path.chmod(0o644)
        assert code == 0, out
        assert '[pm] story 0.1/alpha/s0: ready -> building' in out
        assert 'could not be appended to' in out
        assert 'status: building' in (root / story).read_text(encoding='utf-8')


# --- `pm decide` --------------------------------------------------------------

def test_a_milestone_decision_row():
    with tree() as root:
        code, out = run_cli(root, 'decide', '0.1', 'The ledger is one file')
        assert code == 0, out
        lines = ledger_lines(root)
        assert len(lines) == 1, lines
        row = json.loads(lines[0])
    assert list(row) == ['ts', 'kind', 'grain', 'entry', 'title']
    assert (row['kind'], row['grain'], row['entry'], row['title']) == (
        'decision', '0.1', 'D1', 'The ledger is one file')


def test_a_feature_decision_lands_in_the_MILESTONE_ledger():
    """`decisions.md` is per-grain; the ledger is per-milestone (D6). A second
    ledger beside the feature would split one milestone's rows across files no
    report ever joins."""
    with tree() as root:
        assert run_cli(root, 'decide', '0.1/alpha', 'Ship it')[0] == 0
        assert (root / 'pm/roadmap/features/alpha-decisions.md').is_file()
        # No per-feature ledger, ever: D3's rejected alternative, and a
        # pooled tree makes the absence structural rather than a convention.
        assert not (root / 'pm/roadmap/features'
                    / ledger.LEDGER_FILE_NAME).exists()
        row = only_row(root, ledger.KIND_DECISION)
    assert (row['grain'], row['entry']) == ('0.1/alpha', 'D1')


def test_the_ordinal_on_the_row_is_the_one_written_into_the_log():
    """The row and `decisions.md` must name the same entry, permanently: a
    mismatch makes the machine file and the prose file disagree about which
    decision is which, and neither can be repaired from the other."""
    with tree() as root:
        assert run_cli(root, 'decide', '0.1', 'First')[0] == 0
        assert run_cli(root, 'decide', '0.1', 'Second')[0] == 0
        rows = ledger_rows(root)
        log = (root / 'pm/roadmap/milestones/0.1-decisions.md').read_text()
    assert [(r['entry'], r['title']) for r in rows] == [
        ('D1', 'First'), ('D2', 'Second')]
    assert '## D2 — ' in log


def test_a_refused_decide_appends_nothing():
    with tree() as root:
        # A story has no decision log; a heading a shell cut in half is
        # refused whole; a decide with no title is a usage error. None is a row.
        assert run_cli(root, 'decide', '0.1/alpha/s0', 'x')[0] == 1
        assert run_cli(root, 'decide', '0.1', 'first half;')[0] == 1
        assert run_cli(root, 'decide', '0.1')[0] == 2
        assert ledger_lines(root) == []


@pytest.mark.parametrize('title', [
    'the "ledger" — a\\b, not c',
    # U+2028/U+2029 are line terminators to `str.splitlines()` and to a
    # browser's JSON reader, and `ensure_ascii=False` writes them raw — a row
    # carrying one would read back as TWO rows, the second invalid JSON, in a
    # file that is committed and never rewritten. `decide` refuses \n and \r;
    # nothing refuses these, so the serialiser escapes them.
    'a\u2028b\u2029c',
])
def test_a_hostile_decision_title_stays_ONE_row_and_round_trips(title):
    with tree() as root:
        assert run_cli(root, 'decide', '0.1', title)[0] == 0
        raw = (root / LEDGER_REL).read_text(encoding='utf-8')
    assert len(raw.splitlines()) == 1, raw
    assert json.loads(raw)['title'] == title
    # ensure_ascii=False: prose in the durable log is written as itself.
    assert '\\u2014' not in raw


# --- not a grain document -----------------------------------------------------

def test_validate_and_the_gate_and_status_are_unchanged_by_the_ledger():
    """`ledger.jsonl` is not `.md` and carries no frontmatter. Every reader
    that walks the tree must be byte-identical with it and without it — a
    consumer whose `check pm` reddens the day a row is first written would
    have no way to tell that from real drift."""
    with tree(story_statuses=('building',), feature_status='building',
              milestone_status='building') as root:
        before = (run_cli(root, 'validate'), run_gate(root),
                  run_cli(root, 'status'))
        assert run_cli(root, 'story', 'building', STORY)[0] == 0
        assert (root / LEDGER_REL).is_file()
        after = (run_cli(root, 'validate'), run_gate(root),
                 run_cli(root, 'status'))
    assert before[0] == after[0], 'pm validate saw the ledger'
    assert before[1] == after[1], 'check pm saw the ledger'
    assert before[2] == after[2], 'pm status saw the ledger'
    assert after[0][0] == 0
    assert after[1][0] == 0
    assert ledger.LEDGER_FILE_NAME not in after[2][1]


# --- the merge=union attribute ------------------------------------------------

def test_pm_init_writes_the_merge_union_line_for_the_configured_roadmap_dir():
    """The one file two milestone branches can both append to, and the only
    way that is a merge rather than a conflict. `[pm] roadmap_dir` is config,
    so the attribute cannot be a literal that is right only for the stock path
    — and the project's own attributes are preserved beside it."""
    with tree() as root:
        write_config(root, '[pm]\nroadmap_dir = "planning/ms"\n')
        (root / '.gitattributes').write_text('*.png binary\n', encoding='utf-8')
        code, out = run_cli(root, 'init')
        assert code == 0, out
        body = (root / '.gitattributes').read_text(encoding='utf-8')
    assert body.startswith('*.png binary\n'), "the project's own attributes were lost"
    # `**/*.jsonl`, and both halves are load-bearing. `**` because 0.4.0/D3
    # put a ledger at `<roadmap>/` itself for the rows naming no grain, and
    # `*/` is one directory level too deep to reach it. `*.jsonl` because a
    # pooled milestone's ledger is `<roadmap>/ledgers/<id>.jsonl` — no pattern
    # ending in the FILE NAME reaches it, and every branch appends to the
    # ledger of the milestone it is building. Both paths are proven to MATCH —
    # by git, over a real repo — in test_pm_ledger_report_git.py; this case is
    # about the configured prefix surviving.
    assert 'planning/ms/**/*.jsonl merge=union' in body


def test_a_second_init_does_not_duplicate_the_line():
    """And the ignore line beside it (#48): the local ledger every gate run
    appends to is never tracked, so a commit's own hook leaves the tree clean
    — written once, after the project's own entries, and never twice."""
    from agentic_sdlc.repo.pm import skills
    with tree() as root:
        (root / '.gitignore').write_text('*.tmp', encoding='utf-8')
        assert run_cli(root, 'init')[0] == 0
        before = [(root / name).read_bytes()
                  for name in ('.gitattributes', '.gitignore')]
        code, out = run_cli(root, 'init')
        assert code == 0, out
        assert [(root / name).read_bytes()
                for name in ('.gitattributes', '.gitignore')] == before
        assert 'already carries' in out
        assert 'already ignores' in out
        body = (root / '.gitattributes').read_text(encoding='utf-8')
        ignore = (root / '.gitignore').read_text(encoding='utf-8')
    assert body.count(skills_attribute_line()) == 1, body
    line = skills.local_ignore_line('pm/roadmap')
    assert line == f'pm/roadmap/{ledger.LOCAL_LEDGER_FILE_NAME}'
    assert ignore.startswith('*.tmp\n'), "the project's own entry was lost"
    assert ignore.splitlines().count(line) == 1, ignore


# --- the gate row -------------------------------------------------------------
# Story 02 (the shell that calls the verb) and story 03 (the report that prints
# it) both build against this exact key set, so the cases assert `sorted(row)`
# rather than membership: a membership check passes on a row carrying a sixth
# key nobody agreed to.

@pytest.mark.parametrize('duration_ms,census,expected', [
    # Everything measured.
    (12, 228, {'ts': GATE_TS, 'kind': 'gate', 'gate': 'check',
               'verdict': 'PASS', 'duration_ms': 12, 'census': 228}),
    # A census nobody reported is an absent KEY. A `0` there is this package's
    # cardinal sin with a number on it — indistinguishable afterwards from a
    # gate that really walked nothing.
    (12, None, {'ts': GATE_TS, 'kind': 'gate', 'gate': 'check',
                'verdict': 'PASS', 'duration_ms': 12}),
    # And the other half of the same rule: a measured zero is KEPT.
    (0, 0, {'ts': GATE_TS, 'kind': 'gate', 'gate': 'check',
            'verdict': 'PASS', 'duration_ms': 0, 'census': 0}),
])
def test_the_gate_row_keeps_a_measured_zero_and_omits_what_nobody_measured(
        duration_ms, census, expected):
    assert ledger.gate_row('check', 'PASS', duration_ms,
                           census, ts=GATE_TS) == expected


# --- append_row never joins a line it did not write ---------------------------
# A ledger whose last line lost its newline — a killed writer, a hand edit, a
# `merge=union` that landed a fragment — is the one shape where "open('a') and
# write one line" produces `{…}{…}` on ONE line: two rows nobody can read, one
# of them invalid, and `read_rows` reports a parse defect on a line nobody
# wrote. The well-formed and empty cases are the negative control: a repair
# that always fired would put a blank line in front of every row.

TORN = ledger.dumps(ledger.status_row('0.1/a/s0', 'ready', 'building',
                                      ts=GATE_TS))


@pytest.mark.parametrize('existing,expected_kinds', [
    (TORN, ['status', 'gate']),
    (TORN + '\n', ['status', 'gate']),
    ('', ['gate']),
])
def test_append_row_closes_a_torn_line_and_adds_exactly_one_of_its_own(
        tmp_path, existing, expected_kinds):
    path = ledger.ledger_path(tmp_path)
    if existing:
        path.write_text(existing, encoding='utf-8')
    ledger.append_row(tmp_path, ledger.gate_row('check', 'PASS', 12, 228,
                                                ts=GATE_TS))
    raw = path.read_text(encoding='utf-8')
    assert len(raw.splitlines()) == len(expected_kinds), raw
    assert raw.startswith(existing.rstrip('\n')), raw
    assert [r.data['kind'] for r in ledger.read_rows(path)] == expected_kinds


def test_a_row_of_an_unknown_future_kind_survives_byte_identical(tmp_path):
    """Forward compatibility, which is the property `merge=union` is worth
    having: old consumers read new files. A row this version cannot parse —
    another branch's, a later kind — is not read, not rewritten, not reordered,
    and does not stop the reader."""
    foreign = '{"ts":"2030-01-01T00:00:00Z","kind":"wombat","x":[1,2]}\n'
    path = ledger.ledger_path(tmp_path)
    path.write_text(foreign, encoding='utf-8')
    ledger.append_row(tmp_path, ledger.gate_row('check', 'PASS', 12, None,
                                                ts=GATE_TS))
    assert path.read_bytes()[:len(foreign)] == foreign.encode('utf-8')
    assert [r.data['kind'] for r in ledger.read_rows(path)] == ['wombat', 'gate']


# --- 0.4.0/every-grain-is-on-a-stopwatch --------------------------------------
def test_an_in_flight_grain_is_measured_and_an_unmoved_one_is_not():
    """`total_seconds` answers the CLOSED question and returns None while a
    grain is in flight, which left the number that creates pressure
    unmeasured: 0.3.0 built eleven features in 64 minutes and spent 93 more
    reviewing them, with every one of those features sitting `building` and
    nothing anywhere saying so.

    The sharp half is the third row. **A grain nobody has moved is UNMEASURED,
    never zero** — `0` would read as "moved a moment ago", which is a different
    fact (rule 4).
    """
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

    class Row:
        def __init__(self, ts, to):
            self.data = {'kind': 'status', 'grain': STORY, 'ts': ts, 'to': to}

    with tree(story_statuses=('building',)) as root:
        cfg = cfg_for(root)
        moved = [Row('2026-09-06T09:00:00Z', 'building')]
        assert ledger.open_seconds(cfg, 'story', moved, now) == 3 * 3600
        # Closed: `total_seconds`' question, and not this one's.
        closed = moved + [Row('2026-09-06T11:00:00Z', 'done')]
        assert ledger.open_seconds(cfg, 'story', closed, now) is None
        # Never moved: absent, not zero.
        assert ledger.open_seconds(cfg, 'story', [], now) is None


@pytest.mark.parametrize('seconds,said', [
    (None, '-'), (0, '0s'), (45, '45s'), (750, '12m 30s'),
    (3 * 3600 + 900, '3h 15m'), (2 * 86400 + 4 * 3600, '2d 4h'),
])
def test_a_duration_is_two_units_at_most(seconds, said):
    """A number a human reads at a glance is the point; `271431s` is not one."""
    assert ledger.human_duration(seconds) == said


def test_the_age_prints_over_a_POOL_SHAPED_id_too():
    """M4. `support.pm.tree()` keeps slash-shaped ids (`0.1/alpha`), which are
    valid — an id is opaque in 0.4.0 — but they are not the shape the migration
    or a prefixed project mints. Every case for this feature ran on the slash
    shape, so a resolver deciding a grain's KIND by counting slashes worked in
    all of them and could not work on a real pooled tree: `ft-…`, `st-…` and
    `bg-…` all read as milestones, and the milestone vocabulary was then asked
    whether a bug had closed.

    The case has to make the misclassification VISIBLE, and an open feature
    does not: this repo's feature and milestone flows share `done`, so asking
    the wrong vocabulary gives the right answer. So the tree declares a feature
    flow whose done word the MILESTONE flow does not have. A grain that has
    reached it is finished and must carry no age — and a resolver that decided
    `ft-…` was a milestone asks the milestone vocabulary, does not find
    `shipped` in it, and prints a growing age beside `[shipped]`. That is a
    number that looks legitimate and is not (rule 4), in a read verb.
    """
    flow = declaring(feature={'todo': ('planning',), 'in_progress': ('building',),
                              'done': ('shipped',)})
    with tree(story_statuses=('building',), config=flow) as root:
        for slug, status in (('beta', 'building'), ('gamma', 'shipped')):
            write(root / f'pm/roadmap/features/{slug}.md',
                  {'id': f'ft-{slug}', 'kind': 'feature', 'milestone': '"0.1"',
                   'name': slug, 'status': status, 'reviewed': '', 'phase': ''})
        # ONE call: `put_ledger` writes the file rather than appending to it.
        put_ledger(root, *(ledger.dumps(ledger.status_row(
            f'ft-{slug}', 'planning', status, ts='2020-01-01T00:00:00Z'))
            for slug, status in (('beta', 'building'), ('gamma', 'shipped'))))
        code, out = run_cli(root, 'status')
        assert code == 0, out
        by_slug = {slug: next(ln for ln in out.splitlines() if f'ft-{slug}' in ln)
                   for slug in ('beta', 'gamma')}
        # Open: an age, in days, because the row is from 2020.
        assert 'open ' in by_slug['beta'], out
        assert 'd ' in by_slug['beta'].split('open ')[1], out
        # Finished IN ITS OWN VOCABULARY: no age at all.
        assert 'open ' not in by_slug['gamma'], out


def test_pm_status_prints_the_age_and_nothing_gates_on_it():
    """The report, and the claim that it is only a report: a very old open
    grain changes no exit code. A ceiling on how long a feature may stay open
    would be this package having an opinion about somebody's week (rule 9)."""
    with tree(story_statuses=('building',)) as root:
        # A FEATURE, because `pm status` prints milestone and feature lines —
        # a story's age has nowhere to land there, and `pm list` is the verb
        # that enumerates stories.
        put_ledger(root, ledger.dumps(ledger.status_row(
            '0.1/alpha', 'ready', 'building', ts='2020-01-01T00:00:00Z')))
        code, out = run_cli(root, 'status')
        assert code == 0, out
        # The FEATURE's line: the milestone's own cell now reads `open -`,
        # because it is open and nobody has moved it (rule 4 — unmeasured is
        # not young).
        line = next(ln for ln in out.splitlines() if 'feature alpha' in ln)
        assert 'open ' in line, out
        # Years old, and still exit 0: the number is a report (rule 9).
        assert 'd ' in line.split('open ')[1], out


# --- the lesson row (0.5.0/ft-a-lesson-is-a-row-bound-to-a-grain) -------------
# CAPTURE, and the whole of it: four fields the caller states and nothing
# derived from them. The row kind joins the harness above — it routes by grain
# like every other row, and it is refused rather than half-minted, because a
# lesson naming no grain surfaces nowhere and one naming no source is the
# paraphrase D1 says a lesson must never be.

LESSON_TS = '2026-09-07T12:00:00Z'
LESSON = ('0.1/alpha', 'review-recorded', 'docs/reviews/alpha.md',
          'the fixture is copied, never edited in place')


def test_the_lesson_row_is_the_four_fields_written_and_nothing_derived():
    """Bites: a `weight`, a `confidence`, a `count` — anything the row holds
    that nobody typed. The namesake package's `Learner` pins confidence at 0.1
    forever because `frequency` is incremented nowhere (D1); a field with no
    feedback edge is the shape of that defect, and the assertion is EQUALITY so
    a sixth key fails rather than passes."""
    assert ledger.lesson_row(*LESSON, ts=LESSON_TS) == {
        'ts': LESSON_TS, 'kind': 'lesson', 'grain': '0.1/alpha',
        'rule': 'review-recorded', 'source': 'docs/reviews/alpha.md',
        'text': 'the fixture is copied, never edited in place'}


@pytest.mark.parametrize('field,value', [
    ('grain', ''), ('grain', '   '), ('grain', None),
    ('rule', ''), ('source', ''),
    ('text', ''), ('text', '   '), ('text', '...'),
    ('text', 'one\ntwo'), ('text', 'x' * (ledger.REASON_MAX + 1)),
])
def test_a_lesson_missing_a_pointer_or_a_text_is_refused_not_minted(field,
                                                                   value):
    """Refused HERE, as `deviation_row` refuses a reason, so no path can mint
    one: a row carrying `''` where a pointer belongs reads back as a lesson
    about nothing, and `Store.against_grain('')` answers nothing for it."""
    fields = dict(zip(('grain_id', 'rule', 'source', 'text'), LESSON))
    fields[{'grain': 'grain_id'}.get(field, field)] = value
    with pytest.raises(ValueError, match='lesson'):
        ledger.lesson_row(**fields)


def test_a_lesson_row_lands_in_the_ledger_that_owns_its_grain():
    """The routing quartet's harness, asked of the new kind: a row about a
    story files under the milestone that owns it, and `pm ledger show` prints
    it in the same stream as the status rows — a reader who has to join two
    logs has two logs."""
    with tree() as root:
        target = ledger.ledger_of_grain(cfg_for(root), '0.1/alpha/s0')
        ledger.append_to(target, ledger.lesson_row(
            '0.1/alpha/s0', 'evidence-written', 'docs/reviews/alpha.md',
            'a story with no done: line is not closed', ts=LESSON_TS))
        assert target.resolve() == (root / LEDGER_REL).resolve()
        code, out = run_cli(root, 'ledger', 'show', '0.1/alpha/s0')
        assert code == 0, out
        said = [ln for ln in out.splitlines() if 'lesson' in ln]
        assert len(said) == 1, out
        # Rule 11's read side: the row PRINTS what it holds. A bare `ts kind`
        # teaches a reader the tool does not have the answer.
        for cell in ('evidence-written', 'a story with no done: line',
                     'source: docs/reviews/alpha.md'):
            assert cell in said[0], said[0]


# --- the event schema is the schema the minters mint (0.5.0) -----------------
# `install-sdlc` renders `ledger.EVENT_KEYS` into the protocol document, so the
# tuples there are a CLAIM about three functions in three modules. Bound here
# by minting one row of each kind and comparing: a field added to a payload and
# not to the schema renders a document that is quietly wrong, which is the
# second-scoreboard defect the feature exists to delete.

def test_every_tap_kind_spells_the_tap_check_pm_counts():
    """U3 keys on the last dotted segment (`emit.TAPS`), so a kind that does
    not spell its tap makes the gate noisy rather than blind."""
    from agentic_sdlc.repo import emit
    taps = [kind.rsplit('.', 1)[-1] for kind in ledger.EVENT_KEYS]
    assert taps == list(emit.TAPS), taps
    assert len(ledger.EVENT_KEYS) == len(emit.TAPS)


# The keys a minted row may legitimately LACK, by kind and by name. Everything
# else declared must be minted: `zip` drops a key the value tuple has no
# element for, so a phantom appended to a `*_KEYS` tuple used to publish a
# column into `docs/sdlc-protocol.md` that no row ever carries — the document
# describing a stream that is not emitted, which is what rendering it exists to
# prevent.
OPTIONAL_KEYS = {ledger.KIND_LEAVE: {'value'}}


def test_the_rendered_schema_is_the_row_each_minter_actually_mints():
    from agentic_sdlc.repo.conveyor import driver
    from agentic_sdlc.repo.pm import arrive, ready_for
    minted = {
        ledger.KIND_ENTER: ready_for._enter_row('feature', '0.1/alpha', []),
        ledger.KIND_VERDICT: driver.verdict_row(
            'feature', '0.1/alpha', 'stories-done', driver.Answer.yes('ok'),
            'agentic-sdlc pm ready-for feature <id>'),
        ledger.KIND_LEAVE: ledger.leave_row(
            '0.1/alpha', 'done', None, (), arrive.NOTHING),
    }
    assert set(minted) == set(ledger.EVENT_KEYS), 'a kind mints nothing here'
    for kind, row in minted.items():
        assert row['kind'] == kind
        declared = ledger.EVENT_KEYS[kind]
        assert list(row) == [k for k in declared if k in row], row
        assert set(row) <= set(declared), sorted(set(row) - set(declared))
        phantom = set(declared) - set(row) - OPTIONAL_KEYS.get(kind, set())
        assert not phantom, (
            f'{kind} declares {sorted(phantom)} and mints them nowhere — the '
            f'rendered table would publish a column no consumer will ever '
            f'receive. Mint it, or name it in OPTIONAL_KEYS')


def test_an_answer_that_carried_a_value_fills_the_last_leave_key():
    """`value` is the one optional key, and it is last so nine values zip
    against ten keys. The negative control for the row above: an absent answer
    value must be an absent KEY, never a `''`."""
    from agentic_sdlc.repo.pm import arrive
    said = arrive.Said(answer='--by agent', value='builder')
    row = ledger.leave_row('0.1/alpha', 'building', None, (), said)
    assert row['value'] == 'builder'
    assert list(row) == list(ledger.LEAVE_KEYS)
