---
id: bg-the-telemetry-verb-cannot-compare-two-milestones
kind: bug
milestone: ms-nothing-is-hand-rolled
name: ledger report takes one grain, and every telemetry question asked of it is comparative
status: fixed
caused_by:
changelog: `pm ledger report` takes more than one milestone id and compares them: every block gets one row per milestone and a `delta` row (`last - first`), marked `*` where the census under it moved, and `--json` becomes one joined document instead of a nested report per milestone.
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

## Fixed

`8ffcbeb` — `pm ledger report <a> <b> [<c> …]` compares them. Each of NINE blocks gets one
row per milestone and a `delta` row — `last - first`, the milestones between
printed and not differenced, exactly as a gate's middle runs are — with `*` on
a delta whose census moved underneath. No new measurement: every number is
lifted out of a document `report.build` already returned, so the comparison is
N reports and an arithmetic.

`--json` under more than one id is ONE JOINED DOCUMENT, and the shape is
written down in `report.compare_data`'s docstring, in `pm --help`, in
`.claude/rules/pm-execution.md` and in `README.md`:
`{"milestones": [<id>…], "order": "plan"|"given", "blocks": [{"block",
"columns", "census", "moved", "note", "rows", "delta"}]}`. A nested report per
milestone was the thing a caller should not have to join, so it is not what
they get. ONE id still prints the nested document.

Order is READ, never chosen: the plan's `order` sequences the ids the caller
named when it holds every one of them, otherwise the argument order stands,
and the heading says `plan` or `given` rather than leaving the basis to be
guessed at. Refused at exit 2, nothing written: an id resolving to nothing (the
shared resolver's own sentence), a feature or story id beside another id, one
id named twice, `--from` beside more than one.

### What the brief got wrong

  * **It asked for two shapes at once** — *"one row per milestone plus a delta
    column"* and *"the shape worth copying is `gate cost`'s: first, last,
    delta"*. Those are transposes of each other and only one can ship. Rows are
    milestones and the delta is a ROW, because that keeps a block's column
    count the same whether two ids are named or five: a column per milestone
    would make column 4 a different measure per invocation, which is rule 6's
    line shapes moving under a consumer for a table nobody could pipe.
  * **`gate cost` is the wrong section to compare and the right one to copy.**
    Its own note already says a gate row names no grain and lands in the tree's
    ledger, so every milestone reads the SAME gate rows: its delta is 0 by
    construction and says nothing about either milestone. `rows naming no
    grain` is the same. Both are printed rather than omitted — silence would
    read as "not measured" — each carrying a line saying the rows are the
    tree's. A comparison that had printed a clean `+0` there would have been
    rule 4's first sin with a straight face.
  * **`spend per grain`'s totals are about the FILE, not the milestone.**
    `spend_data` folds every dispatch row in before any narrowing, the tree's
    grainless ones included. Each row therefore carries a tree-wide component
    and only the DELTA cancels it. Said in `_compare_spend`'s docstring; not
    changed, because changing it would move the summary line rule 6 protects.

### A note the numbers contradicted, found by running it

The first landing gave BOTH tree-wide blocks the same note — *"the same rows under every
milestone… this delta is 0 by construction"*. True of `gate cost`, whose rows carry no `tree`
snapshot; **false of `rows naming no grain`, whose rows do**: `named_grains` bills a grainless
dispatch row to the single story in progress when it was filed, so the row leaves that bucket
under that story's milestone and stays in it under every other. Run against this repo's own
ledgers the block printed `dispatches -1` with *"0 by construction"* underneath — nine grainless
rows reading 9 under 0.6.0's milestone and 8 under 0.7.0's.

**Rule 4's first sin in prose, and the arithmetic was right the whole time.** The fix is the
sentence: a second note says what is true of that block, and the claim is GATED rather than
re-read — a note promising a zero delta must deliver one. Probed both ways, the shipped note
restored and the population blinded.

### How this is proven

| claim | case |
|---|---|
| the whole compared report, byte for byte, clock frozen | `tests/test_pm_ledger_report_sections.py::TestTwoMilestonesSideBySide::test_two_ids_print_this_exact_table` |
| `--json` is one joined document, not a report per milestone | `…::test_the_json_is_one_joined_document_and_not_two_reports` |
| the plan sequences what it holds; otherwise the caller's order stands | `…::test_the_plan_sequences_the_ids_it_holds_and_says_so`, `…::test_an_id_the_plan_does_not_hold_leaves_the_order_given` |
| a milestone with no ledger says so under the heading | `…::test_a_milestone_with_no_ledger_of_its_own_says_so` |
| the refusal matrix — 5 inputs, each exit 2 with nothing written | `…::test_every_refusal_exits_2_and_names_what_it_refused` |
| the compared form writes nothing, over every byte in the tree | `…::test_the_report_never_writes` (amended) |
| the form is named in `--help` AND in the rule that auto-loads | `tests/test_cli_surface.py::TestTheSurfaceSaysTelemetry::test_the_help_and_the_auto_loaded_rule_name_the_COMPARISON` |
| a note claiming a zero delta sits only where the delta IS zero | `…::test_a_note_claiming_a_zero_delta_sits_only_where_the_delta_is_zero` |

**A single id prints byte-identical output**, measured rather than asserted:
twelve invocations (bare, `--json`, a story id, a feature id, three milestone
ids in both modes, and a bad id) run against this repo's own `pm/` tree frozen
at HEAD, with the clock frozen rather than masked — `report._now` and
`ledger.open_seconds`'s default `now`, the only two wall-clock reads on this
path — under HEAD's source and under this change. Twelve of twelve sha256
matched; `pm ledger report` bare is
`68255ee9edc2ce0cdcba7feb93639e8b482d9720420b8ace838589cb223f2104` both sides.
