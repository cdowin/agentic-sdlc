---
id: 0.3.0/the-ledger-binds-to-the-current-release
milestone: "0.3.0"
name: The ledger belongs to the current release, not to the one in-progress milestone
status: done
reviewed: docs/reviews/0.3.0-the-ledger-binds-to-the-current-release.md
phase:
depends_on: ["0.3.0/the-order-is-declared-and-appended"]
consumed_by: []
---

# The ledger belongs to the current release, not to the one in-progress milestone

Every gate run in this repo, during the whole of the 0.3.0/0.4.0 design work, printed:

```
gdk-gate: the recorder exited 1: [pm] REFUSED — no milestone in pm/roadmap is in
progress, so there is no ledger this gate row belongs to; no row was written
```

The ledger binds to **the one milestone whose status is in `in_progress`**, and refuses on none or
several. That is a reasonable rule for a tree with one milestone open at a time, and this tree
spent a week with none — planning two milestones, gates green, and **every cost row silently
dropped.** The refusal is well written and it is on the wrong axis: gate cost is a fact about a
RUN, and the run happened whether or not somebody had flipped a status.

It gets worse rather than better under what this milestone and the next one build. Milestones
become cheap to open, split and merge, so "exactly one in progress" is a stronger constraint than
the model wants — and `0.3.0/bugs/the-first-milestone-never-closed` is a live example of the tree
being at rest in a state this rule cannot serve.

**`order` plus `version_at` already answer it, and always with exactly one.** The current release
is the first entry in `order` that has not shipped (or the last that has, under `version_at =
"ship"`) — by construction, never zero and never several, independent of anyone's status field.
The ledger binds there.

`pm/roadmap/ledgers/<version>.jsonl` is where 0.4.0 puts the file; until the pools land it stays
where it is, addressed by the release rather than by a status.

## Ship criterion

A gate cost row is filed against the current release resolved from `order` and `version_at`, and
never refused for want of an in-progress milestone. A tree with no `order` yet still refuses, with
a message naming `pm order` — the one honest reason left. `check budget` and `verify --plan` read
the same file by the same resolution, so the number a human sees and the number the gate grades
cannot disagree.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: the ledger module's test, beside the existing refusal cases
  what already covers this: the none / several / exactly-one refusals are covered and become
    cases about `order` instead — they change what they resolve THROUGH, not what they assert. New:
    a tree with milestones at rest and a valid `order` files a row, which is the bug.

## Out of scope

Where the file sits. The pools move it in 0.4.0; this feature changes what it is keyed by.
