"""`changelog:` — the field a grain earned, and the view that renders it in `order:`.

`CHANGELOG.md` goes the way of `ROADMAP.md` (0.3.0). 0.5.0's `## Unreleased`
was 469 lines by ~12 authors with no binding between an entry and the grain it
described, so an entry could outlive a retired grain, a grain could close with
none, and the ORDER was append-order rather than the parent's `order:`.

`none` is an ANSWER, not an absence — it separates *decided* from *forgotten*
(rule 11).
"""
from __future__ import annotations

from dataclasses import dataclass

from agentic_sdlc.repo.pm import inventory, vocabulary

FIELD = 'changelog'
# "This one is internal", typed by hand, so compared case-insensitively.
NEEDS_NONE = 'none'
COLUMNS = ('id', 'kind', 'status', 'changelog')


@dataclass(frozen=True)
class Entry:
    gid: str
    kind: str
    status: str
    text: str

    @property
    def declined(self) -> bool:
        return self.text.strip().lower() == NEEDS_NONE

    @property
    def said_something(self) -> bool:
        return bool(self.text.strip()) and not self.declined


def _text(grain) -> str:
    return grain.field(FIELD).strip()


# The tool's own mapping, inverted — NOT `[pm.contains]`, which a project may
# narrow, and a narrowed one would drop a level's entries in silence (D11).
_CHILD_KINDS: dict[str, tuple[str, ...]] = {}
for _kind, (_parent, _field) in vocabulary.BINDS_TO.items():
    _CHILD_KINDS[_parent] = _CHILD_KINDS.get(_parent, ()) + (_kind,)


def collect(cfg: vocabulary.PmConfig, gid: str,
            seen: set[str] | None = None) -> list[Entry]:
    """`gid` and everything beneath it, in the `order:` each parent declares.

    DEPTH FIRST, and the parent's `order:` is read WHOLE rather than once per
    kind: a milestone's list interleaves bugs and features, and going
    kind-by-kind would reorder the notes away from what shipped when.
    """
    seen = set() if seen is None else seen
    index = inventory.grain_index(cfg)
    grain = index.get(gid)
    if grain is None or gid in seen:
        return []
    seen.add(gid)
    out = [Entry(gid, grain.kind, grain.field(vocabulary.FIELD_STATUS),
                 _text(grain))]
    for child in _children(cfg, index, grain):
        out.extend(collect(cfg, child, seen))
    return out


def _children(cfg: vocabulary.PmConfig, index: dict, grain) -> list[str]:
    """Bound to `grain`, sequenced by its `order:` then by id — the rule
    `_children_paths` uses one kind at a time."""
    kinds = _CHILD_KINDS.get(grain.kind, ())
    if not kinds:
        return []
    bound = {gid: g for gid, g in index.items()
             if g.kind in kinds and g.binding == grain.gid}
    declared = grain.list_field(vocabulary.ORDER_KEY)
    out = [gid for gid in declared if gid in bound]
    placed = set(out)
    return out + sorted(gid for gid in bound if gid not in placed)


def rows(entries: list[Entry]) -> list[tuple[str, ...]]:
    """Only what SAID something: a declined grain is a decision the tree
    keeps, not a line in a release note."""
    return [(e.gid, e.kind, e.status, e.text)
            for e in entries if e.said_something]


def unanswered(cfg: vocabulary.PmConfig, entries: list[Entry],
               releasing: str = '') -> list[Entry]:
    """Closed grains carrying neither a sentence nor `none`, and `releasing` —
    the grain a release is FOR, not closed until the belt writes it — whatever
    its state. The release check grades THIS, so it names the grain."""
    return [e for e in entries
            if (e.gid == releasing
                or vocabulary.category_of(cfg, e.kind, e.status)
                == vocabulary.DONE_CATEGORY)
            and not e.text.strip()]


USAGE = """usage: agentic-sdlc changelog [<grain-id>] [--json]

  <grain-id>   any grain: a milestone renders its whole release, a feature its
               own line and its stories', a story just itself. Omitted, the
               CURRENT release in the plan is used and its id is named on
               stderr rather than assumed.

  --json       the same rows as objects, keys in column order.

COLUMNS IN ORDER:  id  kind  status  changelog

The sequence is the `order:` each parent declares — the tree already knows what
shipped when, so this verb has no ordering of its own. A grain whose
`changelog:` is `none` has DECLINED and prints nothing; one that is empty has
answered nothing, and `check pm` D12 names it while there is time to write one.

Writes no file. A consumer who wants one redirects this."""

HELP_WORDS = ('-h', '--help', 'help')


def main(argv: list[str]) -> int:
    """Render the entries beneath one grain. `USAGE` is the contract."""
    import json
    import sys
    if argv and argv[0] in HELP_WORDS:
        print(USAGE)
        return 0
    as_json = '--json' in argv
    rest = [a for a in argv if a != '--json']
    if any(a.startswith('-') for a in rest):
        print(f'agentic-sdlc changelog: unexpected argument(s) '
              f'{" ".join(a for a in rest if a.startswith("-"))}',
              file=sys.stderr)
        return 2
    if len(rest) > 1:
        print(f'agentic-sdlc changelog: takes one grain id, got {len(rest)}',
              file=sys.stderr)
        return 2
    cfg = vocabulary.load()
    gid = rest[0] if rest else _current(cfg)
    if not gid:
        print('agentic-sdlc changelog: no grain named and no current release '
              'in the plan — name one', file=sys.stderr)
        return 2
    if gid not in inventory.grain_index(cfg):
        print(f'agentic-sdlc changelog: no grain resolves from {gid!r}',
              file=sys.stderr)
        return 2
    entries = collect(cfg, gid)
    said = rows(entries)
    if as_json:
        print(json.dumps([dict(zip(COLUMNS, r)) for r in said],
                         ensure_ascii=False))
    else:
        for row in said:
            print('\t'.join(c.replace('\t', ' ') for c in row))
    # Rule 4: "no entries" must not read as "nothing shipped".
    declined = sum(1 for e in entries if e.declined)
    empty = len(entries) - len(said) - declined
    print(f'[changelog] {len(said)} entry/ies of {len(entries)} grain(s) '
          f'under {gid}; {declined} declined, {empty} unanswered',
          file=sys.stderr)
    return 0


def _current(cfg: vocabulary.PmConfig) -> str:
    """The current release, or ''. NAMED on stderr: a verb that picks a
    subject silently is one whose output nobody can attribute."""
    import sys
    mid = inventory.current_milestone(cfg)
    if mid:
        print(f'[changelog] no id given — using {mid}, the current entry in '
              f'{cfg.rel(inventory.releases_file(cfg))}', file=sys.stderr)
    return mid or ''
