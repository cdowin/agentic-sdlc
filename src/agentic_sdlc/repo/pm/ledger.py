"""ledger.py — the milestone's append-only row log (`ledger.jsonl`).

One compact JSON object per line beside `decisions.md` (D6); `append_row`
never rewrites a byte already there, so `merge=union` joins branches. A
timestamp is full UTC ISO-8601 at second resolution, `Z`-suffixed (D8).
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from agentic_sdlc.core import apply
from agentic_sdlc.repo import gates_extra

if TYPE_CHECKING:  # the arrival's own vocabulary; nothing is imported at run
    from agentic_sdlc.repo.pm.arrive import Capability, Next, Said

# Inside the milestone directory, so `retire` removes it with the directory and
# git is the archive (D6).
LEDGER_FILE_NAME = 'ledger.jsonl'

# The row kinds minted here; `dispatch`/`session` rows come from `pm ledger
# record`. `STORIES_IN_PROGRESS` is the snapshot bucket a row's live stories sit
# in, named here because THREE modules reach for it — one writes it, one
# resolves off it, one attributes by it.
STORIES_IN_PROGRESS = 'stories_in_progress'

KIND_STATUS = 'status'
KIND_DECISION = 'decision'
KIND_GATE = 'gate'

# THE DURABLE ROW'S OWN THREE FIELDS, spelled once: every shape below stamps
# them and every reader keys on them. `lessons.FIELDS` spelled the stamp `at`
# while the readers keyed `ts`, and those rows sorted to the beginning of time.
TS_FIELD = 'ts'
KIND_FIELD = 'kind'
GRAIN_FIELD = 'grain'

# Stated rather than inherited: `isoformat()` spells the offset `+00:00`, a
# second spelling of one instant.
TS_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# U+2028/U+2029 are line terminators to `splitlines()` and `ensure_ascii=False`
# writes them raw, so they are escaped to keep one row one line.
LINE_BREAKERS = {'\u2028': '\\u2028', '\u2029': '\\u2029'}


def dumps(row: dict) -> str:
    """ONE row as ONE line — the whole serialisation contract, in one place."""
    line = json.dumps(row, separators=(',', ':'), ensure_ascii=False)
    for char, escaped in LINE_BREAKERS.items():
        line = line.replace(char, escaped)
    return line


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(TS_FORMAT)


def status_row(grain_id: str, frm: str, to: str, ts: str = '') -> dict:
    """One status TRANSITION — `cli._arrived` asks whether there was one, a
    `from == to` row being an arrival that did not happen."""
    return {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_STATUS,
            GRAIN_FIELD: grain_id,
            'from': frm, 'to': to}


def decision_row(grain_id: str, entry: str, title: str, ts: str = '') -> dict:
    """One decision heading, as `pm decide` stamped it into `decisions.md`."""
    return {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_DECISION,
            GRAIN_FIELD: grain_id,
            'entry': entry, 'title': title}


# --- the arrival: its disposition, and the row it leaves (0.5.0/D3, D6) -------
# ONE row per arrival, and a skipped check is a FIELD on it, because a
# `close feature --skip review-recorded "…"` is one thing happening: the grain
# arrived at `done`, and this is how its question was answered (0.5.0/D6).
KIND_DISPOSITION = 'disposition'
DISPOSITION_KEYS = (TS_FIELD, KIND_FIELD, GRAIN_FIELD, 'state', 'answer',
                    'value',
                    'skipped')
SKIPPED_KEYS = ('check', 'why')

# --- the three taps a belt emits, and the schema `install-sdlc` renders -------
# `<rung|check>.<tap>`: the last dotted segment is the TAP `check pm`'s U3
# counts off `emit.TAPS`, so a kind that does not spell its tap makes U3 noisy
# rather than blind. `pm/ready_for.py` mints the first and `conveyor/driver.py`
# the second; the KEYS live here with `rung.leave`'s because ONE table is
# rendered, and `tests/test_pm_ledger.py` binds it to all three minters.
KIND_ENTER = 'rung.enter'
KIND_VERDICT = 'check.verdict'
KIND_LEAVE = 'rung.leave'

# A FIELD NAME — "was the entry condition met" — spelled once because it
# collides with a state word, beside the two words its readers render it as.
READY_FIELD = 'ready'
READY, NOT_READY = 'READY', 'NOT READY'
ENTER_KEYS = (TS_FIELD, KIND_FIELD, GRAIN_FIELD, 'rung', READY_FIELD,
              'blockers')
VERDICT_KEYS = (TS_FIELD, KIND_FIELD, 'rung', GRAIN_FIELD, 'check', 'verdict',
                'detail',
                'ran')
# `next_rung` is the belt that runs NEXT; the other two kinds put the rung that
# RAN in `rung`, and one word meaning two things in one rendered table joins a
# story's leave to a feature's verdicts (D6). `value` is LAST and unpaired: `leave_row` zips nine values against these ten
# keys, so an answer that carried none leaves an absent key rather than a `''`.
LEAVE_KEYS = (TS_FIELD, KIND_FIELD, GRAIN_FIELD, 'state', 'answer',
              'next_rung',
              'next_checks', 'next_actions', 'have', 'value')
EVENT_KEYS = {KIND_ENTER: ENTER_KEYS, KIND_VERDICT: VERDICT_KEYS,
              KIND_LEAVE: LEAVE_KEYS}

# What the row says when nobody answered. It cannot collide with a declared
# answer, because `vocabulary._arrive_node_defect` refuses one that does not open
# with `--`. A bare move still writes, and is never invisible.
NO_DISPOSITION = 'none'


def disposition_row(grain_id: str, state: str, said: Said,
                    skipped: Sequence[tuple[str, str]] = (),
                    ts: str = '') -> dict:
    """One arrival: the STATE reached, the answer given, and every check the
    caller answered with `--skip` instead of the belt asking it. No `from` —
    direction is not modelled (D3), and time in a state is the gap between two
    arrivals. `answer` is always present, `none` included, so "nobody
    answered" and "a row written before this shipped" stay two facts; `why` is
    validated HERE, as `deviation_row` validates its reason, so no path can
    mint a skip without one.
    """
    row = {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_DISPOSITION,
           GRAIN_FIELD: grain_id, 'state': state, 'answer': said.answer}
    if said.value:
        row['value'] = said.value
    answered = []
    for check, why in skipped:
        defect = reason_defect(why)
        if defect:
            raise ValueError(f'refusing to mint a {KIND_DISPOSITION} row for '
                             f'{check!r}: {defect}')
        answered.append(dict(zip(SKIPPED_KEYS, (check, why))))
    if answered:
        row['skipped'] = answered
    return row


def leave_row(grain_id: str, state: str, nxt: Next | None,
              have: Sequence[Capability], said: Said,
              ts: str = '') -> dict:
    """The `rung.leave` payload: the same next-step facts the printed
    breadcrumb states, from `arrive.derive_next` — the one derivation. A fact
    this row wants and the printed line lacks belongs there, not here."""
    row = dict(zip(LEAVE_KEYS, (
        ts or utc_now(), KIND_LEAVE, grain_id, state, said.answer,
        nxt.belt if nxt else '',
        list(nxt.checks) if nxt else [],
        [nxt.action] if nxt else [],
        [{'path': c.path, 'why': c.why, 'installed': c.installed}
         for c in have])))
    if said.value:
        row['value'] = said.value
    return row


# --- the lesson row (0.5.0/D1) ------------------------------------------------
# CAPTURE, and only capture: the grain it came from, the rule it is about, and
# the record it was derived from. The row POINTS at its source and never
# restates it — a paraphrase of the record is a second scoreboard — and
# nothing here ranks, scores or infers (rule 9).
KIND_LESSON = 'lesson'
LESSON_KEYS = (TS_FIELD, KIND_FIELD, GRAIN_FIELD, 'rule', 'source', 'text')


def lesson_row(grain_id: str, rule: str, source: str, text: str,
               ts: str = '') -> dict:
    """One recorded lesson. Every field is refused rather than defaulted: a
    lesson naming no grain and no rule surfaces nowhere, and one naming no
    source is the paraphrase this row exists not to be. `text` is graded like
    a deviation's reason — one line, bounded, and it must say something."""
    for name, value in ((GRAIN_FIELD, grain_id), ('rule', rule),
                        ('source', source)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f'refusing to mint a {KIND_LESSON} row: {name} is {value!r}, '
                f'and a lesson nothing can be keyed on surfaces nowhere')
    defect = reason_defect(text)
    if defect:
        raise ValueError(f'refusing to mint a {KIND_LESSON} row against '
                         f'{rule!r}: {defect}')
    return dict(zip(LESSON_KEYS, (ts or utc_now(), KIND_LESSON, grain_id,
                                  rule, source, text)))


# --- the retire row -----------------------------------------------------------
# WHAT OUTLIVES THE DOCUMENTS. `pm retire` removes a milestone's whole grain
# family and `order` keeps its id and nothing else. Here rather than in `order`
# because a retire is an EVENT and this is the event log, the one file `retire`
# does not touch (0.4.0/D3; `bg-retire-drops-the-summary-it-accepts` weighs the
# alternatives).
KIND_RETIRE = 'retire'

# The three fields the tree has no other copy of once the documents are gone.
RETIRE_FIELDS = ('version', 'name', 'summary')


def retire_row(grain_id: str, version: str = '', name: str = '',
               summary: str = '', ts: str = '') -> dict:
    """One retirement. An empty field is an ABSENT KEY, never `''`, so a
    reader can tell "never recorded" from "recorded empty"."""
    row = {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_RETIRE,
           GRAIN_FIELD: grain_id}
    for key, value in zip(RETIRE_FIELDS, (version, name, summary)):
        if value:
            row[key] = value
    return row


def retired_releases(cfg) -> dict[str, dict]:
    """{milestone id: its last retire row} from the tree's grainless ledger.
    LAST wins: a milestone retired twice has two rows and the newer is what
    the plan should print. A ledger that will not parse raises `LedgerError` —
    answering "nothing was retired" over a damaged file is rule 4's first sin.
    """
    out: dict[str, dict] = {}
    for row in read_rows(grainless_path(cfg.roadmap)):
        gid = row.data.get(GRAIN_FIELD)
        if row.data.get(KIND_FIELD) == KIND_RETIRE and isinstance(gid,
                                                                  str) and gid:
            out[gid] = row.data
    return out


# --- the gate row -------------------------------------------------------------
# A gate run is not work somebody was dispatched to do, so it is neither a
# grain row nor a usage row. The name grammar comes from `[gates] extra`
# because the report and the story belt join on this string.
GATE_NAME = gates_extra.TARGET
GATE_NAME_MAX = gates_extra.MAX_LENGTH

# Closed: what a caller can know from an exit code, and "did not run" must not
# read as PASS.
GATE_VERDICTS = ('PASS', 'FAIL', 'HANG', 'SKIP')


def gate_row(gate: str, verdict: str, duration_ms: int | None,
             census: int | None = None, ts: str = '') -> dict:
    """One gate run, costed in whole milliseconds — most gates finish inside a
    second. An absent `census` is an absent key; nothing here judges."""
    row = {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_GATE, 'gate': gate,
           'verdict': verdict}
    for key, value in (('duration_ms', duration_ms), ('census', census)):
        if value is not None:
            row[key] = value
    return row


# --- the verify row -----------------------------------------------------------
# A `gate` row says what a TARGET cost; this says what a RUNG decided and the
# TREE STATE it decided over, so a run over a byte-identical tree can report the
# verdict instead of paying for it again. Its own kind, BESIDE the cost: every
# reader of `gate` rows takes the LAST row per gate name, and `check budget`
# grades a tier on exactly that row.
KIND_VERIFY = 'verify'

# Narrower than `GATE_VERDICTS`: a rung either ran its target to an exit code or
# recorded nothing. `HANG`/`SKIP` are what a wrapper says about a run it could
# not grade, and none of those may be reused as an answer.
VERIFY_VERDICTS = ('PASS', 'FAIL')


def verify_row(rung: str, gate: str, verdict: str, state: str,
               duration_ms: int, exit_code: int, graded: str,
               census: int | None = None, ts: str = '') -> dict:
    """One rung's verdict against the tree state it ran on; `state` is the
    digest that makes the row reusable or not. Every field is refused rather
    than defaulted: a half-built row is one its reader must then distrust.
    `graded` digests the rows `check budget` grades as the ledger held them
    when this verdict was recorded — the one input a tree state CANNOT carry,
    because the run being graded is the run that writes them.
    """
    if verdict not in VERIFY_VERDICTS:
        raise ValueError(f'refusing to mint a {KIND_VERIFY} row for {rung!r}: '
                         f'{verdict!r} is not one of {VERIFY_VERDICTS}')
    for name, value in (('rung', rung), ('gate', gate), ('state', state),
                        ('graded', graded)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'refusing to mint a {KIND_VERIFY} row: {name} is '
                             f'{value!r}, and a verdict nothing can be keyed on '
                             f'is a verdict nothing may reuse')
    for name, value in (('duration_ms', duration_ms), ('exit_code', exit_code)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f'refusing to mint a {KIND_VERIFY} row for '
                             f'{rung!r}: {name} is {value!r}, which is not a '
                             f'whole number')
    # PASS and exit 0 are one fact spelled twice, and a row where they
    # disagree is the shape of rule 4's first sin.
    if (verdict == VERIFY_VERDICTS[0]) != (exit_code == 0):
        raise ValueError(f'refusing to mint a {KIND_VERIFY} row for {rung!r}: '
                         f'{verdict} with exit code {exit_code} — a verdict and '
                         f'an exit code that disagree cannot both be reported')
    row = {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_VERIFY, 'rung': rung,
           'gate': gate, 'verdict': verdict, 'exit_code': exit_code,
           'duration_ms': duration_ms, 'state': state, 'graded': graded}
    # Absent, never 0: a `0` census is the zero-file scan hard rule 4 names.
    if census is not None:
        row['census'] = census
    return row


# --- the deviation row --------------------------------------------------------
# Only DEVIATIONS are rows: the ledger is tracked, so a row per completed step
# would dirty the tree after `tree-clean`. `test` is that economy one level
# down — the `gate` row says what a tier cost, this says which case did, and
# only the slowest few are filed.
KIND_TEST = 'test'

KIND_DEVIATION = 'deviation'

# Closed; `'skipped'` stays because rows carrying it are already in consumer
# ledgers.
OUTCOMES = ('not-true', 'unverifiable', 'skipped', 'forced')

# A durable log is not a paste buffer; the reason is the only free-text field.
REASON_MAX = 1024


def reason_defect(reason: object) -> str:
    """'' when `reason` may be a deviation's reason, else why not."""
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
    # U+2028/U+2029 are escaped by `LINE_BREAKERS`; `\n`, `\r` and `\x00` have
    # no escape here and one row is one line.
    for char, spelling in (('\n', r'\n'), ('\r', r'\r'), ('\x00', r'\x00')):
        if char in reason:
            return f'a reason carrying {spelling} would not be one row'
    return ''


def test_row(tier: str, nodeid: str, duration_ms: int, rank: int,
             ts: str = '') -> dict:
    """One slow test; `rank` 1 is the slowest of that run."""
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
    return {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_TEST, 'tier': tier,
            'nodeid': nodeid, 'duration_ms': duration_ms, 'rank': rank}


def deviation_row(grain_id: str, operation: str, step: str, reason: str,
                  ts: str = '', outcome: str = 'not-true') -> dict:
    """One step of a conveyor run that did not come out true, and why; `reason`
    is validated HERE, so no path can mint a row without one."""
    defect = reason_defect(reason)
    if defect:
        raise ValueError(f'refusing to mint a {KIND_DEVIATION} row for '
                         f'{step!r}: {defect}')
    if outcome not in OUTCOMES:
        raise ValueError(f'refusing to mint a {KIND_DEVIATION} row for '
                         f'{step!r}: {outcome!r} is not one of {OUTCOMES}')
    return {TS_FIELD: ts or utc_now(), KIND_FIELD: KIND_DEVIATION,
            GRAIN_FIELD: grain_id,
            'operation': operation, 'step': step, 'outcome': outcome,
            'reason': reason}


def ledger_path(milestone_dir: Path) -> Path:
    """Where one milestone's ledger lives. The only place this name is joined."""
    return milestone_dir / LEDGER_FILE_NAME


# The pool the ledgers live in once a tree is migrated: milestone-scoped
# machine state is not a grain, so it gets a table of its own named by the same
# mechanism as the others (0.4.0/the-pools-are-the-tables).
LEDGERS_POOL = 'ledgers'


def ledgers_dir(cfg) -> Path:
    """The table the ledgers live in — `[pm] ledger_dir`, or
    `<roadmap>/ledgers`, always relative to the repo root."""
    return (cfg.root / cfg.ledger_dir_key if cfg.ledger_dir_key
            else cfg.roadmap / LEDGERS_POOL)


def ledger_for(cfg, milestone_id: str) -> Path:
    """The ledger of one milestone, in EITHER layout — pooled
    (`<ledger_dir>/<milestone-id>.jsonl`) or nested (inside the milestone's
    own directory). One function, because a reader that guessed would find the
    rows in one layout and silently none in the other.
    """
    from agentic_sdlc.repo.pm import inventory
    if inventory.is_pooled(cfg):
        return ledgers_dir(cfg) / f'{milestone_id}.jsonl'
    mdir = inventory.milestone_dir(cfg, milestone_id)
    return ledger_path(mdir) if mdir is not None else grainless_path(cfg.roadmap)


def ledger_of_grain(cfg, gid: str) -> Path | None:
    """The ledger a row naming `gid` belongs in, followed through the grain's
    BINDINGS — a story to its feature to its milestone (D1). None when the
    grain names no milestone, or when the caller named no grain. The ONE
    answer to "where does this row go": the lookup 0.4.0 retired asked which
    milestone was `in_progress` and lost every row a planning tree wrote.
    """
    from agentic_sdlc.repo.pm import inventory
    mid = inventory.milestone_of(cfg, gid) if gid else ''
    return ledger_for(cfg, mid) if mid else None


def grainless_dir(roadmap_dir: Path) -> Path:
    """The DIRECTORY whose ledger holds every row that names no grain
    (0.4.0/D3) — the roadmap root. It returns its argument, and that is the
    point: WHICH directory is the grainless home is a decision, and it was
    restated at five call sites."""
    return roadmap_dir


def grainless_path(roadmap_dir: Path) -> Path:
    """The grainless ledger itself — `grainless_dir` joined by `ledger_path`.
    What `check budget`, `verify --plan` and `pm ledger report|show` read."""
    return ledger_path(grainless_dir(roadmap_dir))


def ledger_paths(cfg) -> list[Path]:
    """BOTH homes (0.4.0/D3), deduplicated: the tree's own ledger and one per
    milestone — the walk every reader of "every row" takes, and here because
    `conveyor/lessons.py` and `checks/pm.py` were two more spellings of it."""
    from agentic_sdlc.repo.pm import inventory
    found = [grainless_path(cfg.roadmap)]
    found += [ledger_for(cfg, g.gid) for g in inventory.milestones(cfg)]
    return list(dict.fromkeys(found))


def append_to(path: Path, row: dict) -> None:
    """Append one row to a ledger FILE, creating the file and the pool it sits
    in. `open('a')` rather than a `core.apply` overwrite, because
    read-modify-write drops rows under two appenders; a newline closes a torn
    tail first. Raises `OSError`: the caller has already changed the tree."""
    apply.raise_on_error(apply.make_dir(path.parent))
    line = dumps(row) + '\n'
    if _ends_mid_line(path):
        line = '\n' + line
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(line)


def append_row(milestone_dir: Path, row: dict) -> None:
    """`append_to`, addressed by DIRECTORY — what a nested tree gave every
    caller, and what the grainless home still is."""
    append_to(ledger_path(milestone_dir), row)


def _ends_mid_line(path: Path) -> bool:
    r"""True when the file's last byte is not `\n`; an unreadable file answers
    False so the append itself raises."""
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
# orchestrator's totals at one stop. Copy what the transcript holds, omit what
# it lacks, invent nothing — and refuse a transcript this module cannot read,
# because a row of zeros reads like a cheap dispatch.
KIND_DISPATCH = 'dispatch'
KIND_SESSION = 'session'

# The kind is the hook event's, never inferred from the transcript's shape.
EVENT_KINDS = {'SubagentStop': KIND_DISPATCH, 'Stop': KIND_SESSION}

# The tools whose use means the agent started writing; the count before the
# first is raw, never a ratio.
WRITE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')

# Row key <- `message.usage` key; other usage keys are ignored, not copied.
USAGE_FIELDS = (('input', 'input_tokens'),
                ('output', 'output_tokens'),
                ('cache_creation', 'cache_creation_input_tokens'),
                ('cache_read', 'cache_read_input_tokens'))

# Named so the coupling to the transcript shape is greppable in one place.
TYPE_ASSISTANT = 'assistant'
TYPE_TOOL_USE = 'tool_use'

# Not a model: an API-error notice the harness generated itself, with all-zero
# usage. The exact token, not the `<…>` shape, so an unknown pseudo-name comes
# through raw and gets decided.
SYNTHETIC_MODEL = '<synthetic>'

# A hand-recorded ONE TOTAL, beside `usage`'s measured split. Two keys because
# they are two measurements: a caller who was told "1234 tokens" cannot say
# which way they split, and a reader must be able to tell the two apart rather
# than see a guess.
TOTAL_KEY = 'tokens_total'

# Every key a usage row may carry, in order.
ROW_KEYS = (TS_FIELD, KIND_FIELD, GRAIN_FIELD, 'session_id', 'agent_id',
            'agent_type',
            'model', 'started_at', 'ended_at', 'duration_s', 'messages',
            'tool_calls', 'tools', 'tool_calls_before_first_write', 'usage',
            TOTAL_KEY, 'tree')


class TranscriptError(Exception):
    """A transcript this module cannot READ. Never a judgement about content."""


class LedgerError(Exception):
    """A line already in the ledger that will not parse. Names the line."""


class Row(NamedTuple):
    """One ledger line; the raw `line` is kept so `--json` prints the bytes on
    disk, unknown keys intact."""
    lineno: int
    data: dict
    line: str


def normalise_ts(raw: object, where: str) -> str:
    """A transcript timestamp as this ledger spells one. Fractions are
    truncated, not rounded, so `ended_at` cannot land after the stop that
    recorded it; an unparseable one raises."""
    if not isinstance(raw, str) or not raw:
        raise TranscriptError(f'{where} has no timestamp ({raw!r})')
    try:
        when = datetime.fromisoformat(raw)
    except ValueError as err:
        raise TranscriptError(f'{where} timestamp {raw!r} is not ISO-8601 '
                              f'({err})') from err
    if when.tzinfo is None:
        # A naive stamp is UTC by the transcript's convention; reading it as
        # local would shift every duration.
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
    """A count from the transcript, or a loud refusal; absent is 0 (adding
    nothing), present-and-not-an-int is a shape change. `bool` is excluded —
    `True` would sum as 1."""
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise TranscriptError(f'{where} is {value!r}, which is not a number')
    return value


def records_of(path: Path) -> Iterator[tuple[int, dict]]:
    """(line number, record) for every line of a transcript, in file order.
    Read through the handle rather than `splitlines()`, so U+2028 cannot tear a
    row; a line that is not a JSON object raises `TranscriptError`."""
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
    """Sum one transcript into the fields a usage row carries, in one pass.
    `tool_calls_before_first_write` is the TOTAL when it never wrote; `model`
    is first-seen order, a list when it switched, `SYNTHETIC_MODEL` dropped as
    a spelling. A file with no assistant record raises."""
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
                # A block with no `name` still counts as a call, but
                # `tools[None]` would name something the transcript did not.
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
    """The first non-empty `sessionId`/`agentId` a transcript states, or '' —
    second to the caller's flag, and absent in both is no key."""
    for _, record in records:
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return ''


def usage_row(kind: str, **fields: object) -> dict:
    """One `dispatch`/`session` row. `None` and `''` mean "the source did not
    say" and are omitted; `0`, `{}` and `[]` mean "the source said none" and
    are kept. `tree` carries the category keys and the frozen ones (D7)."""
    fields[KIND_FIELD] = kind
    fields.setdefault(TS_FIELD, utc_now())
    unknown = set(fields) - set(ROW_KEYS)
    if unknown:
        raise ValueError(f'not usage-row keys: {" ".join(sorted(unknown))}')
    return {key: fields[key] for key in ROW_KEYS
            if fields.get(key) is not None and fields.get(key) != ''}


# --- where a grain ENDS (D8) --------------------------------------------------
# Finished is the `done` category of the grain's own kind, asked of
# `vocabulary.category_of` — the question the drift rules ask, so `show`, `report`
# and the gate agree on where a grain ended; the kind WORDS live in
# `vocabulary`.


def ends_grain(cfg, grain_kind: str, to_state) -> bool:
    """Does a status row into `to_state` finish a grain of this kind? A `to`
    that is not a string finishes nothing."""
    from agentic_sdlc.repo.pm import vocabulary
    if not isinstance(to_state, str):
        return False
    return vocabulary.category_of(cfg, grain_kind, to_state) == vocabulary.DONE_CATEGORY


def total_seconds(cfg, grain_kind: str, status: list) -> int | None:
    """First status row -> terminal status row, or None while in flight or
    with fewer than two rows. Only status rows bound it — a decision row names
    a grain but does not move it."""
    if not status or not ends_grain(cfg, grain_kind, status[-1].data.get('to')):
        return None
    first, last = status[0], status[-1]
    if first is last:
        return None
    start, end = parse_ts(first.data.get(TS_FIELD)), parse_ts(last.data.get(TS_FIELD))
    if start is None or end is None:
        return None
    return int((end - start).total_seconds())

def open_seconds(cfg, grain_kind: str, status: list,
                 now: datetime | None = None) -> int | None:
    """First status row -> NOW, for a grain that has NOT reached a terminal
    state — the number that creates pressure, which `total_seconds` above
    cannot answer because it answers only the CLOSED question. **A grain with
    no status row is UNMEASURED, never zero** (rule 4): not having been moved
    is a different fact from having been moved a moment ago.
    """
    if not status or ends_grain(cfg, grain_kind, status[-1].data.get('to')):
        return None
    start = parse_ts(status[0].data.get(TS_FIELD))
    if start is None:
        return None
    when = datetime.now(timezone.utc) if now is None else now
    return max(0, int((when - start).total_seconds()))


def human_duration(seconds: int | None) -> str:
    """`3d 4h`, `12m`, `-`. Two units at most: a number a human reads at a
    glance is the point, and `271431s` is not one."""
    if seconds is None:
        return '-'
    units = (('d', 86400), ('h', 3600), ('m', 60), ('s', 1))
    parts = []
    left = seconds
    for name, size in units:
        if left >= size and len(parts) < 2:
            parts.append(f'{left // size}{name}')
            left %= size
    return ' '.join(parts) or '0s'


def row_names(row: dict, names: set[str]) -> bool:
    """True when this row names the grain — in `grain`, or anywhere in `tree`.
    Every value is type-checked first: rows arrive from other branches and
    versions, and an unrecognisable row does not name the grain."""
    if isinstance(row.get(GRAIN_FIELD), str) and row[GRAIN_FIELD] in names:
        return True
    tree = row.get('tree')
    if not isinstance(tree, dict):
        return False
    return any(value in names for ids in tree.values()
               if isinstance(ids, list) for value in ids
               if isinstance(value, str))


def read_rows(path: Path) -> list[Row]:
    """Every row in one ledger, oldest first; an absent ledger is no rows, and
    a line that will not parse is `LedgerError` by line number."""
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
