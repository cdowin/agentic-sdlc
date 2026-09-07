"""cache.py — what a rung remembers, and the TREE STATE it remembers it against.

A run whose digest is byte-identical to a recorded one reports that verdict
rather than buying the answer again — which is hard rule 4's first cardinal sin
(a gate that missed drift and printed PASS) if it is ever wrong or ever quiet.
So: the digest covers UNTRACKED files, hashing the CONTENT of every path
`git ls-files --cached --others --exclude-standard` names, plus HEAD; a reuse
is always printed (`reuse_lines`); a malformed, missing or unreadable row
answers `None`, which means run the target; and a state over 0 files is refused.

NOT in the digest: ignored files, and the ledgers. Both are what a gate WRITES
while it runs, so a state covering them could never repeat. The run's own
leavings are not evidence about the run's input; the rest of the checkout is.
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
# by the older spelling can match a state computed by the newer one.
STATE_ALGO = 'sha256'
STATE_TAG = b'agentic-sdlc/verify-state/v1'
STATE_SHOWN = 12          # of the digest, in a line a human reads

GIT_TIMEOUT_S = 120
READ_CHUNK = 1 << 16

# What a path contributes when it is not a plain readable file; distinct, so
# no digest can miss the move between two of them.
MARK_ABSENT = b'absent'
MARK_LINK = b'link:'
MARK_DIR = b'dir'
MARK_EXEC = b'x'
MARK_PLAIN = b'-'
SEP = b'\x00'

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
    excluded = _excluded(root)
    seen = 0
    for raw in sorted({part for part in listing.split(SEP) if part}):
        path = root / os.fsdecode(raw)
        if excluded(path):
            continue
        _field(digest, raw, _content_of(path))
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


def _content_of(path: Path) -> bytes:
    """What one path contributes: the executable bit and the digest of its
    bytes, or the marker for a path that is not a plain file."""
    try:
        if path.is_symlink():
            # The TARGET: a link repointed is a change even when both files are.
            return MARK_LINK + os.fsencode(os.readlink(path))
        if path.is_dir():
            # A submodule: one path in `ls-files`, another checkout's state.
            return MARK_DIR
        mode = MARK_EXEC if os.access(path, os.X_OK) else MARK_PLAIN
        inner = hashlib.new(STATE_ALGO)
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(READ_CHUNK), b''):
                inner.update(chunk)
    except OSError:
        # Gone, or unreadable: both are states, and both move when it returns.
        return MARK_ABSENT
    return mode + inner.digest()


def _excluded(root: Path):
    """A predicate naming what the digest leaves out: the ledgers, where the
    gate FILES what it cost. An unreadable PM config excludes nothing, and then
    the row the run appends moves the state — failing towards re-running."""
    try:
        from agentic_sdlc.repo.pm import model
        cfg = model.load()
        roadmap, pool = cfg.roadmap, ledger.ledgers_dir(cfg)
    except Exception:  # noqa: BLE001 - no PM tree, no exclusion, no reuse
        return lambda path: False

    def excluded(path: Path) -> bool:
        if path.name == ledger.LEDGER_FILE_NAME and _under(path, roadmap):
            return True
        return _under(path, pool)

    return excluded


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


# --- the record ---------------------------------------------------------------
def ledger_file(root: Path) -> Path | None:
    """The ledger a verdict row lands in — the TREE's, the file `verify --plan`
    reads its costs from. None means no record and no reuse."""
    try:
        from agentic_sdlc.repo.pm import model
        return ledger.grainless_path(model.load().roadmap)
    except Exception:  # noqa: BLE001 - every failure means the same: no record
        return None


def recorded(root: Path, gate: str, state: str) -> Verdict | None:
    """The LAST verdict recorded for this make target over this exact tree
    state, or None — which always means *run the target*. Keyed on the TARGET,
    because what ran is what was proven; the row says which rung bought it."""
    path = ledger_file(root)
    if path is None or not state:
        return None
    try:
        raw = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    found: Verdict | None = None
    for line in raw.splitlines():
        row = _row(line)
        if row is None or row.get('kind') != ledger.KIND_VERIFY:
            continue
        got = _verdict(row)
        if got is not None and got.gate == gate and got.state == state:
            found = got
    return found


def record(root: Path, rung: str, gate: str, state: State, verdict: str,
           exit_code: int, duration_ms: int, census: int | None) -> str:
    """Append this run's verdict; '' when the row landed, else why it did not.
    The caller's exit code never moves for it: an unwritable ledger is a thing
    to SAY, not a reason to call a green run red."""
    path = ledger_file(root)
    if path is None:
        return ('this tree has no PM config, so there is nowhere to record the '
                'verdict — the next run pays for the same answer again')
    try:
        ledger.append_to(path, ledger.verify_row(
            rung=rung, gate=gate, verdict=verdict, state=state.digest,
            duration_ms=duration_ms, exit_code=exit_code, census=census))
    except (OSError, ValueError) as err:
        return f'the verdict could not be recorded in {path} ({err})'
    return ''


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
    for name in ('exit_code', 'duration_ms'):
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
# Joins the `[verify:check]` family, and both lines carry it: one grep finds
# every run that did not pay (rule 6).
CACHE_TAG = '[verify:cache]'


def reuse_lines(found: Verdict, command: str, state: State,
                now: datetime | None = None) -> list[str]:
    """What a reuse prints: the run it came from, its age, its census and its
    cost, then the state that made it reusable and the flag that refuses it.
    Never abbreviated, never conditional."""
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
    ]
