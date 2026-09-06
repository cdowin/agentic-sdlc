"""ledger.py — the milestone's append-only row log (`ledger.jsonl`).

One JSON object per line, in `pm/roadmap/<milestone>/ledger.jsonl`, beside
`decisions.md` (D6). `decisions.md` is the prose sibling — a person writes it
and a person reads it; this is the machine one: the verbs write it and a report
reads it, and neither file is ever a copy of the other.

THREE PROPERTIES, AND EVERY CALLER DEPENDS ON ALL THREE:

  * **Append-only.** `append_row` opens `'a'` and writes one line. It never
    parses and never rewrites a byte that is already there — so a row landed by
    another process, another branch, or an older version of this package
    survives a shape change here, and a `merge=union` on the file makes two
    branches' rows one file rather than one conflict. The one byte it READS is
    the file's last, to know whether the previous writer finished its line: a
    torn tail is the one shape where appending a row JOINS it (`{…}{…}`), and
    the repair is a newline in front of the new row, never a touch to the old.
  * **One line per row, compact.** `separators=(',',':')` and no newline inside
    the line, so a row is exactly one `readline()` and a `wc -l` is a row count.
    `ensure_ascii=False` because a decision title is prose and a `\\u2014` in
    the durable log helps nobody read it.
  * **The timestamp is the whole point** (D8). Full UTC ISO-8601 at second
    resolution, `Z`-suffixed — never a local time and never a bare date: time
    in each state is a SUBTRACTION over two rows, and a date cannot answer
    "how long was this at `review`".

Nothing here decides WHEN a row is written; that is the verb's business, and
the verbs write theirs only after their own write to the tree has landed.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.repo import gates_extra

# Beside `decisions.md`, inside the milestone directory that owns it — so
# `retire` removes it with the directory and git is the archive (D6).
LEDGER_FILE_NAME = 'ledger.jsonl'

# The row kinds this module mints. `dispatch` and `session` rows arrive from
# `pm ledger record` and are not built here.
KIND_STATUS = 'status'
KIND_DECISION = 'decision'
KIND_GATE = 'gate'

# `2026-09-03T21:40:12Z`. `datetime.isoformat()` spells the offset `+00:00`,
# and two spellings of one instant in a durable log is a parser's problem
# forever, so the format is stated rather than inherited.
TS_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# U+2028 and U+2029 are LINE TERMINATORS to `str.splitlines()` (and to a
# browser's JSON reader), and `ensure_ascii=False` writes them out raw — so one
# row carrying either, in a hand-edited id or a pasted decision title, would
# read back as two rows, one of them invalid. Escaped to their `\uXXXX` form,
# which is still exactly the same JSON: every structural character is ASCII, so
# these two can only ever occur inside a string.
LINE_BREAKERS = {'\u2028': '\\u2028', '\u2029': '\\u2029'}


def dumps(row: dict) -> str:
    """ONE row as ONE line — the whole serialisation contract, in one place."""
    line = json.dumps(row, separators=(',', ':'), ensure_ascii=False)
    for char, escaped in LINE_BREAKERS.items():
        line = line.replace(char, escaped)
    return line


def utc_now() -> str:
    """The current instant, full UTC ISO-8601 at second resolution."""
    return datetime.now(timezone.utc).strftime(TS_FORMAT)


def status_row(grain_id: str, frm: str, to: str, ts: str = '') -> dict:
    """One status transition. `from` is what the file HELD, `to` what it holds.

    A no-op flip (`from == to`) is a row like any other: somebody ran the verb,
    and that is a fact about the work (D2's cost note, carried by D8).
    """
    return {'ts': ts or utc_now(), 'kind': KIND_STATUS, 'grain': grain_id,
            'from': frm, 'to': to}


def decision_row(grain_id: str, entry: str, title: str, ts: str = '') -> dict:
    """One decision heading, as `pm decide` stamped it into `decisions.md`."""
    return {'ts': ts or utc_now(), 'kind': KIND_DECISION, 'grain': grain_id,
            'entry': entry, 'title': title}


# --- the gate row -------------------------------------------------------------
# One GATE RUN's cost. Not a grain row and not a usage row: a gate is not work
# somebody was dispatched to do, so folding it into either would make the spend
# table bill a story for the seconds `make check` spent.
#
# The name is a make target, and the SAME grammar `[gates] extra` already
# enforces on one — imported rather than respelled, because story 03's report
# and the story belt both JOIN on this string and a second spelling of one
# grammar is how the two halves come to disagree about which names exist.
GATE_NAME = gates_extra.TARGET
GATE_NAME_MAX = gates_extra.MAX_LENGTH

# The verdict vocabulary, CLOSED. A gate's console line is prose ("PASS (12
# files)", "FAIL — 3 findings") and a durable column is not: free text there
# would give one outcome five spellings and nothing could count them. The four
# are what a caller can know from an exit code — 0, non-zero, the 124/137
# timeout pair, and "this gate did not run", which must not read as a PASS.
GATE_VERDICTS = ('PASS', 'FAIL', 'HANG', 'SKIP')


def gate_row(gate: str, verdict: str, duration_ms: int | None,
             census: int | None = None, ts: str = '') -> dict:
    """One gate run: what it was, how it went, what it cost, over how much.

    MILLISECONDS, and the unit is the whole reason this row is worth writing.
    It was whole seconds for one draft, until the numbers the feature was
    planned from were held against the grammar: of twenty measured gates,
    fourteen are under a second, and the narrow-vs-wide pair that motivates the
    story belt is 0.9 s against 154 s. Under an integer-second row the narrow
    side records `0` — the ratio is undefined — or rounds to `1` and reports
    154x for a measured 170x. A cost column that cannot resolve the cheap half
    of its own headline comparison is a write-only column with extra steps.

    `census` is the corpus the run walked, and it is OPTIONAL because not every
    gate can count one. An absent census is an absent KEY — never a `0`, which
    is a MEASUREMENT ("this gate walked nothing") and reads forever after as
    the zero-file census hard rule 4 calls a cardinal sin. `duration_ms` obeys
    the same rule; the CLI additionally refuses a gate row that carries no
    duration at all, because a cost row with no cost is a write-only column.

    Integer milliseconds rather than a float second: a float in a JSONL row is
    a locale and a repr away from two spellings of one number, and the shell
    that will produce these has no float arithmetic to round with.

    Nothing here judges: no ceiling, no budget, no verdict of its own. The row
    is the measurement, and what it means is the report's question.
    """
    row = {'ts': ts or utc_now(), 'kind': KIND_GATE, 'gate': gate,
           'verdict': verdict}
    for key, value in (('duration_ms', duration_ms), ('census', census)):
        if value is not None:
            row[key] = value
    return row


# --- the deviation row --------------------------------------------------------
# One step of a conveyor run (`agentic-sdlc release` / `adopt`) that was
# SKIPPED, and why. Minted here for `gate_row`'s reason: this module owns
# `dumps`, `TS_FORMAT` and `LINE_BREAKERS`, and a second module writing JSONL
# by hand would be a second serialisation contract.
#
# Only DEVIATIONS are rows. A row per completed step was the first draft and it
# defeats the machine: the ledger is TRACKED, in the milestone directory, so
# writing a row after step 1 (`tree-clean`) makes the tree dirty — the run
# falsifying its own first postcondition, which is exactly the argument
# `conveyor/state.py` makes for gitignoring the run state. The completed half
# of a run lives in that gitignored cache; the DURABLE record is what somebody
# decided to do differently, because that is the half nobody can reconstruct
# from the tree afterwards.
#
# Chris, 2026-09-04: *steps are skippable, and a skip is RECORDED.* Deviation
# stays possible; invisible deviation does not.
#
# D8, 2026-09-05, kept the row and changed who mints it. `--skip <step>
# --reason "<why>"` was how a deviation reached this file, and the flag existed
# to escape a REFUSAL — with nothing refusing, it was ceremony with a grammar.
# The row was always the honest half, so the DRIVER now writes one for every
# step that is not true, carrying the reason the step itself gave. Same row,
# same durability argument, minus the requirement that somebody remember to
# type it. `outcome` is what widened: it was the constant `'skipped'` and it is
# now the step's own verdict.
# ONE SLOW TEST, named. The `gate` row above says what a TIER cost; this says
# which case inside it did. The two answer different questions and the second
# is the one you can act on: a tier that went from 30 s to 45 s tells you to go
# looking, and this tells you where.
#
# ONLY THE SLOWEST FEW ARE FILED, and the cap is the whole design. A row per
# test would be ~1850 rows per run in a file that is COMMITTED — telemetry
# nobody can read is telemetry nobody keeps, and a ledger that doubles every
# afternoon gets deleted. What is worth durable space is the tail, because the
# tail is where a suite's wall clock lives: two cases were once 47 of 96
# seconds here, and nothing recorded that fact.
KIND_TEST = 'test'

KIND_DEVIATION = 'deviation'

# What a `deviation` row may say happened. CLOSED, and `'skipped'` stays in it
# because rows carrying it are already in every consumer's ledger and a reader
# that stopped understanding them would be rewriting history (D7's reasoning,
# one file over).
OUTCOMES = ('not-true', 'unverifiable', 'skipped')

# A durable log is not a paste buffer. The cap is on the REASON because it is
# the only free-text field, and a row is one line.
REASON_MAX = 1024


def reason_defect(reason: object) -> str:
    """'' when `reason` may be a deviation's reason, else why not.

    A skip with no reason is the silence this row exists to end, so an empty
    one cannot be minted at all — not defaulted, not stamped `unknown`. That is
    `COPY WHAT THE RUN DID, OMIT WHAT IT LACKS, INVENT NOTHING`, applied to the
    one field whose absence is the whole defect.
    """
    if not isinstance(reason, str):
        return f'a reason must be a string, got {reason!r}'
    if not reason.strip():
        return 'a reason that is empty or whitespace is not a reason'
    if not any(ch.isalnum() for ch in reason):
        return (f'{reason!r} carries no letter or digit — punctuation is not '
                f'a reason')
    if len(reason) > REASON_MAX:
        return (f'the reason is {len(reason)} characters; the limit is '
                f'{REASON_MAX} — a durable log is not a paste buffer')
    # U+2028 / U+2029 are NOT refused: `LINE_BREAKERS` escapes them, so a
    # reason carrying one still reads back as exactly one row. `\n`, `\r` and
    # `\x00` have no such escape here and one row is one line.
    for char, spelling in (('\n', r'\n'), ('\r', r'\r'), ('\x00', r'\x00')):
        if char in reason:
            return f'a reason carrying {spelling} would not be one row'
    return ''


def test_row(tier: str, nodeid: str, duration_ms: int, rank: int,
             ts: str = '') -> dict:
    """One slow test: which tier it ran in, what it is called, what it cost.

    `rank` is its position in that run's slowest list — 1 is the slowest — so a
    reader can tell "this was the worst case in the suite" from "this was the
    tenth worst" without holding the other nine.

    MILLISECONDS, for the reason `gate_row` gives: the interesting comparison
    spans three orders of magnitude, and a whole-second column cannot resolve
    the cheap half of it.
    """
    if not isinstance(nodeid, str) or not nodeid.strip():
        raise ValueError('refusing to mint a test row with no node id')
    if not isinstance(duration_ms, int) or duration_ms < 0:
        raise ValueError(
            f'refusing to mint a test row for {nodeid!r}: duration_ms is '
            f'{duration_ms!r}, and a cost that is not a whole number of '
            f'milliseconds is not a measurement')
    if not isinstance(rank, int) or rank < 1:
        raise ValueError(f'refusing to mint a test row for {nodeid!r}: rank '
                         f'{rank!r} is not a position in a list')
    return {'ts': ts or utc_now(), 'kind': KIND_TEST, 'tier': tier,
            'nodeid': nodeid, 'duration_ms': duration_ms, 'rank': rank}


def deviation_row(grain_id: str, operation: str, step: str, reason: str,
                  ts: str = '', outcome: str = 'not-true') -> dict:
    """One step of a conveyor run that did not come out true, and why.

    `reason` is validated HERE rather than by the caller, so a row without one
    cannot be minted through any path. A caller that wants a friendlier
    refusal asks `reason_defect` first and never gets a different answer. Under
    D8 the reason is the step's own `Answer.detail`, and `Answer`'s docstring
    already rules that a step answering not-true with an empty detail has told
    the operator that something is wrong and nothing about what — so the same
    validation catches the same defect from the new caller.

    `outcome` must be one of `OUTCOMES`. A row saying something this reader
    does not understand is the drift a closed set exists to stop.
    """
    defect = reason_defect(reason)
    if defect:
        raise ValueError(f'refusing to mint a {KIND_DEVIATION} row for '
                         f'{step!r}: {defect}')
    if outcome not in OUTCOMES:
        raise ValueError(f'refusing to mint a {KIND_DEVIATION} row for '
                         f'{step!r}: {outcome!r} is not one of {OUTCOMES}')
    return {'ts': ts or utc_now(), 'kind': KIND_DEVIATION, 'grain': grain_id,
            'operation': operation, 'step': step, 'outcome': outcome,
            'reason': reason}


def ledger_path(milestone_dir: Path) -> Path:
    """Where one milestone's ledger lives. The only place this name is joined."""
    return milestone_dir / LEDGER_FILE_NAME


def append_row(milestone_dir: Path, row: dict) -> None:
    """Append ONE row to `<milestone_dir>/ledger.jsonl`, creating it if absent.

    Minted on first write, like `decisions.md` — an empty ledger in every
    milestone directory would be the sprawl the scaffolder was cured of. The
    FILE is created; the DIRECTORY is never created here, because every caller
    has just written a grain document that lives in it — and mkdir is one of
    the mutations `core.apply` single-homes (tests/test_boundaries.py).

    The write itself is `open('a')` rather than a `core.apply` overwrite, and
    that is the point: an overwrite is read-modify-write, which drops rows when
    two appenders (two milestone branches, an async SubagentStop hook and a
    verb) land in the same instant, and rewrites bytes `merge=union` is relying
    on nobody rewriting. Append is a different primitive, not a shortcut past
    the one plan.

    ONE byte is read before the write, and it is the last: if the previous
    writer did not finish its line — a killed process, a hand edit, a
    `merge=union` that landed a fragment — `open('a')` puts this row on the END
    of that line and produces `{…}{…}`, which is two rows nobody can read and
    one `LedgerError` on a line nobody wrote. So the newline is closed first.
    That is a READ of one byte, never a parse and never a rewrite: no byte
    already on disk changes, and a reader that arrives between the two writes
    sees a blank line, which every reader here already skips.

    Raises `OSError` when the line cannot be written. It does NOT swallow that:
    the caller has already changed the tree, and "the row is missing" is a fact
    its report has to carry rather than one this function hides.
    """
    path = ledger_path(milestone_dir)
    line = dumps(row) + '\n'
    if _ends_mid_line(path):
        line = '\n' + line
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(line)


def _ends_mid_line(path: Path) -> bool:
    """True when the file exists, is not empty, and its last byte is not `\\n`.

    Binary, and one `seek`: the file is a day's rows and reading it to answer
    this would make an append a read of the whole log. A file that cannot be
    read at all answers False and lets the append itself raise — an OSError
    here would report the wrong failure for the same underlying one.
    """
    try:
        with path.open('rb') as handle:
            if not handle.seek(0, 2):
                return False
            handle.seek(-1, 2)
            return handle.read(1) != b'\n'
    except OSError:
        return False



# --- the usage rows (D3/D4/D5) ------------------------------------------------
# A `dispatch` row is one subagent's whole life; a `session` row is the
# orchestrator's own totals at one stop. Both are minted from a Claude Code
# transcript by `pm ledger record`, and everything below obeys ONE rule:
#
#   COPY WHAT THE TRANSCRIPT HOLDS, OMIT WHAT IT LACKS, INVENT NOTHING.
#
# No sentinel, no label, no zero standing in for a field that was absent, no
# guess at which grain a dispatch was "really" about (D3 puts every candidate
# on the row and leaves attribution to the report). The only thing this module
# refuses is a transcript it cannot READ — a line that is not JSON, a timestamp
# that is not a timestamp, a token count that is not a number, a file with no
# assistant record at all. Those are loud (exit 2 at the CLI) because the
# alternative is a row of zeros that reads exactly like a cheap dispatch, and a
# ledger cannot tell the two apart afterwards (hard rule 4).
KIND_DISPATCH = 'dispatch'
KIND_SESSION = 'session'

# The hook events that mint them. `SubagentStop` fires once per dispatch and
# `Stop` once per orchestrator turn — the kind is the EVENT's, never inferred
# from the transcript's shape (a sidechain flag is the transcript's opinion;
# which hook fired is a fact the caller has).
EVENT_KINDS = {'SubagentStop': KIND_DISPATCH, 'Stop': KIND_SESSION}

# The tools whose use means the agent started WRITING. `tool_calls_before_first
# _write` is the milestone's "overhead shape" question — how much looking a
# dispatch does before it touches the tree — and it is a raw count, never a
# ratio and never a verdict.
WRITE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')

# Our row key ← the transcript's `message.usage` key. Four sums, named for what
# they are rather than for what the API calls them, because the row outlives the
# API's spelling; the OTHER keys `usage` carries are ignored, not copied, so a
# new one appearing upstream changes nothing here.
USAGE_FIELDS = (('input', 'input_tokens'),
                ('output', 'output_tokens'),
                ('cache_creation', 'cache_creation_input_tokens'),
                ('cache_read', 'cache_read_input_tokens'))

# Record and block types this reads. Named so the coupling D4 accepted is
# greppable in one place rather than spelled as literals down the file.
TYPE_ASSISTANT = 'assistant'
TYPE_TOOL_USE = 'tool_use'

# Not a model. Claude Code writes this as the `model` of an assistant record IT
# generated rather than received — an API-error notice, carrying an all-zero
# `usage`. D4 ("never interpret `message.model`") is about not second-guessing
# a real identifier; a bracketed pseudo-name is not one, so dropping it from
# the model list is a SPELLING rule and not a judgement (0.23.0/ledger D3).
#
# The exact token, never the `<…>` shape: a census of 734 real transcripts
# found this value and no other bracketed one in this position, and a shape
# rule would make the NEXT pseudo-name vanish from the one field that would
# have reported it. An unknown one comes through raw and gets decided the same
# way this one was.
SYNTHETIC_MODEL = '<synthetic>'

# Every key a usage row may carry, in the order feature.md writes them. A row
# omits the ones it has no value for — `usage_row` never emits a key with None
# behind it — so this is a key ORDER, not a schema with required fields.
ROW_KEYS = ('ts', 'kind', 'grain', 'session_id', 'agent_id', 'agent_type',
            'model', 'started_at', 'ended_at', 'duration_s', 'messages',
            'tool_calls', 'tools', 'tool_calls_before_first_write', 'usage',
            'tree')


class TranscriptError(Exception):
    """A transcript this module cannot READ. Never a judgement about content."""


class LedgerError(Exception):
    """A line already in the ledger that will not parse. Names the line."""


class Row(NamedTuple):
    """One ledger line, three ways: where it is, what it says, what it IS.

    `line` is kept because `--json` prints the bytes on disk rather than a
    re-serialisation — a row written by a future version of this package, with
    keys this one has never heard of, must come back out unchanged.
    """
    lineno: int
    data: dict
    line: str


def normalise_ts(raw: object, where: str) -> str:
    """A transcript timestamp as this ledger spells one: full UTC, seconds, `Z`.

    The transcript writes milliseconds and this log does not (D8's format is
    one instant, one spelling), so the fractional part is TRUNCATED rather than
    rounded — a rounded `ended_at` can land after the stop that recorded it,
    and a duration is a subtraction over these two strings.

    A timestamp that will not parse RAISES. It is the one field the report
    cannot do without, and a dropped one would leave a row that looks complete
    and answers "how long" with silence.
    """
    if not isinstance(raw, str) or not raw:
        raise TranscriptError(f'{where} has no timestamp ({raw!r})')
    try:
        when = datetime.fromisoformat(raw)
    except ValueError as err:
        raise TranscriptError(f'{where} timestamp {raw!r} is not ISO-8601 '
                              f'({err})') from err
    if when.tzinfo is None:
        # A naive stamp is UTC by the transcript's own convention; reading it as
        # LOCAL would silently shift every duration by the machine's offset.
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc).strftime(TS_FORMAT)


def parse_ts(value: object) -> datetime | None:
    """A `ts` string back to an instant, or None when it is not one."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, TS_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _number(value: object, where: str) -> int:
    """A count from the transcript, or a loud refusal. Absent is 0.

    Absent and zero are the same statement about a SUM (adding nothing adds
    nothing), which is why a record without `usage` contributes 0 rather than
    refusing. A key that is PRESENT and not an integer is a different fact: the
    shape this package reads has changed, and D4's cost note says that fails
    loudly. `bool` is excluded on purpose — `True` is an `int` in Python and
    would sum as 1.
    """
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise TranscriptError(f'{where} is {value!r}, which is not a number')
    return value


def records_of(path: Path) -> Iterator[tuple[int, dict]]:
    """(line number, record) for every line of a transcript, in file order.

    A GENERATOR, and the whole file is never held: a `Stop` hook fires on every
    orchestrator turn against a transcript that grows all day, and the summary
    below is one pass of sums. Lines are read through the file handle rather
    than `splitlines()`, which treats U+2028/U+2029 as terminators and would
    tear one legitimate row into two invalid ones.

    A line that is not a JSON object raises `TranscriptError` naming the line
    number — the transcript is an interface we READ and do not own (D4), so a
    shape we cannot parse is reported, never skipped.
    """
    try:
        handle = path.open(encoding='utf-8')
    except OSError as err:
        raise TranscriptError(f'{path} could not be read ({err})') from err
    with handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as err:
                raise TranscriptError(f'line {lineno} of {path} is not JSON '
                                      f'({err})') from err
            if not isinstance(record, dict):
                raise TranscriptError(f'line {lineno} of {path} is a '
                                      f'{type(record).__name__}, not a record')
            yield lineno, record


def transcript_summary(records: Iterable[tuple[int, dict]]) -> dict:
    """Sum one transcript into the fields a usage row carries. One pass, no judgement.

    What it counts, and nothing else:

      * `usage` — the four `message.usage` numbers summed over the ASSISTANT
        records. A record without `usage` counts as a message and adds 0.
      * `messages` — assistant records. `tool_calls` — `tool_use` blocks.
        `tools` — those blocks by `name`, in first-seen order.
      * `tool_calls_before_first_write` — the blocks before the first
        `WRITE_TOOLS` one; the TOTAL when the dispatch never wrote, because
        "it looked N times and never wrote" is the same number either way and
        a sentinel would be this module inventing a value.
      * `started_at`/`ended_at` — the first and last timestamp of ANY record,
        in file order. The bounds of the whole transcript, not of the model's
        half of it: a dispatch's wall-clock starts at the prompt.
      * `model` — the assistant records' `message.model`, first-seen order; a
        string when there is one, the LIST when a session switched models. Raw
        either way, because "which model" is the report's question to ask —
        except `SYNTHETIC_MODEL`, which is not an identifier at all and is
        dropped as a spelling. It still counts as a message and its usage
        still sums: the record happened, only its `model` says nothing. A
        transcript with no other model has no `model` key on its row.

    A file with NO assistant record raises: there is nothing to sum, and a row
    of zeros is indistinguishable afterwards from a dispatch that really cost
    nothing (hard rule 4).
    """
    usage = {name: 0 for name, _ in USAGE_FIELDS}
    tools: dict[str, int] = {}
    models: list[str] = []
    messages = tool_calls = before_write = 0
    wrote = False
    first_ts = last_ts = ''
    for lineno, record in records:
        where = f'line {lineno}'
        stamp = record.get('timestamp')
        if stamp is not None:
            last_ts = normalise_ts(stamp, where)
            first_ts = first_ts or last_ts
        if record.get('type') != TYPE_ASSISTANT:
            continue
        messages += 1
        message = record.get('message')
        message = message if isinstance(message, dict) else {}
        model = message.get('model')
        if (isinstance(model, str) and model and model != SYNTHETIC_MODEL
                and model not in models):
            models.append(model)
        seen = message.get('usage')
        seen = seen if isinstance(seen, dict) else {}
        for name, key in USAGE_FIELDS:
            usage[name] += _number(seen.get(key), f'{where} usage.{key}')
        content = message.get('content')
        for block in content if isinstance(content, list) else ():
            if not isinstance(block, dict) or block.get(
                    'type') != TYPE_TOOL_USE:
                continue
            tool_calls += 1
            name = block.get('name')
            if isinstance(name, str) and name:
                # A block with no `name` still counts as a CALL — it happened —
                # but it is not attributed to a tool, because `tools[None]` would
                # be this module naming something the transcript did not.
                tools[name] = tools.get(name, 0) + 1
            if not wrote:
                if name in WRITE_TOOLS:
                    wrote = True
                else:
                    before_write += 1
    if not messages:
        raise TranscriptError('no assistant record — nothing to sum')
    summary = {
        'model': models[0] if len(models) == 1 else (models or None),
        'messages': messages,
        'tool_calls': tool_calls,
        'tools': tools,
        'tool_calls_before_first_write': before_write if wrote else tool_calls,
        'usage': usage,
    }
    if first_ts:
        start, end = parse_ts(first_ts), parse_ts(last_ts)
        summary['started_at'] = first_ts
        summary['ended_at'] = last_ts
        summary['duration_s'] = int((end - start).total_seconds())
    return summary


def id_from_records(records: Iterable[tuple[int, dict]], key: str) -> str:
    """The first non-empty `sessionId`/`agentId` a transcript states, or ''.

    Second to the caller's flag, always: the hook payload names the ids
    authoritatively and the transcript is a fallback for a hand run. Absent in
    both is '' — the row simply has no such key (a main-session transcript
    carries no `agentId`, and stamping one would be an invention).
    """
    for _, record in records:
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return ''


def usage_row(kind: str, **fields: object) -> dict:
    """One `dispatch`/`session` row, keys in `ROW_KEYS` order, absences omitted.

    The omission rule is the contract, not a convenience: `None` and `''` mean
    "the source did not say", and a key that is not on the row is the only
    honest way to write that. A ZERO, an empty dict and an empty list all mean
    "the source said none", so all three are KEPT — `tools: {}` is a dispatch
    that called no tool, and `tree.stories_wip: []` is D3's true statement that
    nothing was `wip` when the hook fired.
    """
    fields['kind'] = kind
    fields.setdefault('ts', utc_now())
    unknown = set(fields) - set(ROW_KEYS)
    if unknown:
        raise ValueError(f'not usage-row keys: {" ".join(sorted(unknown))}')
    return {key: fields[key] for key in ROW_KEYS
            if fields.get(key) is not None and fields.get(key) != ''}


# --- where a grain ENDS (D8) --------------------------------------------------
# D8 calls a grain's end its row into a FINISHED state, and `pm ledger show`
# prints a first-row-to-finished-row total only once that row exists.
#
# Finished is the `done` CATEGORY of the grain's own kind, asked of
# `model.category_of` — never a word. This constant used to be `'done'`, named
# rather than read as `cfg.<kind>_states[-1]` so that a `parked` hung off the
# end of a list did not count as finished; that was the right instinct with
# the wrong tool, because a project whose finished word is `shipped` got no
# total at all. The category is what "finished" IS, and the drift rules in
# model.py (D2, D3, D5) ask the same one, so `show`, `report` and the gate
# cannot come to three answers about where a grain ended.
#
# Bugs stopped being the exception. Their machine is `[pm.states.bug]` like
# every other kind's, so the same question answers for them.
GRAIN_BUG = 'bug'


def ends_grain(cfg, grain_kind: str, to_state) -> bool:
    """Does a status row INTO `to_state` finish a grain of this kind?

    One home for the rule, because a report that disagreed with `show` about
    where a grain finished would produce two different durations for one grain
    and no way to tell which was meant. A `to` that is not a string — this
    file is `merge=union` and rows arrive from anywhere — finishes nothing.
    """
    from agentic_sdlc.repo.pm import model
    if not isinstance(to_state, str):
        return False
    return model.category_of(cfg, grain_kind, to_state) == model.DONE_CATEGORY


def total_seconds(cfg, grain_kind: str, status: list) -> int | None:
    """First STATUS row -> terminal STATUS row, or None while still in flight.

    ONE home, shared by `pm ledger show`'s total line and `pm ledger report`'s
    `total_s` column, because one grain must not have two durations depending
    on which verb asked.

    What it measures is STATUS rows and nothing else. A `decision` row and a
    `dispatch` row both NAME a grain — `row_names` says so, and the report
    needs that breadth to attribute spend — but neither MOVES it, so neither
    can bound how long it took. Measuring from the first row that merely
    mentioned the grain billed a decision logged before work started: on this
    repo's own tree `0.23.0/ledger` totalled 4222s against 1799s of measured
    status time, a number its own state columns contradicted (R3).

    Two rows, or nothing. A grain whose first status row IS its terminal one
    has an instant and no duration, and the `0` a subtraction produces there
    reads as "finished in no time at all" — a measurement nobody made, in the
    one column a reader compares grains by. A stamp that will not parse
    contributes no arithmetic for the same reason: a fabricated interval is
    worse than a missing one.
    """
    if not status or not ends_grain(cfg, grain_kind, status[-1].data.get('to')):
        return None
    first, last = status[0], status[-1]
    if first is last:
        return None
    start, end = parse_ts(first.data.get('ts')), parse_ts(last.data.get('ts'))
    if start is None or end is None:
        return None
    return int((end - start).total_seconds())

def row_names(row: dict, names: set[str]) -> bool:
    """True when this row names the grain — in `grain`, or anywhere in `tree`.

    Both, because the two row families name a grain differently: a status row
    IS about one grain, and a dispatch row (D3) carries every grain that was
    live when the hook fired. An attribution POLICY lives above this — the
    report decides which snapshot bucket attributes a dispatch to which kind of
    grain — and the question here is only "does this row mention it". One home,
    because `pm ledger show` and `pm ledger report` both answer "which rows are
    this grain's" and two answers would give one grain two timelines.

    Every value is TYPE-CHECKED before it is matched, and that is not fussiness:
    a grain id is a string, `names` is a set, and `{} in names` raises
    `TypeError` rather than answering False. This file is `merge=union` — rows
    arrive from another branch, another version of this package, and a hand
    edit — so the reader meets shapes it has never emitted. A row this module
    cannot recognise is a row that does not NAME the grain, which is the honest
    answer; a traceback here would take out the whole timeline over one line
    read has already accepted as a JSON object.
    """
    if isinstance(row.get('grain'), str) and row['grain'] in names:
        return True
    tree = row.get('tree')
    if not isinstance(tree, dict):
        return False
    return any(value in names for ids in tree.values()
               if isinstance(ids, list) for value in ids
               if isinstance(value, str))


def read_rows(path: Path) -> list[Row]:
    """Every row in one ledger, oldest first. An absent ledger is no rows.

    Absent is not an error: a milestone nothing has happened in yet has no
    file, and "no rows" is the same fact the reader wanted. A line that will
    not parse IS an error, named by line number — a reader that skipped it
    would print a timeline with a hole in it and no way to know.
    """
    try:
        raw = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as err:
        raise LedgerError(f'{path} could not be read ({err})') from err
    rows = []
    for lineno, line in enumerate(raw.split('\n'), 1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except ValueError as err:
            raise LedgerError(f'line {lineno} of {path} is not JSON '
                              f'({err})') from err
        if not isinstance(data, dict):
            raise LedgerError(f'line {lineno} of {path} is a '
                              f'{type(data).__name__}, not a row')
        rows.append(Row(lineno, data, line))
    return rows
