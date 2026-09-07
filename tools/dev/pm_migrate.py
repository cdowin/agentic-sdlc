#!/usr/bin/env python3
"""pm_migrate.py — a nested PM tree becomes pooled, whole or not. NOT A VERB.

Run it from a checkout that has this package importable:

    python3 tools/dev/pm_migrate.py [--suggest]      # from the repo root

It is deliberately NOT `agentic-sdlc pm migrate`. The CLI is a published API
(rule 6) and this is a one-time move per tree: codifying it would make a verb
every consumer\'s gate depends on forever, for a job that runs once, from a
checkout, with somebody watching. It lives here so the next tree can take it,
and it is expected to rot the moment no nested tree is left.

**The only verb in 0.4.0 that touches an existing tree**, and the riskiest work
in the milestone. Every other feature describes the destination; this one moves
a tree there.

A consumer cannot half-adopt this. Identity, pools, bindings and order change
together, so the migration is one commit or none: a tree that stopped halfway
would have neither the old resolvers nor the new ones working, which is worse
than not starting. `pm move`'s *"whole, or not at all"* is the same instinct at
one-hundredth the scale.

WHAT IT DOES, IN ORDER

  1. reads the NESTED tree — the last time a path is authoritative. Kind comes
     from which slot a document sits in, exactly as the tool used to, and that
     reading is thrown away afterwards;
  2. mints ids: `<kind-prefix>-<slug>` from the grain's current last id
     segment;
  3. resolves collisions, or STOPS — below, and it is the hard part;
  4. writes `id:`, `kind:` and the binding (`milestone:` / `feature:`) the
     path used to carry;
  5. builds each parent's `order` from the nesting being deleted. The `NN-`
     prefix and `phase:` are the migration's INPUT — they encoded sequence, so
     they are read once to produce `order` and then stop mattering;
  6. moves the files into the pools;
  7. rewrites every inbound ref, because ids changed.

THE COLLISION PROBLEM IS THE FEATURE

Story slugs are unique per FEATURE today and must be unique per KIND after, so
a real tree arrives with genuine collisions — one consumer has 254 stories with
reused names and its own notes record "S4" meaning three different stories in
one session.

**The migration does not guess.** It reports every collision with the grains
that share a slug and writes nothing, because an auto-picked id is a name
nobody chose, in the one field that is stable for life and cited from commit
messages (0.4.0/D4). Resolution is `pm rename`, which is the same ref-sweep
problem stated once — so the advice is a command, not a paragraph.

GIT IS THE UNDO. One commit, revertible, so this verb writes no backup of its
own; and it is IDEMPOTENT — a second run finds a pooled tree and says so.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from agentic_sdlc.core import apply, walk
from agentic_sdlc.core.walk import Kind
from agentic_sdlc.repo.pm import model

# The fields that can name another grain, and every one is rewritten when an id
# changes. `pm move` rewrote three of them and skipped the refs pointing AT the
# grain it moved, which is the defect this verb exists not to repeat.
# Every frontmatter key whose VALUE is a grain id. `caught_in` and
# `fix_milestone` were missed on the first run, so eleven bugs kept
# pre-migration milestone ids and the milestone belt counted zero of the six
# that named it — a read that looked right and was not. The list is held to the
# tree's own declarations by `tests/test_pm_rename.py`; keep the two in sync.
REF_FIELDS = ('depends_on', 'consumed_by', 'reviewed', 'caused_by',
              'milestone', 'feature', 'caught_in', 'fix_milestone', 'order')


@dataclass
class Move:
    """One grain's whole change: where it goes, and what its frontmatter says
    when it gets there."""

    old_path: Path
    new_path: Path
    old_id: str
    new_id: str
    kind: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class Planned:
    """The migration as data, before a byte is written — so collisions and
    unrewritable refs are known before anything moves."""

    moves: list[Move] = field(default_factory=list)
    orders: dict[Path, list[str]] = field(default_factory=dict)
    collisions: dict[str, list[str]] = field(default_factory=dict)
    already: bool = False


def mint(kind: str, gid: str) -> str:
    """`<prefix>-<slug>` from a grain's current last id segment.

    Never a number. A counter needs an allocator and a git repo has none:
    scan-and-take-max+1 gives two agents on two branches the same number,
    invisibly, until merge, and a counter file makes every branch that creates
    a grain conflict on one line. Both fail hardest in the workflow this
    package is built for (0.4.0/D4).
    """
    slug = _without_ordinal(gid.rsplit('/', 1)[-1])
    prefix = model.KIND_PREFIX[kind]
    return slug if slug.startswith(f'{prefix}-') else f'{prefix}-{slug}'


# `NN-slug`. Held HERE, not imported: `story_ordinal_prefix` and `phase:` are
# retired, so the model no longer carries either — and this script reads them
# as INPUT, once, to build the `order` that replaced them.
_ORDINAL = re.compile(r'^(?P<n>\d{2})-(?P<slug>.+)$')
_PHASES = ('foundation', 'core', 'polish')


def _without_ordinal(slug: str) -> str:
    """`01-boots` -> `boots`. The number sequenced the build; the slug is the
    identity, and `order` carries the sequence now."""
    match = _ORDINAL.match(slug)
    return match.group('slug') if match is not None else slug


def _phase_key(phase: str) -> tuple:
    """A feature's `phase:` as a sort key — read once, to flatten into the
    milestone's `order`, and then never again."""
    word = (phase or '').strip().strip('"\'').lower()
    if word in _PHASES:
        return (0, _PHASES.index(word), '')
    return (1, 0, word)


def _ordinal_of(path: Path) -> tuple[int, str]:
    """The `NN-` prefix as a sort key, or a large one — the sequence the
    filename encoded, read once so `order` can carry it instead."""
    match = _ORDINAL.match(path.stem)
    if match is None:
        return (10_000, path.stem)
    return (int(match.group('n')), path.stem)


def plan(cfg: model.PmConfig) -> Planned:
    """Read the nested tree and stage everything. Writes nothing."""
    out = Planned()
    nested = list(model.milestone_dirs(cfg))
    if not nested and model.grain_index(cfg):
        out.already = True
        return out
    minted: dict[tuple[str, str], list[str]] = {}

    def take(kind: str, path: Path, old_id: str, binding: str,
             order_key: tuple[int, str] | None = None) -> str:
        new_id = mint(kind, old_id)
        minted.setdefault((kind, new_id), []).append(old_id)
        fields = {'id': new_id, 'kind': kind}
        bind = model.BINDS_TO.get(kind)
        if bind:
            fields[bind[1]] = binding
        out.moves.append(Move(old_path=path,
                              new_path=model.pool_dir(cfg, kind) / f'{new_id}.md',
                              old_id=old_id, new_id=new_id, kind=kind,
                              fields=fields))
        return new_id

    for mdir in nested:
        mfile = mdir / model.MILESTONE_DOC
        mid = model.unquote(model.field_of(mfile, 'id')) or mdir.name
        ms_id = take('milestone', mfile, mid, '')
        feature_ids: list[tuple[tuple, str]] = []
        for ffile in model._nested_feature_files(mdir):
            fid = model.unquote(model.field_of(ffile, 'id'))
            ft_id = take('feature', ffile, fid or ffile.parent.name, ms_id)
            # `phase:` grouped features within a milestone; it flattens into
            # the milestone's order in phase reading order and stops being a
            # field the tool interprets.
            phase = _phase_key(model.field_of(ffile, 'phase'))
            feature_ids.append(((phase, ft_id), ft_id))
            story_ids: list[tuple[tuple, str]] = []
            for sfile in model._nested_story_files(ffile):
                sid = model.unquote(model.field_of(sfile, 'id'))
                st_id = take('story', sfile, sid or sfile.stem, ft_id)
                story_ids.append((_ordinal_of(sfile), st_id))
            if story_ids:
                out.orders[ffile] = [i for _, i in sorted(story_ids)]
        for bfile in model._nested_bug_files(mdir):
            bid = model.unquote(model.field_of(bfile, 'id'))
            take('bug', bfile, bid or bfile.stem, ms_id)
        if feature_ids:
            out.orders[mfile] = [i for _, i in sorted(feature_ids)]

    out.collisions = {new_id: sorted(olds)
                      for (_kind, new_id), olds in minted.items()
                      if len(olds) > 1}
    return out


def _rewritten(text: str, renames: dict[str, str]) -> str:
    """Every inbound reference in one document's frontmatter, rewritten.

    Whole-token, never a substring: `0.1/alpha` must not be rewritten inside
    `0.1/alphabet`, and a ref list is `["a", "b"]` or a block of `- a` lines.
    Both are handled by splitting on the characters a ref cannot contain.
    """
    lines = model._split(text)
    bounds = model._fence_bounds(lines)
    if bounds is None:
        return text
    open_i, close_i = bounds
    for i in range(open_i + 1, close_i):
        line = lines[i]
        key = line.split(':', 1)[0].strip().lstrip('- ')
        if key not in REF_FIELDS and not line.lstrip().startswith('- '):
            continue
        for old, new in renames.items():
            for quote in ('"', "'", ' ', '[', ',', '\t'):
                line = line.replace(f'{quote}{old}"', f'{quote}{new}"')
                line = line.replace(f"{quote}{old}'", f"{quote}{new}'")
            if line.rstrip().endswith(old):
                head = line.rstrip()[:-len(old)]
                if head.endswith((': ', '- ', '"', "'", '[', ', ')):
                    line = head + new + model._eol(lines[i])
        lines[i] = line
    return '\n'.join(lines)


def run(cfg: model.PmConfig, suggest: bool = False) -> tuple[int, list[str]]:
    """(exit code, the lines to print). Writes in ONE pass or not at all."""
    staged = plan(cfg)
    if staged.already:
        return 0, ['[pm] this tree is already pooled — nothing to migrate '
                   '(a second run is a no-op, by design)']
    if not staged.moves:
        return 1, [f'[pm] {cfg.roadmap_dir} holds no nested milestone to '
                   f'migrate, and no pooled grain either — this is a scope '
                   f'problem (wrong [pm] roadmap_dir, or an empty tree?), not '
                   f'a migration']
    if staged.collisions:
        out = [f'[pm] REFUSED — {len(staged.collisions)} slug collision(s); '
               f'nothing was written. An auto-picked id is a name nobody '
               f'chose, in the one field that is stable for life and cited '
               f'from commit messages (D4), so this verb reports and stops.']
        for new_id, olds in sorted(staged.collisions.items()):
            out.append(f'  {new_id} <- {", ".join(olds)}')
            if suggest:
                for old in olds:
                    parts = old.split('/')
                    hint = mint('story', old)
                    if len(parts) > 1:
                        hint = f'{model.KIND_PREFIX["story"]}-{parts[-2]}-{parts[-1]}'
                    out.append(f'    suggest: {hint}   (for {old})')
        out.append('  resolve each with `agentic-sdlc pm rename <old> <new>` '
                   'and re-run; --suggest prints parent-qualified candidates '
                   'and applies none.')
        return 1, out

    renames = {m.old_id: m.new_id for m in staged.moves if m.old_id != m.new_id}
    # Captured BEFORE anything moves: once a milestone.md is out of its
    # directory the directory is no longer a milestone directory, so a second
    # `milestone_dirs()` afterwards returns nothing and the husks stay forever.
    husks = list(model.milestone_dirs(cfg))
    plan_ = apply.Plan()
    lines = []
    for move in staged.moves:
        try:
            text = model.read_raw(move.old_path)
        except (OSError, UnicodeDecodeError) as err:
            return 1, [f'[pm] REFUSED — {cfg.rel(move.old_path)} could not be '
                       f'read ({err.__class__.__name__}); nothing was written']
        text = _rewritten(text, renames)
        text = _with_fields(text, move.fields)
        if move.old_path in staged.orders:
            text = _with_order(text, [renames.get(i, i)
                                      for i in staged.orders[move.old_path]])
        plan_.overwrite(move.new_path, text, newline=None,
                        label=cfg.rel(move.new_path))
        lines.append(f'  {cfg.rel(move.old_path)} -> '
                     f'{cfg.rel(move.new_path)}   [{move.old_id} -> '
                     f'{move.new_id}]')
    applied = plan_.apply()
    if applied.failed is not None:
        return 1, [f'[pm] REFUSED — {applied.failed.label} could not be '
                   f'written ({applied.error}); the tree is unchanged']
    for move in staged.moves:
        apply.remove_file(move.old_path)
    # A husk goes only when it is EMPTY. `plan()` stages four document classes
    # and everything else under a milestone directory used to go with the
    # `delete_tree` — four `ledger.jsonl`, six `decisions.md`, a handoff and a
    # loose design note, on this repo's own tree, none of them named. Git is
    # the undo for a MOVE; there is no undo for a file nobody was told about.
    left: list[str] = []
    for mdir in husks:
        remaining = sorted(walk.descendants(mdir, Kind.FILE).kept)
        if remaining:
            left += [cfg.rel(path) for path in remaining]
            continue
        apply.Plan().delete_tree(mdir).apply(decide=False)
    tail = lines
    if left:
        tail = tail + [
            '',
            f'  {len(left)} file(s) were NOT moved and NOT deleted — this '
            f'script knows four document classes and these are not among '
            f'them. Move them yourself, then remove the empty directories:'
        ] + [f'    {rel}' for rel in left]
    return 0, ([f'[pm] migrated {len(staged.moves)} grain(s) into '
                f'{len(model.FLOW_KINDS)} pool(s); '
                f'{len(renames)} id(s) changed and every inbound ref was '
                f'rewritten. Git is the undo.'] + tail)


def _with_fields(text: str, fields: dict[str, str]) -> str:
    """`set_fields`' logic over a string, because the migration stages every
    write in memory and commits them in one pass."""
    lines = model._split(text)
    bounds = model._fence_bounds(lines)
    if bounds is None:
        return text
    open_i, close_i = bounds
    for key, value in fields.items():
        for i in range(open_i + 1, close_i):
            if lines[i].startswith(f'{key}:'):
                lines[i] = f'{key}: {value}{model._eol(lines[i])}'
                break
        else:
            lines.insert(close_i, f'{key}: {value}{model._eol(lines[close_i])}')
            close_i += 1
    return '\n'.join(lines)


def _with_order(text: str, ids: list[str]) -> str:
    """The parent's `order` block, built from the nesting being deleted."""
    lines = model._split(text)
    bounds = model._fence_bounds(lines)
    if bounds is None:
        return text
    _open_i, close_i = bounds
    block = ['order:'] + [f'  - "{i}"' for i in ids]
    return '\n'.join(lines[:close_i] + block + lines[close_i:])


if __name__ == '__main__':
    import sys

    args = sys.argv[1:]
    unknown = [a for a in args if a != '--suggest']
    if unknown:
        print(f'usage: python3 tools/dev/pm_migrate.py [--suggest] — not '
              f'{" ".join(unknown)!r}', file=sys.stderr)
        raise SystemExit(2)
    code, lines = run(model.load(), suggest='--suggest' in args)
    for line in lines:
        print(line)
    raise SystemExit(code)
