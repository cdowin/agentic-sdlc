"""cache.py — what a rung remembers, and the TREE STATE it remembers it against.

A run whose digest is byte-identical to a recorded one reports that verdict
rather than buying the answer again — which is hard rule 4's first cardinal sin
(a gate that missed drift and printed PASS) if it is ever wrong or ever quiet.
So: the digest covers UNTRACKED files, hashing the CONTENT of every path
`git ls-files --cached --others --exclude-standard` names, plus HEAD and, for a
submodule, that checkout's own state; a reuse is always printed (`reuse_lines`);
a malformed, missing or unreadable row answers `None`, which means run the
target; and a state over 0 files is refused.

NOT in the digest: ignored files, and the ledger rows a run files about ITSELF
— the wrapper's `gate` cost row, the tier's `test` rows, this module's `verify`
row, the couriers' session rows. A state covering those could never repeat.
Every OTHER row IS in it, line by line (`ledger_digest`): a status, a decision,
a deviation or a row this version cannot parse is a fact about the tree, and
`check pm` grades several of them. Dropping the ledger FILE dropped those too.

Two dropped kinds are graded anyway: `check budget` reads the newest `gate` row
per target and `test` row per tier, inside `make milestone`, which IS the
milestone rung. They cannot be hashed (the run writes them) and they cannot be
forgotten (a reused PASS would stand over a tree whose gate now exits 1), so the
row carries HOW MANY of them the ledger held and a reuse over a ledger that has
grown one refuses. What no state covers at all is said out loud instead, on
every reuse: the third `[verify:cache]` line.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agentic_sdlc.repo.pm import ledger

# The TAG versions the digest's INPUTS: change what goes in and no row written
# by the older spelling can match a state computed by the newer one. v2 reads
# the ledgers' rows and a submodule's checkout, which v1 did not.
STATE_ALGO = 'sha256'
STATE_TAG = b'agentic-sdlc/verify-state/v2'
STATE_SHOWN = 12          # of the digest, in a line a human reads

GIT_TIMEOUT_S = 120
READ_CHUNK = 1 << 16

# What a path contributes when it is not a plain readable file; distinct, so
# no digest can miss the move between two of them.
MARK_ABSENT = b'absent'
MARK_LINK = b'link:'
MARK_SUB = b'sub:'
MARK_ROWS = b'rows:'
MARK_EXEC = b'x'
MARK_PLAIN = b'-'
SEP = b'\x00'

# What `check budget` grades and no digest can carry, because the run that is
# being graded is the run that writes them.
GRADED_KINDS = (ledger.KIND_GATE, ledger.KIND_TEST)

# Every kind a run files about its own execution rather than about the work:
# the two above, this module's verdict row, and the couriers' event rows. A
# ledger's OTHER rows are hashed like any other byte in the tree.
SELF_FILED_KINDS = frozenset({ledger.KIND_VERIFY, *GRADED_KINDS,
                              *ledger.EVENT_KINDS.values()})

LEDGER_SUFFIX = '.jsonl'

PASS, FAIL = ledger.VERIFY_VERDICTS


@dataclass(frozen=True)
class State:
    """The tree a rung is about to gate: one digest, and the census of paths
    it covered — printed, because a scan says how much it looked at."""

    digest: str
    files: int

    def short(self) -> str:
        return self.digest[:STATE_SHOWN]


@dataclass(frozen=True)
class Verdict:
    """One recorded verdict, whole: a row missing a field never becomes one."""

    ts: str
    rung: str
    gate: str
    verdict: str
    exit_code: int
    duration_ms: int
    census: int | None
    state: str
    graded: int

    def age(self, now: datetime | None = None) -> str:
        """How old this verdict is, as `ledger.human_duration` spells one."""
        when = ledger.parse_ts(self.ts)
        if when is None:  # pragma: no cover - `_verdict` refuses such a row
            return '?'
        moment = datetime.now(timezone.utc) if now is None else now
        return ledger.human_duration(max(0, int((moment - when).total_seconds())))


# --- the state ----------------------------------------------------------------
def tree_state(root: Path) -> tuple[State | None, str]:
    """(the state of this working tree, '' | why there is none). HEAD, then
    every path git lists — tracked and untracked, ignored excluded — with its
    content's digest. A question git could not answer is never a hit, and the
    defect is returned to be PRINTED (rule 11).
    """
    return _state_of(root, _is_ledger())


def _state_of(root: Path, is_ledger) -> tuple[State | None, str]:
    """`tree_state`, carrying the ledger predicate — built once and passed down
    into every submodule, so one PM config read serves the whole walk."""
    listing = _git(root, 'ls-files', '-z', '--cached', '--others',
                   '--exclude-standard')
    if listing is None:
        return None, ('git could not list this tree, so there is nothing to '
                      'compare a recorded verdict against')
    digest = hashlib.new(STATE_ALGO)
    digest.update(STATE_TAG)
    # Unborn HEAD is the empty string: a state like any other, and it moves the
    # moment a commit lands.
    head = _git(root, 'rev-parse', 'HEAD')
    _field(digest, b'HEAD', head.strip() if head else b'')
    seen = 0
    for raw in sorted({part for part in listing.split(SEP) if part}):
        path = root / os.fsdecode(raw)
        if is_ledger(path):
            content = _ledger_content(path)
            # A ledger holding nothing but a run's own leavings contributes
            # NOTHING rather than an empty field: the first run CREATES that
            # file, and a state that moved for it could never match the row
            # that run wrote.
            if content is None:
                continue
        else:
            content = _content_of(path, is_ledger)
            if content is None:
                return None, (
                    f'{os.fsdecode(raw)} is a directory git lists — a '
                    f'submodule — whose own checkout git could not state, so '
                    f'this tree cannot be keyed on')
        _field(digest, raw, content)
        seen += 1
    if not seen:
        return None, ('this tree has no files git lists, and a state over 0 '
                      'files would match every other empty scan (hard rule 4)')
    return State(digest=digest.hexdigest(), files=seen), ''


def _git(root: Path, *args: str) -> bytes | None:
    """git's raw stdout, or None when git did not answer. Bytes and not
    `core.project.git_lines`: `-z` output has no lines, and a filename carrying
    a newline must not become two entries."""
    try:
        done = subprocess.run(('git', *args), cwd=str(root),
                              capture_output=True, timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _field(digest, *parts: bytes) -> None:
    """One record in, length-prefixed: no two different tuples of parts may
    serialise to the same bytes."""
    for part in parts:
        digest.update(str(len(part)).encode('ascii') + SEP + part + SEP)


def _content_of(path: Path, is_ledger) -> bytes | None:
    """What one path contributes: the executable bit and the digest of its
    bytes, the marker for a path that is not a plain file, or None when the
    path is a state this cannot characterise at all."""
    try:
        if path.is_symlink():
            # The TARGET: a link repointed is a change even when both files are.
            return MARK_LINK + os.fsencode(os.readlink(path))
        if path.is_dir():
            # A submodule: one path in `ls-files`, another checkout's state —
            # so the digest is that checkout's OWN state, which carries its
            # HEAD and its working tree. A commit rolled back inside it is
            # `M <path>` to the superproject's own `git status`, and a constant
            # here made it invisible.
            inner, _ = _state_of(path, is_ledger)
            return None if inner is None else \
                MARK_SUB + inner.digest.encode('ascii')
        mode = MARK_EXEC if os.access(path, os.X_OK) else MARK_PLAIN
        inner_digest = hashlib.new(STATE_ALGO)
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(READ_CHUNK), b''):
                inner_digest.update(chunk)
    except OSError:
        # Gone, or unreadable: both are states, and both move when it returns.
        return MARK_ABSENT
    return mode + inner_digest.digest()


def _ledger_content(path: Path) -> bytes | None:
    """A ledger's rows minus the ones a run files about itself, None when that
    leaves nothing at all."""
    try:
        raw = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        # Unreadable is a state too, and it moves when the file can be read.
        return MARK_ROWS + MARK_ABSENT
    rows = ledger_digest(raw)
    return None if rows is None else MARK_ROWS + rows


def ledger_digest(raw: str) -> bytes | None:
    """The digest of every line of a ledger this tree's runs did NOT file about
    themselves, or None when there is no such line.

    A line that will not parse, or names a kind this version does not know, is
    KEPT. Only a row provably filed by a run may be dropped: the wrong answer
    here is the one that hides a status flip, and `check pm` grades those.
    """
    digest = hashlib.new(STATE_ALGO)
    kept = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        row = _row(line)
        if row is not None and row.get('kind') in SELF_FILED_KINDS:
            continue
        _field(digest, line.encode('utf-8', 'surrogateescape'))
        kept += 1
    return digest.digest() if kept else None


def _is_ledger():
    """A predicate naming the files whose ROWS the digest reads rather than
    whose bytes it hashes. By file name and extension, never by directory: the
    pool is the consumer-settable `[pm] ledger_dir`, and a directory-wide rule
    pointed at a source tree would take real inputs out of the state."""
    try:
        from agentic_sdlc.repo.pm import model
        cfg = model.load()
        roadmap, pool = cfg.roadmap, ledger.ledgers_dir(cfg)
    except Exception:  # noqa: BLE001 - no PM tree, no ledgers, no exception
        return lambda path: False

    def is_ledger(path: Path) -> bool:
        if path.name == ledger.LEDGER_FILE_NAME and _under(path, roadmap):
            return True
        return path.suffix == LEDGER_SUFFIX and _under(path, pool)

    return is_ledger


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


# --- the record ---------------------------------------------------------------
def ledger_file(root: Path) -> Path | None:
    """The ledger a verdict row lands in — the TREE's, the file `verify --plan`
    and `check budget` read. None means no record and no reuse."""
    try:
        from agentic_sdlc.repo.pm import model
        return ledger.grainless_path(model.load().roadmap)
    except Exception:  # noqa: BLE001 - every failure means the same: no record
        return None


def recorded(root: Path, gate: str, state: str) -> tuple[Verdict | None,
                                                         int | None]:
    """(the LAST verdict recorded for this make target over this exact tree
    state, how many rows `check budget` grades this ledger holds NOW).

    One pass, because both answers are the same file. The verdict is keyed on
    the TARGET, because what ran is what was proven; the row says which rung
    bought it. `None` for either always means *run the target*.
    """
    path = ledger_file(root)
    if path is None or not state:
        return None, None
    try:
        raw = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None, None
    found: Verdict | None = None
    graded = 0
    for line in raw.splitlines():
        row = _row(line)
        if row is None:
            continue
        kind = row.get('kind')
        if kind in GRADED_KINDS:
            graded += 1
        elif kind == ledger.KIND_VERIFY:
            got = _verdict(row)
            if got is not None and got.gate == gate and got.state == state:
                found = got
    return found, graded


def record(root: Path, rung: str, gate: str, state: State, verdict: str,
           exit_code: int, duration_ms: int, census: int | None) -> str:
    """Append this run's verdict; '' when the row landed, else why it did not.
    The caller's exit code never moves for it: an unwritable ledger is a thing
    to SAY, not a reason to call a green run red."""
    path = ledger_file(root)
    if path is None:
        return ('this tree has no PM config, so there is nowhere to record the '
                'verdict — the next run pays for the same answer again')
    if not path.parent.is_dir():
        # `append_to` would MAKE the roadmap directory, and a verb that runs a
        # make target has no business minting a PM tree in silence (rule 3).
        return (f'{path.parent} is not there, so this verdict is not recorded '
                f'— `verify` does not create a PM tree, and the next run pays '
                f'for the same answer again')
    graded = _graded_in(path)
    if graded is None:
        return (f'{path} could not be read, so how many rows `check budget` '
                f'grades it holds is unknown — and a row that cannot say that '
                f'is a row nothing may reuse')
    try:
        ledger.append_to(path, ledger.verify_row(
            rung=rung, gate=gate, verdict=verdict, state=state.digest,
            duration_ms=duration_ms, exit_code=exit_code, census=census,
            graded=graded))
    except (OSError, ValueError) as err:
        return f'the verdict could not be recorded in {path} ({err})'
    return ''


def _graded_in(path: Path) -> int | None:
    """How many rows `check budget` grades this ledger holds; 0 for a ledger
    that is not there yet, None for one that is and cannot be read."""
    if not path.is_file():
        return 0
    try:
        raw = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    total = 0
    for line in raw.splitlines():
        row = _row(line)
        if row is not None and row.get('kind') in GRADED_KINDS:
            total += 1
    return total


def ledger_size(root: Path) -> int:
    """The ledger's size now, or 0 — the mark a run's own rows come after."""
    path = ledger_file(root)
    try:
        return path.stat().st_size if path is not None else 0
    except OSError:
        return 0


def census_since(root: Path, gate: str, offset: int) -> int | None:
    """The census the GATE itself filed for this target after `offset`, or
    None. Copied rather than counted: `verify` scans no files, and the number a
    reused verdict quotes must be the one that run reported (rule 4)."""
    path = ledger_file(root)
    if path is None:
        return None
    try:
        with path.open('rb') as handle:
            handle.seek(offset)
            tail = handle.read()
    except OSError:
        return None
    census = None
    for line in tail.decode('utf-8', 'replace').splitlines():
        row = _row(line)
        if row is None or row.get('kind') != ledger.KIND_GATE:
            continue
        if row.get('gate') != gate:
            continue
        value = row.get('census')
        if isinstance(value, int) and not isinstance(value, bool):
            census = value
    return census


def _row(line: str) -> dict | None:
    """One ledger line as a row, or None — a line that will not parse is
    stepped over, never fallen on: other tools append here too."""
    line = line.strip()
    if not line:
        return None
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row if isinstance(row, dict) else None


def _verdict(row: dict) -> Verdict | None:
    """A `verify` row as a `Verdict`, or None when ANY field is missing or the
    wrong shape — the whole trust boundary. Rows arrive from other branches,
    versions and hands, and a half-read row that became a PASS is rule 4's
    first sin with a record behind it."""
    if ledger.parse_ts(row.get('ts')) is None:
        return None
    if row.get('verdict') not in ledger.VERIFY_VERDICTS:
        return None
    fields = {}
    for name in ('ts', 'rung', 'gate', 'verdict', 'state'):
        value = row.get(name)
        if not isinstance(value, str) or not value.strip():
            return None
        fields[name] = value
    # `graded` is required, not defaulted: a row from a spelling that did not
    # count what `check budget` grades cannot say whether it may be reused.
    for name in ('exit_code', 'duration_ms', 'graded'):
        value = row.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        fields[name] = value
    census = row.get('census')
    if census is not None and (isinstance(census, bool)
                               or not isinstance(census, int)):
        return None
    # The disagreement `verify_row` refuses to mint, refused again on the way
    # back in: PASS with a failing code cannot be reported as either.
    if (fields['verdict'] == PASS) != (fields['exit_code'] == 0):
        return None
    return Verdict(census=census, **fields)


# --- what a reuse SAYS --------------------------------------------------------
# Joins the `[verify:check]` family, and all three lines carry it: one grep
# finds every run that did not pay (rule 6).
CACHE_TAG = '[verify:cache]'


def reuse_lines(found: Verdict, command: str, state: State,
                now: datetime | None = None) -> list[str]:
    """What a reuse prints: the run it came from, its age, its census and its
    cost; the state that made it reusable and the flag that refuses it; and
    what this read did NOT re-measure. Never abbreviated, never conditional —
    the third line most of all, because a state is a claim about the working
    tree and nothing else."""
    census = f'census {found.census}' if found.census is not None \
        else 'census unknown'
    # `command` names the recorded run honestly: the row was found BY its
    # target and `rules.py` refuses any rung but `make <target>`.
    return [
        f'{CACHE_TAG} REUSED {found.verdict} — recorded {found.ts} '
        f'({found.age(now)} ago) by `verify --{found.rung}`: {command}, '
        f'{census}, {found.duration_ms} ms',
        f'{CACHE_TAG} this tree is byte-identical to that run (state '
        f'{state.short()}, {state.files} files), so `{command}` did NOT run — '
        f'`--no-cache` runs it anyway',
        f'{CACHE_TAG} NOT re-measured: anything outside this working tree — '
        f'the interpreters `make matrix` runs, an installed tool, the '
        f'environment — and the {found.graded} ledger row(s) `check budget` '
        f'grades, of which that run filed the last (one landing SINCE it '
        f'refuses this reuse and runs `{command}`)',
    ]


def stale_line(found: Verdict, graded: int | None, command: str,
               now: datetime | None = None) -> str:
    """Why a verdict recorded against THIS state was not reused: the rows
    `check budget` grades moved under it. Rule 11 — the operator is standing in
    front of a gate that could have been a read, and silence here reads as a
    cache that simply does not work."""
    return (f'{CACHE_TAG} a {found.verdict} is recorded for this exact tree '
            f'state ({found.age(now)} ago) and the ledger now holds '
            f'{"?" if graded is None else graded} row(s) `check budget` grades '
            f'where that run left {found.graded} — it grades the NEWEST one '
            f'per target, and no tree state can carry a row the run itself '
            f'writes, so `{command}` runs')
