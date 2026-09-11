---
id: bg-the-telemetry-verb-cannot-compare-two-milestones
kind: bug
milestone: 
name: ledger report takes one grain, and every telemetry question asked of it is comparative
status: open
caused_by:
changelog: none
---

# the telemetry verb cannot compare two milestones

## Symptom

`pm ledger report [<grain-id>]` takes ONE grain and reports the clock at that
level. Every telemetry question actually asked of this tree is comparative:

    where are we with telemetry for this milestone?
    compared to the previous?
    how are we improving?

All three need two or more milestones side by side, and no invocation produces
that. `--from <rev>` reads one milestone at an older rev — a different axis, and
the one that exists.

So the answer is assembled by hand: six invocations, or a loop over `--json`
joined by a script. Measured: answering those three questions took six
hand-rolled Python censuses over the raw `.jsonl`, and two of them reproduced
sections the report already has
(`bg-a-read-verb-names-three-of-its-thirteen-sections`). **The remaining four
were this absence.**

## Why the shell is not the answer here, which is the interesting part

Rule 11's read side says composition is the shell's job and *"if you cannot pipe
it the missing thing is a COLUMN, never a verb."* That rule holds for `pm list`,
whose rows are flat and tab-separated.

It does not reach this. `ledger report` emits thirteen SECTIONS with different
column sets, and `--json` emits one nested document per milestone. Comparing two
means joining two nested documents on matching section keys — `jq` work, not
`awk` work — and the numbers that matter are DERIVED across the pair (a delta, a
ratio, a per-case cost), not selected from either. The gate-cost section already
proves the shape is wanted: it computes `first_ms`, `last_ms` and `delta_ms`
within one milestone because a bare pair of numbers was not the answer.

**So the missing thing is neither a column nor a pipeline.** It is the same
arithmetic the `gate cost` section already does, applied across grains instead
of within one.

## Fix, and the cheapest layer is an argument rather than a flag

`ledger report` already resolves an id to a LEVEL. Accepting more than one id,
and emitting each section with one row per milestone plus a delta column, needs
no new section and no new measurement — the rows are already routed by grain and
the aggregation already exists per milestone.

The shape worth copying is `gate cost`'s: first, last, delta, and a `*` when the
thing being compared moved underneath.

## What must NOT be inferred

Which milestones to compare. `releases.md` `order:` declares the sequence, so
"the previous one" is a question the tree can answer — but rule 9 says the tool
reads what the project declared and does not decide what it should do. The ids
are the caller's to name; ordering them by the plan is reading.

## Out of scope

A trend across every milestone as a default. Six milestones of thirteen sections
is a wall, not a report, and nobody asked for all of it at once.

Cost-per-case or any other ratio as a new measurement. The inputs are in the
rows already; what is missing is putting two milestones beside each other.
