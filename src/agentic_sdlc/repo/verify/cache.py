"""cache.py — what a rung remembers, and the TREE STATE it remembers it against.

A run whose digest is byte-identical to a recorded one reports that verdict
rather than buying the answer again — hard rule 4's first cardinal sin (a gate
that missed drift and printed PASS) if it is ever wrong or ever quiet. So: the
digest hashes the CONTENT of every path `git ls-files --cached --others
--exclude-standard` names, UNTRACKED included, plus HEAD by default and a
submodule's own checkout. An explicitly history-independent rung drops HEAD;
`verify.main` salts its tool, command, project and declared environment inputs.
A reuse is always printed; a malformed, missing or unreadable row
answers `None`, which means run the target; a state over 0 files is refused.

Out of the digest: ignored files, and the ledger rows a run files about ITSELF
(`SELF_FILED_KINDS`) — a state covering what a gate writes while it runs could
never repeat. Every OTHER ledger row is IN, line by line (`ledger_digest`):
a status or a decision is a fact about the tree, and dropping the ledger FILE
dropped those too.

A rung may be keyed on LESS than the whole tree: `[verify.inputs]` names the
path prefixes its state covers (`spot = ["src", "tests"]`), so a status flip
under `pm/` or a doc edit does not re-buy a unit tier that read neither. The
scope is in the digest, so a whole-tree row and a scoped row never match.

Every rung is keyed on the tree MINUS what a belt writes (#95), unless
`[verify] reuse_ignores_status = false`: the first frontmatter `status:`
line of each markdown file under the roadmap (`_is_grain_doc`) and the
ledger rows a belt files about its own run (`MOVE_KINDS`) are left out, so
six closes on one commit key on one state.
Every other byte under the roadmap stays in, and so does the choice itself.

Each PASS also writes, into ONE gitignored directory beside the local ledger
(`ledger.LOCAL_INPUTS_DIR_NAME`), each path in its state with a short digest
of what it put in — one file per rung and target, written whole through a
temp file and a rename, never a row and never read back to be merged. So two
PASSes close together each land their own file; two PASSes of the SAME rung
and target race, and the later rename wins, which is the later PASS's view.
The lookup key stays the one digest; on a MISS, `miss_lines` compares this
tree with that file and names each path that changed, was added or was
removed, or says in one line that no file did. No file, or a malformed one,
names nothing. That directory is out of every state, like a run's own ledger
rows: each PASS rewrites a file in it.
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
# Of each input's digest, in the inputs file. It only NAMES a change on a miss
# and never keys a reuse, so it is short.
INPUT_SHOWN = 12

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

# Every kind a run files about its own execution rather than about the work.
SELF_FILED_KINDS = frozenset({ledger.KIND_VERIFY, ledger.KIND_GATE,
                              ledger.KIND_TEST,
                              *ledger.EVENT_KINDS.values()})

# Every kind a status write or a belt files about its own run: `status`, a
# forced release's `deviation`, and the kinds no verb mints since 2.0.0 but
# ledgers still hold — `disposition`, `rung.enter`, `check.verdict`,
# `rung.leave`, `belt.blocked`. Out of a state taken with `moves_out` only.
MOVE_KINDS = frozenset({ledger.KIND_STATUS, ledger.KIND_DISPOSITION,
                        ledger.KIND_DEVIATION, ledger.KIND_ENTER,
                        ledger.KIND_VERDICT, ledger.KIND_LEAVE,
                        ledger.KIND_BELT_BLOCKED})

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
    history_independent: bool = False
    environment: tuple[str, ...] = ()
    # (path, a short digest of what it put into `digest`), sorted by path;
    # () for a state that does not keep them.
    input_digests: tuple[tuple[str, str], ...] = ()

    def short(self) -> str:
        return self.digest[:STATE_SHOWN]

    def where(self) -> str:
        """The paths this state covers, for a line a human reads."""
        covered = ' '.join(self.scope) if self.scope else 'the whole tree'
        if self.moves_out:
            covered += f' except {MOVES_OUT}'
        return covered


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
               moves_out: bool = False,
               history_independent: bool = False) -> tuple[State | None, str]:
    """(the state of this working tree, '' | why there is none). HEAD, then
    every path git lists — tracked and untracked, ignored excluded — with its
    content's digest; with a `scope`, only the paths under one of its
    prefixes, and the scope itself; with `moves_out`, without what a belt
    writes — a grain document's `status:` line and the `MOVE_KINDS` rows. A
    question git could not answer is never a hit, and the defect comes back to
    be PRINTED (rule 11)."""
    return _state_of(root, _is_ledger(), scope,
                     _is_grain_doc() if moves_out else None,
                     history_independent=history_independent,
                     is_inputs_file=_is_inputs_file())


def _state_of(root: Path, is_ledger, scope: tuple[str, ...] = (),
              is_grain_doc=None,
              history_independent: bool = False,
              is_inputs_file=None) -> tuple[State | None, str]:
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
    if history_independent:
        _field(digest, b'HISTORY_INDEPENDENT', b'1')
    else:
        head = _git(root, 'rev-parse', 'HEAD')
        _field(digest, b'HEAD', head.strip() if head else b'')
    seen = 0
    each: list[tuple[str, str]] = []
    for raw in sorted({part for part in listing.split(SEP) if part}):
        if scope and not in_scope(os.fsdecode(raw), scope):
            continue
        path = root / os.fsdecode(raw)
        if is_inputs_file is not None and is_inputs_file(path):
            # Rewritten by every PASS: listed only where the ignore line is
            # missing, and they must not move the state there either.
            continue
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
        each.append((raw.decode('utf-8', 'backslashreplace'),
                     hashlib.new(STATE_ALGO, content).hexdigest()[:INPUT_SHOWN]))
        seen += 1
    if not seen:
        under = f' under {" ".join(scope)}' if scope else ''
        return None, (f'this tree has no files git lists{under}, and a state '
                      f'over 0 files would match every other empty scan '
                      f'(hard rule 4)')
    return State(digest=digest.hexdigest(), files=seen, scope=scope,
                 moves_out=moves_out,
                 history_independent=history_independent,
                 input_digests=tuple(each)), ''


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
    is_inputs_file = _is_inputs_file()
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
        if is_inputs_file(root / os.fsdecode(raw)):
            continue  # what a rung's PASS rewrites, as in `tree_state`
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
    """A grain document with its FIRST frontmatter `status:` line left out,
    the one line a belt rewrites; every other byte, and the mode, still
    count — a duplicate `status:` line too, so editing it moves the state."""
    from agentic_sdlc.core import frontmatter
    from agentic_sdlc.repo.pm import vocabulary
    try:
        lines = frontmatter.split_lines(frontmatter.read_raw(path))
    except (OSError, UnicodeDecodeError):
        return _content_of(path, lambda _: False) or MARK_ABSENT
    bounds = frontmatter.fence_bounds(lines)
    if bounds is not None:
        key = f'{vocabulary.FIELD_STATUS}:'
        first = next((index for index in range(bounds[0] + 1, bounds[1])
                      if lines[index].startswith(key)), None)
        if first is not None:
            lines = lines[:first] + lines[first + 1:]
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


def _is_inputs_file():
    """A predicate naming every path in the directory a rung's PASS writes
    its input digests to, and that directory itself, which no state may
    cover; never true without a PM config."""
    kept = inputs_dir()
    return (lambda _: False) if kept is None else \
        (lambda one: _under(one, kept))


def _is_grain_doc():
    """A predicate naming the documents whose `status:` line a belt may
    rewrite: EVERY markdown file under the roadmap directory, not only the
    grains in its pools — a shared doc there (`releases.md`) has its first
    frontmatter `status:` line left out too. Wide on purpose: a milestone
    kept beside the pools (`<roadmap>/<id>/milestone.md`) is still keyed
    without its status. A grain kept outside the roadmap is hashed whole,
    which re-runs — the safe direction."""
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
    """Every file a verdict can be in, as ONE text, oldest history first —
    the tracked grainless ledger, then the local one, then the clone's shared
    receipts. '' when none
    is there; None when there is no PM config, or one of them is there and
    cannot be read."""
    roadmap = _roadmap()
    if roadmap is None:
        return None
    text = _read_telemetry(roadmap)
    if text is None:
        return None
    shared = shared_receipts(root)
    if shared is not None and shared.is_file():
        try:
            text = text + '\n' + shared.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            pass  # an unreadable shared file is no receipt, never a red gate
    return text


# THE SHARED RECEIPTS. A worktree's local ledger is gitignored and its own, so
# a builder's green verdict never reached the lead's checkout of the same
# bytes: every merge bought every gate again. Each `verify` row is ALSO
# appended under the git COMMON dir, which every worktree of one clone shares;
# the state digest is content, never HEAD, so a merge whose inputs are
# byte-identical to what a builder proved reuses that proof.
# AGENTIC_SDLC_SHARED_RECEIPTS=0 turns it off.
SHARED_RECEIPTS_DIR = 'agentic-sdlc'
SHARED_RECEIPTS_FILE = 'receipts.jsonl'
SHARED_RECEIPTS_ENV = 'AGENTIC_SDLC_SHARED_RECEIPTS'


def shared_receipts(root: Path) -> Path | None:
    """The clone-wide receipt file, or None when off or not a git checkout."""
    if os.environ.get(SHARED_RECEIPTS_ENV, '1') == '0':
        return None
    common = _common_dir(root)
    return None if common is None else (
        common / SHARED_RECEIPTS_DIR / SHARED_RECEIPTS_FILE)


def _common_dir(root: Path) -> Path | None:
    """The git common dir, read from the files git keeps (no spawn): `.git`
    is the dir itself in a main checkout, or a `gitdir:` pointer in a linked
    worktree whose own dir names the common one in `commondir`."""
    dot = root / '.git'
    try:
        if dot.is_dir():
            return dot.resolve()
        text = dot.read_text(encoding='utf-8').strip()
        if not text.startswith('gitdir:'):
            return None
        own = Path(text[len('gitdir:'):].strip())
        own = own if own.is_absolute() else (root / own)
        pointer = own / 'commondir'
        if not pointer.is_file():
            return own.resolve()
        common = Path(pointer.read_text(encoding='utf-8').strip())
        return (common if common.is_absolute() else own / common).resolve()
    except (OSError, UnicodeDecodeError):
        return None


def _read_telemetry(roadmap: Path) -> str | None:
    """Every telemetry ledger under `roadmap` as one text, oldest first; ''
    when none is there, None when one is there and cannot be read."""
    parts = []
    for one in ledger.telemetry_paths(roadmap):
        if not one.is_file():
            continue
        try:
            parts.append(one.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError):
            return None
    return '\n'.join(parts)


def recorded(root: Path, gate: str, state: str) -> Verdict | None:
    """The LAST verdict recorded for this make target over this exact tree
    state — one pass over the tree's telemetry. Keyed on the TARGET, because
    what ran is what was proven; `None` means *run the target*."""
    raw = _telemetry_text(root) if state else None
    if raw is None:
        return None
    return verdicts(raw).get((gate, state))


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
           said: str = '',
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
    row = ledger.verify_row(
        rung=rung, gate=gate, verdict=verdict, state=state.digest,
        duration_ms=duration_ms, exit_code=exit_code, census=census,
        said=said, probed=probed)
    try:
        ledger.append_to(path, row)
    except (OSError, ValueError) as err:
        return f'the verdict could not be recorded in {path} ({err})'
    shared = shared_receipts(root) if verdict == PASS else None
    if shared is not None:
        try:
            ledger.append_to(shared, row)
        except (OSError, ValueError):
            pass  # the local row landed; a shared copy is a speed-up only
    if verdict == PASS and state.input_digests:
        _keep_inputs(rung, gate, state)
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
    for name in (ledger.TS_FIELD, 'rung', 'gate', 'verdict', 'state'):
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


# --- what a miss SAYS ---------------------------------------------------------
CHANGED, ADDED, REMOVED = 'changed', 'added', 'removed'
# A miss names at most this many paths, then one line counts the rest.
MISS_SHOWN = 20


# A miss whose last PASS kept its inputs, none of which moved: the key moved
# for a reason no file carries. One line, so the miss is never silent (rule 11).
NO_INPUT_MOVED = ('[verify] miss: no input file changed since the last PASS '
                  '(HEAD, environment or scope moved)')


def inputs_dir() -> Path | None:
    """The one directory each rung's last-PASS input digests live in, or
    None without a PM config."""
    roadmap = _roadmap()
    return None if roadmap is None else ledger.local_inputs_dir(roadmap)


def inputs_file(rung: str, gate: str) -> Path | None:
    """The file in `inputs_dir` the last PASS of this rung and target kept,
    or None without a PM config. Each name part is percent-quoted, so `@`
    never appears inside one and no two (rung, target) pairs share a file."""
    from urllib.parse import quote
    kept = inputs_dir()
    if kept is None:
        return None
    return kept / f'{quote(rung, safe="")}@{quote(gate, safe="")}.json'


def _read_inputs(path: Path | None) -> dict[str, str] | None:
    """One inputs file as {path: digest}; None when absent, unreadable or
    not that shape."""
    if path is None:
        return None
    try:
        got = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(got, dict) or not all(
            isinstance(one, str) and isinstance(digest, str)
            for one, digest in got.items()):
        return None
    return got


def _keep_inputs(rung: str, gate: str, state: State) -> None:
    """Write this rung's file whole with `state`'s input digests, atomically:
    a temp file beside it, then a rename over it (`core.apply`, the one
    mutator). Nothing is read first, so no other rung's PASS can be lost. A
    file that cannot be written is skipped in silence — it only names a
    change, and never keys a reuse."""
    from agentic_sdlc.core import apply
    path = inputs_file(rung, gate)
    # The roadmap must be there: `verify` does not mint a PM tree (rule 3).
    if path is None or not path.parent.parent.is_dir():
        return
    temp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    done = apply.Plan().overwrite(
        temp, json.dumps(dict(state.input_digests), sort_keys=True,
                         separators=(',', ':'))
    ).move(temp, path).apply(decide=False)
    if done.failed is not None:
        apply.remove_file(temp)


def miss_lines(rung: str, gate: str, state: State) -> list[str]:
    """What a miss prints: each input of `state` that differs from the last
    PASS of this rung and target, as `changed:`, `added:` or `removed:` and
    its path — or `NO_INPUT_MOVED` when that PASS kept its inputs and none
    differs. [] when no PASS kept its inputs, or the file is malformed."""
    if not state.input_digests:
        return []
    before = _read_inputs(inputs_file(rung, gate))
    if before is None:
        return []
    return input_changes(before, dict(state.input_digests)) or [NO_INPUT_MOVED]


def input_changes(before: dict[str, str], now: dict[str, str]) -> list[str]:
    """One line per path whose digest moved, appeared or left, sorted by
    path; past `MISS_SHOWN`, those and one `... and N more` line."""
    found = []
    for path in sorted(before.keys() | now.keys()):
        if path not in before:
            found.append(f'{ADDED}: {path}')
        elif path not in now:
            found.append(f'{REMOVED}: {path}')
        elif before[path] != now[path]:
            found.append(f'{CHANGED}: {path}')
    if len(found) > MISS_SHOWN:
        return [*found[:MISS_SHOWN], f'... and {len(found) - MISS_SHOWN} more']
    return found


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


def reuse_lines(found: Verdict, command: str, state: State,
                now: datetime | None = None, asked: str = '',
                by: str = '') -> list[str]:
    """What a reuse prints: the run it came from with its age, census and cost,
    and `asked`, the static rung's clause when one was asked first; the state
    that made it reusable and the flag that refuses it; and what this read did
    NOT re-measure — never conditional, the third line most of all, since a
    state is a claim about the working tree alone. `by` names the verb that
    recorded it when that is not `verify` (`integrate`)."""
    census = f'census {found.census}' if found.census is not None \
        else 'census unknown'
    by = by or f'verify --{found.rung}'
    # `command` names the recorded run honestly: the row was found BY its
    # target and `rules.py` refuses any rung but `make <target>`.
    return [
        f'{CACHE_TAG} REUSED {found.verdict} — recorded {found.ts} '
        f'({found.age(now)} ago) by `{by}`: {command}, '
        f'{census}, {found.duration_ms} ms{asked}',
        f'{CACHE_TAG} this tree is byte-identical to that run over '
        f'{state.where()} (state {state.short()}, {state.files} files), so '
        f'`{command}` did NOT run — `--no-cache` runs it anyway',
        f'{CACHE_TAG} NOT re-measured: the interpreters `make matrix` runs, '
        f'unnamed environment variables and inputs outside the declared '
        f'project/tool key',
    ]
