"""validate.py — structural and referential integrity of the PM tree.

V1 frontmatter well-formed · V2 and V3 RETIRED (0.4.0) ·
V4 refs (`depends_on`, `consumed_by`, a bug's `caused_by`) resolve · V5 the
feature graph is acyclic · V6 RETIRED (0.4.0, with the execution list) ·
V7 every grain's binding names a grain of the right kind that is in the tree.
"""
from __future__ import annotations

from agentic_sdlc.repo.pm import inventory, ledger, vocabulary

# PUBLIC: the one answer to "is this field list-shaped", so `pm set` writes the
# shape `check pm` grades and cannot produce what this reader refuses (rule 4).
REF_KEYS = ('depends_on', 'consumed_by')

# A scalar, not a list: one bug has one cause, and it is not the binding.
CAUSED_BY = 'caused_by'
EMPTY = ('', '[]', 'null', '~')


class Unparseable(Exception):
    """A ref list this parser cannot read — a finding, never an empty list."""


def render_refs(ids: list[str]) -> str:
    """`ids` as the inline list `refs_in` reads back."""
    return '[' + ', '.join(f'"{i}"' for i in ids) + ']'


def refs_in(key: str, raw: str) -> list[str]:
    """The ids inside a `key: ["a", "b"]` inline list; any other shape is a
    finding.
    """
    raw = raw.strip()
    if raw in EMPTY:
        return []
    if not (raw.startswith('[') and raw.endswith(']')):
        raise Unparseable(f'{key}: {raw!r} is not an inline list — write '
                          f'{key}: ["a", "b"] (a block sequence or trailing '
                          f'comment cannot be read from the frontmatter line)')
    inner = raw[1:-1]
    if '[' in inner or ']' in inner:
        raise Unparseable(f'{key}: {raw!r} nests brackets — only a flat list '
                          f'of ids is supported')
    out = []
    for part in inner.split(','):
        part = part.strip()
        if not part:
            continue
        if part[0] in '"\'' and part[-1] == part[0]:
            part = part[1:-1]
        if ',' in part or ' ' in part.strip():
            raise Unparseable(f'{key}: entry {part!r} contains a separator — '
                              f'ids never contain spaces or commas')
        if part:
            out.append(part)
    return out


def _safe_refs(grain, key: str, bad, rel: str) -> list[str]:
    try:
        return refs_in(key, grain.field(key))
    except Unparseable as err:
        bad(f'{rel}: {err}')
        return []


def scalar_ref_in(key: str, raw: str) -> list[str]:
    """The one id inside a `key: <id>` scalar, as a 0-or-1 list; a bracket,
    comma, quote or space in it is a finding.
    """
    raw = raw.strip()
    if raw in EMPTY:
        return []
    if raw[0] in '[{' or raw[-1] in ']}':
        raise Unparseable(f'{key}: {raw!r} is a list or a mapping — {key} is '
                          f'one id, written bare ({key}: 0.1/some-feature)')
    if any(c in raw for c in ',\'" \t'):
        raise Unparseable(f'{key}: {raw!r} is not a single id — ids hold no '
                          f'commas, quotes or whitespace')
    return [raw]


def _safe_scalar_ref(grain, key: str, bad, rel: str) -> list[str]:
    try:
        return scalar_ref_in(key, grain.field(key))
    except Unparseable as err:
        bad(f'{rel}: {err}')
        return []


def _unverifiable(index: dict, ref: str, retired=frozenset()) -> bool:
    """Whether a ref that resolved to nothing is UNVERIFIABLE rather than broken.

    A retired milestone takes its grains with it, and reddening every ref that
    pointed into it would make `pm retire` unusable — so a ref whose leading
    segment names no milestone in the tree is not graded. That segment is a
    HEURISTIC for this question alone; refs are RESOLVED through the index.

    A FLAT id carries no such segment, so an unresolvable one is a finding —
    unless a `retire` row names it as removed (#102): that is the ledger's
    record, not a guess. Reading `ref not in index` alone as "its milestone is
    gone" would excuse every dangling ref in a flat tree, wearing the word
    UNVERIFIABLE.
    """
    if ref in retired:
        return True
    prefix = ref.partition('/')[0]
    return prefix != ref and prefix not in index


# What a ref is graded against before the ledger is read, or when it will not
# read: no retire row, so nothing is excused by one.
_NOTHING_RETIRED = ledger.Retired(frozenset(), 0, {})


def _grain_exists(cfg: vocabulary.PmConfig, ref: str,
                  retired: ledger.Retired = _NOTHING_RETIRED) -> bool | None:
    """True/False if resolvable, None when the owning milestone is pruned or a
    retire row names the id (UNVERIFIABLE, not a finding).
    """
    try:
        index = inventory.grain_index(cfg)
    except OSError:
        return False
    if ref in index:
        return True
    return None if _unverifiable(index, ref, retired.ids) else False


def _feature_exists(cfg: vocabulary.PmConfig, ref: str,
                    retired: ledger.Retired = _NOTHING_RETIRED) -> bool | None:
    """`_grain_exists` for a ref that must name a FEATURE; a milestone or a
    story id is False, in the tree or recorded so by a retire row — the kind
    is checked BEFORE a retirement excuses the id. An OSError is False too.
    """
    try:
        index = inventory.grain_index(cfg)
    except OSError:
        return False
    found = index.get(ref)
    if found is not None:
        return found.kind == vocabulary.GRAIN_FEATURE
    if retired.kinds.get(ref, vocabulary.GRAIN_FEATURE) != \
            vocabulary.GRAIN_FEATURE:
        return False
    return None if _unverifiable(index, ref, retired.ids) else False


class _RetireRows:
    """The tree's retire rows, read ONCE and only when a ref resolves to
    nothing. A ledger that will not read is a finding, never "nothing was
    retired" answered in silence (rule 4)."""

    def __init__(self, cfg: vocabulary.PmConfig, bad) -> None:
        self.cfg = cfg
        self.bad = bad
        self._got: ledger.Retired | None = None

    def get(self) -> ledger.Retired:
        if self._got is None:
            try:
                self._got = ledger.retired_ids(self.cfg)
            except ledger.LedgerError as err:
                self.bad(f'{err} — no retire row could be read, so a ref to a '
                         f'retired grain is graded as one that resolves to '
                         f'nothing')
                self._got = _NOTHING_RETIRED
        return self._got


def _why_nothing(cfg: vocabulary.PmConfig, ref: str,
                 retired: ledger.Retired) -> str:
    """What was checked, for a ref that resolved to nothing: the grain it
    names is of the wrong kind, the named milestone is in the tree, or no
    grain and no retire row knows the id."""
    try:
        found = inventory.grain_index(cfg).get(ref)
    except OSError:
        found = None
    if found is not None:
        return f'it is a {found.kind}, not a {vocabulary.GRAIN_FEATURE}'
    was = retired.kinds.get(ref, vocabulary.GRAIN_FEATURE)
    if was != vocabulary.GRAIN_FEATURE:
        return (f'a retire row in '
                f'{cfg.rel(ledger.grainless_path(cfg.roadmap))} records it '
                f'as a {was}, not a {vocabulary.GRAIN_FEATURE}')
    if ref.partition('/')[0] != ref:
        return 'its milestone IS in the tree'
    why = (f'no grain in the tree and no retire row in '
           f'{cfg.rel(ledger.grainless_path(cfg.roadmap))} knows it')
    if retired.unlisted:
        why += (f'; {retired.unlisted} retire row(s) predate the list of '
                f'removed ids and cannot say')
    return why


def _check_ref_ids(cfg: vocabulary.PmConfig, grain, key: str, refs: list[str],
                   on: set[str], bad, census: dict, rows: _RetireRows,
                   exists=_grain_exists) -> list[str]:
    """The census / UNVERIFIABLE / V4 block for one ref key's parsed ids.
    Returns the refs that resolved.
    """
    resolved: list[str] = []
    for ref in refs:
        census['refs'] += 1
        got = exists(cfg, ref)
        if got is False:
            got = exists(cfg, ref, rows.get())
        if got is None:
            census['unverifiable'] += 1
        elif not got:
            if 'V4' in on:
                bad(f'{cfg.rel(grain.path)}: {key} {ref!r} resolves to '
                    f'nothing ({_why_nothing(cfg, ref, rows.get())})')
        else:
            resolved.append(ref)
    return resolved


def _check_refs(cfg: vocabulary.PmConfig, grain, key: str, on: set[str], bad,
                census: dict, rows: _RetireRows) -> list[str]:
    """`_check_ref_ids` over an inline-list ref key."""
    return _check_ref_ids(cfg, grain, key,
                          _safe_refs(grain, key, bad, cfg.rel(grain.path)),
                          on, bad, census, rows)


def _check_caused_by(cfg: vocabulary.PmConfig, grain, on: set[str], bad,
                     census: dict, rows: _RetireRows) -> None:
    """`_check_ref_ids` over a bug's scalar `caused_by:`, resolved as a feature."""
    _check_ref_ids(cfg, grain, CAUSED_BY,
                   _safe_scalar_ref(grain, CAUSED_BY, bad, cfg.rel(grain.path)),
                   on, bad, census, rows, exists=_feature_exists)


def run(cfg: vocabulary.PmConfig, enabled: set[str] | None = None) -> tuple[list[str], dict]:
    """Returns (findings, census). A finding names a path a human can open."""
    # `vocabulary.VALIDATE_CHECKS` is the one roster; a local copy would split `pm
    # validate` from `check pm`.
    on = enabled if enabled is not None else set(vocabulary.VALIDATE_CHECKS)
    findings: list[str] = []
    census = {'grains': 0, 'refs': 0, 'unverifiable': 0}

    def bad(msg: str) -> None:
        findings.append(msg)

    # An unreadable ledger is V4's finding: it is what V4 could not ask.
    rows = _RetireRows(cfg, bad if 'V4' in on else lambda _msg: None)

    # (grain path, its declared id, the id its PATH implies, parentage pairs)
    graph: dict[str, list[str]] = {}

    # V1 over the POOLS, before the descent — because these are precisely the
    # documents the descent cannot reach. A document with no readable `id:` is
    # in no index, so nothing below would ever visit it; two documents claiming
    # one id means the descent visits the first and walks past the second.
    if 'V1' in on:
        for path, why in inventory.unkeyed_documents(cfg):
            bad(f'{cfg.rel(path)} {why} — it was SKIPPED by this scan')
        for gid, paths in inventory.duplicate_ids(cfg):
            names = ' '.join(cfg.rel(path) for path in paths)
            bad(f'{len(paths)} documents claim id {gid!r} — a resolver keeps '
                f'the first it reads and the rest are addressable by nothing; '
                f'give each one its own id: {names}')

    # EVERY grain, bound or not: V1 asks about one document, V4 about one ref,
    # V5 about the feature graph, so the descent was never what they needed —
    # and it left a ref on an unbound grain unread while the census counted the
    # grain (rule 4).
    for milestone in inventory.milestones(cfg):
        census['grains'] += 1
        if 'V1' in on and (not milestone.field(vocabulary.FIELD_ID)
                           or not milestone.field(vocabulary.FIELD_STATUS)):
            bad(f'{cfg.rel(milestone.path)}: missing id: or status: in the '
                f'frontmatter')
        _check_refs(cfg, milestone, 'depends_on', on, bad, census, rows)

    for feature in inventory.every_grain(cfg, vocabulary.GRAIN_FEATURE):
        census['grains'] += 1
        expect = feature.field(vocabulary.FIELD_ID)
        if 'V1' in on and (not expect
                           or not feature.field(vocabulary.FIELD_STATUS)):
            bad(f'{cfg.rel(feature.path)}: missing id: or status: in the '
                f'frontmatter')
        # The UNQUOTED id, because that is what a ref carries: keying the node
        # on the raw `id:` meant a quoted one matched none of its own.
        if expect:
            graph[expect] = []
        for key in REF_KEYS:
            resolved = _check_refs(cfg, feature, key, on, bad, census, rows)
            if key == 'depends_on' and expect:
                # Which kind a ref names is a question about the GRAIN;
                # counting slashes left the graph empty on a flat tree.
                graph[expect].extend(ref for ref in resolved
                                     if inventory.kind_of(cfg,
                                                      ref) == vocabulary.GRAIN_FEATURE)

    for story in inventory.every_grain(cfg, vocabulary.GRAIN_STORY):
        census['grains'] += 1
        if 'V1' in on and (not story.field(vocabulary.FIELD_ID)
                           or not story.field(vocabulary.FIELD_STATUS)):
            bad(f'{cfg.rel(story.path)}: missing id: or status: in the '
                f'frontmatter')
        _check_refs(cfg, story, 'depends_on', on, bad, census, rows)

    # Bugs are walked for `caused_by:` alone; `census['grains']` still counts
    # only milestones, features and stories.
    for bug in inventory.every_grain(cfg, vocabulary.GRAIN_BUG):
        _check_caused_by(cfg, bug, on, bad, census, rows)

    if 'V7' in on:
        findings.extend(_unbound_findings(cfg))
    if 'V5' in on:
        findings.extend(_graph_findings(graph))
    return findings, census


def _unbound_findings(cfg: vocabulary.PmConfig) -> list[str]:
    """V7 — a binding that names a grain not in the tree, or one of the wrong
    kind. An EMPTY binding is not here: it is unbound, which is a counted line.

    The walk above descends from the milestones, so a grain whose binding
    resolves to nothing is never REACHED by it. This one starts at the POOLS,
    so every grain is graded exactly once whether or not anything claims it.
    A milestone binds to nothing and is never asked.
    """
    out: list[str] = []
    index = inventory.grain_index(cfg)
    for gid, grain in sorted(index.items()):
        bind = vocabulary.BINDS_TO.get(grain.kind)
        if bind is None:
            continue
        want_kind, field = bind
        ref = grain.field(field)
        rel = cfg.rel(grain.path)
        if not ref:
            # NOT a finding: a grain nobody has bound yet is a plan in
            # progress, and `check pm` counts it in the unbound family.
            continue
        found = index.get(ref)
        if found is None:
            out.append(f'{rel}: {grain.kind} {gid!r} has {field}: {ref!r}, '
                       f'which is not a grain in this tree')
        elif found.kind != want_kind:
            out.append(f'{rel}: {grain.kind} {gid!r} has {field}: {ref!r}, '
                       f'which is a {found.kind} and not a {want_kind}')
    return out


def _graph_findings(graph: dict[str, list[str]]) -> list[str]:
    out: list[str] = []
    # Cycles — a dependency loop means no build order exists at all.
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {k: WHITE for k in graph}

    def walk(node: str, so_far: list[str]) -> None:
        colour[node] = GREY
        for dep in graph.get(node, []):
            if dep not in colour:
                continue
            if colour[dep] == GREY:
                loop = so_far[so_far.index(dep):] if dep in so_far else [dep]
                out.append(f'dependency CYCLE among features: '
                           f'{" -> ".join([*loop, node, dep])}')
            elif colour[dep] == WHITE:
                walk(dep, [*so_far, node])
        colour[node] = BLACK

    for node in sorted(graph):
        if colour[node] == WHITE:
            walk(node, [])

    return out
