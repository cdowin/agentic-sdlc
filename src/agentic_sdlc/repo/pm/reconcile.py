"""reconcile.py — the forward-reconcile record, read (#92).

A milestone that changes foundational contracts leaves the plans AHEAD of it
written against contracts that no longer hold. A milestone opts in with
`reconcile: forward`, and then `<stem>-reconcile.md` beside it is the record of
the pass: which contracts changed, which forward grains were rewritten, and
what needs the owner.

This module only READS. `census` answers one question — is the record there
and complete? — for its three callers: the release step `forward-reconciled`,
`pm ready-for milestone`, and `dispatch --reconcile`. `check pm` asks
`declared` and the record's path. An id that does not resolve is a defect,
never a guess (rule 9).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc.core import frontmatter
from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.markdown import non_fenced_lines
from agentic_sdlc.repo import vehicle
from agentic_sdlc.repo.pm import inventory, vocabulary

# The release step's name, spelled once for its three readers.
STEP = 'forward-reconciled'

CONTRACTS = 'Contracts'
UPDATED = 'Forward grains updated'
NEEDS_YOU = 'Needs you'
SECTIONS = (CONTRACTS, UPDATED, NEEDS_YOU)
NONE_CHANGED = 'none changed'

_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
_SEPARATOR_ROW = re.compile(r'^\|?\s*:?-{3,}')
_LIST_ITEM = re.compile(r'^\s*[-*+]\s+(\S+)')


class Census(NamedTuple):
    """What the record says, and every reason it is not complete."""

    record: Path
    rows: int
    none_changed: bool
    grains: tuple[str, ...]
    defects: tuple[str, ...]


def declared(cfg: vocabulary.PmConfig, milestone: inventory.Grain) -> bool:
    """Does this milestone declare `reconcile: forward`? Absent or empty is
    False; any other word is refused by name, at exit 2 (rule 9)."""
    value = milestone.field(vocabulary.FIELD_RECONCILE).strip()
    if not value:
        return False
    if value in vocabulary.RECONCILE_VALUES:
        return True
    raise ConfigError(
        f'{cfg.rel(milestone.path)}: {vocabulary.FIELD_RECONCILE}: {value!r} '
        f'is not one of {", ".join(vocabulary.RECONCILE_VALUES)} — absent or '
        f'empty declares no forward reconcile')


def record_path(cfg: vocabulary.PmConfig, milestone: inventory.Grain) -> Path:
    """Where this milestone's record lives, beside its document."""
    return inventory.shared_doc(cfg, milestone, vocabulary.RECONCILE_FILE_NAME)


def forward_of(cfg: vocabulary.PmConfig, mid: str) -> list[str]:
    """The milestone ids after `mid` in `releases.md` `order:`, or [] when
    `mid` is not in the order."""
    order = inventory.declared_order(cfg)
    return order[order.index(mid) + 1:] if mid in order else []


def _sections(text: str) -> dict[str, list[str]]:
    """`## <name>` -> its non-fenced lines, comments dropped."""
    lines, _ = non_fenced_lines(_COMMENT.sub('', text))
    out: dict[str, list[str]] = {}
    current = None
    for _, line in lines:
        line = line.rstrip('\r')
        if line.startswith('## '):
            current = line[3:].strip()
            out.setdefault(current, [])
        elif current is not None:
            out[current].append(line)
    return out


def _rows(lines: list[str]) -> int:
    """Data rows in the first table: the header and separator do not count,
    and a row of empty cells is not a row."""
    table = [line.strip() for line in lines if line.strip().startswith('|')]
    body = [row for row in table[1:] if not _SEPARATOR_ROW.match(row)]
    return sum(1 for row in body if row.strip('|').replace('|', '').strip())


def _grain_ids(lines: list[str]) -> tuple[str, ...]:
    out = []
    for line in lines:
        match = _LIST_ITEM.match(line)
        if match:
            out.append(match.group(1).strip('`"\',.'))
    return tuple(gid for gid in out if gid)


def _names(heading: str, mid: str) -> bool:
    return re.search(rf'(?<![\w.-]){re.escape(mid)}(?![\w-])', heading) is not None


def _decided(cfg: vocabulary.PmConfig, owner: inventory.Grain,
             mid: str) -> tuple[bool, Path]:
    """(does `owner`'s decisions log hold a heading naming `mid`, its path)."""
    log = inventory.shared_doc(cfg, owner, vocabulary.DECISION_FILE_NAME)
    try:
        text = frontmatter.read_raw(log) if log.is_file() else ''
    except (OSError, UnicodeDecodeError):
        text = ''
    lines, _ = non_fenced_lines(text)
    return any(line.startswith('#') and _names(line, mid)
               for _, line in lines), log


def census(cfg: vocabulary.PmConfig, milestone: inventory.Grain) -> Census:
    """Read the record of a milestone that declares `reconcile: forward`.
    Every defect is named; an empty tuple is a complete record."""
    mid = milestone.gid
    path = record_path(cfg, milestone)
    rel = cfg.rel(path)
    if not path.is_file():
        mint = vehicle.command('pm', 'new', 'reconcile', mid)
        return Census(path, 0, False, (), (
            f'{mid} declares `{vocabulary.FIELD_RECONCILE}: '
            f'{vocabulary.RECONCILE_FORWARD}` and has no {rel} — `{mint}` '
            f'mints it',))
    try:
        text = frontmatter.read_raw(path)
    except (OSError, UnicodeDecodeError) as err:
        return Census(path, 0, False, (), (f'{rel} cannot be read ({err})',))
    sections = _sections(text)
    defects: list[str] = []
    contracts = sections.get(CONTRACTS)
    rows = _rows(contracts or [])
    none_changed = any(line.strip().strip('`.').lower() == NONE_CHANGED
                       for line in contracts or [])
    if contracts is None:
        defects.append(f'{rel} has no `## {CONTRACTS}` section')
    elif not rows and not none_changed:
        defects.append(f'{rel} `## {CONTRACTS}` has no row — name each '
                       f'contract this milestone changed, or write the single '
                       f'line `{NONE_CHANGED}`')
    grains = _grain_ids(sections.get(UPDATED, []))
    index = inventory.grain_index(cfg)
    owners: dict[str, list[str]] = {}
    ahead = set(forward_of(cfg, mid))
    for gid in grains:
        if gid not in index:
            defects.append(f'{rel} names {gid!r} under `## {UPDATED}`, and it '
                           f'resolves to no grain')
            continue
        owner = inventory.milestone_of(cfg, gid)
        if not owner or owner not in index:
            defects.append(f'{rel} names {gid!r} under `## {UPDATED}`, and it '
                           f'belongs to no milestone')
            continue
        if owner not in ahead:
            defects.append(f'{rel} names {gid!r} under `## {UPDATED}`, and its '
                           f'milestone {owner} is not after {mid} in `order:`')
            continue
        owners.setdefault(owner, []).append(gid)
    for owner, touched in owners.items():
        found, log = _decided(cfg, index[owner], mid)
        if not found:
            decide = vehicle.command('pm', 'decide', owner,
                                     vehicle.Slot(f'<title naming {mid}>'))
            defects.append(f'{owner} owns {", ".join(touched)} and '
                           f'{cfg.rel(log)} has no heading naming {mid} — '
                           f'`{decide}`')
    return Census(path, rows, none_changed, grains, tuple(defects))


def summary(result: Census) -> str:
    """The one-line account of a complete record."""
    contracts = (NONE_CHANGED if result.none_changed and not result.rows
                 else f'{result.rows} contract row(s)')
    return (f'{contracts}, {len(result.grains)} forward grain(s) updated, '
            f'each with a decision')
