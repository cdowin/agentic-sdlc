---
id: st-the-tree-migrates-in-one-pass-or-not-at-all
feature: ft-the-migration-is-whole-or-nothing
milestone: "ms-0.4.0"
name: pm migrate writes the pooled tree whole, or writes nothing and says why
status: building
owner: claude
depends_on: ["st-order-sequences-every-container"]
kind: story
---

# pm migrate writes the pooled tree whole, or writes nothing and says why
`pm migrate` reads a nested tree and either writes the pooled one in a single pass or writes
nothing and names why. **The only feature in this milestone that touches an existing tree**, and
the riskiest work in it.

The seven steps are in the feature file. What this story adds is the bar: every write is staged in
memory and committed in one pass, after every collision is resolved and every ref rewrite is
provably resolvable. A migration that stops halfway leaves a tree where neither the old resolvers
nor the new ones work, which is worse than not starting.

## Acceptance criteria

1. **One pass or none.** A tree that cannot be migrated whole is left byte-identical, and the run
   names what stopped it. Proven by `porcelain` being empty after a refusal, not by an exit code.
2. **Collisions are reported with every grain that shares a slug, and never auto-resolved** (D4).
   An auto-picked id is a name nobody chose, in the one field that is stable for life and cited
   from commit messages. `--suggest` PRINTS parent-qualified candidates
   (`st-two-pin-adoption-two-pins-one-make`) and applies none.
3. Resolution is `pm rename` (`0.4.0/binding-is-a-field/02`), CALLED, not duplicated — the sweep is
   the same problem stated once, and the migration's advice is a command rather than a paragraph.
4. `order` is built from the `NN-` prefixes, `<!-- pm:execution -->` blocks and `phase:` values
   being retired. They are the migration's INPUT: read once to produce sequence, then removed.
   `phase:` flattens in phase reading order.
5. **Every inbound ref is rewritten**; one that cannot be is a refusal naming it.
6. **Idempotent**: a second run finds a migrated tree, says so, exits 0, writes nothing.
7. It reports every file it moved and every ref it rewrote. The diff is large and a human has to be
   able to audit it. **Git is the undo** — one commit, revertible — so the verb writes no backup of
   its own.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 4, 5, 7 | integration | a vendored nested fixture tree that migrates clean | new — this is a process over a real tree; a unit case cannot prove a single-pass write |
| 2 | integration | a fixture with a genuine slug collision; assert the report and `porcelain` empty | new |
| 1, 5 | integration | a fixture with a ref that cannot be rewritten | new |
| 6 | integration | re-run the first fixture | new |

The fixtures are the cost here, not the assertions. They live beside
`tests/test_replay_migration.py`.

## Out of scope

Migrating a consumer. This ships the verb; running it is each project's own commit, and NullBound's
is parked behind this milestone shipping.
