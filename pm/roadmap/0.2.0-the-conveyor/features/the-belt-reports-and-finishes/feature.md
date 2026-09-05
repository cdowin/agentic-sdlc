---
id: 0.2.0/the-belt-reports-and-finishes
milestone: "0.2.0"
name: Every step is a check, every check reports, and the walk always finishes
status: planning
reviewed:
phase: 5
depends_on: []
consumed_by: ["0.2.0/the-inner-levels-are-belts-too"]
risk: medium
size: m
labels: ["conveyor", "sdlc", "subtraction"]
---

# Every step is a check, every check reports, and the walk always finishes

**Chris, 2026-09-05:**

> *"I don't understand tree vs input. Everything is just a check. `release` should release on a red
> tree if I want (we mostly wouldn't but why stop someone?)"*

**That ruling — D8 — made this feature smaller than it was written to be.** The design had an edge
between facts about the INPUT (refuse) and facts about the TREE (report), and the 0.3.0 plan review
sized the work as *"re-rule 14 halting steps, one at a time, under that edge"*, with the red-gate
case called out as genuinely ambiguous.

**There is no edge, because those are not two kinds of step outcome — they are two moments.**

| moment | answer |
|---|---|
| **before the walk** — the engine cannot READ its declaration: malformed id, unknown step, config of the wrong shape | **exit 2, nothing walks.** `validate_config`, `plan_defect`, `subject_defect` already do this. |
| **during the walk** — a step's `check()` answered | **it is a check. It reports.** No taxonomy, no exceptions. |

So there is nothing to re-rule. A red `make gates` reports red and the walk continues to `tag`.

## What changes in the machine, and it is subtraction

`driver.py`'s `_walk` today returns `Result(..., stopped_at=name, 1)` at the first step that is not
true. It stops recording, stops printing, and the seven steps a release most needs to resume into
are unreachable (R1).

**It stops returning early.** It records every answer, prints every line, walks to the end, and
returns a scoreboard. Exit codes keep hard rule 6 exactly:

```
[release:tree-clean]  GATE ALREADY-TRUE — no modified paths
[release:gate]        GATE NOT-TRUE — 12 failures
[release:ci-green]    JUDGEMENT UNVERIFIABLE — no artifact, no command
[release:tag]         AUTOMATIC DONE — tagged v0.2.0
[release] 19/21 true, 1 not true, 1 unverifiable — `gate`, `ci-green`
```

`Truth.UNVERIFIABLE` **stays**. It is not "no", it is "this cannot be decided", and collapsing it
into either one is how a machine prints PASS over a question nobody answered. It stops halting; it
does not stop being distinct.

## What is NOT lost

**The 0.24.0 lesson survives.** That release ran its gate before its reviewer because nobody knew
the ORDER — not because a machine permitted it. The order was always the deliverable; refusal was
belt-and-braces on top.

**`check pm` is untouched.** It is the gate: it FAILS a contradictory tree, in CI and pre-push,
with an exit-code contract for exactly that. `pm` moves and reports; `check` gates. Conflating them
is how the conveyor inherited a job it should never have had.

## Scope

| thing | action |
|---|---|
| `_walk`'s early return | **deleted.** Accumulate, continue, return a scoreboard. |
| the final line | counts true / not-true / unverifiable and **names** the not-true steps |
| `--skip <step> --reason` | **goes.** It exists to escape a refusal; with nothing to escape it is ceremony. The ledger row was the honest half and it becomes what a not-true step records. |
| `Truth`, `StepKind`, `do()`-never-decides, the run-state cache | **keep, unchanged.** |
| `pm ready-for` | a READ verb. Its exit code is information for a caller that wants it. |
| `check pm` | untouched. |
| **R1 + R2** | see below — they are one finding and they close here |

## R1 and R2 are one finding, and the halt was never the whole defect

Removing the halt changes what a false postcondition COSTS. It does not make it true.

`findings-resolved` (step 14, `steps.py:1166-1192`) requires every review record for the milestone
to be **deleted**. `review-landed` and `features-done` require the `reviewed:` pointer to resolve.
Under D8 the run no longer deadlocks — it walks past both and finishes — and it still instructs the
operator to delete a record that leaves `check pm` **permanently RED on D1**, a gate in
`[checks] all`.

R2 arrives at the same place from the other side: the step decides by matching a version SUBSTRING
rather than reading the `reviewed:` pointers. **One fix:** `findings-resolved` reads each pointed-at
record's dispositions and is true when every finding is at a disposition other than `open` — which
is what `pm ready-for tag` already computes.

## Ship criterion

1. **No step halts the walk.** Every step is asked, every answer is recorded and printed, and the
   run reaches its last step regardless of what any check said.
2. The final line is a **scoreboard**: counts of true / not-true / unverifiable, and the names of
   every step that is not true. A caller reading one line knows whether to look.
3. Exit codes, per hard rule 6: **0** every postcondition holds, **1** one or more do not, **2** the
   declaration could not be read. A test asserts a release over a red `make gates` reaches `tag`
   and exits 1.
4. `check pm` is unchanged and still fails a contradictory tree. **A test asserts the belt and the
   gate disagree** — the belt moved it, the gate reports it, and that is correct.
5. `--skip` is gone from the CLI, the docs and the ledger's row vocabulary; a not-true step writes
   the row `--skip` used to.
6. **R1/R2 close**: `findings-resolved` reads the `reviewed:` pointers' dispositions, never a
   version substring and never a record's absence, and a test asserts that a completed release
   leaves `check pm` GREEN.
7. `pm-execution.md`'s report-never-refuse rule is quoted in the driver's docstring, and the
   docstring's first line stops saying *"a step machine that refuses to advance"*.
8. **The 26 stories parked at `reviewing` are walked through `close story` for real**, and the
   ledger holds their rows. That is I2, and it is the only way criterion 10 gets tested before the
   release itself.

## Risks

1. **A warning nobody reads is worse than a refusal.** Criterion 2 is the whole mitigation and it is
   thin: a 21-step run now prints 21 lines where it used to print 5. Make the scoreboard good.
2. **The temptation on the next incident will be to add a halt back for one special case.** That is
   how this got built the first time. The one-line test: *is the engine reading what the project
   declared, or deciding what the project should do?*
3. **Criterion 3's red-gate test is the one that will be argued about**, because releasing over a
   red suite reads as reckless. It is the ruling: the gate told you, and you decided. D8.
