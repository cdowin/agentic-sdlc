"""validate.py — structural and referential integrity of the PM tree.

V1 frontmatter well-formed · V2 id matches path · V3 parentage consistent ·
V4 refs (`depends_on`, `consumed_by`, a bug's `caused_by`) resolve · V5 the
feature graph is acyclic · V6 (opt-in) an execution list matches the tree.
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


def _grain_exists(cfg: model.PmConfig, ref: str) -> bool | None:
    """True/False if resolvable, None when the owning milestone is pruned
    (UNVERIFIABLE, not a finding).
    """
    mid = ref.partition('/')[0]
    if model.milestone_dir(cfg, mid) is None:
        return None
    depth = ref.count('/')
    if depth == 0:
        return True
    if depth == 1:
        return model.feature_file(cfg, ref) is not None
    return model.story_file(cfg, ref) is not None


def _feature_exists(cfg: model.PmConfig, ref: str) -> bool | None:
    """`_grain_exists` for a ref that must name a feature; a milestone or
    story id is False. An OSError is False too: `Path.is_dir()` raises on
    an over-long component before 3.14 and answers False after.
    """
    try:
        if model.milestone_dir(cfg, ref.partition('/')[0]) is None:
            return None
        return model.feature_file(cfg, ref) is not None
    except OSError:
        return False


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

    for mdir in model.milestone_dirs(cfg):
        mfile = mdir / model.MILESTONE_DOC
        mid = model.field_of(mfile, 'id')
        census['grains'] += 1
        if 'V1' in on and (not mid or not model.field_of(mfile, 'status')):
            bad(f'{cfg.rel(mfile)}: missing id: or status: in the frontmatter')
        # The dir carries a human suffix after the version; the id is the prefix.
        if 'V2' in on and mid and not mdir.name.startswith(f'{mid}-'):
            bad(f'{cfg.rel(mfile)}: id {mid!r} does not match its directory '
                f'{mdir.name!r} (expected {mid}-<slug>/)')

        for ffile in model.feature_files(mdir):
            census['grains'] += 1
            fid = model.field_of(ffile, 'id')
            fstat = model.field_of(ffile, 'status')
            if 'V1' in on and (not fid or not fstat):
                bad(f'{cfg.rel(ffile)}: missing id: or status: in the frontmatter')
            expect = f'{mid}/{ffile.parent.name}'
            if 'V2' in on and fid and fid != expect:
                bad(f'{cfg.rel(ffile)}: id {fid!r} does not match its path '
                    f'(expected {expect!r})')
            if 'V3' in on:
                own = model.field_of(ffile, 'milestone')
                if own and own != mid:
                    bad(f'{cfg.rel(ffile)}: milestone: {own!r} but it lives under '
                        f'milestone {mid!r}')
            if fid:
                graph[fid] = []

            for sfile in model.story_files(ffile):
                census['grains'] += 1
                sid = model.field_of(sfile, 'id')
                if 'V1' in on and (not sid or not model.field_of(sfile, 'status')):
                    bad(f'{cfg.rel(sfile)}: missing id: or status: in the frontmatter')
                # The prefix is stripped, never the check skipped: skipping
                # left every story unchecked under VALID.
                s_expect = f'{expect}/{model.story_slug_of(cfg, sfile.stem)}'
                if 'V2' in on and sid and sid != s_expect:
                    bad(f'{cfg.rel(sfile)}: id {sid!r} does not match its path '
                        f'(expected {s_expect!r})')
                if 'V3' in on:
                    parent = model.field_of(sfile, 'feature')
                    if parent and parent != expect:
                        bad(f'{cfg.rel(sfile)}: feature: {parent!r} but it lives '
                            f'under feature {expect!r}')
                    own = model.field_of(sfile, 'milestone')
                    if own and own != mid:
                        bad(f'{cfg.rel(sfile)}: milestone: {own!r} but it lives '
                            f'under milestone {mid!r}')
                _check_refs(cfg, sfile, 'depends_on', on, bad, census)

            for key in _REF_KEYS:
                resolved = _check_refs(cfg, ffile, key, on, bad, census)
                if key == 'depends_on' and fid:
                    graph[fid].extend(ref for ref in resolved
                                      if ref.count('/') == 1)

        _check_refs(cfg, mfile, 'depends_on', on, bad, census)

        # Bugs are walked for `caused_by:` alone; `census['grains']` still
        # counts only milestones, features and stories.
        for bfile in model.bug_files(mdir):
            _check_caused_by(cfg, bfile, on, bad, census)

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
