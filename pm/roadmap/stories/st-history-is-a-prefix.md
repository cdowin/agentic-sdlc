---
id: st-history-is-a-prefix
feature: ft-the-plan-and-the-tree-agree
milestone: "ms-0.3.0"
name: R3 R4 and R6 hold the plan to the tree
status: done
owner:
depends_on: ["st-the-unbound-family"]
kind: story
---

# R3 R4 and R6 hold the plan to the tree

R6 is why this milestone exists: nothing in the package could relate a milestone
to a RELEASE, so a milestone whose work shipped under someone else's version was
invisible to every rule.

## Acceptance criteria

1. R3 — two milestones claiming one `version:` is a finding naming both; which
   ships must never be decided by a directory NAME.
2. R4 — history is a prefix: a shipped release sitting after an unshipped one is
   a finding naming the pair. This is what makes "next = the first unshipped
   entry" correct rather than merely usual.
3. R6 — a release behind the last shipped one whose milestone never closed, and
   a `done` milestone whose version is on no plan. Both directions.
4. **R4 and R6 fire on this repo's own tree on their first run**, against
   `0.3.0/bugs/the-first-milestone-never-closed`.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_r3_refuses_to_let_a_directory_name_decide_which_release_ships` | new |
| 2 | unit | `test_r4_history_is_a_prefix` | new |
| 3 | unit | `test_r6_catches_the_first_milestone_never_closed_in_both_directions` | new — two directions in one case, per the budget |
| — | unit | `test_a_healthy_plan_passes_every_rule_in_the_family` | the other side of all five |

Criterion 4 was measured, not asserted: enabling the family on this tree
reported both R4 and R6 against 0.1.0 before the bug was fixed, and PASS after.

## Out of scope

R5, which is `a-milestone-declares-its-version`.

## Close

done: fd1ea13 — R3/R4/R6 land, and both fired on this tree's own 0.1.0 before
the record was closed. The bug is fixed by the rule that found it.
