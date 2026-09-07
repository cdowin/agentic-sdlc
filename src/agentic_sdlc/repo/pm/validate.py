"""validate.py — structural and referential integrity of the PM tree.

V1 frontmatter well-formed · V2 and V3 RETIRED (0.4.0) ·
V4 refs (`depends_on`, `consumed_by`, a bug's `caused_by`) resolve · V5 the
feature graph is acyclic · V6 (opt-in) an execution list matches the tree ·
V7 every grain's binding names a grain of the right kind that is in the tree.
"""
from __future__ import annotations

from pathlib import Path

from agentic_sdlc.repo.pm import model

_REF_KEYS = ('depends_on', 'consumed_by')

# A scalar, not a list: one bug has one cause; `caught_in:` holds the other
# half.
CAUSED_BY = 'caused_by'


class Unparseable(Exception):
    """A ref list this parser cannot read — a finding, never an empty list."""


def _refs(path: Path, key: str) -> list[str]:
    """The ids inside a `key: ["a", "b"]` inline list; any other shape is a
    finding.
    """
    raw = model.field_of(path, key).strip()
    if not raw or raw in ('[]', 'null', '~'):
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


def _safe_refs(path: Path, key: str, bad, rel: str) -> list[str]:
    try:
        return _refs(path, key)
    except Unparseable as err:
        bad(f'{rel}: {err}')
        return []


def _scalar_ref(path: Path, key: str) -> list[str]:
    """The one id inside a `key: <id>` scalar, as a 0-or-1 list; a bracket,
    comma, quote or space in it is a finding.
    """
    raw = model.field_of(path, key).strip()
    if not raw or raw in ('[]', 'null', '~'):
        return []
    if raw[0] in '[{' or raw[-1] in ']}':
        raise Unparseable(f'{key}: {raw!r} is a list or a mapping — {key} is '
                          f'one id, written bare ({key}: 0.1/some-feature)')
    if any(c in raw for c in ',\'" \t'):
        raise Unparseable(f'{key}: {raw!r} is not a single id — ids hold no '
                          f'commas, quotes or whitespace')
    return [raw]


def _safe_scalar_ref(path: Path, key: str, bad, rel: str) -> list[str]:
    try:
        return _scalar_ref(path, key)
    except Unparseable as err:
        bad(f'{rel}: {err}')
        return []


def _unverifiable(index: dict, ref: str) -> bool:
    """Whether a ref that resolved to nothing is UNVERIFIABLE rather than broken.

    A retired milestone takes its grains with it, and reddening every ref that
    pointed into it would make `pm retire` unusable — so a ref whose leading
    segment names no milestone in the tree is not graded. That segment is a
    HEURISTIC for this question alone; refs are RESOLVED through the index.

    A FLAT id carries no such segment, so an unresolvable one is a finding:
    reading `ref not in index` as "its milestone is gone" would excuse every
    dangling ref in a flat tree, wearing the word UNVERIFIABLE.
    """
    prefix = ref.partition('/')[0]
    return prefix != ref and prefix not in index


def _grain_exists(cfg: model.PmConfig, ref: str) -> bool | None:
    """True/False if resolvable, None when the owning milestone is pruned
    (UNVERIFIABLE, not a finding).
    """
    try:
        index = model.grain_index(cfg)
    except OSError:
        return False
    if ref in index:
        return True
    return None if _unverifiable(index, ref) else False


def _feature_exists(cfg: model.PmConfig, ref: str) -> bool | None:
    """`_grain_exists` for a ref that must name a FEATURE; a milestone or a
    story id is False. An OSError is False too.
    """
    try:
        index = model.grain_index(cfg)
    except OSError:
        return False
    found = index.get(ref)
    if found is not None:
        return found.kind == 'feature'
    return None if _unverifiable(index, ref) else False


def _check_ref_ids(cfg: model.PmConfig, path, key: str, refs: list[str],
                   on: set[str], bad, census: dict, exists=_grain_exists) -> list[str]:
    """The census / UNVERIFIABLE / V4 block for one ref key's parsed ids.
    Returns the refs that resolved.
    """
    resolved: list[str] = []
    for ref in refs:
        census['refs'] += 1
        got = exists(cfg, ref)
        if got is None:
            census['unverifiable'] += 1
        elif not got:
            if 'V4' in on:
                bad(f'{cfg.rel(path)}: {key} {ref!r} resolves to '
                    f'nothing (its milestone IS in the tree)')
        else:
            resolved.append(ref)
    return resolved


def _check_refs(cfg: model.PmConfig, path, key: str, on: set[str], bad,
                census: dict) -> list[str]:
    """`_check_ref_ids` over an inline-list ref key."""
    return _check_ref_ids(cfg, path, key, _safe_refs(path, key, bad, cfg.rel(path)),
                          on, bad, census)


def _check_caused_by(cfg: model.PmConfig, path, on: set[str], bad,
                     census: dict) -> None:
    """`_check_ref_ids` over a bug's scalar `caused_by:`, resolved as a feature."""
    _check_ref_ids(cfg, path, CAUSED_BY,
                   _safe_scalar_ref(path, CAUSED_BY, bad, cfg.rel(path)),
                   on, bad, census, exists=_feature_exists)


def run(cfg: model.PmConfig, enabled: set[str] | None = None) -> tuple[list[str], dict]:
    """Returns (findings, census). A finding names a path a human can open."""
    # `model.VALIDATE_CHECKS` is the one roster; a local copy would split `pm
    # validate` from `check pm`.
    on = enabled if enabled is not None else set(model.VALIDATE_CHECKS)
    findings: list[str] = []
    census = {'grains': 0, 'refs': 0, 'unverifiable': 0}

    def bad(msg: str) -> None:
        findings.append(msg)

    # (grain path, its declared id, the id its PATH implies, parentage pairs)
    graph: dict[str, list[str]] = {}

    # V1 over the POOLS, before the descent — because these are precisely the
    # documents the descent cannot reach. A document with no readable `id:` is
    # in no index, so nothing below would ever visit it; two documents claiming
    # one id means the descent visits the first and walks past the second.
    if 'V1' in on:
        for path, why in model.unkeyed_documents(cfg):
            bad(f'{cfg.rel(path)} {why} — it was SKIPPED by this scan')
        for gid, paths in model.duplicate_ids(cfg):
            names = ' '.join(cfg.rel(path) for path in paths)
            bad(f'{len(paths)} documents claim id {gid!r} — a resolver keeps '
                f'the first it reads and the rest are addressable by nothing; '
                f'give each one its own id: {names}')

    for milestone in model.milestones(cfg):
        mdir = milestone.path.parent
        _mid = milestone.gid
        mfile = milestone.path
        mid = model.field_of(mfile, 'id')
        census['grains'] += 1
        if 'V1' in on and (not mid or not model.field_of(mfile, 'status')):
            bad(f'{cfg.rel(mfile)}: missing id: or status: in the frontmatter')

        for ffile in model.feature_files(cfg, _mid):
            census['grains'] += 1
            fid = model.field_of(ffile, 'id')
            fstat = model.field_of(ffile, 'status')
            if 'V1' in on and (not fid or not fstat):
                bad(f'{cfg.rel(ffile)}: missing id: or status: in the frontmatter')
            expect = model.unquote(fid)
            if fid:
                graph[fid] = []

            for sfile in model.story_files(
                    cfg, model.unquote(model.field_of(ffile, 'id'))):
                census['grains'] += 1
                sid = model.field_of(sfile, 'id')
                if 'V1' in on and (not sid or not model.field_of(sfile, 'status')):
                    bad(f'{cfg.rel(sfile)}: missing id: or status: in the frontmatter')
                _check_refs(cfg, sfile, 'depends_on', on, bad, census)

            for key in _REF_KEYS:
                resolved = _check_refs(cfg, ffile, key, on, bad, census)
                if key == 'depends_on' and fid:
                    graph[fid].extend(ref for ref in resolved
                                      if ref.count('/') == 1)

        _check_refs(cfg, mfile, 'depends_on', on, bad, census)

        # Bugs are walked for `caused_by:` alone; `census['grains']` still
        # counts only milestones, features and stories.
        for bfile in model.bug_files(cfg, _mid):
            _check_caused_by(cfg, bfile, on, bad, census)

    if 'V7' in on:
        findings.extend(_unbound_findings(cfg))
    if 'V5' in on:
        findings.extend(_graph_findings(graph))
    if 'V6' in on:
        # A generated list is only safe because this fails when it drifts.
        from agentic_sdlc.repo.pm import execlist
        try:
            stale = execlist.sync(cfg, write=False, existing_only=True)
        except execlist.Refusal as err:
            # A refused grain is a finding here, never a crash that takes V1-V5
            # down with it.
            findings.extend(str(err).split('\n'))
        else:
            for path, changed in stale:
                if changed:
                    findings.append(
                        f'{cfg.rel(path)}: the execution list is stale — the tree '
                        f'has moved since it was rendered; run `pm sync`')
    return findings, census


def _unbound_findings(cfg: model.PmConfig) -> list[str]:
    """V7 — a binding that names a grain not in the tree, or one of the wrong
    kind. An EMPTY binding is not here: it is unbound, which is a counted line.

    The walk above descends from the milestones, so a grain whose binding
    resolves to nothing is never REACHED by it. This one starts at the POOLS,
    so every grain is graded exactly once whether or not anything claims it.
    A milestone binds to nothing and is never asked.
    """
    out: list[str] = []
    index = model.grain_index(cfg)
    for gid, grain in sorted(index.items()):
        bind = model.BINDS_TO.get(grain.kind)
        if bind is None:
            continue
        want_kind, field = bind
        ref = model.unquote(model.field_of(grain.path, field))
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
