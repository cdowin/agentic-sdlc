"""cache.py — what a rung remembers, and the TREE STATE it remembers it against.

A run whose digest is byte-identical to a recorded one reports that verdict
rather than buying the answer again — hard rule 4's first cardinal sin (a gate
that missed drift and printed PASS) if it is ever wrong or ever quiet. So: the
digest hashes the CONTENT of every path `git ls-files --cached --others
--exclude-standard` names, UNTRACKED included, plus HEAD and a submodule's own
checkout; a reuse is always printed; a malformed, missing or unreadable row
answers `None`, which means run the target; a state over 0 files is refused.

Out of the digest: ignored files, and the ledger rows a run files about ITSELF
(`SELF_FILED_KINDS`) — a state covering what a gate writes while it runs could
never repeat. Every OTHER ledger row is IN, line by line (`ledger_digest`):
a status or a decision is a fact about the tree, and dropping the ledger FILE
dropped those too. Two dropped kinds are graded anyway, by `check budget`
inside `make milestone`, so the row carries a DIGEST of them as that run left
them (`graded_of`) and a reuse over rows that moved refuses (`stale_line`).

A rung may be keyed on LESS than the whole tree: `[verify.inputs]` names the
path prefixes its state covers (`story = ["src", "tests"]`), so a status flip
under `pm/` or a doc edit does not re-buy a unit tier that read neither. The
scope is in the digest, so a whole-tree row and a scoped row never match.

Every rung is keyed on the tree MINUS what a belt writes (#95), unless
`[verify] reuse_ignores_status = false`: each grain document's `status:`
frontmatter line and the ledger rows a belt files about its own run
(`MOVE_KINDS`) are left out, so six closes on one commit key on one state,
and `release` asking the gate at `done` matches a run recorded at `building`.
Every other byte under the roadmap stays in, and so does the choice itself.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agentic_sdlc.core import spawn
from agentic_sdlc.repo.pm import ledger
from agentic_sdlc.repo.verify.rules import REUSE_IGNORES_STATUS, SECTION

# The TAG versions the digest's INPUTS: change what goes in and no row written
# by the older spelling can match a newer state. v2 reads a ledger's rows and a
# submodule's checkout; v3 carries the scope the state is taken over; v4
# whether it leaves out what a close writes; v5 leaves out `rung.enter` too.
STATE_ALGO = 'sha256'
STATE_TAG = b'agentic-sdlc/verify-state/v5'
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

# What `check budget` grades and no digest can carry, because the run being
# graded is the run that writes them.
GRADED_KINDS = (ledger.KIND_GATE, ledger.KIND_TEST)

# Every kind a run files about its own execution rather than about the work.
SELF_FILED_KINDS = frozenset({ledger.KIND_VERIFY, *GRADED_KINDS,
                              *ledger.EVENT_KINDS.values()})

# Every kind a BELT files about its own run: the arrival's `status` and
# `disposition`, a forced close's `deviation`, and the `[emit]` events — the
# `rung.enter` a `ready-for` check files, its checks' `check.verdict`, its
# arrival's `rung.leave`. Out of a state taken with `moves_out` only.
MOVE_KINDS = frozenset({ledger.KIND_STATUS, ledger.KIND_DISPOSITION,
                        ledger.KIND_DEVIATION, ledger.KIND_ENTER,
                        ledger.KIND_VERDICT, ledger.KIND_LEAVE})

# The words a reuse line names that state by, the key FIRST (rule 11: the
# operator whose rung reads statuses finds it in a belt's clipped line too).
MOVES_OUT = (f"what a belt writes ([{SECTION}] {REUSE_IGNORES_STATUS} = false "
             f"keys on it): the grain documents' `status:` lines and the "
             f"{', '.join(sorted(MOVE_KINDS))} ledger rows")

LEDGER_SUFFIX = '.jsonl'

PASS, FAIL = ledger.VERIFY_VERDICTS


@dataclass(frozen=True)
class State:
    """The tree a rung is about to gate: one digest, and the census of paths
    it covered — printed, because a scan says how much it looked at."""

    digest: str
    files: int
    scope: tuple[str, ...] = ()
    moves_out: bool = False

    def short(self) -> str:
        return self.digest[:STATE_SHOWN]

    def where(self) -> str:
        """The paths this state covers, for a line a human reads."""
        covered = ' '.join(self.scope) if self.scope else 'the whole tree'
        if self.moves_out:
            covered += f' except {MOVES_OUT}'
        return covered


@dataclass(frozen=True)
class Graded:
    """The rows `check budget` grades, as one comparable value: what no tree
    state can carry, because the run being graded writes them."""

    digest: str
    rows: int


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
    graded: str
    # Everything a static gate printed, its PASS line in it; '' for a rung
    # (#98).
    said: str = ''
    # Every path the gate probed, as (mode, path, what it saw); None for a
    # row that filed none — which a static gate's reuse refuses (review F1).
    probed: tuple[tuple[str, str, str], ...] | None = None

    def age(self, now: datetime | None = None) -> str:
        """How old this verdict is, as `ledger.human_duration` spells one."""
        when = ledger.parse_ts(self.ts)
        if when is None:  # pragma: no cover - `_verdict` refuses such a row
            return '?'
        moment = datetime.now(timezone.utc) if now is None else now
        return ledger.human_duration(max(0, int((moment - when).total_seconds())))


# --- the state ----------------------------------------------------------------
def tree_state(root: Path, scope: tuple[str, ...] = (),
               moves_out: bool = False) -> tuple[State | None, str]:
    """(the state of this working tree, '' | why there is none). HEAD, then
    every path git lists — tracked and untracked, ignored excluded — with its
    content's digest; with a `scope`, only the paths under one of its
    prefixes, and the scope itself; with `moves_out`, without what a belt
    writes — a grain document's `status:` line and the `MOVE_KINDS` rows. A
    question git could not answer is never a hit, and the defect comes back to
    be PRINTED (rule 11)."""
    return _state_of(root, _is_ledger(), scope,
                     _is_grain_doc() if moves_out else None)


def _state_of(root: Path, is_ledger, scope: tuple[str, ...] = (),
              is_grain_doc=None) -> tuple[State | None, str]:
    """`tree_state`, carrying the ledger predicate down into every submodule so
    one PM config read serves the whole walk. A submodule is walked whole:
    the scope named its path, and a checkout is one input."""
    listing = _git(root, 'ls-files', '-z', '--cached', '--others',
                   '--exclude-standard')
    if listing is None:
        return None, ('git could not list this tree, so there is nothing to '
                      'compare a recorded verdict against')
    digest = hashlib.new(STATE_ALGO)
    digest.update(STATE_TAG)
    # The scope is an input: a whole-tree row must never match a scoped one.
    _field(digest, b'SCOPE', *(prefix.encode('utf-8') for prefix in scope))
    moves_out = is_grain_doc is not None
    _field(digest, b'MOVES_OUT', b'1' if moves_out else b'')
    # Unborn HEAD is the empty string: a state like any other, moving the
    # moment a commit lands.
    head = _git(root, 'rev-parse', 'HEAD')
    _field(digest, b'HEAD', head.strip() if head else b'')
    seen = 0
    for raw in sorted({part for part in listing.split(SEP) if part}):
        if scope and not in_scope(os.fsdecode(raw), scope):
            continue
        path = root / os.fsdecode(raw)
        if is_ledger(path):
            content = _ledger_content(
                path, SELF_FILED_KINDS | MOVE_KINDS if moves_out
                else SELF_FILED_KINDS)
            # Nothing but a run's own leavings contributes NOTHING, not an
            # empty field: the first run CREATES that file, and a state moving
            # for that could never match the row that run wrote.
            if content is None:
                continue
        elif moves_out and is_grain_doc(path):
            content = _without_status(path)
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
        under = f' under {" ".join(scope)}' if scope else ''
        return None, (f'this tree has no files git lists{under}, and a state '
                      f'over 0 files would match every other empty scan '
                      f'(hard rule 4)')
    return State(digest=digest.hexdigest(), files=seen, scope=scope,
                 moves_out=moves_out), ''


# --- a static gate's inputs (#98) ---------------------------------------------
# Its own tag: a gate's state and a rung's are never the same question. v2
# carries the ignored files under the scope.
INPUTS_TAG = b'agentic-sdlc/gate-inputs/v2'


def listing(root: Path) -> bytes | None:
    """Every path git names here, tracked and untracked, ignored excluded —
    the `-z` listing `tree_state` reads, asked once and shared by every gate
    state a `check all` takes. None when git did not answer."""
    return _git(root, 'ls-files', '-z', '--cached', '--others',
                '--exclude-standard')


def ignored_listing(root: Path, scope: tuple[str, ...]) -> bytes | None:
    """Every file git IGNORES under `scope`'s in-tree prefixes, `-z`: a gate
    that walks a directory reads these too (review F1). b'' for a scope with
    no in-tree prefix; None when git did not answer."""
    specs = [one for one in scope
             if one and not os.path.isabs(one) and one.split('/')[0] != '..']
    if not specs:
        return b''
    return _git(root, '--literal-pathspecs', 'ls-files', '-z', '--others',
                '--ignored', '--exclude-standard', '--', *specs)


def inputs_state(root: Path, listed: bytes, scope: tuple[str, ...],
                 also: tuple[str, ...] = (), names: bool = False,
                 salt: tuple[bytes, ...] = (), is_ledger=None,
                 memo: dict | None = None,
                 ignored: bytes = b'') -> tuple[State | None, str]:
    """The state of exactly what one static gate reads: the content of every
    listed path under `scope`, and of every IGNORED one there (`ignored`, as
    `ignored_listing` gives it) — a gate that walks a directory reads what git
    ignores; each `also` path whether git lists it or not (a gitignored
    settings file is still read); with `names`, the NAME of every listed
    path, for a gate that resolves a path anywhere in the tree; and `salt`,
    the facts no file carries — the tool, a config value, a binary's version.
    No HEAD: a commit that moves none of these is not a new input. The same
    fields, marks and ledger rule `tree_state` uses; `memo` shares one read of
    a path between the gates of one run. A state over 0 files is refused, as
    there (hard rule 4)."""
    is_ledger = _is_ledger() if is_ledger is None else is_ledger
    memo = {} if memo is None else memo
    digest = hashlib.new(STATE_ALGO)
    digest.update(INPUTS_TAG)
    _field(digest, b'SCOPE', *(prefix.encode('utf-8') for prefix in scope))
    _field(digest, b'SALT', *salt)
    rels = sorted({part for part in listed.split(SEP) if part})
    if names:
        _field(digest, b'NAMES', *rels)
    wanted = [raw for raw in rels if in_scope(os.fsdecode(raw), scope)]
    also_raw = {os.fsencode(rel) for rel in also}
    extra = sorted(also_raw - set(wanted))
    _field(digest, b'ALSO', *extra)
    hidden = sorted({part.rstrip(b'/') for part in ignored.split(SEP) if part
                     and in_scope(os.fsdecode(part.rstrip(b'/')), scope)}
                    - set(wanted) - also_raw)
    seen = 0
    for raw in [*wanted, *hidden, *extra]:
        content = memo.get(raw)
        if content is None:
            content = _input_content(root / os.fsdecode(raw), is_ledger)
            memo[raw] = content
        if content == MARK_ROWS and raw in hidden:
            # The ignored local ledger holding a run's own rows only: the
            # first run creates it, and it must not move the state (as in
            # `tree_state`). A gate that reads a ledger names it in `also`.
            continue
        if content == MARK_ABSENT and raw in extra:
            # An `also` path that is not there is a state like any other, and
            # it is not a file this gate read.
            _field(digest, raw, content)
            continue
        if not content:
            return None, (f'{os.fsdecode(raw)} is a directory git lists — a '
                          f'submodule — whose own checkout git could not '
                          f'state, so this gate cannot be keyed on it')
        _field(digest, raw, content)
        seen += 1
    if not seen:
        return None, (f'no file this gate reads is here ({" ".join(scope)}), '
                      f'and a state over 0 files would match every other '
                      f'empty scan (hard rule 4)')
    return State(digest=digest.hexdigest(), files=seen, scope=scope), ''


def _input_content(path: Path, is_ledger) -> bytes:
    """One input's contribution; b'' for a submodule git could not state."""
    if is_ledger(path):
        rows = _ledger_content(path)
        # A ledger holding nothing but a run's own rows still EXISTS.
        return MARK_ROWS if rows is None else rows
    content = _content_of(path, is_ledger)
    return b'' if content is None else content


def in_scope(rel: str, scope: tuple[str, ...]) -> bool:
    """Is a repo-relative path under one of the scope's prefixes? A prefix
    matches itself and everything below it, by path segment: `src` covers
    `src/a.py` and not `srcs/a.py`."""
    return any(rel == prefix or rel.startswith(prefix + '/')
               for prefix in scope)


def _git(root: Path, *args: str) -> bytes | None:
    """git's raw stdout, or None when git did not answer. Bytes and not
    `core.project.git_lines`: `-z` output has no lines, and a filename carrying
    a newline must not become two entries."""
    try:
        done = spawn.run(('git', *args), cwd=str(root),
                         capture_output=True, timeout=GIT_TIMEOUT_S)
    except (OSError, spawn.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _field(digest, *parts: bytes) -> None:
    """One record in, length-prefixed: no two different tuples of parts may
    serialise to the same bytes."""
    for part in parts:
        digest.update(str(len(part)).encode('ascii') + SEP + part + SEP)


def _content_of(path: Path, is_ledger) -> bytes | None:
    """What one path contributes: the executable bit and the digest of its
    bytes, a marker for a path that is not a plain file, or None when this
    cannot characterise it at all."""
    try:
        if path.is_symlink():
            # The TARGET: a link repointed is a change even when both files are.
            return MARK_LINK + os.fsencode(os.readlink(path))
        if path.is_dir():
            # A submodule: one path in `ls-files`, another checkout's state.
            # A commit rolled back inside it is `M <path>` to the
            # superproject's own `git status`; a constant here hid that.
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


def _without_status(path: Path) -> bytes:
    """A grain document with its frontmatter `status:` line left out, the one
    line a belt rewrites; every other byte, and the mode, still count."""
    from agentic_sdlc.core import frontmatter
    from agentic_sdlc.repo.pm import vocabulary
    try:
        lines = frontmatter.split_lines(frontmatter.read_raw(path))
    except (OSError, UnicodeDecodeError):
        return _content_of(path, lambda _: False) or MARK_ABSENT
    bounds = frontmatter.fence_bounds(lines)
    if bounds is not None:
        key = f'{vocabulary.FIELD_STATUS}:'
        lines = [line for index, line in enumerate(lines)
                 if not (bounds[0] < index < bounds[1]
                         and line.startswith(key))]
    mode = MARK_EXEC if os.access(path, os.X_OK) else MARK_PLAIN
    body = '\n'.join(lines).encode('utf-8', 'surrogateescape')
    return mode + hashlib.new(STATE_ALGO, body).digest()


def _ledger_content(path: Path,
                    dropped: frozenset = SELF_FILED_KINDS) -> bytes | None:
    """A ledger's rows minus a run's own; None when that leaves nothing."""
    try:
        raw = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        # Unreadable is a state too, and it moves when the file can be read.
        return MARK_ROWS + MARK_ABSENT
    rows = ledger_digest(raw, dropped)
    return None if rows is None else MARK_ROWS + rows


def ledger_digest(raw: str,
                  dropped: frozenset = SELF_FILED_KINDS) -> bytes | None:
    """The digest of every ledger line a run did NOT file about itself, or None
    when there is no such line. A line that will not parse, or names a kind
    this version does not know, is KEPT: only a row provably filed by a run may
    be dropped, and the wrong answer here hides a status flip."""
    digest = hashlib.new(STATE_ALGO)
    kept = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        row = _row(line)
        if row is not None and row.get(ledger.KIND_FIELD) in dropped:
            continue
        _field(digest, line.encode('utf-8', 'surrogateescape'))
        kept += 1
    return digest.digest() if kept else None


def _is_ledger():
    """A predicate naming the files whose ROWS the digest reads rather than
    whose bytes it hashes. By name and extension, never by directory: the pool
    is the consumer-settable `[pm] ledger_dir`, and a directory-wide rule
    pointed at a source tree would take real inputs out of the state."""
    try:
        from agentic_sdlc.repo.pm import vocabulary
        cfg = vocabulary.load()
        roadmap, pool = cfg.roadmap, ledger.ledgers_dir(cfg)
    except Exception:  # noqa: BLE001 - no PM tree, no ledgers, no exception
        return lambda path: False

    def is_ledger(path: Path) -> bool:
        # The local ledger is gitignored and never listed — unless a tree
        # has not taken the ignore line yet (#48), when its rows, all of them
        # a run's own, must still not move the state.
        if path.name in (ledger.LEDGER_FILE_NAME,
                         ledger.LOCAL_LEDGER_FILE_NAME) \
                and _under(path, roadmap):
            return True
        return path.suffix == LEDGER_SUFFIX and _under(path, pool)

    return is_ledger


def _is_grain_doc():
    """A predicate naming the grain documents whose `status:` line a belt
    rewrites: the markdown under the roadmap directory. A grain kept outside
    it is hashed whole, which re-runs — the safe direction."""
    try:
        from agentic_sdlc.repo.pm import vocabulary
        roadmap = vocabulary.load().roadmap
    except Exception:  # noqa: BLE001 - no PM tree, no grain documents
        return lambda path: False
    return lambda path: path.suffix == '.md' and _under(path, roadmap)


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


# --- the record ---------------------------------------------------------------
def ledger_file(root: Path) -> Path | None:
    """The ledger a verdict row lands in — the tree's gitignored LOCAL one,
    where the gate rows it quotes land too (#48). None means no record and no
    reuse."""
    roadmap = _roadmap()
    return None if roadmap is None else ledger.local_path(roadmap)


def _roadmap() -> Path | None:
    try:
        from agentic_sdlc.repo.pm import vocabulary
        return vocabulary.load().roadmap
    except Exception:  # noqa: BLE001 - every failure means the same: no record
        return None


def _telemetry_text(root: Path) -> str | None:
    """Every file a verdict or a graded row can be in, as ONE text, oldest
    history first — the tracked grainless ledger, then the local one — which
    is what `check budget` reads. '' when neither is there; None when there is
    no PM config, or one of them is there and cannot be read."""
    roadmap = _roadmap()
    if roadmap is None:
        return None
    parts = []
    for one in ledger.telemetry_paths(roadmap):
        if not one.is_file():
            continue
        try:
            parts.append(one.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError):
            return None
    return '\n'.join(parts)


def recorded(root: Path, gate: str, state: str) -> tuple[Verdict | None,
                                                         Graded | None]:
    """(the LAST verdict recorded for this make target over this exact tree
    state, the rows `check budget` grades AS THEY ARE NOW) — one pass over
    the tree's telemetry. Keyed on the TARGET, because what ran is what was
    proven; `None` either side means *run the target*."""
    raw = _telemetry_text(root) if state else None
    if raw is None:
        return None, None
    return verdicts(raw).get((gate, state)), graded_of(raw)


def verdicts(raw: str) -> dict[tuple[str, str], Verdict]:
    """Every whole `verify` row in a telemetry text, the LAST one per
    (target, state) — the one pass `recorded` makes, kept whole for a caller
    that asks about many gates at once (`check all`)."""
    found: dict[tuple[str, str], Verdict] = {}
    for line in raw.splitlines():
        row = _row(line)
        if row is not None and row.get(ledger.KIND_FIELD) == ledger.KIND_VERIFY:
            got = _verdict(row)
            if got is not None:
                found[(got.gate, got.state)] = got
    return found


def telemetry(root: Path) -> str | None:
    """The text `recorded` reads, for a caller holding it across a run."""
    return _telemetry_text(root)


def record(root: Path, rung: str, gate: str, state: State, verdict: str,
           exit_code: int, duration_ms: int, census: int | None,
           said: str = '', graded: Graded | None = None,
           probed: list[list[str]] | None = None) -> str:
    """Append this run's verdict; '' when the row landed, else why it did not.
    The caller's exit code never moves for it: an unwritable ledger is a thing
    to SAY, not a reason to call a green run red."""
    path = ledger_file(root)
    if path is None:
        return ('this tree has no PM config, so there is nowhere to record the '
                'verdict — the next run pays for the same answer again')
    if not path.parent.is_dir():
        # `append_to` would MAKE that directory, and a verb that runs a make
        # target has no business minting a PM tree in silence (rule 3).
        return (f'{path.parent} is not there, so this verdict is not recorded '
                f'— `verify` does not create a PM tree, and the next run pays '
                f'for the same answer again')
    if graded is None:
        raw = _telemetry_text(root)
        if raw is None:
            return (f'the ledgers beside {path} could not be read, so what '
                    f'`check budget` would grade over this tree is unknown — '
                    f'and a row that cannot say that is a row nothing may '
                    f'reuse')
        graded = graded_of(raw)
    try:
        ledger.append_to(path, ledger.verify_row(
            rung=rung, gate=gate, verdict=verdict, state=state.digest,
            duration_ms=duration_ms, exit_code=exit_code, census=census,
            graded=graded.digest, said=said, probed=probed))
    except (OSError, ValueError) as err:
        return f'the verdict could not be recorded in {path} ({err})'
    return ''


def graded_of(raw: str) -> Graded:
    """Every row `check budget` grades, digested in file order, and how many.
    A DIGEST, not a count: an edit in place — a merge, a trim, a restored older
    ledger — holds the count and moves the NEWEST row per target."""
    digest = hashlib.new(STATE_ALGO)
    rows = 0
    for line in raw.splitlines():
        row = _row(line)
        if row is None or row.get(ledger.KIND_FIELD) not in GRADED_KINDS:
            continue
        _field(digest, line.strip().encode('utf-8', 'surrogateescape'))
        rows += 1
    return Graded(digest=digest.hexdigest(), rows=rows)


def ledger_size(root: Path) -> int:
    """The ledger's size now, or 0 — the mark a run's own rows come after."""
    path = ledger_file(root)
    try:
        return path.stat().st_size if path is not None else 0
    except OSError:
        return 0


def census_since(root: Path, gate: str, offset: int) -> int | None:
    """The census the GATE itself filed for this target after `offset`, or
    None. Copied, never counted: `verify` scans no files, and the number a
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
        if row is None or row.get(ledger.KIND_FIELD) != ledger.KIND_GATE:
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
    wrong shape — the trust boundary. Rows arrive from other branches, versions
    and hands; a half-read row that became a PASS is rule 4's sin."""
    if ledger.parse_ts(row.get(ledger.TS_FIELD)) is None:
        return None
    if row.get('verdict') not in ledger.VERIFY_VERDICTS:
        return None
    fields = {}
    # `graded` is required, not defaulted: a row from a spelling that did not
    # digest what `check budget` grades cannot say whether it may be reused.
    for name in (ledger.TS_FIELD, 'rung', 'gate', 'verdict', 'state',
                 'graded'):
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
    said = row.get('said', '')
    fields['said'] = said if isinstance(said, str) else ''
    if 'probed' in row:
        probed = _probed(row['probed'])
        if probed is None:
            return None
        fields['probed'] = probed
    # The disagreement `verify_row` refuses to mint, refused again on the way
    # back in: PASS with a failing code cannot be reported as either.
    if (fields['verdict'] == PASS) != (fields['exit_code'] == 0):
        return None
    return Verdict(census=census, **fields)


def _probed(value) -> tuple[tuple[str, str, str], ...] | None:
    """A row's `probed` list, or None when any entry is not a (mode, path,
    saw) triple of strings: a probe half-read is a probe not checked."""
    from agentic_sdlc.repo.verify import probe
    if not isinstance(value, list):
        return None
    found = []
    for entry in value:
        if not (isinstance(entry, list) and len(entry) == 3
                and all(isinstance(part, str) and part for part in entry)
                and entry[0] in probe.MODES):
            return None
        found.append(tuple(entry))
    return tuple(found)


# --- what a reuse SAYS --------------------------------------------------------
# Joins the `[verify:check]` family, and every line carries it: one grep finds
# every run that did not pay (rule 6).
CACHE_TAG = '[verify:cache]'


# The clause a milestone reuse's first line ends with when the static rung was
# asked first; `release` reads it back into its gate's detail.
STATIC_ASKED = '; static rung re-asked: '


def static_clause(command: str, code: int) -> str:
    """`; static rung re-asked: make check exited 0`."""
    return f'{STATIC_ASKED}{command} exited {code}'


def reuse_lines(found: Verdict, command: str, state: State, graded: Graded,
                now: datetime | None = None, asked: str = '') -> list[str]:
    """What a reuse prints: the run it came from with its age, census and cost,
    and `asked`, the static rung's clause when one was asked first; the state
    that made it reusable and the flag that refuses it; and what this read did
    NOT re-measure — never conditional, the third line most of all, since a
    state is a claim about the working tree alone."""
    census = f'census {found.census}' if found.census is not None \
        else 'census unknown'
    # `command` names the recorded run honestly: the row was found BY its
    # target and `rules.py` refuses any rung but `make <target>`.
    return [
        f'{CACHE_TAG} REUSED {found.verdict} — recorded {found.ts} '
        f'({found.age(now)} ago) by `verify --{found.rung}`: {command}, '
        f'{census}, {found.duration_ms} ms{asked}',
        f'{CACHE_TAG} this tree is byte-identical to that run over '
        f'{state.where()} (state {state.short()}, {state.files} files), so '
        f'`{command}` did NOT run — `--no-cache` runs it anyway',
        f'{CACHE_TAG} NOT re-measured: anything outside this working tree — '
        f'the interpreters `make matrix` runs, an installed tool, the '
        f'environment — and the {graded.rows} ledger row(s) `check budget` '
        f'grades, which are byte-identical to the ones that run left (one '
        f'landing or changing SINCE it runs `{command}` instead)',
    ]


def stale_line(found: Verdict, graded: Graded | None, command: str,
               now: datetime | None = None) -> str:
    """Why a verdict recorded against THIS state was not reused: the rows
    `check budget` grades moved under it. Rule 11 — silence here reads as a
    cache that simply does not work."""
    return (f'{CACHE_TAG} a {found.verdict} is recorded for this exact tree '
            f'state ({found.age(now)} ago) and the '
            f'{"unreadable" if graded is None else graded.rows} row(s) '
            f'`check budget` grades are not the ones that run left — it grades '
            f'the NEWEST one per target, and no tree state can carry a row the '
            f'run itself writes, so `{command}` runs')
