"""What a PM TREE CONTAINS, and every fact read off it: the grains, the pools
they live in, the index that finds one by id, the children a binding claims, the
sections inside a grain document, the plan that orders the milestones, and the
drift a gate asks about.

Identity is frontmatter and location is convention: `id:` and `kind:` are read
from the document, the pools are where documents live, and neither is derived
from a path (0.4.0). `grain(cfg, gid, kind)` is the id-addressed handle and
`Grain.field` the read every other module goes through, which
`tests/test_boundaries.py` holds to this module and its named roster. One walk
per scan — `reading_tree()` holds the snapshot.

What a project DECLARES is `vocabulary.py`. This module imports it and is never
imported by it, and no value here comes from `devkit.toml` except through the
`PmConfig` a caller hands in.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from agentic_sdlc.core import apply, frontmatter, walk
from agentic_sdlc.core.config import pointer_escapes
from agentic_sdlc.core.walk import Kind, SkipReason, Walk
from agentic_sdlc.repo.pm.vocabulary import (
    ARCHIVE_DIR_NAME, BINDS_TO, BUGS_DIR, DONE_CATEGORY, FEATURES_DIR,
    FEATURE_DOC, FIELD_ID, FIELD_KIND, FIELD_STATUS, FLOW_KINDS, GRAIN_BUG,
    GRAIN_FEATURE, GRAIN_MILESTONE, GRAIN_STORY, IN_PROGRESS, MILESTONE_DOC,
    ORDER_KEY, PmConfig, RELEASES_DOC, ROOT_ID, ROOT_KIND, SLOT_HEADER,
    STORIES_DIR, TODO, VERSION_AT_START, category_of, flow_of, holds)

# --- id <-> path --------------------------------------------------------------
# Milestone dirs carry a human suffix (`0.28-chronicle`); the id is the
# version, globbed active tree first, then the archive.
# Ids reach glob() as patterns, so an id must be a literal, never a pattern.
_GLOB_CHARS = set('*?[]!')


def id_is_literal(value: str) -> bool:
    return bool(value) and not (_GLOB_CHARS & set(value))


def segment_is_literal(value: str) -> bool:
    """One id segment the resolvers may join onto a directory — the resolution
    twin of `_check_slug`: no `.`/`..`/empty segment, separator or glob."""
    return (id_is_literal(value) and value not in ('.', '..')
            and not any(c in value for c in '/\\'))


# --- THE GRAIN LAYER: identity is frontmatter, location is convention -------
# `id:` and `kind:` are read from the document; the pools are where documents
# live; nothing interprets a path. The ~20 functions this replaced each joined
# an id onto a directory or into a `glob()` pattern — what `segment_is_literal`
# was written to make safe. Match-by-field builds no path from user input.

# The kind prefix a human reads off a bare id, without its location; `kind:` is
# what the TOOL reads. NOT a namespace: it does not make ids unique across
# repos, and cross-repo disambiguation is a display concern, never a filename.
KIND_PREFIX = {GRAIN_MILESTONE: 'ms', GRAIN_FEATURE: 'ft', GRAIN_STORY: 'st',
               GRAIN_BUG: 'bg'}

# What joins the prefix to the slug. Named because `mint_id` and every reader
# that asks "does this already carry its prefix" must agree on the byte.
PREFIX_SEPARATOR = '-'


def mint_id(kind: str, slug: str) -> str:
    """`<prefix>-<slug>` — THE ONE MINTING PATH, for `pm new` and for
    `tools/dev/pm_migrate.py`, so a migrated tree grows one id vocabulary and
    not two (`bg-the-new-verbs-mint-a-compound-id`).
    No parent in it: a binding is the child's own field, and an id restating it
    made re-parenting a `pm rename` plus a ref sweep. It MINTS and nothing else;
    no check grades an id against this (rule 9).
    """
    prefix = KIND_PREFIX[kind] + PREFIX_SEPARATOR
    return slug if slug.startswith(prefix) else f'{prefix}{slug}'


# The pool directory each kind DERIVES when the config names none. Spelled out
# rather than `f'{kind}s'` — English is not a rule to infer, and `storys` is
# what that inference produces.
POOL_NAME = {GRAIN_MILESTONE: 'milestones', GRAIN_FEATURE: 'features',
             GRAIN_STORY: 'stories', GRAIN_BUG: 'bugs'}


@dataclass(frozen=True)
class Grain:
    """One grain document, read once: what it says it is and what it says it
    belongs to. Nothing here is derived from `path`."""

    gid: str
    kind: str
    path: Path
    status: str = ''
    binding: str = ''

    # --- THE READ ADDRESSED BY IDENTITY ---------------------------------------
    # `grain(cfg, gid)` resolves an id to one of these and `.field(key)` asks
    # what it SAYS — so a caller that knows an id never names a file, and the
    # day a grain is not a file on disk this method is the only thing that has
    # to learn it. 102 callers handed `field_of` a `Path` before this existed;
    # `tests/test_boundaries.py::TheEngineAsksByIdNotByPath` holds the roster
    # of the ones that legitimately still hold a file.
    def field(self, key: str) -> str:
        """What this grain says under `key`, or ''."""
        return frontmatter.field_of(self.path, key)

    def list_field(self, key: str) -> list[str]:
        """The block list this grain declares under `key`, or []."""
        return frontmatter.list_field_of(self.path, key)

    def declares(self, key: str) -> bool:
        """Does this grain carry `key:` at ALL — presence, not value, for the
        fields whose mere existence is the finding (`RETIRED_FIELDS`). Raises
        what the read raises, as the parse does: a grain nobody can read is not
        an absence (rule 4)."""
        return key in frontmatter.document(self.path).fields

    def sequence_defect(self, key: str) -> str:
        """Why this grain's block list under `key` cannot be rewritten, or ''."""
        return frontmatter.sequence_defect(self.path, key)


def pool_dir(cfg: PmConfig, kind: str) -> Path:
    """Where documents of one kind live. Configured, or `<roadmap>/<kind>s`,
    relative to the repo root the tool already discovers: an absolute root in a
    committed config is wrong in every worktree, on every other machine and in
    CI, which is why there is no `project_root_dir` key.
    """
    declared = getattr(cfg, f'{kind}_dir_key', '')
    if declared:
        return cfg.root / declared
    return cfg.roadmap / POOL_NAME[kind]


def _is_shared_doc(path: Path) -> bool:
    """A grain's own decisions/handoff/review doc, rather than a grain. BOTH
    halves: a pooled slug is free-form, so a story named like a shared doc is
    not one, and it says so by opening frontmatter — which the two minted
    shared docs never do.
    """
    if not any(path.name.endswith(f'-{slot}') for slot in SLOT_HEADER):
        return False
    return not _is_grain_doc(path)


# --- ONE WALK PER SCAN --------------------------------------------------------
# `document` answers *what does this file say* once; this answers *what is in
# the tree* once. `check pm` asked that question about 330 times over a
# 700-document tree, and every ask was four `rglob`s and a sort.
#
# SCOPED, never a global memo: a verb that writes must see its own write on the
# next read, so the snapshot lives only inside `reading_tree()`. Belt and
# braces, it is dropped the instant anything in this process mutates a file —
# `core.apply` counts every write this package is allowed to make.
_SNAPSHOT: dict | None = None
_MUTATIONS_KEY = 'mutations'


@contextmanager
def reading_tree():
    """Walk the pools ONCE for the length of this block — for a caller that
    only reads. Nested scopes share the outer one; leaving drops it.
    """
    global _SNAPSHOT
    outer = _SNAPSHOT
    if outer is None:
        _SNAPSHOT = {_MUTATIONS_KEY: apply.mutations()}
    try:
        yield
    finally:
        _SNAPSHOT = outer


def _held(key, produce):
    """`produce()`, held for the rest of the scope when there is one and
    nothing has written since it opened."""
    snap = _SNAPSHOT
    if snap is None:
        return produce()
    mutations = apply.mutations()
    if snap.get(_MUTATIONS_KEY) != mutations:
        snap.clear()
        snap[_MUTATIONS_KEY] = mutations
    if key not in snap:
        snap[key] = produce()
    return snap[key]


def pool_scan(cfg: PmConfig, kind: str) -> Walk:
    """One pool as a `Walk` — the kept documents AND what it narrowed away.
    `slot_walk` for a table: a dot prefix is a deliberate hide and a `.md` that
    opens no frontmatter is a note, and both are COUNTED (rule 4).
    """
    base = pool_dir(cfg, kind)
    return _held(('pool', str(base)), lambda: _pool_scan(base))


def _pool_scan(base: Path) -> Walk:
    if not base.is_dir():
        return Walk(())
    return (walk.descendants(base, Kind.FILE, suffix='.md')
            .filter(lambda p: not _is_hidden(base, p), SkipReason.DOTTED_NAME)
            .filter(lambda p: not _is_shared_doc(p), SkipReason.SHARED_DOC)
            .filter(_is_grain_doc, SkipReason.NO_FRONTMATTER))


def pool_walk(cfg: PmConfig, kind: str) -> list[Path]:
    """Every document in one pool, sorted."""
    return sorted(pool_scan(cfg, kind).kept)


def pool_census(cfg: PmConfig, kind: str, label: str) -> str:
    """One pool's count WITH its narrowings. A bare number is not available on
    purpose: the count and what the walk left out render together, or the count
    is a claim about the filter rather than about the tree (rule 4).
    """
    return pool_scan(cfg, kind).census(label)


def pool_skipped(cfg: PmConfig, kind: str) -> int:
    """How many candidates a narrowing removed from one pool."""
    return sum(pool_scan(cfg, kind).counts().values())


def doc_grain(path: Path, kind: str = '') -> Grain:
    """One document as a `Grain`, whatever it declares — `read_grain`'s TOTAL
    sibling, for a walk that must not drop the document it just found.

    `gid` is '' when the document declares no `id:` or cannot be read, which is
    exactly what a reader of the field got; `read_grain` answers None there
    instead, and `check pm` counts those SKIPPED rather than dropping them
    (`ft-identity-lives-in-frontmatter`). The two answers are different
    questions and both have callers, so both are spelled.
    """
    try:
        doc = frontmatter.document(path)
    except (OSError, UnicodeDecodeError):
        return Grain(gid='', kind=kind, path=path)
    declared = doc.field(FIELD_KIND) or kind
    field = BINDS_TO.get(declared, ('', ''))[1]
    return Grain(gid=doc.field(FIELD_ID), kind=declared, path=path,
                 status=doc.field(FIELD_STATUS),
                 binding=doc.field(field) if field else '')


def read_grain(cfg: PmConfig, path: Path, kind: str) -> Grain | None:
    """One document as a `Grain`, or None when it declares no id.

    `kind` is the POOL it was found in, and it is only a default: a document
    that declares `kind:` is that kind wherever it sits, because the location
    is convention the tool does not interpret. A document that cannot be read
    declares no id.
    """
    found = doc_grain(path, kind)
    return found if found.gid else None


def is_pooled(cfg: PmConfig) -> bool:
    """Has this tree been migrated? True when any pool holds a document.

    The one place the two layouts are told apart, and a fact about the tree
    rather than a config key: a key would be a second copy of what the
    directory already says, to be kept in agreement mid-migration.
    """
    return any(pool_dir(cfg, kind).is_dir() and pool_walk(cfg, kind)
               for kind in FLOW_KINDS)


def is_nested(cfg: PmConfig) -> bool:
    """Does this tree still hold grain DIRECTORIES? The question a WRITE asks:
    a reader tells the layouts apart by what it finds, a writer has to choose
    before anything exists."""
    return bool(milestone_dirs(cfg))


def mint_dir(cfg: PmConfig, kind: str, parent: Path | None = None) -> Path:
    """Where `pm new` puts a NEW document of `kind` — the pool, unless the tree
    is still nested, in which case it keeps its shape. Minting into a pool on a
    nested tree flips `is_pooled` and hides every other grain behind it."""
    if not is_nested(cfg):
        return pool_dir(cfg, kind)
    if kind == GRAIN_MILESTONE:
        return cfg.roadmap
    if parent is None:
        return pool_dir(cfg, kind)
    if kind == GRAIN_FEATURE:
        return parent / FEATURES_DIR
    if kind == GRAIN_STORY:
        return parent / STORIES_DIR
    return parent / BUGS_DIR


def _nested_index(cfg: PmConfig) -> dict[str, Grain]:
    """The pre-0.4.0 layout, read the way it was always read: kind from the
    slot the document sits in, parent from the directory above.

    Kept so a consumer's tree keeps working the day they bump and before it is
    moved — the alternative reads nothing until a migration lands, which is a
    breaking change wearing a minor number. The ONLY code left that treats a
    path as schema; `tools/dev/pm_migrate.py` is the mover.
    """
    out: dict[str, Grain] = {}

    def take(path: Path, kind: str, binding: str) -> str:
        gid = frontmatter.field_of(path, FIELD_ID)
        if not gid:
            return ''
        out.setdefault(gid, Grain(gid=gid, kind=kind, path=path,
                                  status=frontmatter.field_of(path, FIELD_STATUS),
                                  binding=binding))
        return gid

    for mdir in milestone_dirs(cfg):
        mid = take(mdir / MILESTONE_DOC, GRAIN_MILESTONE, '')
        for ffile in _nested_feature_files(mdir):
            fid = take(ffile, GRAIN_FEATURE, mid)
            for sfile in _nested_story_files(ffile):
                take(sfile, GRAIN_STORY, fid)
        for bfile in _nested_bug_files(mdir):
            take(bfile, GRAIN_BUG, mid)
    return out


def grain_index(cfg: PmConfig) -> dict[str, Grain]:
    """Every grain in the tree, by id — the pools plus the ROOT container. The
    one walk every resolver goes through.

    A duplicate id is NOT resolved here — the first one read wins and V1 names
    every file that shares one. Uniqueness is a gate FINDING and never a
    runtime lock (0.4.0/D4).

    Held for the length of a `reading_tree()` scope; built afresh outside one.
    Every caller READS the mapping — inside a scope, editing it would be
    editing the next reader's answer.
    """
    return _held(('index', str(cfg.roadmap),
                  tuple(str(pool_dir(cfg, k)) for k in FLOW_KINDS)),
                 lambda: _grain_index(cfg))


def _grain_index(cfg: PmConfig) -> dict[str, Grain]:
    if is_pooled(cfg):
        out: dict[str, Grain] = {}
        for kind in FLOW_KINDS:
            for path in pool_walk(cfg, kind):
                grain = read_grain(cfg, path, kind)
                if grain is not None:
                    out.setdefault(grain.gid, grain)
    else:
        out = _nested_index(cfg)
    root = root_grain(cfg)
    if root is not None:
        # LAST: a pool document claiming the plan's id is a duplicate the gate
        # reports, and the resolver must not answer it with the plan.
        out.setdefault(root.gid, root)
    return out


# The characters an id cannot carry in EITHER layout. NOT the security guard —
# match-by-field is, and no id reaches a path. This is CHEAPNESS: an id that
# cannot be a grain's is refused before the tree is walked, so a hostile string
# is answered without reading a document, which the resolvers this replaced did.
_ID_FORBIDDEN = set('*?[]!\\:~\n\t\r\x00')
ID_MAX = 200


def id_defect(gid: str) -> str:
    """'' when `gid` could name a grain, else why not. Never opens a file."""
    if not gid or not gid.strip():
        return 'an id may not be empty'
    if len(gid) > ID_MAX:
        return f'an id of {len(gid)} characters is past the {ID_MAX} limit'
    if _ID_FORBIDDEN & set(gid):
        return f'{gid!r} carries a character no id may hold'
    parts = gid.split('/')
    if any(p in ('', '.', '..') for p in parts):
        return f'{gid!r} has an empty or dot segment'
    return ''


def kind_of(cfg: PmConfig, gid: str) -> str:
    """The kind a grain declares, or '' when nothing in the tree claims the id.
    The id's SHAPE is not consulted: `ft-x` and `0.1/x` are both just ids, and
    reading a kind out of either is the derivation 0.4.0 deleted.
    """
    found = grain_index(cfg).get(gid)
    return found.kind if found is not None else ''


def grain(cfg: PmConfig, gid: str, kind: str = '') -> Grain | None:
    """THE ID-ADDRESSED HANDLE: the grain an id names, or None; `kind` narrows
    when a caller knows it.

    `grain(cfg, gid).field(key)` is how a module that knows an id asks what
    that grain SAYS, and it is the whole of what such a module needs — the six
    resolvers this replaced each joined an id onto a directory, and every
    caller then had a `Path` and asked storage directly. This reads `id:` and
    matches, so no user input reaches a path and no caller names a file.
    """
    if id_defect(gid):
        return None
    found = grain_index(cfg).get(gid)
    if found is None or (kind and found.kind != kind):
        return None
    return found


def grain_file(cfg: PmConfig, gid: str, kind: str = '') -> Path | None:
    """The DOCUMENT for an id, or None — for the callers that need the file
    itself (a shared doc beside it, a path in a message). A caller that wants
    a FIELD asks `grain(cfg, gid).field(key)` instead.
    """
    found = grain(cfg, gid, kind)
    return None if found is None else found.path


def children(cfg: PmConfig, kind: str, parent_id: str) -> list[Grain]:
    """Grains of `kind` whose binding field names `parent_id` — found by their
    BINDING, not by which directory they sit in."""
    return [g for g in grain_index(cfg).values()
            if g.kind == kind and g.binding == parent_id]


def unbound(cfg: PmConfig, kind: str) -> list[Grain]:
    """Grains of `kind` that name no parent. Normal and expected: a grain
    written and not yet bound is what separating authoring from binding is
    FOR, and it is a census line, never a finding."""
    return [g for g in grain_index(cfg).values()
            if g.kind == kind and BINDS_TO.get(kind) and not g.binding]


def milestone_of(cfg: PmConfig, gid: str) -> str:
    """Which milestone a grain belongs to, followed through its bindings — a
    story takes one hop more than a feature. `milestone_dir_of(path)` used to
    answer this by counting path components: the same fact, derived from where
    a file sat.
    """
    index = grain_index(cfg)
    seen: set[str] = set()
    while gid and gid not in seen:
        seen.add(gid)
        grain = index.get(gid)
        if grain is None:
            return ''
        if grain.kind == GRAIN_MILESTONE:
            return grain.gid
        gid = grain.binding
    return ''


def undeclared_kinds(cfg: PmConfig) -> list[tuple[Path, str]]:
    """(document, the `kind:` it declares) for kinds this project does not
    have. A fact about the INPUT — refused by name where a verb reads one,
    reported by the gate over a tree."""
    out = []
    for kind in FLOW_KINDS:
        for path in pool_walk(cfg, kind):
            declared = frontmatter.field_of(path, FIELD_KIND)
            if declared and declared not in FLOW_KINDS:
                out.append((path, declared))
    return out


# --- the nested layout, read only by the migration ----------------------------
def milestone_dir(cfg: PmConfig, mid: str) -> Path | None:
    if not segment_is_literal(mid):
        return None
    for base in (cfg.roadmap, cfg.roadmap / ARCHIVE_DIR_NAME):
        if not base.is_dir():
            continue
        for d in walk.matching(base, f'{mid}-*', Kind.DIR).kept:
            return d
    return None


def milestone_file(cfg: PmConfig, mid: str) -> Path | None:
    """The milestone's document, in either layout — `grain_file` reads `id:`
    and matches, so no id reaches a path."""
    return grain_file(cfg, mid, GRAIN_MILESTONE)


def feature_dir(cfg: PmConfig, fid: str) -> Path | None:
    mid, _, slug = fid.partition('/')
    if not segment_is_literal(slug):
        return None
    d = milestone_dir(cfg, mid)
    if d is None:
        return None
    fdir = d / FEATURES_DIR / slug
    return fdir if fdir.is_dir() else None


def feature_file(cfg: PmConfig, fid: str) -> Path | None:
    """The feature's document, in either layout."""
    return grain_file(cfg, fid, GRAIN_FEATURE)


def story_grain(cfg: PmConfig, sid: str) -> Grain | None:
    """The story an id names, in either layout — `grain(cfg, sid, 'story')` on a
    pooled tree, and `story_file`'s own slug resolution on a nested one, where
    the index cannot answer because a nested story's id is its path.
    """
    if is_pooled(cfg):
        return grain(cfg, sid, GRAIN_STORY)
    path = story_file(cfg, sid)
    return None if path is None else doc_grain(path, GRAIN_STORY)


def story_file(cfg: PmConfig, sid: str) -> Path | None:
    """The story's document, in either layout.

    `AmbiguousStory` — *two files claim one story id* — cannot happen against a
    pooled tree: the index is keyed by id and `check pm` reports a duplicate as
    a finding. It survives for the nested layout, where a slug plus an ordinal
    prefix could resolve two ways.
    """
    if is_pooled(cfg):
        return grain_file(cfg, sid, GRAIN_STORY)
    # The nested layout keeps its own resolution WHOLE: the index answers by
    # id and `setdefault`, so consulting it first would silently pick one of
    # two files claiming a slug — a refusal turned into a wrong answer.
    mid, _, rest = sid.partition('/')
    fslug, _, sslug = rest.partition('/')
    if not fslug or not segment_is_literal(sslug):
        return None
    fdir = feature_dir(cfg, f'{mid}/{fslug}')
    if fdir is None:
        return None
    matches = [path for path in grain_docs(fdir / STORIES_DIR)
               if path.name[:-len(path.suffix)] == sslug]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AmbiguousStory(sid, [cfg.rel(p) for p in matches])
    return None


class AmbiguousStory(Exception):
    """Two files claim one story id — an authoring error, never auto-resolved."""

    def __init__(self, sid: str, paths: list[str]) -> None:
        super().__init__(f'story id {sid!r} matches {len(paths)} files: {", ".join(paths)}')
        self.sid = sid
        self.paths = paths


# --- children -----------------------------------------------------------------
def shared_doc(cfg: PmConfig, grain: 'Grain | Path', name: str) -> Path:
    """Where a grain's shared document lives. Pooled: beside the grain, under
    the grain's own stem, because a pool is flat and a bare `decisions.md`
    would be one file for every grain of that kind. Nested: inside the grain's
    directory.
    """
    path = grain if isinstance(grain, Path) else grain.path
    # `is_pooled` and not the parent's NAME: a tree that configured its pools
    # elsewhere is still pooled, and the name would put its shared docs back
    # inside directories that do not exist.
    if is_pooled(cfg):
        return path.with_name(f'{path.stem}-{name}')
    return path.parent / name


def milestone_doc(handle: Path) -> Path:
    """The milestone's DOCUMENT from whatever `known_milestones` handed back —
    a document when pooled, a directory when nested. One function, so the
    `handle / MILESTONE_DOC` join, which is the path being schema, exists in
    one place instead of a dozen.
    """
    return handle if handle.is_file() else handle / MILESTONE_DOC


def milestones(cfg: PmConfig) -> list[Grain]:
    """Every milestone, by id — for a caller that wants the grains."""
    return sorted((g for g in grain_index(cfg).values()
                   if g.kind == GRAIN_MILESTONE), key=lambda g: g.gid)


def _children_grains(cfg: PmConfig, kind: str, parent_id: str) -> list[Grain]:
    """The grains of one kind bound to one parent, in the parent's declared
    `order` where it has one and by id after that. **Sequence is the parent's
    list and membership is the child's field** — the two questions the nested
    layout answered with one directory.
    """
    found = {g.gid: g for g in children(cfg, kind, parent_id)}
    parent = grain_index(cfg).get(parent_id)
    declared = parent.list_field(ORDER_KEY) if parent is not None else []
    out = [found.pop(gid) for gid in declared if gid in found]
    return out + [found[gid] for gid in sorted(found)]


# A nested tree keeps its SLOT walk, whole: the index is keyed by `id:`, so a
# damaged document has no key and would silently leave the census, and the slot
# walk sees it either way (rule 4). A POOLED tree has no slot, so a document
# with no id is reported by `check pm` on its own line instead.
# The GRAIN walk and the PATH walk of the same children. The grains are what a
# caller reads fields from; the paths are what `report.Source` declares, since
# a rev-addressed source hands back handles that are not files at all. The path
# list is DERIVED from the grain list, so the two cannot answer differently
# about what is in the tree.
#
# `doc_grain`, not `read_grain`: a child document declaring no `id:` is in the
# parent's slot and is COUNTED, and `read_grain` would have dropped it — the
# census loss `check pm` reports as SKIPPED instead (rule 4).
def feature_grains(cfg: PmConfig, mid: str) -> list[Grain]:
    """The features bound to one milestone, in its declared order."""
    if not is_pooled(cfg):
        mdir = milestone_dir(cfg, mid)
        return [doc_grain(p, GRAIN_FEATURE)
                for p in (_nested_feature_files(mdir) if mdir is not None
                          else [])]
    return _children_grains(cfg, GRAIN_FEATURE, mid)


def story_grains(cfg: PmConfig, fid: str) -> list[Grain]:
    """The stories bound to one feature, in its declared order."""
    if not is_pooled(cfg):
        ffile = feature_file(cfg, fid)
        return [doc_grain(p, GRAIN_STORY)
                for p in (_nested_story_files(ffile) if ffile is not None
                          else [])]
    return _children_grains(cfg, GRAIN_STORY, fid)


def bug_grains(cfg: PmConfig, mid: str) -> list[Grain]:
    """The bugs bound to one milestone, in its declared order."""
    if not is_pooled(cfg):
        mdir = milestone_dir(cfg, mid)
        return [doc_grain(p, GRAIN_BUG)
                for p in (_nested_bug_files(mdir) if mdir is not None else [])]
    return _children_grains(cfg, GRAIN_BUG, mid)


def feature_files(cfg: PmConfig, mid: str) -> list[Path]:
    """The feature DOCUMENTS bound to one milestone, in its declared order."""
    return [g.path for g in feature_grains(cfg, mid)]


def story_files(cfg: PmConfig, fid: str) -> list[Path]:
    """The story DOCUMENTS bound to one feature, in its declared order."""
    return [g.path for g in story_grains(cfg, fid)]


def bug_files(cfg: PmConfig, mid: str) -> list[Path]:
    """The bug DOCUMENTS bound to one milestone, in its declared order."""
    return [g.path for g in bug_grains(cfg, mid)]


def duplicate_ids(cfg: PmConfig) -> list[tuple[str, list[Path]]]:
    """[(id, every document claiming it)] for each id claimed more than once.
    The other half of D4: `grain_index` keeps the first document read, so the
    second is in the tree, is counted, and is addressable by nothing.
    """
    seen: dict[str, list[Path]] = {}
    for kind in FLOW_KINDS:
        for path in pool_walk(cfg, kind):
            gid = frontmatter.field_of(path, FIELD_ID)
            if gid:
                seen.setdefault(gid, []).append(path)
    return [(gid, paths) for gid, paths in sorted(seen.items())
            if len(paths) > 1]


def unbound_grains(cfg: PmConfig) -> dict[str, list[str]]:
    """{'feature': [ids naming no milestone], 'story': [...], 'bug': [...]}.
    Only kinds that BIND, and only an EMPTY binding — a binding naming a grain
    that is not in the tree is V7's, because that is drift rather than a
    decision nobody has made yet.
    """
    out: dict[str, list[str]] = {}
    for gid, grain in sorted(grain_index(cfg).items()):
        bind = BINDS_TO.get(grain.kind)
        if bind is None:
            continue
        if not frontmatter.field_of(grain.path, bind[1]):
            out.setdefault(grain.kind, []).append(gid)
    return out


def stray_documents(cfg: PmConfig) -> list[Grain]:
    """Grain documents under the roadmap that sit in no pool: every pooled
    reader walks the pools, so a document outside all four is read by NOTHING
    while `check grain-shape`, which walks the roadmap whole, counts it. Shared
    docs and the plan are expected outside a pool.

    As GRAINS, because the one caller reports what each one DECLARES and a
    stray is only a stray because it declares an `id:` nothing indexes.
    """
    if not is_pooled(cfg):
        return []
    pools = {pool_dir(cfg, kind) for kind in FLOW_KINDS}
    known = {releases_file(cfg)}
    out: list[Path] = []
    for path in walk.descendants(cfg.roadmap, Kind.FILE, suffix='.md').kept:
        if path in known or _is_hidden(cfg.roadmap, path):
            continue
        if any(pool == path.parent or pool in path.parents for pool in pools):
            continue
        if _is_grain_doc(path) and frontmatter.field_of(path, FIELD_ID):
            out.append(path)
    return [doc_grain(path) for path in sorted(out)]


def unkeyed_documents(cfg: PmConfig) -> list[tuple[Path, str]]:
    """Documents in a pool that the index cannot key on, and why. `orphan_dirs`'
    successor: a document with no readable `id:` has no key, is in no index,
    and would leave the census silently.
    """
    out: list[tuple[Path, str]] = []
    for kind in FLOW_KINDS:
        for path in pool_walk(cfg, kind):
            if not frontmatter.field_of(path, FIELD_ID):
                out.append((path, 'declares no `id:`, so nothing can key on '
                                  'it'))
                continue
            if not frontmatter.field_of(path, FIELD_STATUS):
                out.append((path, 'declares no `status:` — it is in the tree '
                                  'and no question about it can be answered'))
                continue
            declared = frontmatter.field_of(path, FIELD_KIND)
            if declared and declared not in FLOW_KINDS:
                out.append((path, f'declares kind {declared!r}, which this '
                                  f'project does not have '
                                  f'({" ".join(FLOW_KINDS)})'))
    return out


def _has_milestone_file(d: Path) -> bool:
    return (d / MILESTONE_DOC).is_file()


def _has_feature_file(d: Path) -> bool:
    return (d / FEATURE_DOC).is_file()


def _milestone_candidates(base: Path, exclude_archive: bool) -> Walk:
    """Directories under one roadmap base that a milestone could be."""
    found = walk.children(base, Kind.DIR)
    if exclude_archive:
        found = found.filter(lambda d: d.name != ARCHIVE_DIR_NAME,
                             SkipReason.EXCLUDED_PATH)
    return found


def milestone_walk(cfg: PmConfig) -> Walk:
    """Milestone dirs in the active tree, with the scaffold-only dirs the walk
    dropped beside them."""
    return _milestone_candidates(cfg.roadmap, exclude_archive=True).filter(
        _has_milestone_file, SkipReason.NO_GRAIN_FILE)


def milestone_dirs(cfg: PmConfig) -> list[Path]:
    """Milestone dirs in the ACTIVE tree (archived ones predate the schema)."""
    return list(milestone_walk(cfg).kept)


def known_milestones(cfg: PmConfig) -> list[tuple[Path, str]]:
    """(a handle, the declared id) per milestone — the one enumeration
    `pm status`, `pm list` and `retire` read.

    The handle is the milestone's own DIRECTORY in a nested tree and its
    DOCUMENT in a pooled one; a caller that needs a directory asks
    `milestone_dir`.
    """
    if is_pooled(cfg):
        return [(g.path, g.gid) for g in milestones(cfg)]
    return [(mdir, frontmatter.field_of(mdir / MILESTONE_DOC, FIELD_ID))
            for mdir in milestone_dirs(cfg)]


def known_milestone_grains(cfg: PmConfig) -> list[tuple[Path, Grain]]:
    """(`known_milestones`' handle, that milestone's GRAIN) — for the readers
    that go on to ask the milestone what it SAYS.

    The handle stays beside the grain because it is the nested tree's
    DIRECTORY, which `shared_doc` and `ledger_for` need and a document cannot
    replace; the grain is `milestone_doc(handle)` read once, so a milestone
    declaring no `id:` is still in the list with an empty one — the id the
    handle-and-id pairing returned for it.
    """
    return [(handle, doc_grain(milestone_doc(handle), GRAIN_MILESTONE))
            for handle, _ in known_milestones(cfg)]


BOM = '﻿'


def _opens_frontmatter(lines: Sequence[str]) -> bool:
    """True when this text attempts a leading `---` block — lenient on a BOM,
    blank lines and fence indent, so a damaged grain is a finding rather than
    a note, but never past prose.
    """
    for line in lines:
        probe = line.lstrip(BOM)
        if not probe.strip():
            continue
        return frontmatter._FENCE.match(probe.lstrip(' \t')) is not None
    return False


def _is_grain_doc(path: Path) -> bool:
    """True when this file is a grain document rather than a note beside one.
    Detection is lenient and parsing strict, so a damaged grain stays in scope
    for the rules; so does a file that cannot be read.
    """
    try:
        return _opens_frontmatter(frontmatter.document(path).lines)
    except (OSError, UnicodeDecodeError):
        return True


def slot_walk(gdir: Path) -> Walk:
    """The walk of one slot directory (`bugs/`, `stories/`) — the single
    definition every reader shares, with two disclosed narrowings: dot-prefixed
    components, and a `.md` that opens no frontmatter.
    """
    return (walk.descendants(gdir, Kind.FILE, suffix='.md')
            .filter(lambda p: not _is_hidden(gdir, p), SkipReason.DOTTED_NAME)
            .filter(_is_grain_doc, SkipReason.NO_FRONTMATTER))


def _is_hidden(gdir: Path, p: Path) -> bool:
    """True if any path component under `gdir` is dot-prefixed."""
    return any(part.startswith('.') for part in p.relative_to(gdir).parts)


def grain_docs(gdir: Path) -> list[Path]:
    """Every grain document under one slot directory, in reading order."""
    return list(slot_walk(gdir).kept)


def _nested_feature_files(mdir: Path) -> list[Path]:
    return [d / FEATURE_DOC for d in walk.children(mdir / FEATURES_DIR, Kind.DIR)
            .filter(_has_feature_file, SkipReason.NO_GRAIN_FILE).kept]


def _nested_story_files(ffile: Path) -> list[Path]:
    return grain_docs(ffile.parent / STORIES_DIR)


def tree_walk(cfg: PmConfig) -> Walk:
    """Every slot document in the active tree and everything the walk skipped;
    `Walk.census` is the only way to a number here.
    """
    found = Walk(())
    if is_pooled(cfg):
        # The same two kinds the nested walk disclosed for, through the same
        # narrowings — `pool_scan` IS `slot_walk` for a table.
        for kind in (GRAIN_STORY, GRAIN_BUG):
            found = found.merge(pool_scan(cfg, kind))
        return found
    for mdir in milestone_dirs(cfg):
        found = found.merge(slot_walk(mdir / BUGS_DIR))
        for ffile in _nested_feature_files(mdir):
            found = found.merge(slot_walk(ffile.parent / STORIES_DIR))
    return found


def dir_entries(path: Path) -> dict[str, str]:
    """{exact name: 'file'|'dir'} for one directory, through `core.walk`."""
    return walk.entries(path)


def case_variants(entries: dict[str, str], name: str) -> list[str]:
    """Names in `entries` that differ from `name` only by case (excluding it)."""
    low = name.lower()
    return sorted(n for n in entries if n != name and n.lower() == low)


# --- THE review-record definition --------------------------------------------
def record_resolves(path: Path) -> bool:
    """True if the pointer names a file that is there — the whole definition;
    how much a reviewer wrote is not a fact about anything."""
    return path.is_file()


def record_path(cfg: PmConfig, pointer: str) -> Path:
    """The file a record pointer names — `--review-record`'s and `--source`'s
    ONE resolution, so the escape guard beside it is asked at both."""
    return Path(pointer) if pointer.startswith('/') else cfg.root / pointer


def review_record_for(cfg: PmConfig, fid: str) -> str | None:
    """The feature's resolved review record, or None; the `reviewed:` pointer
    is the whole mechanism, with no filename fallback."""
    feature = grain(cfg, fid, GRAIN_FEATURE)
    if feature is None:
        return None
    pointer = feature.field('reviewed')
    if pointer and pointer != 'null':
        # Repo-relative, always (hard rule 8): an absolute pointer is a
        # record nobody reviewing this repo can read.
        if pointer_escapes(pointer):
            return None
        if record_resolves(cfg.root / pointer):
            return pointer
    return None


# --- flow helpers (D9/D10, and the ledger's home) -----------------------------
def in_progress_milestones(cfg: PmConfig) -> list[tuple[str, str, Path]]:
    """(id, branch, milestone.md) for every active milestone in `in_progress`.
    There is no "the building milestone" (D5): readers report over every one or
    refuse naming them all.
    """
    out = []
    for milestone in milestones(cfg):
        if category_of(cfg, GRAIN_MILESTONE, milestone.status) != IN_PROGRESS:
            continue
        out.append((milestone.field(FIELD_ID), milestone.field('branch'),
                    milestone.path))
    return out


def shipped_version(cfg: PmConfig) -> str | None:
    """The version string from the project's own manifest, or None."""
    path = cfg.root / cfg.version_file
    if not path.is_file():
        return None
    pattern = re.compile(cfg.version_pattern)
    try:
        for line in frontmatter.read_raw(path).split('\n'):
            m = pattern.match(line.strip())
            if m:
                return m.group(1)
    except (OSError, UnicodeDecodeError):
        return None
    return None


# --- the plan: a declared order of versions, and the grain that claims each ---
# Nothing here parses, compares or increments a version string. "Did it
# increase" is a POSITION in `order`; `"1.1.1"` and `"cow"` are equally valid.
def releases_file(cfg: PmConfig) -> Path:
    """`pm/roadmap/releases.md` — the plan. Absent until `pm add` writes it."""
    return cfg.roadmap / RELEASES_DOC


def root_grain(cfg: PmConfig) -> Grain | None:
    """The plan document as a grain — the ROOT container — or None. A plan
    written before 0.4.0 declares neither `id:` nor `kind:` and answers to
    `roadmap`, so adopting `pm add` costs no edit."""
    path = releases_file(cfg)
    if not path.is_file():
        return None
    return Grain(gid=frontmatter.field_of(path, FIELD_ID) or ROOT_ID,
                 kind=frontmatter.field_of(path, FIELD_KIND) or ROOT_KIND,
                 path=path)


def plan_defect(cfg: PmConfig) -> str | None:
    """Why `releases.md` cannot be read as a plan, or None.

    An ABSENT plan is not a defect — a tree mid-adoption has none. A plan that
    is THERE and unreadable is: reporting "declares no `order`" over a damaged
    file is rule 4's first cardinal sin, a gate passing over what it did not
    measure.
    """
    path = releases_file(cfg)
    if not path.is_file():
        return None
    try:
        doc = frontmatter.document(path)
    except (OSError, UnicodeDecodeError) as err:
        return f'could not be read as UTF-8 text ({err.__class__.__name__})'
    lines = doc.lines
    if doc.bounds is None:
        if lines and lines[0].startswith(BOM):
            # Naming it "no frontmatter" sent the reader looking for a block
            # that is there behind three invisible bytes (review B5).
            return ('opens with a UTF-8 BOM before its `---`, so the '
                    'frontmatter block is not the first line — strip the BOM')
        opens = bool(lines) and frontmatter._FENCE.match(lines[0]) is not None
        return ('has an opening `---` with no closing one'
                if opens else
                'has no frontmatter block — the plan is a grain, and `order` '
                'lives in its frontmatter')
    open_i, close_i = frontmatter._fence_bounds(lines)
    for i in range(open_i + 1, close_i):
        if not lines[i].startswith(f'{ORDER_KEY}:'):
            continue
        rest = lines[i][len(ORDER_KEY) + 1:].strip()
        if rest and not rest.startswith('#'):
            return (f'`{ORDER_KEY}:` carries a scalar ({rest!r}) rather than a '
                    f'block list — one `- "<milestone-id>"` per line')
        return None
    return (f'declares no `{ORDER_KEY}:` key — the file is there, so this is a '
            f'plan that lost its list rather than a tree that has none')


def declared_order(cfg: PmConfig) -> list[str]:
    """The declared sequence of MILESTONE IDS, or [] when there is no plan.
    Ids, not versions (0.4.0/D4): a milestone that re-versions never touches
    the plan, and `pm rename` sweeps the entry with every other reference.
    """
    return frontmatter.list_field_of(releases_file(cfg), ORDER_KEY)


def milestone_version(cfg: PmConfig, mid: str) -> str:
    """The version a milestone declares it ships as, or '' — it is optional,
    and a milestone without one is BACKLOG, never a finding (R2)."""
    milestone = grain(cfg, mid, GRAIN_MILESTONE)
    return milestone.field('version').strip() if milestone is not None else ''


def version_claims(cfg: PmConfig) -> list[tuple[str, str]]:
    """(version, milestone id) for every milestone that declares one, in tree
    order. A list rather than a dict: R3 asks whether two milestones claim the
    same version, and a dict would have eaten the duplicate."""
    out = []
    for handle, mid in known_milestones(cfg):
        mfile = handle if handle.is_file() else handle / MILESTONE_DOC
        # `.strip()`: a whitespace-only `version:` is not a claim.
        version = frontmatter.field_of(mfile, 'version').strip()
        if version:
            out.append((version, mid))
    return out


def milestones_of_version(cfg: PmConfig, version: str) -> list[str]:
    """Every milestone claiming `version`, in tree order. A list, because two
    milestones claiming one version is a real tree defect (R3), and answering
    with the first would make the verdict depend on read order.
    """
    return [mid for claimed, mid in version_claims(cfg) if claimed == version]


def milestone_of_version(cfg: PmConfig, version: str) -> str | None:
    """The one milestone claiming `version`, or None when none or several do."""
    claimants = milestones_of_version(cfg, version)
    return claimants[0] if len(claimants) == 1 else None


def entry_is_shipped(cfg: PmConfig, mid: str) -> bool:
    """Has the milestone this plan entry names finished?"""
    milestone = grain(cfg, mid, GRAIN_MILESTONE)
    if milestone is None:
        return False
    return category_of(cfg, GRAIN_MILESTONE,
                       milestone.field(FIELD_STATUS)) == DONE_CATEGORY


def entry_is_dangling(cfg: PmConfig, mid: str) -> bool:
    """Does this plan entry name no milestone in the tree? Never read as "not
    shipped": a RETIRED milestone and one nobody has written look identical
    from here, and calling either unshipped rolled the release BACKWARD."""
    return milestone_file(cfg, mid) is None


def last_shipped_index(cfg: PmConfig) -> int:
    """Position of the last entry in `order` whose milestone is `done`, or -1.
    "Behind us" is a POSITION, which is the whole reason order is declared: no
    comparator is asked whether 0.90.10 follows 0.90.4.
    """
    last = -1
    for i, mid in enumerate(declared_order(cfg)):
        if entry_is_shipped(cfg, mid):
            last = i
    return last


def current_milestone(cfg: PmConfig) -> str | None:
    """The milestone being WORKED ON: the first entry in `order` not yet done.
    A DANGLING entry is stepped over rather than stopping the walk (it would
    break the belt for every tree that prunes) and R1 names it every run."""
    for mid in declared_order(cfg):
        if entry_is_shipped(cfg, mid) or entry_is_dangling(cfg, mid):
            continue
        return mid
    return None


def current_release(cfg: PmConfig) -> str | None:
    """The VERSION the current milestone declares, or None. Never `[pm]
    version_at`, which answers *which entry should the version FILE equal* — a
    project bumping at CLOSE answers that with the last SHIPPED release, so
    feeding it here re-released a finished milestone.
    """
    mid = current_milestone(cfg)
    return (milestone_version(cfg, mid) or None) if mid is not None else None


def graded_release(cfg: PmConfig) -> tuple[str | None, str]:
    """(the version `[pm] version_file` must equal, or None; why not) — R5's
    question, and R5's only.
    """
    order = declared_order(cfg)
    if not order:
        return None, 'the plan declares no `order`'
    if cfg.version_at == VERSION_AT_START:
        mid = current_milestone(cfg)
        if mid is None:
            return None, ('every entry in `order` has shipped, or the next one '
                          'names no milestone in the tree')
        version = milestone_version(cfg, mid)
        if not version:
            return None, (f'{mid} is the current entry in `order` and declares '
                          f'no `version:` — `agentic-sdlc pm set {mid} version '
                          f'<x.y.z>` says which release it is')
        return version, ''
    shipped = [mid for mid in order if entry_is_shipped(cfg, mid)]
    if not shipped:
        return None, ('no entry in `order` has shipped yet, so there is no '
                      'previous release for the version file to carry')
    version = milestone_version(cfg, shipped[-1])
    if not version:
        return None, (f'{shipped[-1]} is the last shipped entry in `order` and '
                      f'declares no `version:`')
    return version, ''


def graded_release_accepts(cfg: PmConfig) -> tuple[list[str], str]:
    """Every value `[pm] version_file` may hold, and why, for [pm] version_at.

    `start` has one answer. **`ship` has two, and that is what bump-at-CLOSE
    means**: the release COMMIT moves the file, so between that commit and the
    status flip it correctly names a release that has not shipped. Found by
    running the belt — `version-sync` wanted 0.3.0 and R5 wanted 0.2.0 at the
    same instant, and neither was wrong. A file naming NEITHER still fails.
    """
    one, why = graded_release(cfg)
    if one is None:
        return [], why
    if cfg.version_at == VERSION_AT_START:
        return [one], ''
    nxt = current_release(cfg)
    return ([one] if nxt is None or nxt == one else [one, nxt]), ''


def release_milestone(cfg: PmConfig) -> tuple[Path | None, str]:
    """(the DOCUMENT of the milestone the current release belongs to, or None;
    why not). `order` answers with exactly one BY CONSTRUCTION — a position in
    a list is one place. It does NOT read `[pm] version_at`: conflating the two
    filed cost rows into a shipped milestone's ledger. The in-progress fallback
    covers a consumer who bumped the pin before adopting a plan.
    """
    mid = current_milestone(cfg)
    if mid is not None:
        found = milestone_file(cfg, mid)
        if found is not None:
            return found, ''
    live = in_progress_milestones(cfg)
    if len(live) == 1:
        # The milestone's DOCUMENT, like the branch above: a pooled tree has no
        # per-milestone directory, and every caller wants the grain, not a place.
        return live[0][2], ''
    order = declared_order(cfg)
    if not order:
        return None, (f'{cfg.rel(releases_file(cfg))} declares no `order`, so '
                      f'there is no current release to file against — '
                      f'`agentic-sdlc pm add {root_id(cfg)} <milestone-id>` '
                      f'writes the plan')
    # Read off the plan rather than asserted (review C4): an entry naming
    # nothing is stepped over, and "everything shipped" would be false.
    dangling = [mid for mid in order if entry_is_dangling(cfg, mid)]
    if dangling:
        return None, (f'{dangling[0]} is in {cfg.rel(releases_file(cfg))} '
                      f'`order` and names no milestone in the tree, so there '
                      f'is no ledger to file against — `agentic-sdlc pm '
                      f'roadmap` shows the plan against the tree')
    return None, (f'every release in {cfg.rel(releases_file(cfg))} has shipped, '
                  f'so there is no release in progress to file against')


def root_id(cfg: PmConfig) -> str:
    """The id the plan answers to — its own `id:`, or `roadmap`."""
    root = root_grain(cfg)
    return root.gid if root is not None else ROOT_ID


@dataclass(frozen=True)
class SequenceCensus:
    """One container's `order` against the children it holds — THREE numbers,
    each a different fact (rule 4): `dangling` names a grain the tree HAS and
    this parent does not hold (drift); `unverifiable` names no grain at all (a
    retired one looks the same); `unsequenced` is a child nobody has placed."""

    dangling: list[str]
    unverifiable: list[str]
    unsequenced: list[str]


def sequence_census(cfg: PmConfig, parent: Grain,
                    index: dict[str, Grain] | None = None) -> SequenceCensus:
    """`parent`'s `order` graded against the children bound to it. A caller
    grading MANY parents passes the index it already walked."""
    index = grain_index(cfg) if index is None else index
    held = {g.gid for g in contained(cfg, parent, index)}
    declared = parent.list_field(ORDER_KEY)
    return SequenceCensus(
        dangling=[gid for gid in declared
                  if gid not in held and gid in index],
        unverifiable=[gid for gid in declared if gid not in index],
        unsequenced=sorted(gid for gid in held if gid not in declared))


def contained(cfg: PmConfig, parent: Grain,
              index: dict[str, Grain] | None = None) -> list[Grain]:
    """Every grain `parent` holds — its bound children, per `[pm.contains]`. A
    milestone names no parent (there is one root), so at that level membership
    IS the tree and the plan says which are scheduled."""
    found = grain_index(cfg) if index is None else index
    out: list[Grain] = []
    for kind in cfg.contains.get(parent.kind, ()):
        rootward = BINDS_TO.get(kind) is None
        out.extend(g for g in found.values() if g.kind == kind
                   and (rootward or g.binding == parent.gid))
    return out


def drift_dangling_record(cfg: PmConfig, fid: str) -> str | None:
    """D1 — a `reviewed:` pointer naming a file that is not there. An absent
    pointer is not a finding; only a dangling one is."""
    feature = grain(cfg, fid, GRAIN_FEATURE)
    if feature is None:
        return None
    pointer = feature.field('reviewed')
    if not pointer or pointer == 'null':
        return None
    target = record_path(cfg, pointer)
    if record_resolves(target):
        return None
    return f'reviewed: {pointer!r} resolves to nothing'


def drift_stalled(cfg: PmConfig, view: 'FeatureView') -> str | None:
    """D2 — every story finished but the feature still in `todo` (a forgotten
    flip). A feature at any `in_progress` state over finished stories has
    simply advanced.
    """
    if view.total == 0 or view.done_n != view.total:
        return None
    if category_of(cfg, GRAIN_FEATURE, view.status) == TODO:
        return f'all stories done, feature still {view.status}'
    return None


def drift_ahead_of_parent(cfg: PmConfig, child: str, parent: str) -> bool:
    """D5 — a story has left `todo` under a feature still in it: work started
    in one place and not the other. Asked of the categories, so it places in
    every vocabulary.
    """
    child_cat = category_of(cfg, GRAIN_STORY, child)
    parent_cat = category_of(cfg, GRAIN_FEATURE, parent)
    if child_cat is None or parent_cat is None:
        return False
    return parent_cat == TODO and child_cat != TODO


@dataclass
class FeatureView:
    """One feature plus the tallies every reader needs; `done_n` counts the
    `done` category through `holds`.

    `stories` are GRAINS, not paths: every reader of this view then asks each
    story what it SAYS rather than handing storage a file, and `doc_grain`
    keeps a story declaring no `id:` in the list, so `total` counts the same
    documents it always did.
    """
    fid: str
    status: str
    path: Path
    stories: list[Grain] = field(default_factory=list)
    done_n: int = 0

    @property
    def total(self) -> int:
        return len(self.stories)


def read_feature(cfg: PmConfig, ffile: Path) -> FeatureView:
    feature = doc_grain(ffile, GRAIN_FEATURE)
    view = FeatureView(
        fid=feature.field(FIELD_ID),
        status=feature.field(FIELD_STATUS),
        path=ffile,
        stories=story_grains(cfg, feature.field(FIELD_ID)),
    )
    finished = holds(cfg, GRAIN_STORY,
                     ((s.path, s.field(FIELD_STATUS)) for s in view.stories),
                     DONE_CATEGORY)
    view.done_n = finished.counted - len(finished.blockers)
    return view


# --- shared-doc headers -------------------------------------------------------
def header_of(path: Path) -> str:
    """The file's first non-blank line, stripped — its canonical header slot."""
    try:
        lines = frontmatter.document(path).lines
    except (OSError, UnicodeDecodeError):
        return ''
    for line in lines:
        if line.strip():
            return line.strip()
    return ''


# --- bug status vocabulary (D4) -----------------------------------------------
# A bug is never moved by this tool; what is checkable is D4's fact, a status
# outside the vocabulary — and every "is it open" reader tests a name, so a
# typo would pass in silence.
def _nested_bug_files(mdir: Path) -> list[Path]:
    return grain_docs(mdir / BUGS_DIR)


def bug_status_findings(cfg: PmConfig) -> tuple[list[tuple[Path, str]], int]:
    """(findings, bugs scanned) — every bug whose status the project never
    declared. The walk is recursive and case-insensitive on the extension, so
    the census cannot undercount silently.
    """
    out: list[tuple[Path, str]] = []
    scanned = 0
    # The POOL: a bug nobody has bound was counted and asked nothing.
    for bug in every_grain(cfg, GRAIN_BUG):
        scanned += 1
        bstat = bug.field(FIELD_STATUS)
        if category_of(cfg, GRAIN_BUG, bstat) is None:
            # The bug line's shape is grepped (rule 6), so it is kept verbatim.
            out.append((bug.path, f'bug status {bstat!r} is not in '
                                  f'({" ".join(flow_of(cfg, GRAIN_BUG).order)})'))
    return out, scanned


def every_grain(cfg: PmConfig, kind: str) -> list[Grain]:
    """Every grain of one kind in the tree, bound or not — through `doc_grain`,
    so a document declaring no `id:` is still in the census with an empty one
    rather than silently absent from it (rule 4)."""
    if is_pooled(cfg):
        return [doc_grain(path, kind) for path in pool_walk(cfg, kind)]
    if kind == GRAIN_BUG:
        return [b for m in milestones(cfg) for b in bug_grains(cfg, m.gid)]
    if kind == GRAIN_FEATURE:
        return [f for m in milestones(cfg) for f in feature_grains(cfg, m.gid)]
    return [s for m in milestones(cfg)
            for f in feature_grains(cfg, m.gid)
            for s in story_grains(cfg, f.field(FIELD_ID))]


def state_usage(cfg: PmConfig) -> dict[str, dict[str, int]]:
    """Per kind, how many grains hold each DECLARED state — zero included.

    D4 asks "is this word declared", never "is this word used", so a tree using
    two of eight states is indistinguishable, to every gate, from one using all
    eight. That is how a project adopted the conveyor as a CONFIG FIX and never
    noticed: four of its states appeared zero times across 85 grains, and every
    gate was green the whole time.
    """
    used: dict[str, dict[str, int]] = {
        kind: {state: 0 for state in flow.order}
        for kind, flow in cfg.flows.items()
    }

    def count(kind: str, status: str) -> None:
        bucket = used.get(kind)
        # An undeclared word is D4's finding, not this census's business.
        if bucket is not None and status in bucket:
            bucket[status] += 1

    # Bound or not: U1's claim is that a word is held nowhere in the TREE, and
    # a descent made that sentence false as soon as an unbound grain held it.
    for milestone in milestones(cfg):
        count(GRAIN_MILESTONE, milestone.status)
    for kind in (GRAIN_FEATURE, GRAIN_STORY, GRAIN_BUG):
        for found in every_grain(cfg, kind):
            count(kind, found.field(FIELD_STATUS))
    return used


def undeclared_status(cfg: PmConfig, kind: str, status: str) -> str | None:
    """D4's one sentence: the word, and the words the project did declare; None
    when `status` is in some category. One wording for every grain kind.
    """
    if category_of(cfg, kind, status) is not None:
        return None
    return (f'status {status!r} not in '
            f'({" ".join(flow_of(cfg, kind).order)})')


# --- ready: a stamp, and what `check pm` says about an empty one -------------
# `ready` is one command, `pm <kind> ready <id>`; what leaving `todo` means is
# a `check pm` WARNING, never a gate. Asked of the category: order within
# `todo` is presentation, and an undeclared word is D4's finding, not asked.
def left_todo(cfg: PmConfig, kind: str, status: str) -> bool:
    """True when `status` is declared for `kind` and its category is not `todo`."""
    category = category_of(cfg, kind, status)
    return category is not None and category != TODO


# The three sections `pm new` scaffolds and this reads, spelled once beside the
# templates' headings.
ACCEPTANCE_HEADING = 'Acceptance criteria'
SHIP_HEADING = 'Ship criterion'
# The anti-bloat contract: how many cases a feature should cost, named before it
# is built and compared after. Every feature template carries it and nothing had
# ever checked it was filled in — a contract nobody verifies is a suggestion.
PROOF_HEADING = 'Proof budget'

_HEADING = re.compile(r'^(#{1,2})[ \t]+(.*?)[ \t]*$')


def section_lines(text: str, heading: str) -> list[str] | None:
    """The lines under `## <heading>`, up to the next heading; None when the
    heading is absent, which is a different sentence from "empty"."""
    return section_lines_in(frontmatter._split(text), heading)


def section_lines_in(lines: Sequence[str], heading: str) -> list[str] | None:
    """`section_lines` over lines already read — the body of one parse."""
    start = None
    for i, line in enumerate(lines):
        m = _HEADING.match(line)
        if m is None:
            continue
        if start is None:
            if len(m.group(1)) == 2 and m.group(2) == heading:
                start = i + 1
        else:
            return lines[start:i]
    return None if start is None else lines[start:]


def section_is_empty(lines: list[str]) -> bool:
    """True when nothing but blank lines and HTML comments is under it — the
    template's own prompt is not content."""
    in_comment = False
    for line in lines:
        rest = line
        while rest:
            if in_comment:
                end = rest.find('-->')
                if end < 0:
                    rest = ''
                    break
                in_comment = False
                rest = rest[end + 3:]
                continue
            stripped = rest.strip()
            if not stripped:
                break
            if stripped.startswith('<!--'):
                in_comment = True
                rest = stripped[4:]
                continue
            return False
    return True


def empty_section(path: Path, heading: str) -> str | None:
    """'' when `## <heading>` is present and written; else why it is not."""
    lines = section_lines_in(frontmatter.document(path).lines, heading)
    if lines is None:
        return f'has no `## {heading}` section'
    if section_is_empty(lines):
        return f'has an empty `## {heading}`'
    return None


# --- appending a decision heading (`pm decide`) -------------------------------
# The verb stamps the date and the ordinal, the two things a hand-written
# heading gets wrong, and imposes no field schema.
_ENTRY_ORDINAL = re.compile(r'^##[ \t]+([A-Za-z]{1,4})(\d+)\b')
DECISION_PREFIX = 'D'


def next_entry_id(text: str) -> str:
    """The next ordinal for this log, from the ids the log itself holds: the
    prefix follows the last id-shaped heading, and numbering is per file by
    design.
    """
    seen = [m for m in (_ENTRY_ORDINAL.match(line) for line in frontmatter._split(text)) if m]
    if not seen:
        return f'{DECISION_PREFIX}1'
    prefix = seen[-1].group(1)
    highest = max(int(m.group(2)) for m in seen if m.group(1) == prefix)
    return f'{prefix}{highest + 1}'


def append_heading(text: str, eid: str, when: str, title: str) -> str:
    """`text` with one `## <id> — <date> — <title>` heading appended; the em
    dash is what `next_entry_id` and every log already use."""
    eol = '\r\n' if '\r\n' in text else '\n'
    body = text
    if body and not body.endswith(('\n', '\r')):
        body += eol
    if body and not body.endswith(eol * 2):
        body += eol
    return body + f'## {eid} — {when} — {title}{eol}'