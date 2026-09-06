"""report.py — `pm ledger report`: the milestone's raw rows, added up.

The ledger never judges; this is the caller judgement is left to. It may
sum, count, subtract and group, never weight, price or label (D5). Absent
is `-`, not zero; the tree is walked, so every grain gets a row; nothing is
dropped. It fails only on a document that will not parse, never on a
number.
"""
from __future__ import annotations

import fnmatch
import io
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.repo.pm import ledger, model, verdict

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

# Frontmatter key printed as a column and used for nothing else (D5).
SIZE_FIELD = 'size'

# Grain kinds, in the order their tables print.
KIND_STORY = 'story'
KIND_FEATURE = 'feature'
KIND_BUG = ledger.GRAIN_BUG
KIND_ORDER = (KIND_STORY, KIND_FEATURE, KIND_BUG)

# D3's snapshot buckets, by the kind of grain whose ids they hold;
# `milestones_in_progress` is on every row and would attribute every dispatch
# to every grain.
CATEGORY_BUCKETS = (
    (KIND_STORY, ('stories_in_progress',)),
    (KIND_FEATURE, ('features_in_progress',)),
)
# The old shape, read as-is (D7): rows written before the category keys carry
# only these, matched by the seed's words when written, and never re-read
# through a later declaration.
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
# The dispatch-side twin of UNPLACED_NOTE: a new-shape row whose frozen key
# names a grain the category key does not is read through the category keys,
# and the drop is said out loud.
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

# The columns every spend table opens with, before the per-state ones.
SPEND_COLUMNS = ('dispatches',) + tuple(
    USAGE_LABELS[key] for key in USAGE_KEYS) + COUNT_KEYS
GRAIN_COLUMN = 'grain'
SIZE_COLUMN = 'size'
TOTAL_COLUMN = 'total_s'
NO_GRAIN_TITLE = 'rows naming no grain'

# Section 2's columns; `verdict.DISPOSITION_KINDS` supplies the disposition
# columns, so a new kind appears rather than counting into nothing.
FEATURE_COLUMN = 'feature'
RECORD_COLUMN = 'record'
# One record, N passes; the ordinal is a column so two passes' rows can be told
# apart.
PASS_COLUMN = 'pass'
VERDICT_COLUMN = 'verdict'
FINDINGS_COLUMN = 'findings'
SEVERITY_COLUMN = 'severity'
TARGET_COLUMN = 'target'
VERDICT_TITLE = 'verdict'
SEVERITY_TITLE = 'findings by severity'
DEFERRED_TITLE = 'deferred to'

# Section 3's; this module reads no seed word (tests/test_pm_flow.py asserts
# it).
STORY_COLUMN = 'story'
PASSES_COLUMN = 'passes'
DISTRIBUTION_TITLE = 'verdict distribution'

# Section 4's. `caught_in:` is a different fact and is not read here.
CAUSED_BY_FIELD = 'caused_by'
CAUSE_COLUMN = 'caused_by'
BUG_COLUMN = 'bug'
STATUS_COLUMN = 'status'
FEATURE_STATUS_COLUMN = 'feature_status'
ESCAPE_TITLE = 'bugs naming a cause'

# Section 5's row keys, and the separator that makes the per-dispatch list one
# cell.
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
# construction. `DiskSource` delegates to the walkers the gate uses;
# `GitSource` runs `rev-parse`, `ls-tree`, `cat-file` and `show`, none of which
# writes or touches the index (D6). The slot names are `model`'s.
FEATURES_DIR = model.FEATURES_DIR
STORIES_DIR = model.STORIES_DIR
BUGS_DIR = model.BUGS_DIR
MD_SUFFIX = '.md'

GIT = 'git'
GIT_MISSING = (f'{GIT} is not on PATH, so a report `--from` a rev cannot be '
               f'read — a retired milestone is only in history')
# `<rev>:<path>`, git's own spelling, so a reader can paste it after `git
# show`.
REV_SEPARATOR = ':'

# The two object types `git ls-tree` names for the things a PM tree is made of.
TREE = 'tree'
BLOB = 'blob'


class GitError(OSError):
    """A git invocation that failed, carrying git's own stderr verbatim. An
    `OSError`, so a blob absent at the rev lands in the `RecordError`
    handler that already exists.
    """


def check_rev(rev: str) -> None:
    """The `--from` grammar: a leading `-`, whitespace/NUL, and an empty rev
    (which names the index) are refused here; whether the rev exists is
    git's answer.
    """
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
    """`Path.read_text`'s universal-newline translation, applied by hand to
    the ledger read alone, so a CRLF ledger reads the same from disk and
    from history.
    """
    return text.replace('\r\n', '\n').replace('\r', '\n')


class _Blob:
    """One file at a rev, shaped as `open(...)` and `read_text(...)` so
    `model` and `ledger` stay the only readers of their formats. `str()` is
    git's `<rev>:<path>`; the text is produced lazily, so an absent blob
    raises inside the reader that already handles it.
    """

    def __init__(self, display: str, read: Callable[[], str]) -> None:
        self._display, self._read = display, read

    def open(self, mode: str = 'r', encoding: str | None = None,
             newline: str | None = None) -> io.StringIO:
        # `newline=''` on a StringIO is the same disabled translation
        # `model.read_raw` asks of `open()`.
        return io.StringIO(self._read(), newline='')

    def read_text(self, encoding: str = 'utf-8') -> str:
        return _universal(self._read())

    def __str__(self) -> str:
        return self._display


class Source:
    """The tree the report reads, as the ten reads it makes — no more, none
    writing; both subclasses are checked against this list.
    """

    #: The rev this source reads, or `''` for the working tree; `render` puts
    #: it in the heading.
    rev = ''

    def milestone_dir(self, cfg: model.PmConfig, mid: str) -> Path | None:
        raise NotImplementedError

    def feature_file(self, cfg: model.PmConfig, fid: str) -> Path | None:
        raise NotImplementedError

    def feature_files(self, mdir: Path) -> list[Path]:
        raise NotImplementedError

    def story_files(self, ffile: Path) -> list[Path]:
        raise NotImplementedError

    def bug_files(self, mdir: Path) -> list[Path]:
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


class DiskSource(Source):
    """The working tree, delegated to `model` and `ledger` so the live census
    is the gate's census.
    """

    def milestone_dir(self, cfg: model.PmConfig, mid: str) -> Path | None:
        return model.milestone_dir(cfg, mid)

    def feature_file(self, cfg: model.PmConfig, fid: str) -> Path | None:
        return model.feature_file(cfg, fid)

    def feature_files(self, mdir: Path) -> list[Path]:
        return model.feature_files(mdir)

    def story_files(self, ffile: Path) -> list[Path]:
        return model.story_files(ffile)

    def bug_files(self, mdir: Path) -> list[Path]:
        return model.bug_files(mdir)

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


class GitSource(Source):
    """The same tree at a rev, through `git show`, read-only by construction.
    The rev is the caller's; the directory is resolved by version prefix as
    `model.milestone_dir` globs on disk; paths keep `model`'s shapes but
    never reach the filesystem. Blobs and object types are memoised, since
    a rev is immutable.
    """

    def __init__(self, root: Path, rev: str) -> None:
        check_rev(rev)
        self.root = root
        self.rev = rev
        self._blobs: dict[str, bytes] = {}
        self._types: dict[str, str] = {}
        self._trees: dict[tuple[str, bool], list[tuple[str, str]]] = {}
        # `rev-parse --verify` first, so "no such rev" is answered once, in
        # git's words.
        self._git(['rev-parse', '--verify', rev])

    # --- the four verbs -------------------------------------------------------
    def _git(self, args: list[str]) -> bytes:
        """One git run in the repo root, stdout as bytes — `text=True` would
        apply newline translation and the locale's encoding.
        """
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
        outside the root, which is in no rev.
        """
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return None

    def _ls(self, path: Path, recursive: bool) -> list[tuple[str, str]]:
        """`(object type, name)` for one directory at the rev, git's order; a
        missing tree is empty, `walk.children`'s own answer.
        """
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
        `fnmatchcase` because `Path.glob` is case-sensitive and so is git's
        tree.
        """
        return sorted(path / name for kind, name in self._ls(path, False)
                      if kind == TREE
                      and (not pattern or fnmatch.fnmatchcase(name, pattern)))

    def _grain_docs(self, gdir: Path) -> list[Path]:
        """`model.grain_docs` at the rev: the same walk and the same four
        narrowings, in the same order, so a milestone read from history has
        the census it had on disk.
        """
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
        """`model._is_grain_doc` at the rev — the predicate itself, not a
        copy, so this census cannot disagree with the gate's. An unreadable
        blob stays in scope, as on disk.
        """
        return model._is_grain_doc(self._doc(path))

    def _doc(self, path: Path) -> _Blob:
        """This path at the rev, handed to a reader that expects a `Path`."""
        return _Blob(self.spec(path), lambda: self._text(path))

    def _text(self, path: Path) -> str:
        """One blob, decoded, terminators intact — the one read under them
        all. `UnicodeDecodeError` propagates, since every reader already
        catches it beside `OSError`.
        """
        rel = self._rel(path)
        if rel is None:
            raise GitError(f'{path} is outside {self.root}, so no rev holds it')
        if rel not in self._blobs:
            self._blobs[rel] = self._git(
                ['show', f'{self.rev}{REV_SEPARATOR}{rel}'])
        return self._blobs[rel].decode('utf-8')

    # --- the ten reads --------------------------------------------------------
    def milestone_dir(self, cfg: model.PmConfig, mid: str) -> Path | None:
        if not model.segment_is_literal(mid):
            return None
        for base in (cfg.roadmap, cfg.roadmap / model.ARCHIVE_DIR_NAME):
            for found in self._dirs(base, f'{mid}-*'):
                return found
        return None

    def feature_file(self, cfg: model.PmConfig, fid: str) -> Path | None:
        mid, _, slug = fid.partition('/')
        if not model.segment_is_literal(slug):
            return None
        mdir = self.milestone_dir(cfg, mid)
        if mdir is None:
            return None
        ffile = mdir / FEATURES_DIR / slug / model.FEATURE_DOC
        return ffile if self.is_file(ffile) else None

    def feature_files(self, mdir: Path) -> list[Path]:
        features = mdir / FEATURES_DIR
        return [d / model.FEATURE_DOC for d in self._dirs(features)
                if self.is_file(d / model.FEATURE_DOC)]

    def story_files(self, ffile: Path) -> list[Path]:
        return self._grain_docs(ffile.parent / STORIES_DIR)

    def bug_files(self, mdir: Path) -> list[Path]:
        return self._grain_docs(mdir / BUGS_DIR)

    def review_record_for(self, cfg: model.PmConfig, fid: str) -> str | None:
        """`model.review_record_for` at the rev. An absolute pointer resolves
        to nothing here, even one that falls inside the root: it named a
        place on one machine's disk, not a path in the rev.
        """
        ffile = self.feature_file(cfg, fid)
        if ffile is None:
            return None
        pointer = model.unquote(self.field_of(ffile, 'reviewed'))
        if pointer and pointer != 'null' and not pointer.startswith('/'):
            if self.is_file(cfg.root / pointer):
                return pointer
        return None

    def field_of(self, path: Path, key: str) -> str:
        return model.field_of(self._doc(path), key)

    def read_raw(self, path: Path) -> str:
        return model.read_raw(self._doc(path))

    def is_file(self, path: Path) -> bool:
        """Is there a blob at this path at the rev? A tree is not a file —
        `git show <rev>:<dir>` succeeds with a listing.
        """
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
        one that will not parse is `ledger.LedgerError` naming
        `<rev>:<path>`.
        """
        if not self.is_file(path):
            return []
        return ledger.read_rows(self._doc(path))


class Grain(NamedTuple):
    """One story, feature or bug under the milestone, as the TREE holds it."""
    gid: str
    kind: str
    size: str


class Section(NamedTuple):
    """One of the milestone's questions: `data` returns its own keys and
    `lines` reads the whole object back, so a section may print another's
    number and none recomputes one. Sections are added to the registry,
    never as a branch inside one.
    """
    name: str
    data: Callable[[Source, model.PmConfig, str, Path, list], dict]
    lines: Callable[[model.PmConfig, dict], list[str]]


# --- the numbers --------------------------------------------------------------
def _blank() -> dict:
    """An accumulator that has seen nothing. Every sum starts ABSENT, not 0."""
    return {'dispatches': 0, 'usage': {key: None for key in USAGE_KEYS},
            'tool_calls': None, 'duration_s': None}


def _plus(running: int | None, value: object) -> int | None:
    """`running` plus `value`, where an absent or non-integer value adds
    nothing: `None + absent` stays None, `0 + absent` stays 0. No number is
    ever this module's reason to fail.
    """
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
    for key in COUNT_KEYS:
        acc[key] = _plus(acc[key], row.get(key))


# --- the tree -----------------------------------------------------------------
def _grain(src: Source, path: Path, kind: str, fallback: str) -> Grain:
    """One grain document as a row: its own `id:` (the id `_ledger_id` writes,
    which the report joins on), its kind, its `size:`; a missing id falls
    back to the path's.
    """
    gid = model.unquote(src.field_of(path, 'id')) or fallback
    return Grain(gid, kind, src.field_of(path, SIZE_FIELD))


def _bug_slug(mdir: Path, path: Path) -> str:
    """`bugs/` is walked recursively, so a bug's slug may carry a directory."""
    return path.relative_to(mdir / BUGS_DIR).with_suffix('').as_posix()


def walk_grains(src: Source, cfg: model.PmConfig, mid: str,
                mdir: Path) -> tuple[list[Grain], dict[str, set[str]]]:
    """Every grain under the milestone, and which stories each feature owns —
    the walkers `check pm` uses.
    """
    grains: list[Grain] = []
    owned: dict[str, set[str]] = {}
    for ffile in src.feature_files(mdir):
        feature = _grain(src, ffile, KIND_FEATURE, f'{mid}/{ffile.parent.name}')
        grains.append(feature)
        stories = set()
        for sfile in src.story_files(ffile):
            slug = model.story_slug_of(cfg, sfile.stem)
            story = _grain(src, sfile, KIND_STORY, f'{feature.gid}/{slug}')
            grains.append(story)
            stories.add(story.gid)
        owned[feature.gid] = stories
    for bfile in src.bug_files(mdir):
        grains.append(_grain(src, bfile, KIND_BUG,
                             f'{mid}/{BUGS_DIR}/{_bug_slug(mdir, bfile)}'))
    return grains, owned


def named_grains(row: dict, kinds: dict[str, str],
                 owned: dict[str, set[str]]) -> set[str]:
    """The grains under this milestone that one dispatch row names.

    Two ways, and the FIRST outranks the second because it is a statement
    rather than an inference:

      `grain`  what the dispatch was told it was working on (0.4.0/D2). The
               couriers pass it from `GDK_LEDGER_GRAIN`; a hand entry passes
               `--grain`. It says what the work was ON.
      `tree`   the snapshot: a story by being in progress, a feature by being
               in progress or owning a named story. An inference from what was
               live at the instant of the row, and the only thing that existed
               before 0.4.0.

    They agree in the ordinary case and the snapshot is kept for the rows
    already written, which are never rewritten. **A row that names its grain is
    attributed by it and by nothing else** — the snapshot would otherwise add
    every OTHER story that happened to be live, and a dispatch billed for work
    it did not do is the read-side of rule 4.

    A row naming several grains through the snapshot is added to each whole (no
    weighting, D5). Category keys when present; frozen keys only for an
    old-shape row.
    """
    stated = row.get('grain')
    if isinstance(stated, str) and stated in kinds:
        return {stated} | {fid for fid, stories in owned.items()
                           if stated in stories}
    buckets_by_kind = LEGACY_BUCKETS if is_legacy(row) else CATEGORY_BUCKETS
    return _named_through(row, buckets_by_kind, kinds, owned)


def frozen_only_grains(row: dict, kinds: dict[str, str],
                       owned: dict[str, set[str]]) -> set[str]:
    """The grains a new-shape row names through the frozen keys and not the
    category keys — what `named_grains` reads past, disclosed rather than
    silent (rule 4). Empty for an old-shape row, and empty for a row that
    STATES its grain, which reads past the snapshot entirely and is not a
    silent drop: the row said which grain it was.
    """
    if is_legacy(row) or isinstance(row.get('grain'), str):
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
    row with no `tree` at all is not legacy; it never snapshotted.
    """
    tree = row.get('tree')
    return isinstance(tree, dict) and not (CATEGORY_KEYS & set(tree))


# --- the clock ----------------------------------------------------------------
def state_columns() -> tuple[str, ...]:
    """The dwell columns: one per category, whatever the vocabulary; which
    word within `in_progress` is `pm ledger show`. `done` has a column
    because a reopened grain leaves it; the seconds after the last row are
    never counted; re-entered categories sum; a stint in an undeclared word
    is disclosed as `unplaced_s`.
    """
    return model.CATEGORIES


def category_seconds(cfg: model.PmConfig, kind: str,
                     seconds: dict[str, int]) -> tuple[dict[str, int], int]:
    """(seconds per category, seconds in words the declaration does not name),
    read through the current declaration.
    """
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
    file's order is not time order under `merge=union`, and a subtraction
    over merged file order bills a negative stint. Sorting adds no fact the
    rows do not carry.
    """
    return sorted(rows, key=lambda row: (
        (stamp := ledger.parse_ts(row.data.get('ts'))) is None, stamp))


def state_seconds(rows: list) -> dict[str, int]:
    """Seconds in each state by subtraction over consecutive status rows; the
    interval belongs to the state the earlier row moved to. Nothing before
    the first row or after the last is measured; an unparseable `ts`
    contributes nothing.
    """
    seconds: dict[str, int] = {}
    for earlier, later in zip(rows, rows[1:]):
        state = earlier.data.get('to')
        start = ledger.parse_ts(earlier.data.get('ts'))
        end = ledger.parse_ts(later.data.get('ts'))
        if not isinstance(state, str) or not state or None in (start, end):
            continue
        seconds[state] = seconds.get(state, 0) + int(
            (end - start).total_seconds())
    return seconds


# --- section 1: spend per grain -----------------------------------------------
def spend_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
               rows: list) -> dict:
    """Section 1 as data: one entry per grain, the strays, and the totals."""
    grains, owned = walk_grains(src, cfg, mid, mdir)
    kinds = {g.gid: g.kind for g in grains}
    dispatch = [r for r in rows if r.data.get('kind') == ledger.KIND_DISPATCH]
    status = [r for r in rows if r.data.get('kind') == ledger.KIND_STATUS]
    per_grain = {g.gid: _blank() for g in grains}
    per_type: dict[str, dict[str | None, dict]] = {g.gid: {} for g in grains}
    unattributed, totals = _blank(), _blank()
    # The boundary, counted (D7): old-shape rows, and how many named nothing
    # here.
    legacy_rows = 0
    legacy_unattributed = 0
    # The drop, counted per grain: rows that named it only through a frozen
    # key.
    frozen_only = {g.gid: 0 for g in grains}
    for row in dispatch:
        # Every row lands in the totals exactly once, so the summary line is a
        # statement about the file.
        _add(totals, row.data)
        legacy = is_legacy(row.data)
        legacy_rows += legacy
        for gid in frozen_only_grains(row.data, kinds, owned):
            frozen_only[gid] += 1
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
        my_status = [r for r in status if r.data.get('grain') in names]
        placed, unplaced = category_seconds(
            cfg, grain.kind, state_seconds(my_status))
        out.append({
            'grain': grain.gid, 'kind': grain.kind,
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
    return {'section': SECTION_SPEND, 'grains': out,
            'unattributed': unattributed,
            'legacy': {'rows': legacy_rows,
                       'unattributed': legacy_unattributed},
            'totals': {'dispatch_rows': len(dispatch),
                       'status_rows': len(status), 'grains': len(grains),
                       **{k: v for k, v in totals.items()
                          if k != 'dispatches'}}}


AT_REV = ' — at {rev}'


def heading_id(data: dict) -> str:
    """The milestone id as a heading names it, plus ` — at <rev>` from git;
    every section heading carries it, the summary line does not.
    """
    rev = data.get('rev')
    return f'{data["milestone"]}{AT_REV.format(rev=rev)}' if rev else str(
        data['milestone'])


def _cell(value: object) -> str:
    """One number as a cell: the integer, or `-` when nobody recorded it."""
    return DASH if value is None else str(value)


def _table(title: str, headers: tuple[str, ...], aligns: tuple[str, ...],
           rows: list[tuple[str, ...]]) -> list[str]:
    """One `-- <title> (n)` block, columns padded; the heading prints even at
    `(0)`, because silence reads like a scan that never happened.
    """
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
    """The columns every spend row shares: dispatches, four sums, two counts."""
    return (_cell(entry['dispatches']),
            *(_cell(entry['usage'][key]) for key in USAGE_KEYS),
            *(_cell(entry[key]) for key in COUNT_KEYS))


def spend_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 1 as lines: a heading, one table per kind, the strays, a total."""
    totals = data['totals']
    out = [f'{HEADING_PREFIX} {heading_id(data)} — {SPEND_TITLE} — '
           f'{totals["dispatch_rows"]} dispatch row(s), '
           f'{totals["status_rows"]} status row(s), '
           f'{totals["grains"]} grain(s)']
    for kind in KIND_ORDER:
        entries = [e for e in data['grains'] if e['kind'] == kind]
        states = state_columns()
        headers = (GRAIN_COLUMN, SIZE_COLUMN, *SPEND_COLUMNS, *states,
                   TOTAL_COLUMN)
        aligns = (LEFT, LEFT) + (RIGHT,) * (len(headers) - 2)
        rows: list[tuple[str, ...]] = []
        for entry in entries:
            rows.append((entry['grain'], entry['size'] or '',
                         *_spend_cells(entry),
                         *(_cell(entry['states'][state]) for state in states),
                         _cell(entry['total_s'])))
            # One agent type is the grain's row said twice; the split prints
            # only where there is something to split.
            if len(entry['agent_types']) > 1:
                for split in entry['agent_types']:
                    rows.append((
                        f'{SUB_ROW_INDENT}{split["agent_type"] or DASH}', '',
                        *_spend_cells(split), *('',) * (len(states) + 1)))
        out.append('')
        out.extend(_table(f'{kind} ({len(entries)})', headers, aligns, rows))
        # Disclosed under the table it is missing from: a stint in an
        # undeclared word must not read as "no stint measured".
        unplaced = [(e['grain'], e['unplaced_s']) for e in entries
                    if e.get('unplaced_s')]
        for gid, spent in unplaced:
            out.append(f'   {gid} {UNPLACED_NOTE}: {spent} s')
        # Its dispatch-side twin: a frozen-key-only attribution must not read
        # as "no row".
        for entry in entries:
            if entry.get('frozen_only'):
                out.append(f'   {entry["grain"]} {FROZEN_ONLY_NOTE}: '
                           f'{entry["frozen_only"]} dispatch row(s)')
    stray = data['unattributed']
    out.append('')
    out.extend(_table(f'{NO_GRAIN_TITLE} ({stray["dispatches"]})',
                      SPEND_COLUMNS, (RIGHT,) * len(SPEND_COLUMNS),
                      [_spend_cells(stray)] if stray['dispatches'] else []))
    legacy = data.get('legacy') or {}
    if legacy.get('unattributed'):
        out.append(f'   {legacy["unattributed"]} of these {LEGACY_NOTE}')
    out.append('')
    out.append(f'{HEADING_PREFIX} {data["milestone"]} — '
               f'{_cell(totals["usage"]["output"])} out / '
               f'{_cell(totals["tool_calls"])} tool calls / '
               f'{_cell(totals["duration_s"])} s across '
               f'{totals["dispatch_rows"]} dispatch row(s)')
    return out


# --- the review records (sections 2 and 3) ------------------------------------
# Where one feature's record is: the `reviewed:` pointer, then
# `features/<slug>/review.md`; the table prints the path it read.
NO_VERDICT = 'no verdict block'


class RecordError(Exception):
    """A review record whose verdict block exists and will not parse, naming
    record and line — the one content refusal sections 2-5 make. No block
    at all is `NoVerdict`, listed as a fact.
    """


def review_records(src: Source, cfg: model.PmConfig, mid: str,
                   mdir: Path) -> list[tuple[str, str, Path]]:
    """(feature id, the path as the report prints it, the path) per record."""
    out: list[tuple[str, str, Path]] = []
    for ffile in src.feature_files(mdir):
        fid = (model.unquote(src.field_of(ffile, 'id'))
               or f'{mid}/{ffile.parent.name}')
        rel = src.review_record_for(cfg, fid)
        path = (cfg.root / rel) if rel else None
        if path is None:
            beside = ffile.parent / model.REVIEW_FILE_NAME
            if src.is_file(beside):
                path, rel = beside, cfg.rel(beside)
        if path is not None and rel is not None:
            out.append((fid, rel, path))
    # By feature id: the table's order is a contract, a walker's is a
    # filesystem fact.
    out.sort(key=lambda found: found[0])
    return out


def parsed_records(src: Source, cfg: model.PmConfig, mid: str,
                   mdir: Path) -> list[tuple[str, str, object]]:
    """Every record, parsed: its passes (one per verdict block, in order), or
    `None` when it carries no block. Sections 2 and 3 both call this;
    `verdict.parse` is the only reader either has.
    """
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
    it has none. Inside a section with rows, an empty block still prints
    its `(0)` heading.
    """
    out = ['', f'{HEADING_PREFIX} {mid} — {title} — {census}']
    if not any(rows for _, _, _, rows in blocks):
        out.append(NO_DATA)
        return out
    for btitle, headers, aligns, rows in blocks:
        out.append('')
        out.extend(_table(btitle, headers, aligns, rows))
    return out


# --- section 2: yield per review pass -----------------------------------------
def yield_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
               rows: list) -> dict:
    """Section 2 as data: counting over the block's closed sets per record.
    The disposition is read as its kind, never as the shape of its value;
    `open` is its own column. Spend is not joined in — picking
    "reviewer-shaped" agent types would be a label (D5).
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
        records.append({'feature': fid, 'record': rel, 'passes': passes})
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
    passes = [(r['feature'], r['record'], str(one['pass']), one['verdict'],
               _cell(one['findings']),
               *(_cell(one['dispositions'][kind])
                 for kind in verdict.DISPOSITION_KINDS))
              if one else
              (r['feature'], r['record'], DASH, NO_VERDICT, _cell(None),
               *(_cell(None) for _ in verdict.DISPOSITION_KINDS))
              for r in records for one in (r['passes'] or [None])]
    severities = [(r['feature'], str(one['pass']), sev, str(n))
                  for r in records for one in r['passes']
                  for sev, n in one['severities'].items()]
    deferred = sorted((d['target'], r['feature'], str(one['pass']),
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
    """Section 3 as data: the verdict spread, per pass rather than per
    record.
    """
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
    """Section 4 as data: every bug whose `caused_by:` names a feature,
    grouped by the id named, resolved wherever it lives; an unresolved
    cause keeps its row with `-`. The feature's `status:` is copied
    verbatim; `feature_done` is the equality, never a judgement.
    """
    out = []
    for bfile in src.bug_files(mdir):
        cause = src.field_of(bfile, CAUSED_BY_FIELD)
        if not cause:
            continue
        gid = (model.unquote(src.field_of(bfile, 'id'))
               or f'{mid}/{BUGS_DIR}/{_bug_slug(mdir, bfile)}')
        ffile = src.feature_file(cfg, cause)
        fstatus = src.field_of(ffile, 'status') if ffile is not None else ''
        out.append({
            'caused_by': cause, 'bug': gid,
            'status': src.field_of(bfile, 'status') or None,
            'feature_status': fstatus or None,
            'feature_done': (None if not fstatus
                             else ledger.ends_grain(cfg, KIND_FEATURE, fstatus))})
    out.sort(key=lambda e: (e['caused_by'], e['bug']))
    return {SECTION_ESCAPES: {
        'bugs': out,
        'totals': {'bugs': len(out),
                   'features': len({e['caused_by'] for e in out})}}}


def escapes_lines(cfg: model.PmConfig, data: dict) -> list[str]:
    """Section 4 as lines: cause, bug, the bug's state, the feature's."""
    section = data[SECTION_ESCAPES]
    bugs = [(e['caused_by'], e['bug'], _cell(e['status']),
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
    """`later - earlier`, or None unless both ends are integers — an absent
    end read as zero would invert a cumulative row.
    """
    a, b = _int(earlier), _int(later)
    return None if a is None or b is None else b - a


def _usage_of(row: dict, key: str) -> object:
    usage = row.get('usage')
    return usage.get(key) if isinstance(usage, dict) else None


def overhead_data(src: Source, cfg: model.PmConfig, mid: str, mdir: Path,
                  rows: list) -> dict:
    """Section 5 as data: a story's `tool_calls_before_first_write` summed and
    listed; a decision row against the grain its own `grain` names, never
    divided or attributed; the seconds after a decision to the next status
    row in its scope; session rows diffed per `session_id` (cumulative
    totals, D4).
    """
    grains, owned = walk_grains(src, cfg, mid, mdir)
    kinds = {g.gid: g.kind for g in grains}
    dispatch = [r for r in rows if r.data.get('kind') == ledger.KIND_DISPATCH]
    status = [r for r in rows if r.data.get('kind') == ledger.KIND_STATUS
              and isinstance(r.data.get('grain'), str)]
    decisions = [r for r in rows if r.data.get('kind') == ledger.KIND_DECISION]
    sessions = [r for r in rows if r.data.get('kind') == ledger.KIND_SESSION]

    stories = []
    for grain in sorted((g for g in grains if g.kind == KIND_STORY),
                        key=lambda g: g.gid):
        mine = [r for r in dispatch
                if grain.gid in named_grains(r.data, kinds, owned)]
        calls = [n for n in (_int(r.data.get(BEFORE_WRITE_KEY)) for r in mine)
                 if n is not None]
        stories.append({'grain': grain.gid, 'dispatches': len(mine),
                        'before_first_write': sum(calls) if calls else None,
                        'calls': calls})

    scopes = {mid: {g.gid for g in grains} | {mid}}
    for fid, sids in owned.items():
        scopes[fid] = {fid} | sids
    # Every feature and the milestone itself, but only once something has been
    # decided; zeros under a ledger with no decision row would wear a
    # measurement's shape.
    per_grain = ([{'grain': gid,
                   'decisions': sum(1 for r in decisions
                                    if r.data.get('grain') == gid)}
                  for gid in [mid, *sorted(owned)]] if decisions else [])
    events = []
    for row in decisions:
        gid = row.data.get('grain')
        gid = gid if isinstance(gid, str) else None
        scope = scopes.get(gid, {gid} if gid else set())
        moment = ledger.parse_ts(row.data.get('ts'))
        seconds = None
        if moment is not None:
            later = [ts for ts in (ledger.parse_ts(r.data.get('ts'))
                                   for r in status
                                   if r.data['grain'] in scope)
                     if ts is not None and ts > moment]
            if later:
                seconds = int((min(later) - moment).total_seconds())
        entry = row.data.get('entry')
        title = row.data.get('title')
        stamp = row.data.get('ts')
        events.append({'grain': gid,
                       'entry': entry if isinstance(entry, str) else None,
                       'title': title if isinstance(title, str) else None,
                       'ts': stamp if isinstance(stamp, str) else None,
                       'next_status_s': seconds})

    grouped: dict = {}
    for row in sessions:
        sid = row.data.get('session_id')
        grouped.setdefault(sid if isinstance(sid, str) and sid else None,
                           []).append(row)
    deltas = []
    for sid in sorted(grouped, key=lambda s: (s is None, s or '')):
        for earlier, later in zip(grouped[sid], grouped[sid][1:]):
            stamp = later.data.get('ts')
            deltas.append({
                'session_id': sid,
                'ts': stamp if isinstance(stamp, str) else None,
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
    stories = [(e['grain'], str(e['dispatches']),
                _cell(e['before_first_write']),
                LIST_SEPARATOR.join(str(n) for n in e['calls']) or DASH)
               for e in section['stories']]
    decisions = [(e['grain'], str(e['decisions']))
                 for e in section['decisions']]
    gaps = [(_cell(e['grain']), _cell(e['entry']), _cell(e['ts']),
             _cell(e['next_status_s'])) for e in section['gaps']]
    deltas = [(_cell(e['session_id']), _cell(e['ts']), _cell(e['output']),
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
# says so on the line rather than leaving a reader to assume otherwise.
#
# A `gate` row names no grain by design — a gate run is not work somebody was
# dispatched to do — so 0.4.0/D3 files every one of them in the tree's own
# ledger, and every milestone's report reads the same set. `runs`, `first_ms`
# and `delta_ms` are therefore lifetime-of-TREE numbers: two milestones'
# reports print identical gate rows, correctly.
#
# The alternative was windowing the rows by the milestone's timestamps, and it
# loses on this package's own rule: a milestone has no declared time range, so
# the window would be inferred from status rows — a number nobody stated,
# quoted as if it had been. Naming what the numbers are about is the cheapest
# honest fix (rule 11), and per-release gate cost stays answerable from `ts`.
GATES_SCOPE_NOTE = ('across the whole tree, not this milestone: a gate row '
                    'names no grain, so every one lands in the tree\'s ledger')


def _gate_unusable(row: dict) -> str | None:
    """Why this `kind: gate` row cannot be counted, or None — named beside the
    row rather than dropped, so the table cannot look clean over discarded
    input.
    """
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
    `delta_ms` is `last - first`. A gate with one run still appears, with
    `-`; a delta whose census moved is printed and marked (`comparable`).
    Nothing is a ceiling or a budget.
    """
    gate_rows = [r.data for r in rows
                 if r.data.get('kind') == ledger.KIND_GATE]
    unusable, runs_of = [], {}
    for row in gate_rows:
        why = _gate_unusable(row)
        if why is not None:
            name = row.get(GATE_KEY)
            unusable.append({'gate': name if isinstance(name, str) and name
                             else None, 'why': why,
                             'ts': row.get('ts') if isinstance(row.get('ts'),
                                                               str) else None})
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
    is no answer.
    """
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
    unusable = [(_cell(e['gate']), e['why'], _cell(e['ts']))
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
    sit at the top level as shipped; sections 2-5 each add one key. `rev`
    is present only when there was a rev (a `"rev": null` would be a
    question nobody asked).
    """
    src = DiskSource() if src is None else src
    rows = in_time_order(rows)
    out: dict = {'milestone': mid}
    if src.rev:
        out['rev'] = src.rev
    for section in SECTIONS:
        out.update(section.data(src, cfg, mid, mdir, rows))
    return out


def beyond_ledger(data: dict) -> bool:
    """Did anything outside `ledger.jsonl` get measured — a verdict block or
    an escape — so the caller does not stop at the one-line form over a
    tree that holds one? Narrow: a record with no block is not a
    measurement.
    """
    return (any(record['passes'] for record in data[SECTION_YIELD]['records'])
            or bool(data[SECTION_ESCAPES]['totals']['bugs']))


def render(cfg: model.PmConfig, data: dict) -> list[str]:
    """The whole report as lines, in section order."""
    lines: list[str] = []
    for section in SECTIONS:
        lines.extend(section.lines(cfg, data))
    return lines
