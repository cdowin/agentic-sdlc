"""report.py — `pm ledger report`: the milestone's raw rows, added up.

The ledger never judges; this is the caller judgement is left to. It may
**sum, count, subtract and group, never weight, price or label** — no `size:`
as a divisor, no dollar figure, no score. Stated here rather than cited,
because a dangling decision id reads as settled while stopping an argument
that was never had. Absent is `-`, not zero; the tree is walked, so every grain
gets a row; nothing is dropped. It fails only on a document that will not
parse, never on a number.
"""
from __future__ import annotations

import fnmatch
import io
import subprocess
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.repo.pm import arrive, ledger, model, verdict

# The two line shapes a consumer greps (rule 6); both carry the milestone id.
HEADING_PREFIX = '[ledger:report]'

# What a section calls itself in `--json` and in its heading, in the order the
# milestone asks.
SECTION_SPEND = 'spend'
SPEND_TITLE = 'spend per grain'
SECTION_YIELD = 'yield'
YIELD_TITLE = 'yield per review pass'
SECTION_REWORK = 'rework'
REWORK_TITLE = 'rework'
SECTION_ESCAPES = 'escapes'
ESCAPES_TITLE = 'escapes'
SECTION_OVERHEAD = 'overhead'
OVERHEAD_TITLE = 'overhead shape'
SECTION_GATES = 'gates'
GATES_TITLE = 'gate cost'

# Printed for a number nobody recorded: a blank reads as zero and a `0` would
# be a lie.
DASH = '-'

# No `ledger.jsonl` at all: a fact, exit 0, one line.
NO_LEDGER = 'no ledger'

# A section that found nothing to count prints one line, never a table of
# zeros.
NO_DATA = 'no data'

# The shape `pm status` already uses for its phase buckets.
COLUMN_GAP = '  '
BLOCK_PREFIX = '--'
SUB_ROW_INDENT = '  '

# Frontmatter key printed as a column and used for nothing else — never a
# divisor: dividing spend by `size` would be this module pricing work.
SIZE_FIELD = 'size'

# Grain kinds, in the order their tables print.
KIND_STORY = model.GRAIN_STORY
KIND_FEATURE = model.GRAIN_FEATURE
KIND_BUG = model.GRAIN_BUG
KIND_ORDER = (KIND_STORY, KIND_FEATURE, KIND_BUG)

# D3's snapshot buckets, by the kind of grain whose ids they hold;
# `milestones_in_progress` is on every row and would attribute every dispatch
# to every grain.
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
# What a spend table says about old-shape rows that named nothing here: one of
# three things, and only that it is not the fourth.
LEGACY_NOTE = ('predate category keys and name no grain of this milestone — '
               'an idle tree, another milestone\'s work, or words that shape '
               'could not spell; not counted as empty')
UNPLACED_NOTE = ('spent time in a state this declaration does not name — '
                 'seconds in no category column, not zero')
# UNPLACED_NOTE's dispatch-side twin: the drop is said out loud.
FROZEN_ONLY_NOTE = ('named only through a deprecated key — at a word this '
                    'declaration does not place in in_progress, so counted '
                    'in no column above')

# Column label <- `usage` key, in `ledger.USAGE_FIELDS` order so a new field
# appears rather than being dropped.
USAGE_KEYS = tuple(name for name, _ in ledger.USAGE_FIELDS)
USAGE_LABELS = {'input': 'in', 'output': 'out',
                'cache_creation': 'cache_create', 'cache_read': 'cache_read'}

# The two summed keys a dispatch row carries outside `usage`.
COUNT_KEYS = ('tool_calls', 'duration_s')

# A hand-recorded ONE TOTAL, summed in its own column and folded into no other.
# `in`/`out` is a split somebody MEASURED; this is a number somebody was TOLD,
# and adding the two would report a spend nobody observed.
TOTAL_KEY = ledger.TOTAL_KEY
TOTAL_ROWS = 'total_rows'
SPLIT_NOTE = ('reported ONE total rather than the measured split — summed in '
              f'`{TOTAL_KEY}` and added into no other column, because a total '
              'and a split are not the same measurement')

# The columns every spend table opens with, before the per-state ones.
SPEND_COLUMNS = ('dispatches',) + tuple(
    USAGE_LABELS[key] for key in USAGE_KEYS) + (TOTAL_KEY,) + COUNT_KEYS
GRAIN_COLUMN = 'grain'
KIND_COLUMN = 'kind'
SIZE_COLUMN = 'size'
TOTAL_COLUMN = 'total_s'
NO_GRAIN_TITLE = 'rows naming no grain'
# Said beside that bucket and counted apart from it: a row that named its grain
# precisely, and named one this milestone does not hold, is the OPPOSITE of a
# row that named none.
ELSEWHERE_NOTE = ('name a grain this milestone does not hold — another '
                  'milestone\'s work, read out of the tree\'s shared ledger; '
                  'not unattributed')

# The payload key naming which milestone the report is OF — a key, not a kind.
MILESTONE_KEY = 'milestone'

# Section 2's columns; `verdict.DISPOSITION_KINDS` supplies the disposition
# columns, so a new kind appears rather than counting into nothing.
FEATURE_COLUMN = 'feature'
RECORD_COLUMN = 'record'
# One record, N passes; the ordinal is a column so two passes are told apart.
PASS_COLUMN = 'pass'
VERDICT_COLUMN = 'verdict'
FINDINGS_COLUMN = 'findings'
SEVERITY_COLUMN = 'severity'
TARGET_COLUMN = 'target'
VERDICT_TITLE = 'verdict'
SEVERITY_TITLE = 'findings by severity'
DEFERRED_TITLE = 'deferred to'

# Section 3's; this module reads no seed word (tests/test_pm_flow.py asserts it).
STORY_COLUMN = 'story'
PASSES_COLUMN = 'passes'
DISTRIBUTION_TITLE = 'verdict distribution'

# Section 4's. The BINDING is `milestone:` and is not read here.
CAUSED_BY_FIELD = 'caused_by'
CAUSE_COLUMN = 'caused_by'
BUG_COLUMN = 'bug'
STATUS_COLUMN = 'status'
FEATURE_STATUS_COLUMN = 'feature_status'
ESCAPE_TITLE = 'bugs naming a cause'

# Section 5's row keys; the separator makes the per-dispatch list one cell.
BEFORE_WRITE_KEY = 'tool_calls_before_first_write'
TOOL_CALLS_KEY = 'tool_calls'
OUTPUT_KEY = 'output'
LIST_SEPARATOR = ','
DISPATCHES_COLUMN = 'dispatches'
BEFORE_WRITE_COLUMN = 'before_first_write'
CALLS_COLUMN = 'calls'
DECISIONS_COLUMN = 'decisions'
ENTRY_COLUMN = 'entry'
TS_COLUMN = 'ts'
NEXT_STATUS_COLUMN = 'next_status_s'
SESSION_COLUMN = 'session_id'
# The delta columns are headed by the keys they diff, in section 1's spelling.
OUT_DELTA_COLUMN = USAGE_LABELS[OUTPUT_KEY]
TOOL_CALLS_COLUMN = TOOL_CALLS_KEY
BEFORE_WRITE_TITLE = 'story'
DECISION_COUNT_TITLE = 'decisions per grain'
DECISION_GAP_TITLE = 'decision to next status row'
SESSION_TITLE = 'session deltas'

# Section 6's, in milliseconds, the unit the row carries; rounding to seconds
# would print `0` for most gates.
GATE_KEY = 'gate'
GATE_DURATION_KEY = 'duration_ms'
GATE_CENSUS_KEY = 'census'
GATE_COLUMN = 'gate'
RUNS_COLUMN = 'runs'
FIRST_MS_COLUMN = 'first_ms'
LAST_MS_COLUMN = 'last_ms'
DELTA_MS_COLUMN = 'delta_ms'
CENSUS_COLUMN = 'census'
WHY_COLUMN = 'why'
GATE_COST_TITLE = 'gate'
GATE_UNUSABLE_TITLE = 'rows this section could not use'
# Marks a delta whose corpus moved: still printed, but a bigger tree is not a
# regression.
INCOMPARABLE_MARK = '*'
CENSUS_ARROW = ' → '

LEFT, RIGHT = 'left', 'right'


# --- WHERE the report reads from ----------------------------------------------
# Every file this module opens goes through a `Source`; `build` is one function
# over one tree, so a report read from history is the same report by
# construction. `GitSource` runs `rev-parse`, `ls-tree`, `cat-file` and `show`,
# none of which writes or touches the index (D6).
FEATURES_DIR = model.FEATURES_DIR
STORIES_DIR = model.STORIES_DIR
BUGS_DIR = model.BUGS_DIR
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
    """One file at a rev, shaped as `open(...)` and `read_text(...)` so `model`
    and `ledger` stay the only readers of their formats. The text is produced
    lazily, so an absent blob raises inside the reader that already handles it.
    """

    def __init__(self, display: str, read: Callable[[], str]) -> None:
        self._display, self._read = display, read

    def open(self, mode: str = 'r', encoding: str | None = None,
             newline: str | None = None) -> io.StringIO:
        # The same disabled translation `model.read_raw` asks of `open()`.
        return io.StringIO(self._read(), newline='')

    def read_text(self, encoding: str = 'utf-8') -> str:
        return _universal(self._read())

    def __str__(self) -> str:
        return self._display


class Source:
    """The tree the report reads, as the fourteen reads it makes — no more,
    none writing. The last four are the LAYOUT family: a rev read that asked
    `model.is_pooled` would look for a retired milestone's ledger, document and
    records in the layout the retire left.
    """

    #: The rev this source reads, or `''` for the working tree; `render` puts
    #: it in the heading.
    rev = ''

    def milestone_dir(self, cfg: model.PmConfig, mid: str) -> Path | None:
        raise NotImplementedError

    def feature_file(self, cfg: model.PmConfig, fid: str) -> Path | None:
        raise NotImplementedError

    def feature_files(self, cfg: model.PmConfig, mid: str) -> list[Path]:
        raise NotImplementedError

    def story_files(self, cfg: model.PmConfig, fid: str) -> list[Path]:
        raise NotImplementedError

    def bug_files(self, cfg: model.PmConfig, mid: str) -> list[Path]:
        raise NotImplementedError

    def review_record_for(self, cfg: model.PmConfig, fid: str) -> str | None:
        raise NotImplementedError

    def field_of(self, path: Path, key: str) -> str:
        raise NotImplementedError

    def read_raw(self, path: Path) -> str:
        raise NotImplementedError

    def is_file(self, path: Path) -> bool:
        raise NotImplementedError

    def ledger_rows(self, path: Path) -> list:
        raise NotImplementedError

    def is_pooled(self, cfg: model.PmConfig) -> bool:
        raise NotImplementedError

    def milestone_doc(self, handle: Path) -> Path:
        raise NotImplementedError

    def ledger_for(self, cfg: model.PmConfig, mid: str) -> Path:
        raise NotImplementedError

    def shared_doc(self, cfg: model.PmConfig, path: Path, name: str) -> Path:
        raise NotImplementedError


class DiskSource(Source):
    """The working tree, delegated to `model` and `ledger` so the live census
    is the gate's census."""

    def milestone_dir(self, cfg: model.PmConfig, mid: str) -> Path | None:
        return model.milestone_dir(cfg, mid)

    def feature_file(self, cfg: model.PmConfig, fid: str) -> Path | None:
        return model.feature_file(cfg, fid)

    def feature_files(self, cfg: model.PmConfig, mid: str) -> list[Path]:
        return model.feature_files(cfg, mid)

    def story_files(self, cfg: model.PmConfig, fid: str) -> list[Path]:
        return model.story_files(cfg, fid)

    def bug_files(self, cfg: model.PmConfig, mid: str) -> list[Path]:
        return model.bug_files(cfg, mid)

    def review_record_for(self, cfg: model.PmConfig, fid: str) -> str | None:
        return model.review_record_for(cfg, fid)

    def field_of(self, path: Path, key: str) -> str:
        return model.field_of(path, key)

    def read_raw(self, path: Path) -> str:
        return model.read_raw(path)

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def ledger_rows(self, path: Path) -> list:
        return ledger.read_rows(path)

    def is_pooled(self, cfg: model.PmConfig) -> bool:
        return model.is_pooled(cfg)

    def milestone_doc(self, handle: Path) -> Path:
        return model.milestone_doc(handle)

    def ledger_for(self, cfg: model.PmConfig, mid: str) -> Path:
        return ledger.ledger_for(cfg, mid)

    def shared_doc(self, cfg: model.PmConfig, path: Path, name: str) -> Path:
        return model.shared_doc(cfg, path, name)


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
            done = subprocess.run([GIT, '-C', str(self.root), *args],
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
        """`model.grain_docs` at the rev: the same walk and the same four
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
        """`model._is_grain_doc` at the rev — the predicate itself, not a copy,
        so this census cannot disagree with the gate's. An unreadable blob
        stays in scope, as on disk."""
        return model._is_grain_doc(self._doc(path))

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
    def is_pooled(self, cfg: model.PmConfig) -> bool:
        """`model.is_pooled` at the rev, because the two disagree in the case
        this verb exists for: a retire empties the pools on disk while the rev
        still holds every grain."""
        if self._pooled is None:
            self._pooled = any(self._grain_docs(model.pool_dir(cfg, kind))
                               for kind in model.FLOW_KINDS)
        return self._pooled

    def _pool_grain(self, cfg: model.PmConfig, kind: str,
                    gid: str) -> Path | None:
        """The document in one pool DECLARING this id, at the rev — what
        `model.grain_index` answers on disk, for one id."""
        for path in self._grain_docs(model.pool_dir(cfg, kind)):
            if model.unquote(self.field_of(path, model.FIELD_ID)) == gid:
                return path
        return None

    # --- the fourteen reads ---------------------------------------------------
    def milestone_dir(self, cfg: model.PmConfig, mid: str) -> Path | None:
        """The milestone's HANDLE at the rev: its document in the pool, or the
        `<mid>-*` directory a pre-migration rev holds."""
        if not model.segment_is_literal(mid):
            return None
        if self.is_pooled(cfg):
            return self._pool_grain(cfg, model.GRAIN_MILESTONE, mid)
        for base in (cfg.roadmap, cfg.roadmap / model.ARCHIVE_DIR_NAME):
            for found in self._dirs(base, f'{mid}-*'):
                return found
        return None

    def feature_file(self, cfg: model.PmConfig, fid: str) -> Path | None:
        if self.is_pooled(cfg):
            return self._pool_grain(cfg, model.GRAIN_FEATURE, fid)
        mid, _, slug = fid.partition('/')
        if not model.segment_is_literal(slug):
            return None
        mdir = self.milestone_dir(cfg, mid)
        if mdir is None:
            return None
        ffile = mdir / FEATURES_DIR / slug / model.FEATURE_DOC
        return ffile if self.is_file(ffile) else None

    def _pool_children(self, cfg: model.PmConfig, kind: str,
                       parent_id: str) -> list[Path]:
        """`model._children_paths` at the rev, in the parent's declared `order`
        and by id after that — the ORDER is half of the equality with disk."""
        field = model.BINDS_TO.get(kind, ('', ''))[1]
        if not field:
            return []
        found: dict[str, Path] = {}
        for path in self._grain_docs(model.pool_dir(cfg, kind)):
            if model.unquote(self.field_of(path, field)) != parent_id:
                continue
            found[model.unquote(self.field_of(path,
                                              model.FIELD_ID)) or path.stem] = path
        parent = self._grain_at(cfg, parent_id)
        declared = (model.list_field_of(self._doc(parent), model.ORDER_KEY)
                    if parent is not None else [])
        out = [found.pop(gid) for gid in declared if gid in found]
        return out + [found[gid] for gid in sorted(found)]

    def _grain_at(self, cfg: model.PmConfig, gid: str) -> Path | None:
        """Any grain's document at the rev — the parent whose `order`
        `_pool_children` reads."""
        for kind in model.FLOW_KINDS:
            found = self._pool_grain(cfg, kind, gid)
            if found is not None:
                return found
        return None

    def feature_files(self, cfg: model.PmConfig, mid: str) -> list[Path]:
        if self.is_pooled(cfg):
            return self._pool_children(cfg, model.GRAIN_FEATURE, mid)
        mdir = self.milestone_dir(cfg, mid)
        if mdir is None:
            return []
        features = mdir / FEATURES_DIR
        return [d / model.FEATURE_DOC for d in self._dirs(features)
                if self.is_file(d / model.FEATURE_DOC)]

    def story_files(self, cfg: model.PmConfig, fid: str) -> list[Path]:
        if self.is_pooled(cfg):
            return self._pool_children(cfg, model.GRAIN_STORY, fid)
        ffile = self.feature_file(cfg, fid)
        return self._grain_docs(ffile.parent / STORIES_DIR) if ffile else []

    def bug_files(self, cfg: model.PmConfig, mid: str) -> list[Path]:
        if self.is_pooled(cfg):
            return self._pool_children(cfg, model.GRAIN_BUG, mid)
        mdir = self.milestone_dir(cfg, mid)
        return self._grain_docs(mdir / BUGS_DIR) if mdir is not None else []

    def review_record_for(self, cfg: model.PmConfig, fid: str) -> str | None:
        """`model.review_record_for` at the rev. An absolute pointer resolves
        to nothing here, even one inside the root: it named a place on one
        machine's disk, not a path in the rev."""
        ffile = self.feature_file(cfg, fid)
        if ffile is None:
            return None
        pointer = model.unquote(self.field_of(ffile, 'reviewed'))
        # `pointer_escapes`, not `startswith('/')`: the local check accepted
        # `../outside.md` and `~/x.md` (0.6.0, F1's class).
        if pointer and pointer != 'null' and not model.pointer_escapes(pointer):
            if self.is_file(cfg.root / pointer):
                return pointer
        return None

    def field_of(self, path: Path, key: str) -> str:
        return model.field_of(self._doc(path), key)

    def read_raw(self, path: Path) -> str:
        return model.read_raw(self._doc(path))

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
        """`model.milestone_doc` at the rev: a pooled handle IS the document."""
        return handle if self.is_file(handle) else handle / model.MILESTONE_DOC

    def ledger_for(self, cfg: model.PmConfig, mid: str) -> Path:
        """`ledger.ledger_for` at the rev."""
        if self.is_pooled(cfg):
            return ledger.ledgers_dir(cfg) / f'{mid}.jsonl'
        mdir = self.milestone_dir(cfg, mid)
        return (ledger.ledger_path(mdir) if mdir is not None
                else ledger.grainless_path(cfg.roadmap))

    def shared_doc(self, cfg: model.PmConfig, path: Path, name: str) -> Path:
        """`model.shared_doc` at the rev."""
        if self.is_pooled(cfg):
            return path.with_name(f'{path.stem}-{name}')
        return path.parent / name


class Grain(NamedTuple):
    """One story, feature or bug under the milestone, as the TREE holds it."""
    gid: str
    kind: str
    size: str


class Section(NamedTuple):
    """One of the milestone's questions: `data` returns its own keys and
    `lines` reads the whole object back, so a section may print another's
    number and none recomputes one."""
    name: str
    data: Callable[[Source, model.PmConfig, str, Path, list], dict]
    lines: Callable[[model.PmConfig, dict], list[str]]


# --- the numbers --------------------------------------------------------------
def _blank() -> dict:
    """An accumulator that has seen nothing. Every sum starts ABSENT, not 0."""
    return {'dispatches': 0, 'usage': {key: None for key in USAGE_KEYS},
            TOTAL_KEY: None, 'tool_calls': None, 'duration_s': None}


def _plus(running: int | None, value: object) -> int | None:
    """`running` plus `value`, where an absent or non-integer value adds
    nothing: `None + absent` stays None, `0 + absent` stays 0. No number is
    ever this module's reason to fail."""
    if isinstance(value, bool) or not isinstance(value, int):
        return running
    return value if running is None else running + value


def _add(acc: dict, row: dict) -> None:
    """Fold one dispatch row into an accumulator. One row, counted once."""
    acc['dispatches'] += 1
    usage = row.get('usage')
    usage = usage if isinstance(usage, dict) else {}
    for key in USAGE_KEYS:
        acc['usage'][key] = _plus(acc['usage'][key], usage.get(key))
    for key in (TOTAL_KEY, *COUNT_KEYS):
        acc[key] = _plus(acc[key], row.get(key))


# --- the tree -----------------------------------------------------------------
def _grain(src: Source, path: Path, kind: str, fallback: str) -> Grain:
    """One grain document as a row: its own `id:` (the id `_ledger_id` writes,
    which the report joins on), its kind, its `size:`; a missing id falls back
    to the path's."""
    gid = model.unquote(src.field_of(path, model.FIELD_ID)) or fallback
    return Grain(gid, kind, src.field_of(path, SIZE_FIELD))


def _bug_slug(mdir: Path, path: Path) -> str:
    """`bugs/` was walked recursively, so a bug's slug could carry a directory.
    Only reachable for a NESTED tree — a pooled bug declares its id."""
    try:
        return path.relative_to(mdir / BUGS_DIR).with_suffix('').as_posix()
    except ValueError:
        return path.stem


def walk_grains(src: Source, cfg: model.PmConfig, mid: str,
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
    """The grains under this milestone that one dispatch row names.

    `grain` — what the dispatch was TOLD it was working on (0.4.0/D2) —
    outranks the `tree` snapshot, and **a row that states a grain is attributed
    by it and by nothing else**: falling through billed a row naming a
    since-renamed story to whichever OTHER story was live.

    **A snapshot places a row only when it is UNAMBIGUOUS** (0.4.0/D8): `pm
    ledger record` omits the `grain` key rather than pick one, so a reader
    billing BOTH un-did the decision on the way out.

    Category keys when present; frozen keys only for an old-shape row.
    """
    stated = row.get(ledger.GRAIN_FIELD)
    if isinstance(stated, str) and stated:
        return {stated} | {fid for fid, stories in owned.items()
                           if stated in stories} if stated in kinds else set()
    buckets_by_kind = LEGACY_BUCKETS if is_legacy(row) else CATEGORY_BUCKETS
    named = _named_through(row, buckets_by_kind, kinds, owned)
    return set() if _snapshot_is_ambiguous(named, kinds) else named


def _snapshot_is_ambiguous(named: set[str], kinds: dict[str, str]) -> bool:
    """Does this snapshot name more than one candidate at its finest kind?

    Stories first: a snapshot naming two of them named no one thing, whatever
    else is in it. A single story plus the feature that owns it is ONE
    candidate — the feature is a roll-up `_named_through` added.
    """
    stories = {gid for gid in named if kinds.get(gid) == KIND_STORY}
    if stories:
        return len(stories) > 1
    return len({gid for gid in named if kinds.get(gid) == KIND_FEATURE}) > 1


def stated_elsewhere(row: dict, kinds: dict[str, str]) -> bool:
    """Does this row STATE a grain this milestone does not hold? Its own line
    in the spend section rather than pooled with `rows naming no grain` — see
    `ELSEWHERE_NOTE`.
    """
    stated = row.get(ledger.GRAIN_FIELD)
    return isinstance(stated, str) and bool(stated) and stated not in kinds


def frozen_only_grains(row: dict, kinds: dict[str, str],
                       owned: dict[str, set[str]]) -> set[str]:
    """The grains a new-shape row names through the frozen keys and not the
    category keys — what `named_grains` reads past, disclosed rather than
    silent (rule 4). Empty for an old-shape row, and for a row that STATES its
    grain: that is not a silent drop, the row said which grain it was.
    """
    if is_legacy(row) or isinstance(row.get(ledger.GRAIN_FIELD), str):
        return set()
    return (_named_through(row, LEGACY_BUCKETS, kinds, owned)
            - _named_through(row, CATEGORY_BUCKETS, kinds, owned))


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
    """Was this dispatch row written before the snapshot carried categories? A
    row with no `tree` at all is not legacy; it never snapshotted."""
    tree = row.get('tree')
    return isinstance(tree, dict) and not (CATEGORY_KEYS & set(tree))


# --- the clock ----------------------------------------------------------------
def state_columns() -> tuple[str, ...]:
    """The dwell columns: one per category, whatever the vocabulary; which word
    within `in_progress` is `pm ledger show`. `done` has a column because a
    reopened grain leaves it; the seconds after the last row are never counted;
    re-entered categories sum; an undeclared word is `unplaced_s`.
    """
    return model.CATEGORIES


def category_seconds(cfg: model.PmConfig, kind: str,
                     seconds: dict[str, int]) -> tuple[dict[str, int], int]:
    """(seconds per category, seconds in words the declaration does not name),
    read through the current declaration."""
    placed: dict[str, int] = {}
    unplaced = 0
    for word, spent in seconds.items():
        category = model.category_of(cfg, kind, word)
        if category is None:
            unplaced += spent
            continue
        placed[category] = placed.get(category, 0) + spent
    return placed, unplaced


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


def open_charge(cfg: model.PmConfig, kind: str, rows: list,
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
ACTOR_TITLE = 'time per actor'
STATE_SUFFIX = '_s'
CLOSED_COLUMN = 'closed_s'
OPEN_COLUMN = 'open_s'
OPEN_STATE_COLUMN = 'open_state'
ACTOR_COLUMN = 'actor'
ARRIVALS_COLUMN = 'arrivals'
GRAINS_COLUMN = 'grains'
SECONDS_COLUMN = 'seconds'
KIND_MILESTONE = model.GRAIN_MILESTONE
# What `--help` names, in order (rule 11's read side): "total review time for
# this milestone" is `… | awk` over these, never a flag this verb grew.
CLOCK_COLUMNS = (GRAIN_COLUMN, f'<state>{STATE_SUFFIX}', CLOSED_COLUMN,
                 OPEN_COLUMN, OPEN_STATE_COLUMN)
ACTOR_COLUMNS = (ACTOR_COLUMN, ARRIVALS_COLUMN, GRAINS_COLUMN, SECONDS_COLUMN)


def _sum_into(into: dict[str, int], more: dict[str, int]) -> None:
    """One grain's seconds folded into its parent's; absent stays absent."""
    for state, spent in more.items():
        into[state] = into.get(state, 0) + spent


def _actor_of(row: dict) -> str:
    """The actor an arrival named, AS TYPED — `--by agent developer`. Nothing
    here goes looking for that agent (rule 9), and `none` is an answer."""
    answer = row.get('answer')
    answer = answer if isinstance(answer, str) and answer else (
        ledger.NO_DISPOSITION)
    value = row.get('value')
    return (f'{answer} {value}'.strip()
            if isinstance(value, str) and value else answer)


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


def clock_data(cfg: model.PmConfig, mid: str, grains: list, owned: dict,
               rows: list, now: datetime | None = None,
               focus: str = '') -> dict:
    """The milestone, its features, their stories and its bugs, each with the
    seconds ITS OWN SUBTREE spent in each state and the charge it is accruing,
    plus who was named at each arrival. `grains` arrives in tree order from
    `walk_grains`, so `depth` is the shape and the walk is the sum."""
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
    stories = {sid for owns in owned.values() for sid in owns}
    for feature, owns in owned.items():
        for sid in owns:
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
    # Rolled over the milestone either way; the id says which level prints,
    # actors included or the two tables disagree.
    out = subtree(out, focus) if focus else out
    named = {row[GRAIN_COLUMN] for row in out}
    return {'rows': out,
            'actors': actor_rows({gid: kind for gid, kind in kinds.items()
                                  if not focus or gid in named}, mine)}


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


def actor_rows(kinds: dict[str, str], mine: dict[str, list]) -> list[dict]:
    """Spend per actor, from disposition rows ALONE: how many arrivals each
    answer opened, on how many grains, and how long those stints ran. A stint
    still RUNNING contributes no seconds, because crediting a running clock to
    whoever last spoke is the partial credit this feature refuses."""
    tally: dict[str, dict] = {}
    for gid in sorted(kinds):
        grain_rows = mine.get(gid, [])
        marks = arrivals(grain_rows)
        ends = {start: end for (start, _s), (end, _e) in zip(marks, marks[1:])}
        for row in grain_rows:
            if not arrive.disposition_of(row.data):
                continue
            stamp = ledger.parse_ts(row.data.get(ledger.TS_FIELD))
            entry = tally.setdefault(_actor_of(row.data),
                                     {ACTOR_COLUMN: _actor_of(row.data),
                                      ARRIVALS_COLUMN: 0, GRAINS_COLUMN: [],
                                      SECONDS_COLUMN: None})
            entry[ARRIVALS_COLUMN] += 1
            if gid not in entry[GRAINS_COLUMN]:
                entry[GRAINS_COLUMN].append(gid)
            end = ends.get(stamp)
            if end is not None:
                entry[SECONDS_COLUMN] = _plus(
                    entry[SECONDS_COLUMN], int((end - stamp).total_seconds()))
    return [dict(entry, **{GRAINS_COLUMN: len(entry[GRAINS_COLUMN])})
            for _actor, entry in sorted(tally.items())]


def clock_columns(cfg: model.PmConfig, rows: list) -> tuple[str, ...]:
    """Which state WORDS this milestone's rows hold, in the order the project
    declared them and any word `[pm.states.*]` does not name appended. A state
    nobody held is no column: a zero nobody measured is the one number this
    report must never print (rule 4)."""
    held = {state for row in rows for state in row['state_s']}
    declared = list(dict.fromkeys(state for kind in model.FLOW_KINDS
                                  for state in model.flow_of(cfg, kind).order))
    named = [state for state in declared if state in held]
    return tuple(named + sorted(held - set(named)))


def clock_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """The two blocks the clock adds to section 1: one row per grain in tree
    order, indented by depth, then one row per actor."""
    rows = data['rows']
    states = clock_columns(cfg, rows)
    headers = (GRAIN_COLUMN, *(f'{s}{STATE_SUFFIX}' for s in states),
               CLOSED_COLUMN, OPEN_COLUMN, OPEN_STATE_COLUMN)
    aligns = (LEFT,) + (RIGHT,) * (len(headers) - 2) + (LEFT,)
    body = [(f'{SUB_ROW_INDENT * entry["depth"]}{entry[GRAIN_COLUMN]}',
             *(_cell(entry['state_s'].get(state)) for state in states),
             _cell(entry[CLOSED_COLUMN]), _cell(entry[OPEN_COLUMN]),
             entry[OPEN_STATE_COLUMN] or DASH) for entry in rows]
    out = _table(f'{CLOCK_TITLE} ({len(rows)})', headers, aligns, body)
    actors = data['actors']
    out.append('')
    out.extend(_table(f'{ACTOR_TITLE} ({len(actors)})', ACTOR_COLUMNS,
                      (LEFT, RIGHT, RIGHT, RIGHT),
                      [(entry[ACTOR_COLUMN], str(entry[ARRIVALS_COLUMN]),
                        str(entry[GRAINS_COLUMN]),
                        _cell(entry[SECONDS_COLUMN])) for entry in actors]))
    return out


# --- section 1: spend per grain -----------------------------------------------
def spend_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
               rows: list) -> dict:
    """Section 1 as data: one entry per grain, the strays, and the totals."""
    grains, owned = walk_grains(src, cfg, mid, mdir)
    kinds = {g.gid: g.kind for g in grains}
    dispatch = [r for r in rows if r.data.get(ledger.KIND_FIELD) == ledger.KIND_DISPATCH]
    status = [r for r in rows if r.data.get(ledger.KIND_FIELD) == ledger.KIND_STATUS]
    # The clock reads ARRIVALS, of which `status` is only half (D3/D6).
    arrived = [r for r in rows if arrival_state(r.data)]
    per_grain = {g.gid: _blank() for g in grains}
    per_type: dict[str, dict[str | None, dict]] = {g.gid: {} for g in grains}
    unattributed, totals = _blank(), _blank()
    # The boundary, counted (D7): old-shape rows, and how many named nothing here.
    legacy_rows = 0
    legacy_unattributed = 0
    # The drop, counted per grain: rows that named it only through a frozen key.
    frozen_only = {g.gid: 0 for g in grains}
    elsewhere = 0
    for row in dispatch:
        # Once, and before any narrowing: the summary line is about the FILE.
        _add(totals, row.data)
        legacy = is_legacy(row.data)
        legacy_rows += legacy
        for gid in frozen_only_grains(row.data, kinds, owned):
            frozen_only[gid] += 1
        if stated_elsewhere(row.data, kinds):
            # Counted apart from `unattributed`: pooling the two would make a
            # report over the tree's shared ledger look like a tree full of
            # unattributed work.
            elsewhere += 1
            continue
        named = named_grains(row.data, kinds, owned)
        if not named:
            _add(unattributed, row.data)
            legacy_unattributed += legacy
            continue
        agent = row.data.get('agent_type')
        agent = agent if isinstance(agent, str) and agent else None
        for gid in named:
            _add(per_grain[gid], row.data)
            _add(per_type[gid].setdefault(agent, _blank()), row.data)
    out = []
    for grain in sorted(grains, key=lambda g: (KIND_ORDER.index(g.kind),
                                               g.gid)):
        names = {grain.gid}
        my_status = [r for r in status if r.data.get(ledger.GRAIN_FIELD) in names]
        # The category columns are now DERIVED from the state totals rather
        # than the only number: `building` and `reviewing` are both
        # `in_progress`, the distinction the clock block below stopped losing.
        placed, unplaced = category_seconds(
            cfg, grain.kind,
            state_seconds([r for r in arrived
                           if r.data.get(ledger.GRAIN_FIELD) in names]))
        out.append({
            GRAIN_COLUMN: grain.gid, KIND_COLUMN: grain.kind,
            'size': grain.size or None,
            **per_grain[grain.gid],
            'agent_types': [{'agent_type': agent, **spend}
                            for agent, spend in sorted(
                                per_type[grain.gid].items(),
                                key=lambda kv: (kv[0] is None, kv[0] or ''))],
            'states': {category: placed.get(category)
                       for category in state_columns()},
            'unplaced_s': unplaced or None,
            'frozen_only': frozen_only[grain.gid] or None,
            'total_s': ledger.total_seconds(cfg, grain.kind, my_status),
        })
    in_flight, unplaceable = _in_flight_ages(cfg, kinds, status, arrived)
    return {'section': SECTION_SPEND, 'grains': out,
            'clock': clock_data(cfg, mid, grains, owned, arrived),
            'in_flight': in_flight,
            'in_flight_unplaceable': unplaceable,
            'unattributed': unattributed,
            'stated_elsewhere': elsewhere,
            'legacy': {'rows': legacy_rows,
                       'unattributed': legacy_unattributed},
            'totals': {'dispatch_rows': len(dispatch),
                       'status_rows': len(status), 'grains': len(grains),
                       TOTAL_ROWS: sum(1 for r in dispatch
                                       if TOTAL_KEY in r.data),
                       **{k: v for k, v in totals.items()
                          if k != 'dispatches'}}}


AT_REV = ' — at {rev}'


def heading_id(data: dict) -> str:
    """The milestone id as a heading names it, plus ` — at <rev>` from git;
    every section heading carries it, the summary line does not."""
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


def _spend_cells(entry: dict) -> tuple[str, ...]:
    """The columns every spend row shares: dispatches, the four measured sums,
    the reported total, two counts."""
    return (_cell(entry['dispatches']),
            *(_cell(entry['usage'][key]) for key in USAGE_KEYS),
            *(_cell(entry[key]) for key in (TOTAL_KEY, *COUNT_KEYS)))


def spend_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 1 as lines: a heading, one table per kind, the strays, a total."""
    totals = data['totals']
    out = [f'{HEADING_PREFIX} {heading_id(data)} — {SPEND_TITLE} — '
           f'{totals["dispatch_rows"]} dispatch row(s), '
           f'{totals["status_rows"]} status row(s), '
           f'{totals["grains"]} grain(s)']
    for kind in KIND_ORDER:
        entries = [e for e in data['grains'] if e[KIND_COLUMN] == kind]
        states = state_columns()
        headers = (GRAIN_COLUMN, SIZE_COLUMN, *SPEND_COLUMNS, *states,
                   TOTAL_COLUMN)
        aligns = (LEFT, LEFT) + (RIGHT,) * (len(headers) - 2)
        rows: list[tuple[str, ...]] = []
        for entry in entries:
            rows.append((entry[GRAIN_COLUMN], entry['size'] or '',
                         *_spend_cells(entry),
                         *(_cell(entry['states'][state]) for state in states),
                         _cell(entry['total_s'])))
            # One agent type is the grain's own row said twice.
            if len(entry['agent_types']) > 1:
                for split in entry['agent_types']:
                    rows.append((
                        f'{SUB_ROW_INDENT}{split["agent_type"] or DASH}', '',
                        *_spend_cells(split), *('',) * (len(states) + 1)))
        out.append('')
        out.extend(_table(f'{kind} ({len(entries)})', headers, aligns, rows))
        # Disclosed under the table it is missing from, so it cannot read as
        # "no stint measured".
        unplaced = [(e[GRAIN_COLUMN], e['unplaced_s']) for e in entries
                    if e.get('unplaced_s')]
        for gid, spent in unplaced:
            out.append(f'   {gid} {UNPLACED_NOTE}: {spent} s')
        # Its dispatch-side twin: a frozen-key-only attribution is not "no row".
        for entry in entries:
            if entry.get('frozen_only'):
                out.append(f'   {entry[GRAIN_COLUMN]} {FROZEN_ONLY_NOTE}: '
                           f'{entry["frozen_only"]} dispatch row(s)')
    for entry in data.get('in_flight') or []:
        out.append(f'   {entry["in_flight"]} {entry[KIND_COLUMN]}(s) in flight — '
                   f'median {ledger.human_duration(entry["median_s"])}, worst '
                   f'{ledger.human_duration(entry["worst_s"])}')
    # Rule 4: a distribution over nothing says so, rather than reading as
    # "nothing is in flight".
    if data.get('in_flight_unplaceable'):
        out.append(f'   {data["in_flight_unplaceable"]} arrival row(s) '
                   f'{IN_FLIGHT_UNPLACEABLE}')
    out.append('')
    out.extend(clock_lines(cfg, data['clock']))
    stray = data['unattributed']
    out.append('')
    out.extend(_table(f'{NO_GRAIN_TITLE} ({stray["dispatches"]})',
                      SPEND_COLUMNS, (RIGHT,) * len(SPEND_COLUMNS),
                      [_spend_cells(stray)] if stray['dispatches'] else []))
    legacy = data.get('legacy') or {}
    if legacy.get('unattributed'):
        out.append(f'   {legacy["unattributed"]} of these {LEGACY_NOTE}')
    if data.get('stated_elsewhere'):
        out.append(f'   {data["stated_elsewhere"]} further row(s) {ELSEWHERE_NOTE}')
    out.append('')
    out.append(f'{HEADING_PREFIX} {data[MILESTONE_KEY]} — '
               f'{_cell(totals["usage"]["output"])} out / '
               f'{_cell(totals["tool_calls"])} tool calls / '
               f'{_cell(totals["duration_s"])} s across '
               f'{totals["dispatch_rows"]} dispatch row(s)')
    # WHICH number that `out` is, said where it is read: the summary sums the
    # measured split, so a row carrying only a total is spend it does not cover.
    if totals.get(TOTAL_ROWS):
        out.append(f'   {totals[TOTAL_ROWS]} of those row(s) {SPLIT_NOTE}: '
                   f'{_cell(totals[TOTAL_KEY])} token(s)')
    return out


# --- the review records (sections 2 and 3) ------------------------------------
# Where one feature's record is: the `reviewed:` pointer, then the record
# beside the grain; the table prints the path it read.
NO_VERDICT = 'no verdict block'


class RecordError(Exception):
    """A review record whose verdict block exists and will not parse, naming
    record and line — the one content refusal sections 2-5 make. No block at
    all is `NoVerdict`, listed as a fact."""


def review_records(src: Source, cfg: model.PmConfig, mid: str,
                   mdir: Path) -> list[tuple[str, str, Path]]:
    """(feature id, the path as the report prints it, the path) per record."""
    out: list[tuple[str, str, Path]] = []
    for ffile in src.feature_files(cfg, mid):
        fid = (model.unquote(src.field_of(ffile, model.FIELD_ID))
               or f'{mid}/{ffile.parent.name}')
        rel = src.review_record_for(cfg, fid)
        path = (cfg.root / rel) if rel else None
        if path is None:
            # BESIDE the grain, wherever it sits. Asked of the SOURCE, since
            # which layout it is, is a fact about the tree being read.
            beside = src.shared_doc(cfg, ffile, model.REVIEW_FILE_NAME)
            if src.is_file(beside):
                path, rel = beside, cfg.rel(beside)
        if path is not None and rel is not None:
            out.append((fid, rel, path))
    # The table's order is a contract; a walker's is a filesystem fact.
    out.sort(key=lambda found: found[0])
    return out


def parsed_records(src: Source, cfg: model.PmConfig, mid: str,
                   mdir: Path) -> list[tuple[str, str, object]]:
    """Every record, parsed: its passes (one per verdict block, in order), or
    `None` when it carries no block. Sections 2 and 3 both call this;
    `verdict.parse` is the only reader either has."""
    out: list[tuple[str, str, object]] = []
    for fid, rel, path in review_records(src, cfg, mid, mdir):
        try:
            text = src.read_raw(path)
        except (OSError, UnicodeDecodeError) as err:
            raise RecordError(f'{rel} could not be read ({err})') from err
        try:
            out.append((fid, rel, verdict.parse(text)))
        except verdict.NoVerdict:
            out.append((fid, rel, None))
        except verdict.MalformedVerdict as err:
            raise RecordError(f'{rel}: line {err.lineno}: {err.why}\n'
                              f'    {err.line}') from err
    return out


def _tally(values: Iterable) -> dict:
    """Count per distinct value. The only thing this module does to a label."""
    counts: dict = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _section(mid: str, title: str, census: str,
             blocks: list[tuple[str, tuple, tuple, list]]) -> list[str]:
    """One section: its heading, then its blocks — or one `no data` line when
    it has none. Inside a section with rows, an empty block still prints its
    `(0)` heading."""
    out = ['', f'{HEADING_PREFIX} {mid} — {title} — {census}']
    if not any(rows for _, _, _, rows in blocks):
        out.append(NO_DATA)
        return out
    for btitle, headers, aligns, rows in blocks:
        out.append('')
        out.extend(_table(btitle, headers, aligns, rows))
    return out


# The disclosure that keeps an empty distribution from reading as a calm zero.
IN_FLIGHT_UNPLACEABLE = ('name a grain this milestone does not hold, so no age '
                         'was measured from them — `pm rename` moves a row\'s '
                         'grain, or the ids were replaced under it')


def _in_flight_ages(cfg: model.PmConfig, kinds: dict[str, str],
                    status: list, arrived: list) -> tuple[list[dict], int]:
    """`(per kind: in-flight count, median age, worst), rows this could not
    place`.

    Read off the same status rows the dwell columns use; a grain nobody has
    moved contributes nothing, because it is UNMEASURED rather than young.

    **The second number is what this shipped without.** A row naming a grain
    the milestone does not hold was DISCARDED, so a tree whose ledger names
    renamed ids reported `[]` with nothing saying one had been attempted
    (rule 4). Over ARRIVALS, BOTH kinds: `status` alone left the
    disposition-only ledger this feature serves silently short.

    No threshold, no colour, no exit code: a ceiling on how long a grain may
    stay in flight is this package having an opinion about somebody's week
    (rule 9).
    """
    by_grain: dict[str, list] = {}
    unplaceable = sum(1 for row in arrived
                      if isinstance(row.data.get(ledger.GRAIN_FIELD), str)
                      and row.data.get(ledger.GRAIN_FIELD)
                      and row.data[ledger.GRAIN_FIELD] not in kinds)
    for row in status:
        gid = row.data.get(ledger.GRAIN_FIELD)
        if isinstance(gid, str) and gid and gid in kinds:
            by_grain.setdefault(gid, []).append(row)
    ages: dict[str, list[int]] = {}
    for gid, rows in by_grain.items():
        rows.sort(key=lambda r: str(r.data.get(ledger.TS_FIELD) or ''))
        seconds = ledger.open_seconds(cfg, kinds[gid], rows)
        if seconds is not None:
            ages.setdefault(kinds[gid], []).append(seconds)
    out = []
    for kind in KIND_ORDER:
        found = sorted(ages.get(kind, ()))
        if found:
            out.append({KIND_COLUMN: kind, 'in_flight': len(found),
                        'median_s': found[len(found) // 2],
                        'worst_s': found[-1]})
    return out, unplaceable


# --- section 2: yield per review pass -----------------------------------------
def yield_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
               rows: list) -> dict:
    """Section 2 as data: counting over the block's closed sets per record. The
    disposition is read as its kind, never as the shape of its value. Spend is
    not joined in — picking "reviewer-shaped" agent types would be this module
    LABELLING, the one thing a report over a ledger may not do.
    """
    records = []
    for fid, rel, parsed in parsed_records(src, cfg, mid, mdir):
        passes = []
        for ordinal, one in enumerate(parsed or [], 1):
            found = one.findings
            passes.append({
                'pass': ordinal,
                'verdict': one.verdict,
                'findings': len(found),
                'severities': {
                    sev: n for sev, n in
                    sorted(_tally(f.severity for f in found).items(),
                           key=lambda kv: verdict.SEVERITIES.index(kv[0]))},
                'dispositions': {
                    kind: sum(1 for f in found if f.disposition_kind == kind)
                    for kind in verdict.DISPOSITION_KINDS},
                'deferred': [
                    {'target': target, 'findings': n} for target, n in
                    sorted(_tally(f.disposition_value for f in found
                                  if f.disposition_kind == verdict.DEFERRED
                                  ).items())]})
        records.append({FEATURE_COLUMN: fid, 'record': rel, 'passes': passes})
    return {SECTION_YIELD: {
        'records': records,
        'totals': {'records': len(records),
                   'passes': sum(len(r['passes']) for r in records),
                   'findings': sum(one['findings'] for r in records
                                   for one in r['passes'])}}}


def yield_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 2 as lines: the pass, its severities, and where it deferred."""
    section = data[SECTION_YIELD]
    records = section['records']
    # A record with no block keeps its one row; dropping it would read as every
    # record reviewed.
    passes = [(r[FEATURE_COLUMN], r['record'], str(one['pass']),
               one['verdict'],
               _cell(one['findings']),
               *(_cell(one['dispositions'][kind])
                 for kind in verdict.DISPOSITION_KINDS))
              if one else
              (r[FEATURE_COLUMN], r['record'], DASH, NO_VERDICT, _cell(None),
               *(_cell(None) for _ in verdict.DISPOSITION_KINDS))
              for r in records for one in (r['passes'] or [None])]
    severities = [(r[FEATURE_COLUMN], str(one['pass']), sev, str(n))
                  for r in records for one in r['passes']
                  for sev, n in one['severities'].items()]
    deferred = sorted((d['target'], r[FEATURE_COLUMN], str(one['pass']),
                       str(d['findings']))
                      for r in records for one in r['passes']
                      for d in one['deferred'])
    totals = section['totals']
    return _section(
        heading_id(data), YIELD_TITLE,
        f'{totals["records"]} record(s), {totals["passes"]} pass(es), '
        f'{totals["findings"]} finding(s)',
        [(f'{VERDICT_TITLE} ({len(passes)})',
          (FEATURE_COLUMN, RECORD_COLUMN, PASS_COLUMN, VERDICT_COLUMN,
           FINDINGS_COLUMN, *verdict.DISPOSITION_KINDS),
          (LEFT, LEFT, RIGHT, LEFT)
          + (RIGHT,) * (1 + len(verdict.DISPOSITION_KINDS)),
          passes),
         (f'{SEVERITY_TITLE} ({len(severities)})',
          (FEATURE_COLUMN, PASS_COLUMN, SEVERITY_COLUMN, FINDINGS_COLUMN),
          (LEFT, RIGHT, LEFT, RIGHT), severities),
         (f'{DEFERRED_TITLE} ({len(deferred)})',
          (TARGET_COLUMN, FEATURE_COLUMN, PASS_COLUMN, FINDINGS_COLUMN),
          (LEFT, LEFT, RIGHT, RIGHT), deferred)])


# --- section 3: rework --------------------------------------------------------
def rework_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
                rows: list) -> dict:
    """Section 3 as data: the verdict spread, per pass rather than per record."""
    spread = _tally(one.verdict
                    for _, _, parsed in parsed_records(src, cfg, mid, mdir)
                    if parsed is not None for one in parsed)
    return {SECTION_REWORK: {
        'verdicts': [{'verdict': name, 'passes': spread[name]}
                     for name in verdict.VERDICTS if name in spread],
        'totals': {'passes': sum(spread.values())}}}


def rework_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 3 as lines: one row per verdict that was given."""
    section = data[SECTION_REWORK]
    spread = [(v['verdict'], str(v['passes'])) for v in section['verdicts']]
    totals = section['totals']
    return _section(
        heading_id(data), REWORK_TITLE,
        f'{totals["passes"]} pass(es) with a verdict',
        [(f'{DISTRIBUTION_TITLE} ({len(spread)})',
          (VERDICT_COLUMN, PASSES_COLUMN), (LEFT, RIGHT), spread)])


# --- section 4: escapes -------------------------------------------------------
def escapes_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
                 rows: list) -> dict:
    """Section 4 as data: every bug whose `caused_by:` names a feature, grouped
    by the id named, resolved wherever it lives; an unresolved cause keeps its
    row with `-`. `feature_done` is the equality, never a judgement.
    """
    out = []
    for bfile in src.bug_files(cfg, mid):
        cause = src.field_of(bfile, CAUSED_BY_FIELD)
        if not cause:
            continue
        gid = (model.unquote(src.field_of(bfile, model.FIELD_ID))
               or f'{mid}/{BUGS_DIR}/{_bug_slug(mdir, bfile)}')
        ffile = src.feature_file(cfg, cause)
        fstatus = src.field_of(ffile,
                               model.FIELD_STATUS) if ffile is not None else ''
        out.append({
            'caused_by': cause, BUG_COLUMN: gid,
            STATUS_COLUMN: src.field_of(bfile, model.FIELD_STATUS) or None,
            'feature_status': fstatus or None,
            'feature_done': (None if not fstatus
                             else ledger.ends_grain(cfg, KIND_FEATURE, fstatus))})
    out.sort(key=lambda e: (e['caused_by'], e[BUG_COLUMN]))
    return {SECTION_ESCAPES: {
        'bugs': out,
        'totals': {'bugs': len(out),
                   'features': len({e['caused_by'] for e in out})}}}


def escapes_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 4 as lines: cause, bug, the bug's state, the feature's."""
    section = data[SECTION_ESCAPES]
    bugs = [(e['caused_by'], e[BUG_COLUMN], _cell(e[STATUS_COLUMN]),
             _cell(e['feature_status'])) for e in section['bugs']]
    totals = section['totals']
    return _section(
        heading_id(data), ESCAPES_TITLE,
        f'{totals["bugs"]} bug(s) naming a cause, '
        f'{totals["features"]} feature(s)',
        [(f'{ESCAPE_TITLE} ({len(bugs)})',
          (CAUSE_COLUMN, BUG_COLUMN, STATUS_COLUMN, FEATURE_STATUS_COLUMN),
          (LEFT, LEFT, LEFT, LEFT), bugs)])


# --- section 5: overhead shape ------------------------------------------------
def _int(value: object) -> int | None:
    """The integer on the row, or None for anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _delta(earlier: object, later: object) -> int | None:
    """`later - earlier`, or None unless both ends are integers — an absent end
    read as zero would invert a cumulative row."""
    a, b = _int(earlier), _int(later)
    return None if a is None or b is None else b - a


def _usage_of(row: dict, key: str) -> object:
    usage = row.get('usage')
    return usage.get(key) if isinstance(usage, dict) else None


def overhead_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
                  rows: list) -> dict:
    """Section 5 as data: a story's `tool_calls_before_first_write` summed and
    listed; a decision row against the grain its own `grain` names, never
    divided or attributed; the seconds from a decision to the next status row
    in its scope; session rows diffed per `session_id` (cumulative totals, D4).
    """
    grains, owned = walk_grains(src, cfg, mid, mdir)
    kinds = {g.gid: g.kind for g in grains}
    dispatch = [r for r in rows if r.data.get(ledger.KIND_FIELD) == ledger.KIND_DISPATCH]
    status = [r for r in rows if r.data.get(ledger.KIND_FIELD) == ledger.KIND_STATUS
              and isinstance(r.data.get(ledger.GRAIN_FIELD), str)]
    decisions = [r for r in rows if r.data.get(ledger.KIND_FIELD) == ledger.KIND_DECISION]
    sessions = [r for r in rows if r.data.get(ledger.KIND_FIELD) == ledger.KIND_SESSION]

    stories = []
    for grain in sorted((g for g in grains if g.kind == KIND_STORY),
                        key=lambda g: g.gid):
        mine = [r for r in dispatch
                if grain.gid in named_grains(r.data, kinds, owned)]
        calls = [n for n in (_int(r.data.get(BEFORE_WRITE_KEY)) for r in mine)
                 if n is not None]
        stories.append({GRAIN_COLUMN: grain.gid, 'dispatches': len(mine),
                        'before_first_write': sum(calls) if calls else None,
                        'calls': calls})

    scopes = {mid: {g.gid for g in grains} | {mid}}
    for fid, sids in owned.items():
        scopes[fid] = {fid} | sids
    # Every feature and the milestone itself, but only once something has been
    # decided; zeros under a ledger with no decision row would wear a
    # measurement's shape.
    per_grain = ([{GRAIN_COLUMN: gid,
                   'decisions': sum(1 for r in decisions
                                    if r.data.get(ledger.GRAIN_FIELD) == gid)}
                  for gid in [mid, *sorted(owned)]] if decisions else [])
    events = []
    for row in decisions:
        gid = row.data.get(ledger.GRAIN_FIELD)
        gid = gid if isinstance(gid, str) else None
        scope = scopes.get(gid, {gid} if gid else set())
        moment = ledger.parse_ts(row.data.get(ledger.TS_FIELD))
        seconds = None
        if moment is not None:
            later = [ts for ts in (ledger.parse_ts(r.data.get(ledger.TS_FIELD))
                                   for r in status
                                   if r.data[ledger.GRAIN_FIELD] in scope)
                     if ts is not None and ts > moment]
            if later:
                seconds = int((min(later) - moment).total_seconds())
        entry = row.data.get('entry')
        title = row.data.get('title')
        stamp = row.data.get(ledger.TS_FIELD)
        events.append({GRAIN_COLUMN: gid,
                       'entry': entry if isinstance(entry, str) else None,
                       'title': title if isinstance(title, str) else None,
                       TS_COLUMN: stamp if isinstance(stamp, str) else None,
                       'next_status_s': seconds})

    grouped: dict = {}
    for row in sessions:
        sid = row.data.get('session_id')
        grouped.setdefault(sid if isinstance(sid, str) and sid else None,
                           []).append(row)
    deltas = []
    for sid in sorted(grouped, key=lambda s: (s is None, s or '')):
        for earlier, later in zip(grouped[sid], grouped[sid][1:]):
            stamp = later.data.get(ledger.TS_FIELD)
            deltas.append({
                'session_id': sid,
                TS_COLUMN: stamp if isinstance(stamp, str) else None,
                'output': _delta(_usage_of(earlier.data, OUTPUT_KEY),
                                 _usage_of(later.data, OUTPUT_KEY)),
                'tool_calls': _delta(earlier.data.get(TOOL_CALLS_KEY),
                                     later.data.get(TOOL_CALLS_KEY))})
    return {SECTION_OVERHEAD: {
        'stories': stories, 'decisions': per_grain, 'gaps': events,
        'sessions': deltas,
        'totals': {'dispatch_rows': len(dispatch),
                   'decision_rows': len(decisions),
                   'session_rows': len(sessions)}}}


def overhead_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 5 as lines: four blocks, one per thing the shape is made of."""
    section = data[SECTION_OVERHEAD]
    stories = [(e[GRAIN_COLUMN], str(e['dispatches']),
                _cell(e['before_first_write']),
                LIST_SEPARATOR.join(str(n) for n in e['calls']) or DASH)
               for e in section['stories']]
    decisions = [(e[GRAIN_COLUMN], str(e['decisions']))
                 for e in section['decisions']]
    gaps = [(_cell(e[GRAIN_COLUMN]), _cell(e['entry']), _cell(e[TS_COLUMN]),
             _cell(e['next_status_s'])) for e in section['gaps']]
    deltas = [(_cell(e['session_id']), _cell(e[TS_COLUMN]), _cell(e['output']),
               _cell(e['tool_calls'])) for e in section['sessions']]
    totals = section['totals']
    return _section(
        heading_id(data), OVERHEAD_TITLE,
        f'{totals["dispatch_rows"]} dispatch row(s), '
        f'{totals["decision_rows"]} decision row(s), '
        f'{totals["session_rows"]} session row(s)',
        [(f'{BEFORE_WRITE_TITLE} ({len(stories)})',
          (STORY_COLUMN, DISPATCHES_COLUMN, BEFORE_WRITE_COLUMN, CALLS_COLUMN),
          (LEFT, RIGHT, RIGHT, LEFT), stories),
         (f'{DECISION_COUNT_TITLE} ({len(decisions)})',
          (GRAIN_COLUMN, DECISIONS_COLUMN), (LEFT, RIGHT), decisions),
         (f'{DECISION_GAP_TITLE} ({len(gaps)})',
          (GRAIN_COLUMN, ENTRY_COLUMN, TS_COLUMN, NEXT_STATUS_COLUMN),
          (LEFT, LEFT, LEFT, RIGHT), gaps),
         (f'{SESSION_TITLE} ({len(deltas)})',
          (SESSION_COLUMN, TS_COLUMN, OUT_DELTA_COLUMN, TOOL_CALLS_COLUMN),
          (LEFT, LEFT, RIGHT, RIGHT), deltas)])


# --- section 6: gate cost -----------------------------------------------------
# **THE ONE SECTION THAT IS NOT ABOUT THE MILESTONE IN THE HEADING**, and it
# says so on the line rather than leaving a reader to assume otherwise: a gate
# row lands in the tree's own ledger (0.4.0/D3), so `runs`, `first_ms` and
# `delta_ms` are lifetime-of-TREE numbers and two milestones' reports print
# identical gate rows, correctly.
#
# REJECTED: windowing the rows by the milestone's timestamps. A milestone has
# no declared time range, so the window would be inferred from status rows — a
# number nobody stated, quoted as if it had been. Naming what the numbers are
# about is the cheapest honest fix (rule 11).
GATES_SCOPE_NOTE = ('across the whole tree, not this milestone: a gate row '
                    'names no grain, so every one lands in the tree\'s ledger')


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


def gates_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
               rows: list) -> dict:
    """Section 6 as data: one entry per `gate`, slowest-latest first;
    `delta_ms` is `last - first`. A gate with one run still appears, with `-`;
    a delta whose census moved is printed and marked (`comparable`). Nothing
    here is a ceiling or a budget.
    """
    gate_rows = [r.data for r in rows
                 if r.data.get(ledger.KIND_FIELD) == ledger.KIND_GATE]
    unusable, runs_of = [], {}
    for row in gate_rows:
        why = _gate_unusable(row)
        if why is not None:
            name = row.get(GATE_KEY)
            unusable.append({'gate': name if isinstance(name, str) and name
                             else None, 'why': why,
                             TS_COLUMN: row.get(ledger.TS_FIELD)
                             if isinstance(row.get(ledger.TS_FIELD), str)
                             else None})
            continue
        runs_of.setdefault(row[GATE_KEY], []).append(row)

    entries = []
    for name, runs in runs_of.items():
        first, last = runs[0][GATE_DURATION_KEY], runs[-1][GATE_DURATION_KEY]
        delta = last - first if len(runs) > 1 else None
        censuses = (_int(runs[0].get(GATE_CENSUS_KEY)),
                    _int(runs[-1].get(GATE_CENSUS_KEY)))
        entries.append({
            'gate': name, 'runs': len(runs),
            'first_ms': first, 'last_ms': last, 'delta_ms': delta,
            'first_census': censuses[0], 'last_census': censuses[1],
            'comparable': None if delta is None else (
                None not in censuses and censuses[0] == censuses[1])})
    entries.sort(key=lambda e: (-e['last_ms'], e['gate']))
    return {SECTION_GATES: {
        'gates': entries, 'unusable': unusable,
        'totals': {'rows': len(gate_rows), 'gates': len(entries),
                   'incomparable': sum(1 for e in entries
                                       if e['comparable'] is False),
                   'unusable': len(unusable)}}}


def _gate_census_cell(entry: dict) -> str:
    """`first → last`, or `-` when either end was never recorded — half a pair
    is no answer."""
    first, last = entry['first_census'], entry['last_census']
    return (DASH if first is None or last is None
            else f'{first}{CENSUS_ARROW}{last}')


def gates_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 6 as lines: the cost table, then whatever it could not read."""
    section = data[SECTION_GATES]
    cost = []
    for entry in section['gates']:
        delta = (DASH if entry['delta_ms'] is None
                 else f'{entry["delta_ms"]:+d}')
        if entry['comparable'] is False:
            delta += INCOMPARABLE_MARK
        cost.append((entry['gate'], str(entry['runs']),
                     _cell(entry['first_ms']), _cell(entry['last_ms']),
                     delta, _gate_census_cell(entry)))
    unusable = [(_cell(e['gate']), e['why'], _cell(e[TS_COLUMN]))
                for e in section['unusable']]
    totals = section['totals']
    return _section(
        heading_id(data), GATES_TITLE,
        f'{totals["rows"]} gate row(s), {totals["gates"]} gate(s), '
        f'{GATES_SCOPE_NOTE}; '
        f'{totals["incomparable"]} delta(s) marked {INCOMPARABLE_MARK} for a '
        f'census that moved or is absent, '
        f'{totals["unusable"]} row(s) this section could not use',
        [(f'{GATE_COST_TITLE} ({len(cost)})',
          (GATE_COLUMN, RUNS_COLUMN, FIRST_MS_COLUMN, LAST_MS_COLUMN,
           DELTA_MS_COLUMN, CENSUS_COLUMN),
          (LEFT, RIGHT, RIGHT, RIGHT, RIGHT, LEFT), cost),
         (f'{GATE_UNUSABLE_TITLE} ({len(unusable)})',
          (GATE_COLUMN, WHY_COLUMN, TS_COLUMN),
          (LEFT, LEFT, LEFT), unusable)])


# The registry: one row per question, one pair of functions each; a section is
# added here and nowhere else.
SECTIONS = (Section(SECTION_SPEND, spend_data, spend_lines),
            Section(SECTION_YIELD, yield_data, yield_lines),
            Section(SECTION_REWORK, rework_data, rework_lines),
            Section(SECTION_ESCAPES, escapes_data, escapes_lines),
            Section(SECTION_OVERHEAD, overhead_data, overhead_lines),
            Section(SECTION_GATES, gates_data, gates_lines))


def build(cfg: model.PmConfig, mid: str, mdir: Path, rows: list,
          src: Source | None = None) -> dict:
    """The whole report as one object — what `--json` prints. Section 1's keys
    sit at the top level as shipped; sections 2-5 each add one key. `rev` is
    present only when there was one (a `"rev": null` is a question nobody put).
    """
    src = DiskSource() if src is None else src
    rows = in_time_order(rows)
    out: dict = {MILESTONE_KEY: mid}
    if src.rev:
        out['rev'] = src.rev
    for section in SECTIONS:
        out.update(section.data(src, cfg, mid, mdir, rows))
    return out


def clock_report(cfg: model.PmConfig, mid: str, mdir: Path, rows: list,
                 src: Source, focus: str) -> dict:
    """The clock at the LEVEL an id names — `pm ledger report <feature-id>`.
    The rows are the milestone's, because that is where a ledger is (D6); the
    id chooses which grain roots the table. Spend, review passes and gate cost
    are the MILESTONE's questions and are not printed under it (rule 4)."""
    grains, owned = walk_grains(src, cfg, mid, mdir)
    arrived = [r for r in in_time_order(rows) if arrival_state(r.data)]
    out = {MILESTONE_KEY: mid, 'focus': focus,
           'clock': clock_data(cfg, mid, grains, owned, arrived, focus=focus)}
    if src.rev:
        out['rev'] = src.rev
    return out


def clock_render(cfg: model.PmConfig, data: dict) -> list[str]:
    """The focused report as lines: the grain, its milestone, both tables."""
    rows = data['clock']['rows']
    return [f'{HEADING_PREFIX} {data["focus"]} — {CLOCK_TITLE} — '
            f'{len(rows)} grain(s), from {heading_id(data)}',
            ''] + clock_lines(cfg, data['clock'])


def beyond_ledger(data: dict) -> bool:
    """Did anything outside `ledger.jsonl` get measured — a verdict block or an
    escape — so the caller does not stop at the one-line form? Narrow: a record
    with no block is not a measurement."""
    return (any(record['passes'] for record in data[SECTION_YIELD]['records'])
            or bool(data[SECTION_ESCAPES]['totals']['bugs']))


def render(cfg: model.PmConfig, data: dict) -> list[str]:
    """The whole report as lines, in section order."""
    lines: list[str] = []
    for section in SECTIONS:
        lines.extend(section.lines(cfg, data))
    return lines
