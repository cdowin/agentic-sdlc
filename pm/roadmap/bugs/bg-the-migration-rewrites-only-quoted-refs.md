---
id: bg-the-migration-rewrites-only-quoted-refs
kind: bug
milestone: "ms-a-move-is-an-event"
name: the migration rewrites only QUOTED refs, and 52 refs went UNVERIFIABLE in silence
status: fixed
caught_in: "ms-a-move-is-an-event"
fix_milestone:
caused_by:
---

# the migration rewrites only quoted refs

GitHub issue #7. Migrating a 497-grain consumer tree with `tools/dev/pm_migrate.py` at v0.4.0 left
**52 references** naming grains by their pre-migration id. Zero slug collisions, so the migration
reported success and wrote everything.

`_rewritten()` requires a quote on BOTH sides of the id, so a quoted ref is rewritten and an ordinary
unquoted YAML inline sequence is not:

    depends_on: ["0.90.3.2/power-is-a-resource"]                 rewritten
    consumed_by: [0.90.3.2/power-is-a-resource,0.90.3.2/…]       NOT rewritten
    milestone: [0.90.4]                                          NOT rewritten

52 of them across 41 files, concentrated where the graph is densest.

## Why it is silent, and why that is the real defect

An unrewritten ref still names a grain that IS in the tree, under an id nothing answers to. So
nothing fails — the ref is counted UNVERIFIABLE, the same bucket as a legitimately retired milestone:

    before migration:  287 refs, 13 UNVERIFIABLE
    after  migration:  287 refs, 49 UNVERIFIABLE
    after  hand-fix:   285 refs, 13 UNVERIFIABLE

The `depends_on` / `consumed_by` graph went decorative for 36 refs and `check pm` exited 0
throughout. **This is rule 4's first cardinal sin — a gate that misses drift and prints PASS — and it
degraded real consumer data.**

## Fix

Match on TOKEN BOUNDARIES, not on quote characters. The id grammar already says what a token is, so
matching whole-token over the value side of a ref line needs no quote and preserves the property the
quote-matching was reaching for (`0.1/alphabet` is not a ref to `0.1/alpha`) by construction.

And the migration must PRINT the UNVERIFIABLE count before and after. It writes whole-or-nothing and
reports every move; the one number that says whether the refs survived is the one it does not print.
Rule 11: the absence of that number is what let this land quietly.
