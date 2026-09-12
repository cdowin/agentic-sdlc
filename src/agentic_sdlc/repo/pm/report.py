"""report.py — `pm ledger report`: the rows a milestone OWNS, as units.

One milestone's rows, or more than one milestone's totals side by side, or the
tree's own rows (`--tree`). The ledger never judges; this is the caller
judgement is left to. It may **sum, count, subtract and group** — and the one
ratio it prints, an agent's `share` of the tokens its milestone's units
recorded, is that sum divided by that sum, never a weight, price or score.
Absent is `-`, not zero; nothing is dropped, and a row no report can place is
COUNTED on a line of its own (rule 11). It never fails on a number.

**Ownership is read, never inferred.** A milestone owns a row that names one
of its grains, or — for a row naming no grain — one stamped with the branch
the milestone DECLARES in `branch:`. A row from before either stamp is placed
by its `tree` snapshot when that names exactly one of the milestone's stories.
Every other root row is the tree's, and is printed once, under its own heading.
"""
from __future__ import annotations

import fnmatch
import io
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.core import frontmatter, spawn
from agentic_sdlc.repo.pm import arrive, inventory, ledger, vocabulary

# The line shape a consumer greps (rule 6); every heading carries the id.
HEADING_PREFIX = '[ledger:report]'

# Printed for a number nobody recorded: a blank reads as zero and a `0` would
# be a lie.
DASH = '-'

# No `ledger.jsonl` at all: a fact, exit 0, one line.
NO_LEDGER = 'no ledger'

# The shape `pm status` already uses for its phase buckets.
COLUMN_GAP = '  '
BLOCK_PREFIX = '--'
SUB_ROW_INDENT = '  '
NOTE_INDENT = '   '

# Grain kinds.
KIND_STORY = vocabulary.GRAIN_STORY
KIND_FEATURE = vocabulary.GRAIN_FEATURE
KIND_BUG = vocabulary.GRAIN_BUG
KIND_MILESTONE = vocabulary.GRAIN_MILESTONE

# D3's snapshot buckets, by the kind of grain whose ids they hold;
# `milestones_in_progress` is on every row and would place every dispatch
# under every milestone.
CATEGORY_BUCKETS = (
    (KIND_STORY, (ledger.STORIES_IN_PROGRESS,)),
    (KIND_FEATURE, ('features_in_progress',)),
)
# The old shape, read as-is (D7): matched by the seed's words when written, and
# never re-read through a later declaration.
LEGACY_BUCKETS = (
    (KIND_STORY, ('stories_wip', 'stories_review')),
    (KIND_FEATURE, ('features_building', 'features_review')),
)
CATEGORY_KEYS = frozenset(key for _, keys in CATEGORY_BUCKETS for key in keys)

# A hand-recorded ONE TOTAL — the number a dispatch unit's `tokens` reads.
TOTAL_KEY = ledger.TOTAL_KEY
# The two counts a courier row carries outside `usage`, read by the join.
COUNT_KEYS = ('tool_calls', 'duration_s')
AGENT_ID_KEY = 'agent_id'
AGENT_TYPE_KEY = 'agent_type'
MEASURED_KEY = 'messages'
JOINED_KEY = 'joined'
JOINED_NOTE = ('courier/hand pair(s) joined by agent_id — one dispatch each, on '
               'the hand row\'s grain with the courier row\'s measured spend')

# The payload key naming which milestone the report is OF — a key, not a kind.
MILESTONE_KEY = 'milestone'

# THE ROW CONTRACT this report reads (0.10.0). Every row may carry `branch`,
# the HEAD it was filed on; a `stamp` row opens or closes one unit of work.
BRANCH_FIELD = 'branch'
KIND_STAMP = 'stamp'
EDGE_FIELD = 'edge'
EDGE_START, EDGE_STOP = 'start', 'stop'
ISSUE_FIELD = 'issue'
AGENT_FIELD = 'agent'
TOKENS_FIELD = 'tokens'
OUTCOME_FIELD = 'outcome'

# --- the columns, IN ORDER — what `--help` names (rule 11's read side) --------
UNIT_TITLE = 'units'
# The one-milestone heading; not `units`, which is the table under it.
STAMP_TITLE = 'stamp table'
UNIT_COLUMN, GRAIN_COLUMN, ISSUE_COLUMN, AGENT_COLUMN = (
    'unit', 'grain', 'issue', 'agent')
START_COLUMN, STOP_COLUMN, DURATION_COLUMN = 'start', 'stop', 'duration'
TOKENS_COLUMN, OUTCOME_COLUMN = 'tokens', 'outcome'
UNIT_COLUMNS = (UNIT_COLUMN, GRAIN_COLUMN, ISSUE_COLUMN, AGENT_COLUMN,
                START_COLUMN, STOP_COLUMN, DURATION_COLUMN, TOKENS_COLUMN,
                OUTCOME_COLUMN)
AGENT_TITLE = 'by agent'
UNITS_COLUMN, SHARE_COLUMN = 'units', 'share'
AGENT_COLUMNS = (AGENT_COLUMN, UNITS_COLUMN, TOKENS_COLUMN, DURATION_COLUMN,
                 SHARE_COLUMN)
SHARE_MARK = '%'
ISSUE_SEPARATOR = ','

# The named count lines under the tables: each a fact the units do not hold.
OWNED_NOTE = 'row(s) this milestone owns'
NO_BRANCH_NOTE = ('no `branch:` declared, so no row naming no grain is placed '
                  'here by branch')
UNPAIRED_NOTE = ('stamp row(s) pair with nothing — a stop with no open start '
                 'on its grain, or an edge that is neither; counted in no unit')
SUPERSEDED_NOTE = ('superseded spend: {rows} row(s), {tokens} token(s) in this '
                   'milestone\'s ledger naming a grain it does not hold')
NO_GRAIN_NOTE = ('row(s) in this milestone\'s ledger name no grain and no '
                 'branch it declares — counted in no unit')

LEFT, RIGHT = 'left', 'right'


# --- WHERE the report reads from ----------------------------------------------
# Every file this module opens goes through a `Source`; `build` is one function
# over one tree, so a report read from history is the same report by
# construction. `GitSource` runs `rev-parse`, `ls-tree`, `cat-file` and `show`,
# none of which writes or touches the index (D6).
FEATURES_DIR = vocabulary.FEATURES_DIR
STORIES_DIR = vocabulary.STORIES_DIR
BUGS_DIR = vocabulary.BUGS_DIR
MD_SUFFIX = '.md'

GIT = 'git'
GIT_MISSING = (f'{GIT} is not on PATH, so a report `--from` a rev cannot be '
               f'read — a retired milestone is only in history')
# git's own spelling, so a reader can paste it after `git show`.
REV_SEPARATOR = ':'

# The two object types `git ls-tree` names for the things a PM tree is made of.
TREE = 'tree'
BLOB = 'blob'


class GitError(OSError):
    """A git invocation that failed, carrying git's own stderr verbatim. An
    `OSError`, so a blob absent at the rev lands in the `RecordError` handler
    that already exists."""


def check_rev(rev: str) -> None:
    """The `--from` grammar: a leading `-`, whitespace/NUL, and an empty rev
    (which names the index) are refused here; whether the rev exists is git's
    answer."""
    if not rev:
        raise GitError('--from needs a rev — a tag, a hash or a ref '
                       '(the release tag `vX.Y.Z` is the usual anchor: a '
                       'milestone directory is still in the tree at its own '
                       'release and is retired at the next close)')
    if rev.startswith('-'):
        raise GitError(f'--from {rev!r} starts with `-`, so it is a flag and '
                       f'not a rev — name a tag, a hash or a ref')
    if any(c.isspace() or c == '\0' for c in rev):
        raise GitError(f'--from {rev!r} holds whitespace or NUL — a rev is one '
                       f'word, and two would be two arguments')


def _universal(text: str) -> str:
    """`Path.read_text`'s universal-newline translation, applied by hand to the
    ledger read alone, so a CRLF ledger reads the same from disk and from
    history."""
    return text.replace('\r\n', '\n').replace('\r', '\n')


class _Blob:
    """One file at a rev, shaped as `open(...)` and `read_text(...)` so
    `inventory` and `ledger` stay the only readers of their formats. The text is produced
    lazily, so an absent blob raises inside the reader that already handles it.
    """

    def __init__(self, display: str, read: Callable[[], str]) -> None:
        self._display, self._read = display, read

    def open(self, mode: str = 'r', encoding: str | None = None,
             newline: str | None = None) -> io.StringIO:
        # The same disabled translation `frontmatter.read_raw` asks of `open()`.
        return io.StringIO(self._read(), newline='')

    def read_text(self, encoding: str = 'utf-8') -> str:
        return _universal(self._read())

    def __str__(self) -> str:
        return self._display


class Source:
    """The tree the report reads, as the eleven reads it makes — no more,
    none writing. The last four are the LAYOUT family: a rev read that asked
    `inventory.is_pooled` would look for a retired milestone's ledger, document and
    records in the layout the retire left.
    """

    #: The rev this source reads, or `''` for the working tree; `render` puts
    #: it in the heading.
    rev = ''

    def milestone_dir(self, cfg: vocabulary.PmConfig, mid: str) -> Path | None:
        raise NotImplementedError

    def feature_file(self, cfg: vocabulary.PmConfig, fid: str) -> Path | None:
        raise NotImplementedError

    def feature_files(self, cfg: vocabulary.PmConfig, mid: str) -> list[Path]:
        raise NotImplementedError

    def story_files(self, cfg: vocabulary.PmConfig, fid: str) -> list[Path]:
        raise NotImplementedError

    def bug_files(self, cfg: vocabulary.PmConfig, mid: str) -> list[Path]:
        raise NotImplementedError

    def field_of(self, path: Path, key: str) -> str:
        raise NotImplementedError

    def is_file(self, path: Path) -> bool:
        raise NotImplementedError

    def ledger_rows(self, path: Path) -> list:
        raise NotImplementedError

    def is_pooled(self, cfg: vocabulary.PmConfig) -> bool:
        raise NotImplementedError

    def milestone_doc(self, handle: Path) -> Path:
        raise NotImplementedError

    def ledger_for(self, cfg: vocabulary.PmConfig, mid: str) -> Path:
        raise NotImplementedError

class DiskSource(Source):
    """The working tree, delegated to `inventory` and `ledger` so the live
    census is the gate's census."""

    def milestone_dir(self, cfg: vocabulary.PmConfig, mid: str) -> Path | None:
        return inventory.milestone_dir(cfg, mid)

    def feature_file(self, cfg: vocabulary.PmConfig, fid: str) -> Path | None:
        return inventory.feature_file(cfg, fid)

    def feature_files(self, cfg: vocabulary.PmConfig, mid: str) -> list[Path]:
        return inventory.feature_files(cfg, mid)

    def story_files(self, cfg: vocabulary.PmConfig, fid: str) -> list[Path]:
        return inventory.story_files(cfg, fid)

    def bug_files(self, cfg: vocabulary.PmConfig, mid: str) -> list[Path]:
        return inventory.bug_files(cfg, mid)

    def field_of(self, path: Path, key: str) -> str:
        return frontmatter.field_of(path, key)

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def ledger_rows(self, path: Path) -> list:
        return ledger.read_rows(path)

    def is_pooled(self, cfg: vocabulary.PmConfig) -> bool:
        return inventory.is_pooled(cfg)

    def milestone_doc(self, handle: Path) -> Path:
        return inventory.milestone_doc(handle)

    def ledger_for(self, cfg: vocabulary.PmConfig, mid: str) -> Path:
        return ledger.ledger_for(cfg, mid)

class GitSource(Source):
    """The same tree at a rev, through `git show`, read-only by construction.
    A grain resolves by the `id:` it declares as it does on disk, falling back
    to the version-prefix glob for a rev from before the migration; paths keep
    `model`'s shapes but never reach the filesystem. Blobs and object types are
    memoised, since a rev is immutable.
    """

    def __init__(self, root: Path, rev: str) -> None:
        check_rev(rev)
        self.root = root
        self.rev = rev
        self._blobs: dict[str, bytes] = {}
        self._types: dict[str, str] = {}
        self._trees: dict[tuple[str, bool], list[tuple[str, str]]] = {}
        # One report reads one tree, so the layout is asked of the rev once.
        self._pooled: bool | None = None
        # `rev-parse --verify` first, so "no such rev" is answered once, in
        # git's words.
        self._git(['rev-parse', '--verify', rev])

    # --- the four verbs -------------------------------------------------------
    def _git(self, args: list[str]) -> bytes:
        """One git run in the repo root, stdout as bytes — `text=True` would
        apply newline translation and the locale's encoding."""
        try:
            done = spawn.run([GIT, '-C', str(self.root), *args],
                             capture_output=True, check=False)
        except FileNotFoundError as err:
            raise GitError(GIT_MISSING) from err
        if done.returncode != 0:
            why = done.stderr.decode('utf-8', 'replace').strip()
            raise GitError(why or f'`{GIT} {" ".join(args)}` failed '
                                  f'(exit {done.returncode})')
        return done.stdout

    def spec(self, path: Path) -> str:
        """`<rev>:<path>` — what a reader would type to see this file."""
        return f'{self.rev}{REV_SEPARATOR}{self._rel(path) or path}'

    def _rel(self, path: Path) -> str | None:
        """The repo-relative posix path git addresses, or None for a path
        outside the root, which is in no rev."""
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return None

    def _ls(self, path: Path, recursive: bool) -> list[tuple[str, str]]:
        """`(object type, name)` for one directory at the rev, git's order; a
        missing tree is empty, `walk.children`'s own answer."""
        rel = self._rel(path)
        if rel is None:
            return []
        key = (rel, recursive)
        if key in self._trees:
            return self._trees[key]
        args = ['ls-tree', '-z']
        if recursive:
            args.append('-r')
        args.append(f'{self.rev}{REV_SEPARATOR}{rel}')
        try:
            raw = self._git(args)
        except GitError:
            self._trees[key] = []
            return []
        out: list[tuple[str, str]] = []
        # `-z` turns off path quoting; `surrogateescape` carries a non-UTF-8
        # name through `Path` losslessly.
        for record in raw.decode('utf-8', 'surrogateescape').split('\0'):
            if not record:
                continue
            meta, _, name = record.partition('\t')
            fields = meta.split(' ')
            if len(fields) >= 2 and name:
                out.append((fields[1], name))
        self._trees[key] = out
        return out

    def _dirs(self, path: Path, pattern: str = '') -> list[Path]:
        """This directory's immediate subdirectories at the rev, sorted;
        `fnmatchcase` because git's tree is case-sensitive, as `Path.glob` is.
        """
        return sorted(path / name for kind, name in self._ls(path, False)
                      if kind == TREE
                      and (not pattern or fnmatch.fnmatchcase(name, pattern)))

    def _grain_docs(self, gdir: Path) -> list[Path]:
        """`inventory.grain_docs` at the rev: the same walk and the same four
        narrowings, in the same order, so a milestone read from history has the
        census it had on disk."""
        out: list[Path] = []
        for kind, name in self._ls(gdir, True):
            if kind != BLOB:
                continue
            parts = name.split('/')
            if not name.lower().endswith(MD_SUFFIX):
                continue
            if any(part.startswith('.') for part in parts):
                continue
            path = gdir.joinpath(*parts)
            if self._is_grain_doc(path):
                out.append(path)
        return sorted(out)

    def _is_grain_doc(self, path: Path) -> bool:
        """`inventory._is_grain_doc` at the rev — the predicate itself, not a copy,
        so this census cannot disagree with the gate's. An unreadable blob
        stays in scope, as on disk."""
        return inventory._is_grain_doc(self._doc(path))

    def _doc(self, path: Path) -> _Blob:
        """This path at the rev, handed to a reader that expects a `Path`."""
        return _Blob(self.spec(path), lambda: self._text(path))

    def _text(self, path: Path) -> str:
        """One blob, decoded, terminators intact — the one read under them all.
        `UnicodeDecodeError` propagates, since every reader already catches it
        beside `OSError`."""
        rel = self._rel(path)
        if rel is None:
            raise GitError(f'{path} is outside {self.root}, so no rev holds it')
        if rel not in self._blobs:
            self._blobs[rel] = self._git(
                ['show', f'{self.rev}{REV_SEPARATOR}{rel}'])
        return self._blobs[rel].decode('utf-8')

    # --- the layout, asked of the REV ------------------------------------------
    def is_pooled(self, cfg: vocabulary.PmConfig) -> bool:
        """`inventory.is_pooled` at the rev, because the two disagree in the case
        this verb exists for: a retire empties the pools on disk while the rev
        still holds every grain."""
        if self._pooled is None:
            self._pooled = any(self._grain_docs(inventory.pool_dir(cfg, kind))
                               for kind in vocabulary.FLOW_KINDS)
        return self._pooled

    def _pool_grain(self, cfg: vocabulary.PmConfig, kind: str,
                    gid: str) -> Path | None:
        """The document in one pool DECLARING this id, at the rev — what
        `inventory.grain_index` answers on disk, for one id."""
        for path in self._grain_docs(inventory.pool_dir(cfg, kind)):
            if self.field_of(path, vocabulary.FIELD_ID) == gid:
                return path
        return None

    # --- the eleven reads -----------------------------------------------------
    def milestone_dir(self, cfg: vocabulary.PmConfig, mid: str) -> Path | None:
        """The milestone's HANDLE at the rev: its document in the pool, or the
        `<mid>-*` directory a pre-migration rev holds."""
        if not inventory.segment_is_literal(mid):
            return None
        if self.is_pooled(cfg):
            return self._pool_grain(cfg, vocabulary.GRAIN_MILESTONE, mid)
        for base in (cfg.roadmap, cfg.roadmap / vocabulary.ARCHIVE_DIR_NAME):
            for found in self._dirs(base, f'{mid}-*'):
                return found
        return None

    def feature_file(self, cfg: vocabulary.PmConfig, fid: str) -> Path | None:
        if self.is_pooled(cfg):
            return self._pool_grain(cfg, vocabulary.GRAIN_FEATURE, fid)
        mid, _, slug = fid.partition('/')
        if not inventory.segment_is_literal(slug):
            return None
        mdir = self.milestone_dir(cfg, mid)
        if mdir is None:
            return None
        ffile = mdir / FEATURES_DIR / slug / vocabulary.FEATURE_DOC
        return ffile if self.is_file(ffile) else None

    def _pool_children(self, cfg: vocabulary.PmConfig, kind: str,
                       parent_id: str) -> list[Path]:
        """`inventory._children_grains` at the rev, in the parent's declared `order`
        and by id after that — the ORDER is half of the equality with disk."""
        field = vocabulary.BINDS_TO.get(kind, ('', ''))[1]
        if not field:
            return []
        found: dict[str, Path] = {}
        for path in self._grain_docs(inventory.pool_dir(cfg, kind)):
            if self.field_of(path, field) != parent_id:
                continue
            found[self.field_of(path, vocabulary.FIELD_ID) or path.stem] = path
        parent = self._grain_at(cfg, parent_id)
        declared = (frontmatter.list_field_of(self._doc(parent), vocabulary.ORDER_KEY)
                    if parent is not None else [])
        out = [found.pop(gid) for gid in declared if gid in found]
        return out + [found[gid] for gid in sorted(found)]

    def _grain_at(self, cfg: vocabulary.PmConfig, gid: str) -> Path | None:
        """Any grain's document at the rev — the parent whose `order`
        `_pool_children` reads."""
        for kind in vocabulary.FLOW_KINDS:
            found = self._pool_grain(cfg, kind, gid)
            if found is not None:
                return found
        return None

    def feature_files(self, cfg: vocabulary.PmConfig, mid: str) -> list[Path]:
        if self.is_pooled(cfg):
            return self._pool_children(cfg, vocabulary.GRAIN_FEATURE, mid)
        mdir = self.milestone_dir(cfg, mid)
        if mdir is None:
            return []
        features = mdir / FEATURES_DIR
        return [d / vocabulary.FEATURE_DOC for d in self._dirs(features)
                if self.is_file(d / vocabulary.FEATURE_DOC)]

    def story_files(self, cfg: vocabulary.PmConfig, fid: str) -> list[Path]:
        if self.is_pooled(cfg):
            return self._pool_children(cfg, vocabulary.GRAIN_STORY, fid)
        ffile = self.feature_file(cfg, fid)
        return self._grain_docs(ffile.parent / STORIES_DIR) if ffile else []

    def bug_files(self, cfg: vocabulary.PmConfig, mid: str) -> list[Path]:
        if self.is_pooled(cfg):
            return self._pool_children(cfg, vocabulary.GRAIN_BUG, mid)
        mdir = self.milestone_dir(cfg, mid)
        return self._grain_docs(mdir / BUGS_DIR) if mdir is not None else []

    def field_of(self, path: Path, key: str) -> str:
        return frontmatter.field_of(self._doc(path), key)

    def is_file(self, path: Path) -> bool:
        """Is there a blob at this path at the rev? A tree is not a file —
        `git show <rev>:<dir>` succeeds with a listing."""
        rel = self._rel(path)
        if rel is None:
            return False
        if rel not in self._types:
            try:
                found = self._git(
                    ['cat-file', '-t', f'{self.rev}{REV_SEPARATOR}{rel}'])
            except GitError:
                found = b''
            self._types[rel] = found.decode('utf-8', 'replace').strip()
        return self._types[rel] == BLOB

    def ledger_rows(self, path: Path) -> list:
        """The milestone's rows at the rev; an absent ledger is no rows, and
        one that will not parse is `ledger.LedgerError` naming `<rev>:<path>`.
        """
        if not self.is_file(path):
            return []
        return ledger.read_rows(self._doc(path))

    def milestone_doc(self, handle: Path) -> Path:
        """`inventory.milestone_doc` at the rev: a pooled handle IS the document."""
        return handle if self.is_file(handle) else handle / vocabulary.MILESTONE_DOC

    def ledger_for(self, cfg: vocabulary.PmConfig, mid: str) -> Path:
        """`ledger.ledger_for` at the rev."""
        if self.is_pooled(cfg):
            return ledger.ledgers_dir(cfg) / f'{mid}.jsonl'
        mdir = self.milestone_dir(cfg, mid)
        return (ledger.ledger_path(mdir) if mdir is not None
                else ledger.grainless_path(cfg.roadmap))

class Grain(NamedTuple):
    """One story, feature or bug under the milestone, as the TREE holds it."""
    gid: str
    kind: str


# --- the numbers --------------------------------------------------------------
def _int(value: object) -> int | None:
    """The integer on the row, or None for anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _text(value: object) -> str:
    """The string on the row, or '' for anything that is not one."""
    return value if isinstance(value, str) else ''


def _plus(running: int | None, value: object) -> int | None:
    """`running` plus `value`, where an absent or non-integer value adds
    nothing: `None + absent` stays None, `0 + absent` stays 0. No number is
    ever this module's reason to fail."""
    if _int(value) is None:
        return running
    return value if running is None else running + value  # type: ignore[operator]


def _tally(values) -> dict[str, int]:
    """Count per distinct value, sorted by value."""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _agent_of(row: dict) -> str:
    agent = row.get(AGENT_ID_KEY)
    if row.get(ledger.KIND_FIELD) != ledger.KIND_DISPATCH or not isinstance(agent, str):
        return ''
    return agent


def _folded(courier: dict, hand: dict) -> dict:
    """The hand row's grain on the courier row's numbers; the hand's where it has none."""
    data = dict(courier)
    if hand.get(ledger.GRAIN_FIELD):
        data[ledger.GRAIN_FIELD] = hand[ledger.GRAIN_FIELD]
    spend = ('usage', TOTAL_KEY) if not courier.get('usage') else ()
    for key in (*spend, *COUNT_KEYS, AGENT_TYPE_KEY):
        if key in hand and courier.get(key) in (None, '', {}):
            data[key] = hand[key]
    return data


def join_twins(rows: list) -> tuple[list, int]:
    """(rows, pairs joined): each hand dispatch row folded into the ONE courier
    row a transcript measured under its `agent_id` (#39), since rows are never
    rewritten (D7). No id, or not exactly one courier, joins nothing."""
    couriers: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        if _agent_of(row.data) and MEASURED_KEY in row.data:
            couriers.setdefault(_agent_of(row.data), []).append(i)
    out, folded = list(rows), set()
    for i, row in enumerate(rows):
        twins = couriers.get(_agent_of(row.data), [])
        if MEASURED_KEY in row.data or len(twins) != 1:
            continue
        out[twins[0]] = out[twins[0]]._replace(
            data=_folded(out[twins[0]].data, row.data))
        folded.add(i)
    return [row for i, row in enumerate(out) if i not in folded], len(folded)


# --- the tree -----------------------------------------------------------------
def _grain(src: Source, path: Path, kind: str, fallback: str) -> Grain:
    """One grain document as a row: its own `id:` (the id `_ledger_id` writes,
    which the report joins on); a missing id falls back to the path's."""
    return Grain(src.field_of(path, vocabulary.FIELD_ID) or fallback, kind)


def _bug_slug(mdir: Path, path: Path) -> str:
    """`bugs/` was walked recursively, so a bug's slug could carry a directory.
    Only reachable for a NESTED tree — a pooled bug declares its id."""
    try:
        return path.relative_to(mdir / BUGS_DIR).with_suffix('').as_posix()
    except ValueError:
        return path.stem


def walk_grains(src: Source, cfg: vocabulary.PmConfig, mid: str,
                mdir: Path) -> tuple[list[Grain], dict[str, set[str]]]:
    """Every grain under the milestone, and which stories each feature owns —
    the walkers `check pm` uses."""
    grains: list[Grain] = []
    owned: dict[str, set[str]] = {}
    for ffile in src.feature_files(cfg, mid):
        # The id the document DECLARES, with the path-derived one as the
        # fallback for a nested tree that has not migrated (0.4.0).
        feature = _grain(src, ffile, KIND_FEATURE, f'{mid}/{ffile.parent.name}')
        grains.append(feature)
        stories = set()
        for sfile in src.story_files(cfg, feature.gid):
            story = _grain(src, sfile, KIND_STORY,
                           f'{feature.gid}/{sfile.stem}')
            grains.append(story)
            stories.add(story.gid)
        owned[feature.gid] = stories
    for bfile in src.bug_files(cfg, mid):
        grains.append(_grain(src, bfile, KIND_BUG,
                             f'{mid}/{BUGS_DIR}/{_bug_slug(mdir, bfile)}'))
    return grains, owned


def named_grains(row: dict, kinds: dict[str, str],
                 owned: dict[str, set[str]]) -> set[str]:
    """The grains under this milestone that one row names.

    `grain` — what the work was TOLD it was on (0.4.0/D2) — outranks the `tree`
    snapshot, and **a row that states a grain is placed by it and by nothing
    else**: falling through billed a row naming a since-renamed story to
    whichever OTHER story was live.

    **A snapshot places a row only when it names exactly ONE story** (0.4.0/D8,
    its finest-kind clause superseded in 0.9.0): a feature is that story's
    roll-up, never a candidate, since bugs and milestone work are in no snapshot.
    Category keys when present; frozen keys only for an old-shape row.
    """
    stated = row.get(ledger.GRAIN_FIELD)
    if isinstance(stated, str) and stated:
        return {stated} | {fid for fid, stories in owned.items()
                           if stated in stories} if stated in kinds else set()
    buckets_by_kind = LEGACY_BUCKETS if is_legacy(row) else CATEGORY_BUCKETS
    stories = {gid for gid in _named_through(row, buckets_by_kind, kinds, owned)
               if kinds.get(gid) == KIND_STORY}
    if len(stories) != 1:
        return set()
    return stories | {fid for fid, sids in owned.items() if sids & stories}


def _named_through(row: dict, buckets_by_kind: tuple, kinds: dict[str, str],
                   owned: dict[str, set[str]]) -> set[str]:
    """`named_grains`' rule over one key family."""
    tree = row.get('tree')
    if not isinstance(tree, dict):
        return set()
    named: set[str] = set()
    for kind, buckets in buckets_by_kind:
        for bucket in buckets:
            ids = tree.get(bucket)
            for gid in ids if isinstance(ids, list) else ():
                if kinds.get(gid) == kind:
                    named.add(gid)
    for fid, stories in owned.items():
        if stories & named:
            named.add(fid)
    return named


def is_legacy(row: dict) -> bool:
    """Was this row written before the snapshot carried categories? A row with
    no `tree` at all is not legacy; it never snapshotted."""
    tree = row.get('tree')
    return isinstance(tree, dict) and not (CATEGORY_KEYS & set(tree))


class Claim(NamedTuple):
    """What one milestone may claim a row by: the grains it holds (itself
    included), which stories each feature owns, and its declared branch."""
    kinds: dict[str, str]
    owned: dict[str, set[str]]
    branch: str


def claim_of(src: Source, cfg: vocabulary.PmConfig, mid: str,
             mdir: Path) -> tuple[Claim, list[Grain]]:
    """The milestone's claim, read off its tree and its own `branch:`."""
    grains, owned = walk_grains(src, cfg, mid, mdir)
    kinds = {g.gid: g.kind for g in grains}
    kinds[mid] = KIND_MILESTONE
    branch = src.field_of(src.milestone_doc(mdir), BRANCH_FIELD)
    return Claim(kinds, owned, '' if branch in ('', 'null') else branch), grains


def owns(row: dict, claim: Claim) -> bool:
    """Does this milestone own this row? A stated grain decides alone; a row
    naming no grain is placed by its `branch` when it carries one, and by its
    `tree` snapshot only when it carries neither — each a stamp the tree made
    when the row was filed, never a guess from timestamps. So two milestones
    with distinct grains and distinct branches can never share a row."""
    if _text(row.get(ledger.GRAIN_FIELD)):
        return row[ledger.GRAIN_FIELD] in claim.kinds
    branch = _text(row.get(BRANCH_FIELD))
    if branch:
        return branch == claim.branch
    return bool(named_grains(row, claim.kinds, claim.owned))


# --- the clock ----------------------------------------------------------------
def in_time_order(rows: list) -> list:
    """The rows sorted stably by their own `ts`, unstamped ones last. The
    file's order is not time order under `merge=union`, and a subtraction over
    merged file order bills a negative stint.
    """
    return sorted(rows, key=lambda row: (
        (stamp := ledger.parse_ts(row.data.get(ledger.TS_FIELD))) is None, stamp))


def arrival_state(row: dict) -> str:
    """The state this row says a grain ARRIVED at, or '' when it says none.

    Two rows carry the one event (D3) — `to` on the `status` row, `state` on
    the `disposition` row the same move mints — and reading BOTH is what makes
    the clock hook-free."""
    if arrive.disposition_of(row):
        state = row.get('state')
    elif row.get(ledger.KIND_FIELD) == ledger.KIND_STATUS:
        state = row.get('to')
    else:
        return ''
    return state if isinstance(state, str) else ''


def arrivals(rows: list) -> list[tuple[datetime, str]]:
    """Every arrival on one grain, oldest first, each STINT counted ONCE.

    The fold is on the STATE: one move writes two rows and a no-op re-run
    writes another, and none is a second arrival at a state nobody left —
    folding on the stamp alone billed part of an OPEN stint as a closed one.
    An unparseable `ts` is no arrival: `build` sorted it past every stamp.
    """
    marks: list[tuple[datetime, str]] = []
    for row in rows:
        state = arrival_state(row.data)
        stamp = ledger.parse_ts(row.data.get(ledger.TS_FIELD))
        if not state or stamp is None or (marks and marks[-1][1] == state):
            continue
        marks.append((stamp, state))
    return marks


def state_seconds(rows: list) -> dict[str, int]:
    """Seconds in each state, by subtraction over consecutive ARRIVALS; the
    interval belongs to the state the earlier arrival reached. The time after
    the last is the OPEN charge below and never a completed number, and a
    state nobody held gets no key rather than a zero."""
    seconds: dict[str, int] = {}
    marks = arrivals(rows)
    for (start, state), (end, _unused) in zip(marks, marks[1:]):
        seconds[state] = seconds.get(state, 0) + int(
            (end - start).total_seconds())
    return seconds


def _now() -> datetime:
    """Read time, asked ONCE so every open charge shares one instant."""
    return datetime.now(timezone.utc)


def open_charge(cfg: vocabulary.PmConfig, kind: str, rows: list,
                now: datetime | None = None) -> tuple[str, int | None]:
    """(the state this grain is sitting in now, seconds since it got there),
    or `('', None)` — a closed grain accrues nothing, and one nobody ever
    moved is UNMEASURED rather than zero (rule 4)."""
    marks = arrivals(rows)
    if not marks:
        return '', None
    stamp, state = marks[-1]
    if ledger.ends_grain(cfg, kind, state):
        return '', None
    return state, max(0, int(((now or _now()) - stamp).total_seconds()))


# --- the roll-up --------------------------------------------------------------
# Roll-up is the FEATURE, not a view: membership is a field, so a
# milestone's building time is a WALK of its features' and theirs of their
# stories' — every level the one below plus its own, open charge included.
CLOCK_TITLE = 'time per state'
KIND_COLUMN = 'kind'
STATE_SUFFIX = '_s'
CLOSED_COLUMN = 'closed_s'
OPEN_COLUMN = 'open_s'
OPEN_STATE_COLUMN = 'open_state'
GRAINS_COLUMN = 'grains'
# What `--help` names, in order (rule 11's read side): "total review time for
# this milestone" is `… | awk` over these, never a flag this verb grew.
CLOCK_COLUMNS = (GRAIN_COLUMN, f'<state>{STATE_SUFFIX}', CLOSED_COLUMN,
                 OPEN_COLUMN, OPEN_STATE_COLUMN)


def _sum_into(into: dict[str, int], more: dict[str, int]) -> None:
    """One grain's seconds folded into its parent's; absent stays absent."""
    for state, spent in more.items():
        into[state] = into.get(state, 0) + spent


def subtree(rows: list[dict], focus: str) -> list[dict]:
    """`focus`'s clock row and its descendants', re-based so it is the root:
    tree order and `depth` are the shape, so a LEVEL is a slice, not a walk."""
    at = next((i for i, row in enumerate(rows) if row[GRAIN_COLUMN] == focus),
              None)
    if at is None:
        return []
    base = rows[at]['depth']
    kept = [rows[at]]
    for row in rows[at + 1:]:
        if row['depth'] <= base:
            break
        kept.append(row)
    return [dict(row, depth=row['depth'] - base) for row in kept]


def clock_data(cfg: vocabulary.PmConfig, mid: str, grains: list, owned: dict,
               rows: list, now: datetime | None = None,
               focus: str = '') -> dict:
    """The milestone, its features, their stories and its bugs, each with the
    seconds ITS OWN SUBTREE spent in each state and the charge it is accruing.
    `grains` arrives in tree order from `walk_grains`, so `depth` is the shape
    and the walk is the sum."""
    when = now or _now()
    kinds = {g.gid: g.kind for g in grains}
    kinds[mid] = KIND_MILESTONE
    mine: dict[str, list] = {}
    for row in rows:
        gid = row.data.get(ledger.GRAIN_FIELD)
        if isinstance(gid, str) and gid in kinds:
            mine.setdefault(gid, []).append(row)
    own = {gid: state_seconds(mine.get(gid, [])) for gid in kinds}
    charge = {gid: open_charge(cfg, kind, mine.get(gid, []), when)
              for gid, kind in kinds.items()}
    rolled = {gid: dict(spent) for gid, spent in own.items()}
    open_s = {gid: seconds for gid, (_state, seconds) in charge.items()}
    stories = {sid for owns_ in owned.values() for sid in owns_}
    for feature, owns_ in owned.items():
        for sid in owns_:
            _sum_into(rolled[feature], own[sid])
            open_s[feature] = _plus(open_s[feature], open_s[sid])
    for grain in grains:
        if grain.gid in stories:
            continue
        _sum_into(rolled[mid], rolled[grain.gid])
        open_s[mid] = _plus(open_s[mid], open_s[grain.gid])
    out = [_clock_row(mid, KIND_MILESTONE, 0, rolled, open_s, charge)]
    out.extend(_clock_row(g.gid, g.kind, 2 if g.gid in stories else 1,
                          rolled, open_s, charge) for g in grains)
    return {'rows': subtree(out, focus) if focus else out}


def _clock_row(gid: str, kind: str, depth: int, rolled: dict, open_s: dict,
               charge: dict) -> dict:
    """One row of the roll-up: `state_s` is what the table prints (own plus
    every descendant's), `open_state` this grain's OWN state."""
    spent = rolled[gid]
    return {GRAIN_COLUMN: gid, KIND_COLUMN: kind, 'depth': depth,
            'state_s': dict(spent),
            CLOSED_COLUMN: sum(spent.values()) if spent else None,
            OPEN_COLUMN: open_s[gid],
            OPEN_STATE_COLUMN: charge[gid][0] or None}


def clock_columns(cfg: vocabulary.PmConfig, rows: list) -> tuple[str, ...]:
    """Which state WORDS this milestone's rows hold, in the order the project
    declared them and any word `[pm.states.*]` does not name appended. A state
    nobody held is no column: a zero nobody measured is the one number this
    report must never print (rule 4)."""
    held = {state for row in rows for state in row['state_s']}
    declared = list(dict.fromkeys(state for kind in vocabulary.FLOW_KINDS
                                  for state in vocabulary.flow_of(cfg, kind).order))
    named = [state for state in declared if state in held]
    return tuple(named + sorted(held - set(named)))


def clock_lines(cfg: vocabulary.PmConfig, data: dict) -> list[str]:
    """One row per grain in tree order, indented by depth."""
    rows = data['rows']
    states = clock_columns(cfg, rows)
    headers = (GRAIN_COLUMN, *(f'{s}{STATE_SUFFIX}' for s in states),
               CLOSED_COLUMN, OPEN_COLUMN, OPEN_STATE_COLUMN)
    aligns = (LEFT,) + (RIGHT,) * (len(headers) - 2) + (LEFT,)
    body = [(f'{SUB_ROW_INDENT * entry["depth"]}{entry[GRAIN_COLUMN]}',
             *(_cell(entry['state_s'].get(state)) for state in states),
             _cell(entry[CLOSED_COLUMN]), _cell(entry[OPEN_COLUMN]),
             entry[OPEN_STATE_COLUMN] or DASH) for entry in rows]
    return _table(f'{CLOCK_TITLE} ({len(rows)})', headers, aligns, body)


# --- the units ----------------------------------------------------------------
# A UNIT is one piece of work with a start and a stop: a `stamp` start paired
# with the next unclaimed stop on the same grain, or one `dispatch` row, whose
# start is its `ts` less its `duration_s`. Pairing is by grain and order alone:
# which of two concurrent starts a stop closes is the earlier one, because the
# row says nothing more and this module may not guess (rule 9).
def _issues(*rows: dict) -> list[str]:
    """Every issue the rows name, first seen first."""
    out: list[str] = []
    for row in rows:
        value = row.get(ISSUE_FIELD)
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, str) and item and item not in out:
                out.append(item)
    return out


def _unit(grain: str, start: str, stop: str, *, issue: list[str] | None = None,
          agent: str = '', duration: int | None = None,
          tokens: int | None = None, outcome: str = '', kind: str) -> dict:
    return {GRAIN_COLUMN: grain or None, ISSUE_COLUMN: issue or [],
            AGENT_COLUMN: agent or None, START_COLUMN: start or None,
            STOP_COLUMN: stop or None, DURATION_COLUMN: duration,
            TOKENS_COLUMN: tokens, OUTCOME_COLUMN: outcome or None,
            KIND_COLUMN: kind}


def _seconds_between(start: str, stop: str) -> int | None:
    begun, ended = ledger.parse_ts(start), ledger.parse_ts(stop)
    if begun is None or ended is None:
        return None
    return int((ended - begun).total_seconds())


def stamp_units(rows: list) -> tuple[list[dict], list[dict]]:
    """(units, the stamp rows no unit holds). An unpaired start is an OPEN
    unit, stop blank; an unpaired stop is returned to be COUNTED."""
    units: list[dict] = []
    stray: list[dict] = []
    waiting: dict[str, list[tuple[dict, dict]]] = {}
    for row in rows:
        data = row.data
        if data.get(ledger.KIND_FIELD) != KIND_STAMP:
            continue
        grain, edge = _text(data.get(ledger.GRAIN_FIELD)), data.get(EDGE_FIELD)
        if edge == EDGE_START:
            unit = _unit(grain, _text(data.get(ledger.TS_FIELD)), '',
                         issue=_issues(data),
                         agent=_text(data.get(AGENT_FIELD)), kind=KIND_STAMP)
            units.append(unit)
            waiting.setdefault(grain, []).append((unit, data))
            continue
        if edge != EDGE_STOP or not waiting.get(grain):
            stray.append(data)
            continue
        unit, begun = waiting[grain].pop(0)
        stop = _text(data.get(ledger.TS_FIELD))
        unit.update({
            STOP_COLUMN: stop or None,
            DURATION_COLUMN: _seconds_between(unit[START_COLUMN] or '', stop),
            ISSUE_COLUMN: _issues(begun, data),
            AGENT_COLUMN: unit[AGENT_COLUMN] or _text(data.get(AGENT_FIELD)) or None,
            TOKENS_COLUMN: _int(data.get(TOKENS_FIELD)),
            OUTCOME_COLUMN: _text(data.get(OUTCOME_FIELD)) or None})
    return units, stray


def dispatch_unit(row: dict, grain: str) -> dict:
    """One dispatch row as a unit: it ENDED at `ts` and ran `duration_s`, so
    its start is the subtraction, blank when either is missing."""
    stop = _text(row.get(ledger.TS_FIELD))
    duration = _int(row.get('duration_s'))
    ended = ledger.parse_ts(stop)
    start = ((ended - timedelta(seconds=duration)).strftime(ledger.TS_FORMAT)
             if ended is not None and duration is not None else '')
    return _unit(grain, start, stop, agent=_text(row.get(AGENT_TYPE_KEY)),
                 duration=duration, tokens=_int(row.get(TOTAL_KEY)),
                 outcome=_text(row.get(OUTCOME_FIELD)), kind=ledger.KIND_DISPATCH)


def agent_rows(units: list[dict]) -> list[dict]:
    """Units, tokens and duration per agent, and each agent's share of the
    tokens the units recorded — `-` when none recorded any."""
    tally: dict[str | None, dict] = {}
    for unit in units:
        entry = tally.setdefault(unit[AGENT_COLUMN], {
            AGENT_COLUMN: unit[AGENT_COLUMN], UNITS_COLUMN: 0,
            TOKENS_COLUMN: None, DURATION_COLUMN: None})
        entry[UNITS_COLUMN] += 1
        entry[TOKENS_COLUMN] = _plus(entry[TOKENS_COLUMN], unit[TOKENS_COLUMN])
        entry[DURATION_COLUMN] = _plus(entry[DURATION_COLUMN],
                                       unit[DURATION_COLUMN])
    total = None
    for entry in tally.values():
        total = _plus(total, entry[TOKENS_COLUMN])
    for entry in tally.values():
        spent = entry[TOKENS_COLUMN]
        entry[SHARE_COLUMN] = (round(100 * spent / total)
                               if total and spent is not None else None)
    return [tally[key] for key in sorted(tally, key=lambda k: (k is None, k or ''))]


# --- one milestone ------------------------------------------------------------
AT_REV = ' — at {rev}'


def build(cfg: vocabulary.PmConfig, mid: str, mdir: Path, own_rows: list,
          root_rows: list, src: Source | None = None) -> dict:
    """The whole report as one object — what `--json` prints. `own_rows` are
    the milestone's ledger, `root_rows` the tree's; a row is read only if the
    milestone OWNS it (`owns`), and a row in its own ledger it cannot place is
    counted, never folded in. `rev` is present only when there was one."""
    src = DiskSource() if src is None else src
    own_lines = {row.line for row in own_rows}
    rows, joined = join_twins(in_time_order(list(own_rows) + list(root_rows)))
    claim, grains = claim_of(src, cfg, mid, mdir)
    mine, superseded, no_grain = [], [], []
    for row in rows:
        if owns(row.data, claim):
            mine.append(row)
        elif row.line in own_lines:
            (superseded if _text(row.data.get(ledger.GRAIN_FIELD))
             else no_grain).append(row.data)
    units, unpaired = stamp_units(mine)
    for row in mine:
        if row.data.get(ledger.KIND_FIELD) == ledger.KIND_DISPATCH:
            named = named_grains(row.data, claim.kinds, claim.owned)
            stated = _text(row.data.get(ledger.GRAIN_FIELD))
            story = [g for g in named if claim.kinds.get(g) == KIND_STORY]
            units.append(dispatch_unit(
                row.data, stated or (story[0] if story else '')))
    units.sort(key=lambda u: u[START_COLUMN] or u[STOP_COLUMN] or '')
    for number, unit in enumerate(units, 1):
        unit[UNIT_COLUMN] = number
    spent = None
    for data in superseded:
        spent = _plus(spent, data.get(TOTAL_KEY))
        spent = _plus(spent, data.get(TOKENS_FIELD))
    out: dict = {
        MILESTONE_KEY: mid, BRANCH_FIELD: claim.branch or None,
        GRAINS_COLUMN: len(grains), JOINED_KEY: joined,
        'units': units, 'agents': agent_rows(units),
        'clock': clock_data(cfg, mid, grains, claim.owned,
                            [r for r in mine if arrival_state(r.data)]),
        'owned': _tally(_text(r.data.get(ledger.KIND_FIELD)) or DASH
                        for r in mine),
        'unpaired': len(unpaired),
        'superseded': {'rows': len(superseded), 'tokens': spent,
                       'grains': sorted({d[ledger.GRAIN_FIELD]
                                         for d in superseded})},
        'no_grain': len(no_grain)}
    if src.rev:
        out['rev'] = src.rev
    return out


def heading_id(data: dict) -> str:
    """The milestone id as a heading names it, plus ` — at <rev>` from git."""
    rev = data.get('rev')
    return f'{data[MILESTONE_KEY]}{AT_REV.format(rev=rev)}' if rev else str(
        data[MILESTONE_KEY])


def _cell(value: object) -> str:
    """One number as a cell: the integer, or `-` when nobody recorded it."""
    return DASH if value is None else str(value)


def _table(title: str, headers: tuple[str, ...], aligns: tuple[str, ...],
           rows: list[tuple[str, ...]]) -> list[str]:
    """One `-- <title> (n)` block, columns padded; the heading prints even at
    `(0)`, because silence reads like a scan that never happened."""
    lines = [f'{BLOCK_PREFIX} {title}']
    if not rows:
        return lines
    widths = [max(len(header), *(len(row[i]) for row in rows))
              for i, header in enumerate(headers)]
    for cells in [headers, *rows]:
        lines.append(COLUMN_GAP.join(
            cell.ljust(width) if align == LEFT else cell.rjust(width)
            for cell, align, width in zip(cells, aligns, widths)).rstrip())
    return lines


def _by_kind(counts: dict[str, int]) -> str:
    return ', '.join(f'{kind} {n}' for kind, n in counts.items()) or 'none'


def render(cfg: vocabulary.PmConfig, data: dict) -> list[str]:
    """The report as lines: the units, the agents, the clock, the counts."""
    units, agents = data['units'], data['agents']
    tokens = None
    for unit in units:
        tokens = _plus(tokens, unit[TOKENS_COLUMN])
    out = [f'{HEADING_PREFIX} {heading_id(data)} — {STAMP_TITLE} — '
           f'{len(units)} unit(s), '
           f'{sum(1 for u in units if u[STOP_COLUMN] is None)} open unit(s), '
           f'{_cell(tokens)} token(s)', '']
    out.extend(_table(
        f'{UNIT_TITLE} ({len(units)})', UNIT_COLUMNS,
        (RIGHT, LEFT, LEFT, LEFT, LEFT, LEFT, RIGHT, RIGHT, LEFT),
        [(str(u[UNIT_COLUMN]), u[GRAIN_COLUMN] or DASH,
          ISSUE_SEPARATOR.join(u[ISSUE_COLUMN]) or DASH,
          u[AGENT_COLUMN] or DASH, u[START_COLUMN] or DASH,
          u[STOP_COLUMN] or DASH, _cell(u[DURATION_COLUMN]),
          _cell(u[TOKENS_COLUMN]), u[OUTCOME_COLUMN] or DASH)
         for u in units]))
    out.append('')
    out.extend(_table(
        f'{AGENT_TITLE} ({len(agents)})', AGENT_COLUMNS,
        (LEFT, RIGHT, RIGHT, RIGHT, RIGHT),
        [(a[AGENT_COLUMN] or DASH, str(a[UNITS_COLUMN]),
          _cell(a[TOKENS_COLUMN]), _cell(a[DURATION_COLUMN]),
          DASH if a[SHARE_COLUMN] is None else f'{a[SHARE_COLUMN]}{SHARE_MARK}')
         for a in agents]))
    out.append('')
    out.extend(clock_lines(cfg, data['clock']))
    out.append('')
    owned = data['owned']
    branch = data[BRANCH_FIELD]
    out.append(f'{NOTE_INDENT}{sum(owned.values())} {OWNED_NOTE}: '
               f'{_by_kind(owned)} — '
               + (f'by grain, or by branch {branch} on a row naming no grain'
                  if branch else f'by grain; {NO_BRANCH_NOTE}'))
    out.append(f'{NOTE_INDENT}{data["unpaired"]} {UNPAIRED_NOTE}')
    superseded = data['superseded']
    out.append(NOTE_INDENT + SUPERSEDED_NOTE.format(
        rows=superseded['rows'], tokens=_cell(superseded['tokens']))
        + (f': {", ".join(superseded["grains"])}' if superseded['grains']
           else ''))
    out.append(f'{NOTE_INDENT}{data["no_grain"]} {NO_GRAIN_NOTE}')
    out.append(f'{NOTE_INDENT}{data.get(JOINED_KEY, 0)} {JOINED_NOTE}')
    return out


def clock_report(cfg: vocabulary.PmConfig, mid: str, mdir: Path, rows: list,
                 src: Source, focus: str) -> dict:
    """The clock at the LEVEL an id names — `pm ledger report <feature-id>`.
    The rows are the milestone's, because that is where a ledger is (D6); the
    id chooses which grain roots the table."""
    grains, owned = walk_grains(src, cfg, mid, mdir)
    arrived = [r for r in in_time_order(rows) if arrival_state(r.data)]
    out = {MILESTONE_KEY: mid, 'focus': focus,
           'clock': clock_data(cfg, mid, grains, owned, arrived, focus=focus)}
    if src.rev:
        out['rev'] = src.rev
    return out


def clock_render(cfg: vocabulary.PmConfig, data: dict) -> list[str]:
    """The focused report as lines: the grain, its milestone, the clock."""
    rows = data['clock']['rows']
    return [f'{HEADING_PREFIX} {data["focus"]} — {CLOCK_TITLE} — '
            f'{len(rows)} grain(s), from {heading_id(data)}',
            ''] + clock_lines(cfg, data['clock'])


# --- the tree: the rows no milestone owns -------------------------------------
# Gate, test, verify and session rows, and dispatches naming no grain, land in
# the tree's ledger (0.4.0/D3). A milestone claims the ones stamped with its
# declared branch; the rest are the TREE's, reported once, under their own
# heading — never under every milestone, which is what they used to be.
TREE_ID = 'tree'
GATES_TITLE = 'gate cost'
GATE_KEY = 'gate'
GATE_DURATION_KEY = 'duration_ms'
GATE_CENSUS_KEY = 'census'
RUNS_COLUMN = 'runs'
FIRST_MS_COLUMN = 'first_ms'
LAST_MS_COLUMN = 'last_ms'
DELTA_MS_COLUMN = 'delta_ms'
CENSUS_COLUMN = 'census'
WHY_COLUMN = 'why'
TS_COLUMN = 'ts'
GATE_COLUMNS = (GATE_KEY, RUNS_COLUMN, FIRST_MS_COLUMN, LAST_MS_COLUMN,
                DELTA_MS_COLUMN, CENSUS_COLUMN)
GATE_UNUSABLE_TITLE = 'rows this section could not use'
UNUSABLE_COLUMNS = (GATE_KEY, WHY_COLUMN, TS_COLUMN)
# Marks a delta whose corpus moved: still printed, but a bigger tree is not a
# regression.
INCOMPARABLE_MARK = '*'
CENSUS_ARROW = ' → '
MOVED_NOTE = 'census that moved or is absent'
TREE_ROWS_NOTE = 'tree row(s) no milestone owns, by kind'
BY_BRANCH_NOTE = 'the same rows by branch'
UNPLACED_NOTE = ('row(s) name a grain no milestone in this tree holds — '
                 'counted in no report')


def _gate_unusable(row: dict) -> str | None:
    """Why this `kind: gate` row cannot be counted, or None — named beside the
    row rather than dropped, so the table cannot look clean over discarded
    input."""
    name = row.get(GATE_KEY)
    if not isinstance(name, str) or not name:
        return 'no gate name'
    duration = row.get(GATE_DURATION_KEY)
    if duration is None:
        return f'no {GATE_DURATION_KEY}'
    if _int(duration) is None:
        return f'{GATE_DURATION_KEY} is not an integer'
    if duration < 0:
        return f'{GATE_DURATION_KEY} is negative'
    return None


def gates_data(rows: list[dict]) -> dict:
    """One entry per `gate`, slowest-latest first, ONE run per row; `delta_ms`
    is `last - first`. A gate with one run still appears, with `-`; a delta
    whose census moved is printed and marked (`comparable`)."""
    gate_rows = [r for r in rows if r.get(ledger.KIND_FIELD) == ledger.KIND_GATE]
    unusable, runs_of = [], {}
    for row in gate_rows:
        why = _gate_unusable(row)
        if why is not None:
            name = row.get(GATE_KEY)
            unusable.append({GATE_KEY: name if isinstance(name, str) and name
                             else None, WHY_COLUMN: why,
                             TS_COLUMN: _text(row.get(ledger.TS_FIELD)) or None})
            continue
        runs_of.setdefault(row[GATE_KEY], []).append(row)
    entries = []
    for name, runs in runs_of.items():
        first, last = runs[0][GATE_DURATION_KEY], runs[-1][GATE_DURATION_KEY]
        delta = last - first if len(runs) > 1 else None
        censuses = (_int(runs[0].get(GATE_CENSUS_KEY)),
                    _int(runs[-1].get(GATE_CENSUS_KEY)))
        entries.append({
            GATE_KEY: name, RUNS_COLUMN: len(runs),
            FIRST_MS_COLUMN: first, LAST_MS_COLUMN: last,
            DELTA_MS_COLUMN: delta,
            'first_census': censuses[0], 'last_census': censuses[1],
            'comparable': None if delta is None else (
                None not in censuses and censuses[0] == censuses[1])})
    entries.sort(key=lambda e: (-e[LAST_MS_COLUMN], e[GATE_KEY]))
    return {'gates': entries, 'unusable': unusable,
            'totals': {'rows': len(gate_rows), 'gates': len(entries),
                       'incomparable': sum(1 for e in entries
                                           if e['comparable'] is False),
                       'unusable': len(unusable)}}


def tree_data(root_rows: list, claims: list[Claim]) -> dict:
    """The tree's report: every root row no milestone's `Claim` owns. A row
    that NAMES a grain no milestone holds is counted, never kept."""
    rows, _joined = join_twins(in_time_order(list(root_rows)))
    mine, unplaced = [], 0
    for row in rows:
        if any(owns(row.data, claim) for claim in claims):
            continue
        if _text(row.data.get(ledger.GRAIN_FIELD)):
            unplaced += 1
            continue
        mine.append(row.data)
    return {MILESTONE_KEY: TREE_ID, 'gates': gates_data(mine),
            'rows': _tally(_text(r.get(ledger.KIND_FIELD)) or DASH
                           for r in mine),
            'branches': _tally(_text(r.get(BRANCH_FIELD)) or DASH
                               for r in mine),
            'unplaced': unplaced}


def _gate_census_cell(entry: dict) -> str:
    """`first → last`, or `-` when either end was never recorded — half a pair
    is no answer."""
    first, last = entry['first_census'], entry['last_census']
    return (DASH if first is None or last is None
            else f'{first}{CENSUS_ARROW}{last}')


def tree_lines(data: dict) -> list[str]:
    """The tree's report as lines: the gate table, what it could not use, and
    the counts."""
    section = data['gates']
    cost = []
    for entry in section['gates']:
        delta = (DASH if entry[DELTA_MS_COLUMN] is None
                 else f'{entry[DELTA_MS_COLUMN]:+d}')
        if entry['comparable'] is False:
            delta += INCOMPARABLE_MARK
        cost.append((entry[GATE_KEY], str(entry[RUNS_COLUMN]),
                     _cell(entry[FIRST_MS_COLUMN]), _cell(entry[LAST_MS_COLUMN]),
                     delta, _gate_census_cell(entry)))
    unusable = [(_cell(e[GATE_KEY]), e[WHY_COLUMN], _cell(e[TS_COLUMN]))
                for e in section['unusable']]
    totals = section['totals']
    out = [f'{HEADING_PREFIX} {TREE_ID} — {GATES_TITLE} — '
           f'{totals["rows"]} gate row(s), {totals["gates"]} gate(s), '
           f'{totals["incomparable"]} delta(s) marked {INCOMPARABLE_MARK} for '
           f'a {MOVED_NOTE}, {totals["unusable"]} row(s) this section could '
           f'not use', '']
    out.extend(_table(f'{GATE_KEY} ({len(cost)})', GATE_COLUMNS,
                      (LEFT, RIGHT, RIGHT, RIGHT, RIGHT, LEFT), cost))
    out.append('')
    out.extend(_table(f'{GATE_UNUSABLE_TITLE} ({len(unusable)})',
                      UNUSABLE_COLUMNS, (LEFT, LEFT, LEFT), unusable))
    out.append('')
    out.append(f'{NOTE_INDENT}{sum(data["rows"].values())} {TREE_ROWS_NOTE}: '
               f'{_by_kind(data["rows"])}; {BY_BRANCH_NOTE}: '
               f'{_by_kind(data["branches"])}')
    out.append(f'{NOTE_INDENT}{data["unplaced"]} {UNPLACED_NOTE}')
    return out


# --- more than one milestone, side by side ------------------------------------
# **The comparison is these same reports' own totals, put beside each other**,
# then the tree's report once, under its own heading: every number is read out
# of a document `build` already returned, and no row is under two milestones.
#
# THE SHAPE: rows are MILESTONES, so a block has the same columns whether two
# ids are named or five and `… | awk '$1 == "delta"'` means one thing every
# time; the delta is a ROW, `last - first`.
COMPARE_TITLE = 'milestone comparison'
COMPARE_COLUMN = MILESTONE_KEY
DELTA_ROW = 'delta'
# The plan is READ to sequence ids the caller named; it never chooses them
# (rule 9). Which basis was used is printed.
ORDER_PLAN = 'plan'
ORDER_GIVEN = 'given'
OPEN_UNITS_COLUMN = 'open_units'
ROWS_COLUMN = 'rows'
AGENTS_COLUMN = 'agents'


class CompareBlock(NamedTuple):
    """One block of the comparison: what it is called, the measures it lifts
    out of one milestone's document, and WHICH of those measures is the corpus
    the others were taken over — the column a moved census is read off."""
    title: str
    measures: Callable[[vocabulary.PmConfig, dict], dict]
    census: str


def _compare_units(cfg: vocabulary.PmConfig, doc: dict) -> dict:
    """The stamp table's totals, and how many rows the milestone owns."""
    tokens = duration = None
    for unit in doc['units']:
        tokens = _plus(tokens, unit[TOKENS_COLUMN])
        duration = _plus(duration, unit[DURATION_COLUMN])
    return {UNITS_COLUMN: len(doc['units']),
            OPEN_UNITS_COLUMN: sum(1 for u in doc['units']
                                   if u[STOP_COLUMN] is None),
            TOKENS_COLUMN: tokens, DURATION_COLUMN: duration,
            ROWS_COLUMN: sum(doc['owned'].values())}


def _compare_agents(cfg: vocabulary.PmConfig, doc: dict) -> dict:
    """Tokens per agent, one column each — `-` under a milestone that never
    dispatched it."""
    return {AGENTS_COLUMN: len(doc['agents']),
            **{entry[AGENT_COLUMN] or DASH: entry[TOKENS_COLUMN]
               for entry in doc['agents']}}


def _compare_clock(cfg: vocabulary.PmConfig, doc: dict) -> dict:
    """The milestone's OWN roll-up row — `clock_data` already summed every
    descendant into it. The grain census rides along."""
    rows = doc['clock']['rows']
    root = rows[0] if rows else {}
    spent = root.get('state_s') or {}
    return {GRAINS_COLUMN: doc[GRAINS_COLUMN],
            **{f'{state}{STATE_SUFFIX}': spent.get(state)
               for state in clock_columns(cfg, rows)},
            CLOSED_COLUMN: root.get(CLOSED_COLUMN),
            OPEN_COLUMN: root.get(OPEN_COLUMN)}


# The registry, in the order the report prints its blocks.
COMPARE_BLOCKS = (
    CompareBlock(UNIT_TITLE, _compare_units, UNITS_COLUMN),
    CompareBlock(AGENT_TITLE, _compare_agents, AGENTS_COLUMN),
    CompareBlock(CLOCK_TITLE, _compare_clock, GRAINS_COLUMN))


def _columns_of(cells: list[dict]) -> tuple[str, ...]:
    """Every measure any of these milestones carried, first seen first."""
    out: list[str] = []
    for row in cells:
        for key in row:
            if key not in out:
                out.append(key)
    return tuple(out)


def _difference(first: object, last: object) -> int | None:
    """`last - first`, or None when either end was never recorded."""
    a, b = _int(first), _int(last)
    return None if a is None or b is None else b - a


def compare_data(cfg: vocabulary.PmConfig, documents: list[tuple[str, dict]],
                 basis: str, tree: dict) -> dict:
    """More than one milestone as ONE object — what `--json` prints when more
    than one id is named. Top level::

        {"milestones": [<id>, ...],        # in the order compared
         "order": "plan" | "given",        # what sequenced them
         "blocks": [{"block": <title>,
                     "columns": [<measure>, ...],
                     "census": <measure>,   # the corpus the rest was taken over
                     "moved": <bool>,       # did that corpus move, first to last
                     "rows": [{"milestone": <id>, <measure>: <n|null>, ...}],
                     "delta": {<measure>: <n|null>, ...}}],   # last - first
         "tree": <the `--tree` document>}  # the rows no milestone owns
    """
    blocks = []
    for block in COMPARE_BLOCKS:
        cells = [block.measures(cfg, doc) for _mid, doc in documents]
        columns = _columns_of(cells)
        first, last = cells[0], cells[-1]
        moved = _difference(first.get(block.census),
                            last.get(block.census)) != 0
        blocks.append({
            'block': block.title, 'columns': list(columns),
            'census': block.census, 'moved': moved,
            'rows': [{COMPARE_COLUMN: mid,
                      **{c: row.get(c) for c in columns}}
                     for (mid, _doc), row in zip(documents, cells)],
            'delta': {c: _difference(first.get(c), last.get(c))
                      for c in columns}})
    return {'milestones': [mid for mid, _doc in documents],
            'order': basis, 'blocks': blocks, 'tree': tree}


def _delta_cell(value: int | None, moved: bool) -> str:
    """One delta: signed, `-` when either end was absent, `*` when the census
    under it moved."""
    if value is None:
        return DASH
    return f'{value:+d}{INCOMPARABLE_MARK}' if moved else f'{value:+d}'


def compare_lines(cfg: vocabulary.PmConfig, data: dict) -> list[str]:
    """The comparison as lines: one heading, one block per measure family with
    a row per milestone and a `delta` row under them, then the tree's report."""
    marked = sum(1 for block in data['blocks'] if block['moved'])
    out = [f'{HEADING_PREFIX} {CENSUS_ARROW.join(data["milestones"])} — '
           f'{COMPARE_TITLE} — {len(data["milestones"])} milestone(s) in '
           f'{data["order"]} order, {len(data["blocks"])} block(s), '
           f'{marked} block(s) marked {INCOMPARABLE_MARK} for a '
           f'{MOVED_NOTE}']
    for block in data['blocks']:
        columns = tuple(block['columns'])
        body = [(row[COMPARE_COLUMN], *(_cell(row[c]) for c in columns))
                for row in block['rows']]
        # The census column's own delta IS the statement that it moved.
        body.append((DELTA_ROW,
                     *(_delta_cell(block['delta'][c],
                                   block['moved'] and c != block['census'])
                       for c in columns)))
        out.append('')
        out.extend(_table(f'{block["block"]} ({len(block["rows"])})',
                          (COMPARE_COLUMN, *columns),
                          (LEFT,) + (RIGHT,) * len(columns), body))
    out.append('')
    out.extend(tree_lines(data['tree']))
    return out
