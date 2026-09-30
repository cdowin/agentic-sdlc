---
id: ft-the-tree-is-walked-once
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: the tree is walked once
status: building
reviewed: docs/reviews/2026-09-30-1.0.0-walk.md
depends_on: []
consumed_by: []
changelog: `pm validate` and every other tree reader walk each pool once per run: a 2,000-grain tree validates in about a second rather than minutes.
---

# the tree is walked once

Issue: #100. A consumer profiled `pm validate` over 840 grains: 274M function calls; 852 grain
reads fan out to 4,274 inventory lookups, 12,822 `core/walk.py` walks, 47s in `sorted` alone;
~61s wall. `inventory.reading_tree()` exists and scopes one walk per pool, but the validate path
(and likely other readers) looks grains up outside it, so each lookup re-walks every pool.

## Decided (do not re-plan)

- **Every tree reader runs inside one `reading_tree()` scope.** Wrap at the entry points, not
  per call site: the `pm` router for every read verb, `check pm`, `check grain-shape`,
  `check doc` where it reads the tree, `ready-for`, the belts' checks, `dispatch`, `changelog`,
  `ledger report`. A write verb re-reads after its write (the scope must never serve a stale
  index to a reader AFTER a write in the same process: invalidate on every write through
  `core/apply.py` / `frontmatter` writes, or keep writes outside the scope — pick one and hold
  it with a test).
- **Walks are linear.** Find the quadratic path with a profile first (`python -m cProfile`) on
  a synthetic tree, name it in the commit message, and fix it at its layer; a sort that runs per
  lookup moves to once per walk.
- **A timing test that can fail.** Generate a synthetic 2,000-grain pooled tree in a temp dir
  (milestones, features, stories, bugs, decisions; realistic frontmatter) and assert
  `pm validate` and `check pm` each finish under a budget set at about 5x the measured cost on an
  idle laptop, with the measured cost recorded in the test's docstring. It also asserts the walk
  COUNT (a counter on `core/walk.py`'s entry point): at most one walk per pool per process.
  The count is the real guard, since wall time is noisy; the time budget catches a regression
  the count misses. Keep it out of the unit tier if it spawns; if it runs in-process, it may
  sit in unit only if it stays under 2s.
- Report before/after for `pm validate` and `check pm` on this repo's tree and on the synthetic
  one, with call counts from the profile.

## Ship criterion

- `pm validate` over a 2,000-grain synthetic tree walks each pool once and finishes under its
  budget; on this tree it is at least 5x faster than 0.17.0 (or already under 0.5s).
- A reader after a write in the same process sees the write.

## Proof budget

  cases: 2 — the walk-count + budget case, the read-after-write case
  tier: in-process (unit) if under 2s, else integration
  lands in: tests for pm/inventory.py
  what already covers this: nothing counts walks.
