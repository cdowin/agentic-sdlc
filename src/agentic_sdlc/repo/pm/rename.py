"""rename.py — one grain's `id:`, and every reference naming it, in one pass.

Whole or not at all: a half-swept tree has refs pointing at an id that exists
and refs pointing at one that does not, and no gate can tell which was meant.
So `sweep` decides against the tree and the writes go through one `apply.Plan`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agentic_sdlc.core import apply, frontmatter
from agentic_sdlc.repo.pm import inventory, vocabulary

# Every frontmatter key whose value can be a grain id. `tests/test_pm_rename.py`
# holds it to the shipped templates and to `BINDS_TO`/`ORDER_KEY`/`validate`'s
# ref keys, so a template or a bound kind cannot grow a reference without
# joining the sweep.
REF_FIELDS = ('depends_on', 'consumed_by', 'caused_by', 'reviewed', 'order',
              vocabulary.GRAIN_MILESTONE, vocabulary.GRAIN_FEATURE)


@dataclass
class Edit:
    """One document's whole new text, and the keys that changed in it."""

    path: Path
    text: str
    fields: tuple[str, ...]


@dataclass
class Sweep:
    """The rename as data, before a byte is written."""

    old: str = ''
    new: str = ''
    edits: list[Edit] = field(default_factory=list)
    plan: apply.Plan = field(default_factory=apply.Plan)
    blockers: list[str] = field(default_factory=list)
    defect: str = ''
    noop: str = ''


def _claimants(cfg: vocabulary.PmConfig, gid: str) -> list[str]:
    """Every document declaring `gid`, by path — usually one."""
    for claimed, paths in inventory.duplicate_ids(cfg):
        if claimed == gid:
            return [cfg.rel(path) for path in paths]
    return []


def _verdict(cfg: vocabulary.PmConfig, out: Sweep, target: inventory.Grain | None,
             holder: inventory.Grain | None) -> bool:
    """The answers that need no sweep at all, onto `out`; True when one of them
    applies."""
    # BOTH directions of one sentence: refusing a taken `new` and then picking
    # between two documents claiming `old` is a filename deciding identity.
    twins = _claimants(cfg, out.old)
    if len(twins) > 1:
        out.blockers.append(
            f'{out.old} is claimed by {len(twins)} documents '
            f'({", ".join(twins)}) — renaming one leaves the other holding the '
            f'id and every ref pointing at whichever is read first; this verb '
            f'never picks. Give one of them its own id first')
        return True
    if out.old == out.new:
        if target is None:
            out.defect = f'no grain resolves from id {out.old!r}'
        else:
            out.noop = (f'{out.old} already holds this id — nothing was '
                        f'written')
    elif target is None:
        if holder is None:
            out.defect = f'no grain resolves from id {out.old!r}'
        else:
            out.noop = (f'no grain holds {out.old} and {out.new} is already in '
                        f'{cfg.rel(holder.path)} — nothing was written')
    elif holder is not None:
        out.blockers.append(
            f'{out.new} is already held by {cfg.rel(holder.path)} '
            f'({holder.kind}) — two documents claiming one id is addressable '
            f'by neither, and this verb never picks a name for you')
    return bool(out.defect or out.noop or out.blockers)


def documents(cfg: vocabulary.PmConfig, index: dict[str, inventory.Grain]) -> list[Path]:
    """Every document the sweep must read, in whichever layout the tree is in.

    The POOL, not the index, because a document the index cannot key on still
    holds refs — and the INDEX when there is no pool, because `pm_migrate`
    sends a collision here before the move and a pool-only walk would report a
    rename over nothing (rule 4). **The ROOT is one of them**: `releases.md` is
    a container now and its `order` holds milestone IDS, so a pools-only sweep
    left `order: ["ms-a"]` naming a renamed grain, at exit 0.
    """
    if inventory.is_pooled(cfg):
        pooled = [p for kind in vocabulary.FLOW_KINDS
                  for p in inventory.pool_walk(cfg, kind)]
        root = inventory.root_grain(cfg)
        return pooled + ([root.path] if root is not None else [])
    return sorted({g.path for g in index.values()})


def sweep(cfg: vocabulary.PmConfig, old: str, new: str) -> Sweep:
    """Decide the whole rename against the tree; writes nothing. A malformed id
    is answered before a document is opened, so a hostile string costs no read
    — the property `inventory.id_defect` exists to keep."""
    out = Sweep(old=old, new=new)
    for gid in (old, new):
        defect = inventory.id_defect(gid)
        if defect:
            out.defect = f'{defect} — nothing was read'
            return out
    index = inventory.grain_index(cfg)
    target = index.get(old)
    if _verdict(cfg, out, target, index.get(new)):
        return out
    for path in documents(cfg, index):
        _take(cfg, out, path, path == target.path)
    out.blockers += [b.describe() for b in out.plan.decide()]
    return out


def _take(cfg: vocabulary.PmConfig, out: Sweep, path: Path, is_target: bool) -> None:
    """One document's share of the sweep, staged or reported."""
    try:
        text = frontmatter.read_raw(path)
    except (OSError, UnicodeDecodeError) as err:
        out.blockers.append(f'{cfg.rel(path)} could not be read '
                            f'({err.__class__.__name__})')
        return
    keys = REF_FIELDS + ((vocabulary.FIELD_ID,) if is_target else ())
    swept, fields = (frontmatter.renamed_in(text, keys, {out.old: out.new})
                     or ('', ()))
    if is_target and swept:
        # A target whose own `id:` did not move is a grain not renamed.
        if vocabulary.FIELD_ID not in fields:
            swept = ''
        fields = (vocabulary.FIELD_ID,) + tuple(
            k for k in fields if k != vocabulary.FIELD_ID)
    if not swept:
        # No fence to locate a field in. A document that never names `old` is
        # simply not a reference; one that does is a ref this verb cannot
        # rewrite, and rule 4 says name it rather than sweep around it.
        if is_target or out.old in text:
            out.blockers.append(f'{cfg.rel(path)} holds {out.old} in '
                                f'frontmatter this verb cannot parse')
        return
    if not fields:
        return
    out.edits.append(Edit(path=path, text=swept, fields=fields))
    out.plan.overwrite(path, swept, label=cfg.rel(path))
