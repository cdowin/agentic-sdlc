"""rename.py — one grain's `id:`, and every reference naming it, in one pass.

Whole or not at all: a half-swept tree has refs pointing at an id that exists
and refs pointing at one that does not, and no gate can tell which was meant.
So `sweep` decides against the tree and the writes go through one `apply.Plan`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from agentic_sdlc.core import apply
from agentic_sdlc.repo.pm import model

# Every frontmatter key whose value can be a grain id. `tests/test_pm_rename.py`
# holds it to the shipped templates and to `BINDS_TO`/`ORDER_KEY`/`validate`'s
# ref keys, so a template or a bound kind cannot grow a reference without
# joining the sweep. `caught_in`/`fix_milestone` are `pm_migrate.py`'s misses.
REF_FIELDS = ('depends_on', 'consumed_by', 'caused_by', 'reviewed', 'order',
              'milestone', 'feature', 'caught_in', 'fix_milestone')

# An unindented frontmatter key, which is the only shape the readers accept.
_KEY = re.compile(r'^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?P<rest>.*)$')


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


def _swapped(raw: str, old: str, new: str) -> str | None:
    """One value token — spacing, quotes and trailing comment kept — with `old`
    become `new`; None when the token does not name `old`. WHOLE-token, never a
    substring: `0.1/alpha/s0` and `0.1/alphabet` are not refs to `0.1/alpha`."""
    value = model._without_trailing_comment(raw).strip()
    if model.unquote(value) != old:
        return None
    quote = value[0] if value[:1] in ('"', "'") else ''
    return raw.replace(value, f'{quote}{new}{quote}', 1)


def _inline(rest: str, old: str, new: str) -> str | None:
    """`["a", "b"]` with every element naming `old` rewritten; None when none
    does. Each element keeps its own spacing, so the join restores the line."""
    if '[' not in rest or ']' not in rest:
        return None
    head, tail = rest.index('[') + 1, rest.rindex(']')
    parts = rest[head:tail].split(',')
    swapped = [_swapped(p, old, new) or p for p in parts]
    if swapped == parts:
        return None
    return rest[:head] + ','.join(swapped) + rest[tail:]


def rewritten(text: str, old: str, new: str) -> tuple[str, tuple[str, ...]]:
    """One document's frontmatter with every ref to `old` naming `new`, and
    the keys that moved. `('', ())` when there is no readable fence."""
    lines = model._split(text)
    bounds = model._fence_bounds(lines)
    if bounds is None:
        return '', ()
    open_i, close_i = bounds
    moved: list[str] = []
    key = ''
    for i in range(open_i + 1, close_i):
        line = lines[i]
        match = _KEY.match(line)
        if match is not None:
            key, rest = match.group('key'), match.group('rest')
            if key not in REF_FIELDS:
                continue
            swapped = (_inline(rest, old, new) if rest.lstrip()[:1] == '['
                       else _swapped(rest, old, new))
            if swapped is not None:
                lines[i] = f'{key}:{swapped}'
                moved.append(key)
            continue
        item = model._LIST_ITEM.match(line)
        if item is None or key not in REF_FIELDS:
            continue
        # The bullet is the first `-`, so a dashed id cannot be split on.
        indent, _, rest = line.partition('-')
        swapped = _swapped(rest, old, new)
        if swapped is not None:
            lines[i] = f'{indent}-{swapped}'
            moved.append(key)
    return '\n'.join(lines), tuple(dict.fromkeys(moved))


def reidentified(text: str, new: str) -> str:
    """The grain's own `id:` line, rewritten; '' when it has none to rewrite."""
    lines = model._split(text)
    bounds = model._fence_bounds(lines)
    if bounds is None:
        return ''
    for i in range(bounds[0] + 1, bounds[1]):
        match = _KEY.match(lines[i])
        if match is None or match.group('key') != 'id':
            continue
        rest = match.group('rest')
        value = model._without_trailing_comment(rest).strip()
        if not value:
            return ''
        quote = value[0] if value[:1] in ('"', "'") else ''
        return '\n'.join(lines[:i]
                         + [f'id:{rest.replace(value, f"{quote}{new}{quote}", 1)}']
                         + lines[i + 1:])
    return ''


def _verdict(cfg: model.PmConfig, out: Sweep, target: model.Grain | None,
             holder: model.Grain | None) -> bool:
    """The four answers that need no sweep at all, onto `out`; True when one
    of them applies."""
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


def documents(cfg: model.PmConfig, index: dict[str, model.Grain]) -> list[Path]:
    """Every document the sweep must read, in whichever layout the tree is in.
    The POOL, not the index, because a document the index cannot key on still
    holds refs — and the INDEX when there is no pool, because `pm_migrate`
    sends a collision here before the move and a pool-only walk would report a
    rename over nothing (rule 4)."""
    if model.is_pooled(cfg):
        return [p for kind in model.FLOW_KINDS
                for p in model.pool_walk(cfg, kind)]
    return sorted({g.path for g in index.values()})


def sweep(cfg: model.PmConfig, old: str, new: str) -> Sweep:
    """Decide the whole rename against the tree; writes nothing. A malformed id
    is answered before a document is opened, so a hostile string costs no read
    — the property `model.id_defect` exists to keep."""
    out = Sweep(old=old, new=new)
    for gid in (old, new):
        defect = model.id_defect(gid)
        if defect:
            out.defect = f'{defect} — nothing was read'
            return out
    index = model.grain_index(cfg)
    target = index.get(old)
    if _verdict(cfg, out, target, index.get(new)):
        return out
    for path in documents(cfg, index):
        _take(cfg, out, path, path == target.path)
    out.blockers += [b.describe() for b in out.plan.decide()]
    return out


def _take(cfg: model.PmConfig, out: Sweep, path: Path, is_target: bool) -> None:
    """One document's share of the sweep, staged or reported."""
    try:
        text = model.read_raw(path)
    except (OSError, UnicodeDecodeError) as err:
        out.blockers.append(f'{cfg.rel(path)} could not be read '
                            f'({err.__class__.__name__})')
        return
    swept, fields = rewritten(text, out.old, out.new)
    if is_target and swept:
        swept, fields = reidentified(swept, out.new), ('id',) + fields
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
