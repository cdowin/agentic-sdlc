---
id: 0.4.0/the-migration-is-whole-or-nothing
milestone: "0.4.0"
name: The tree migrates once, whole, and every rename sweeps its refs
status: planning
reviewed:
phase:
depends_on: ["0.4.0/identity-lives-in-frontmatter", "0.4.0/the-pools-are-the-tables", "0.4.0/binding-is-a-field", "0.4.0/the-order-is-one-mechanism"]
consumed_by: []
---

# The tree migrates once, whole, and every rename sweeps its refs

Every other feature here describes the destination. **This one is the only thing that touches a
consumer's existing tree**, it is the riskiest work in the milestone, and until now it was one
line in another feature's ship criterion and two of the milestone's three risks.

A consumer cannot half-adopt this. Identity, pools, bindings and order change together, so the
migration is one commit or none.

## What it does, in order

1. **Reads the nested tree** — the LAST time a path is authoritative. Kind comes from which slot a
   document sits in, exactly as `model.py` does today, and that reading is thrown away after.
2. **Mints ids.** `<kind-prefix>-<slug>` from the grain's current last id segment.
3. **Resolves collisions, or stops** — below; this is the hard part.
4. **Writes frontmatter**: `id:`, `kind:`, and the binding (`milestone:` / `feature:`) that the
   path used to carry.
5. **Builds each parent's `order` from the nesting that is being deleted.** The `NN-` prefix and
   the `pm:execution` block are the migration's INPUT — they encoded sequence, so they are read
   once to produce `order` and then removed. `phase:` flattens into the milestone's order in phase
   reading order; a project that wants the grouping back keeps it as a label.
6. **Moves files into the pools** and the ledger to its own table.
7. **Rewrites every inbound ref** — `depends_on`, `consumed_by`, `reviewed:` and every binding —
   because ids changed.

## The collision problem is the feature

NullBound has **254 stories with reused names**; its own CLAUDE.md records "S4" meaning three
different stories in one session. Story slugs are unique per FEATURE today and must be unique per
KIND after, so a real tree arrives with dozens of genuine collisions.

**The migration does not guess.** It reports every collision with the grains that share a slug and
writes nothing — because an auto-disambiguated id is a name nobody chose, in the one field that is
now stable for life and cited from commit messages.

The resolution is `pm rename` (`binding-is-a-field`), which is the same problem stated once: rename
the grain and sweep every inbound reference, whole or not at all. So the migration's advice is a
command, not a paragraph, and the sweep is code that exists rather than code the migration
duplicates. A `--suggest` pass may PRINT parent-qualified candidates
(`st-two-pin-adoption-two-pins-one-make`) for a human to accept or edit; it never applies them.

## Whole, or nothing

Every write is staged in memory and committed to disk in one pass, after every collision is
resolved and every ref rewrite is provably resolvable. A migration that stops halfway leaves a tree
where neither the old resolvers nor the new ones work, which is worse than not starting — and
`pm move`'s *"whole, or not at all"* is the same instinct at one-hundredth the scale.

It is **idempotent**: a second run finds a migrated tree and says so, exit 0, writing nothing. It
**reports every file it moved and every ref it rewrote**, because the diff is large and a human
must be able to audit it. Git is the undo — one commit, revertible — so the verb never writes a
backup of its own.

## Ship criterion

`pm migrate` reads a nested tree, and either writes the pooled one in a single pass or writes
nothing and names why. Collisions are reported with every grain that shares a slug and are never
auto-resolved; `--suggest` prints candidates and applies none. `order` is built from the `NN-`
prefixes, `pm:execution` blocks and `phase:` values being retired. Every inbound ref is rewritten
and a ref that cannot be is a refusal naming it. A second run is a no-op that says so. The run
reports every move and every rewrite.

## Proof budget

  cases: 5-6
  tier: integration (shell) — this is a process over a real tree; a unit case cannot prove a
    single-pass write
  lands in: a new migration module beside `test_replay_migration.py`, over vendored fixture trees
  what already covers this: nothing. The fixtures are the cost here, not the assertions — one
    nested tree that migrates clean, one with a genuine slug collision, one with a ref that cannot
    be rewritten. The idempotence case re-runs the first fixture.

## Out of scope

Migrating a consumer. This ships the verb; running it is each project's own commit, and NullBound's
is parked behind this milestone shipping.
