---
id: ft-no-ref-dangles-after-a-grain-leaves
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: no ref dangles after a grain leaves
status: building
reviewed: docs/reviews/2026-09-30-1.0.0-dangling.md
depends_on: []
consumed_by: []
changelog: `pm retire` records every id it removes and names each live grain that still depends on one; `validate` and `check pm` count a ref to a retired id as UNVERIFIABLE (retired), not INVALID, and the INVALID text says what was checked; `pm set` and `pm add` on a grain already bound elsewhere MOVE its `order:` entry to the new parent, and unbinding removes it (0.4.0 left it dangling).
---

# no ref dangles after a grain leaves

Issue: #102. A consumer retired 18 finished milestones; 7 live grains kept `depends_on` entries
naming retired grains, and `pm validate` reported 7 INVALID with a wrong parenthetical ("its
milestone IS in the tree"). `pm set <feature> milestone <new>` left the feature in the OLD
milestone's `order:`, so `check pm` failed DANGLING until a hand `pm remove`. Grains removed by
hand left 3 dangling `depends_on`, and the commit hook let the commit through.

## Decided (do not re-plan)

- **`pm retire` records what it removed.** Its `retire` ledger row carries the ids of every grain
  it deleted (the row already carries version, name, why). `validate` and `check pm` treat a
  ref to a RETIRED id as satisfied and census it as UNVERIFIABLE (retired), exactly as a ref into
  a retired milestone is today; never INVALID. A `retire` row written before this change has
  no id list: those refs keep today's behaviour, and the finding names `pm retire --backfill`
  or the equivalent only if such a verb already exists (do not invent one).
- **`pm retire` names the live dependents.** Before it writes, it prints one `noticed:` line per
  live grain whose `depends_on`/`consumed_by` names a grain it will remove (`--dry-run` prints
  them too). It never edits those grains (rule 3: a write touches only what it was asked).
- **The INVALID text is true.** Fix the parenthetical so it says what was checked: whether the
  named id's milestone is in the tree, or that no grain and no retire row knows the id.
- **Re-binding moves the order entry.** `pm set <id> milestone|feature <new>` removes the id from
  the old parent's `order:` and appends it to the new parent's `order:` (the `pm add` sequencing
  primitive, reused), printing both moves. Unbinding (empty value) removes it from the old
  order only.
- **A dangling ref FAILS the gate the hooks run.** `check pm` (inside `make check`) fails on a
  `depends_on`/`consumed_by` naming an id that no grain and no retire row knows — the same rule
  `validate` applies. If `check pm` already runs validate's ref rules, find why the consumer's
  hook passed and fix that instead. Prove: delete a depended-on grain by hand, `make check`
  exits 1 naming the dependent and the missing id.

## Ship criterion

- Retire a milestone whose grain a live grain depends on: retire prints the dependent; after it,
  `validate` and `check pm` pass, the ref counted UNVERIFIABLE (retired).
- `pm set ft-x milestone ms-b` leaves `ft-x` in `ms-b`'s order and not in the old one's.
- A hand-deleted depended-on grain fails `make check` by name.

## Proof budget

  cases: ~4 — retire census + dependents line, validate on a retired ref, re-bind order move, hand-delete fails check pm
  tier: temp tree, in-process (unit) where possible
  lands in: tests for pm retire, validate, pm set, checks/pm.py
  what already covers this: retire and validate cases for retired MILESTONE refs; nothing for grain ids.
