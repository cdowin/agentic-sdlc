---
id: 0.2.0/the-code-knows-entry-and-exit/03-claiming-a-child-moves-its-parents
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: Claiming the first story moves its feature and milestone to work
status: planning
owner:
depends_on: []
---

# Claiming the first story moves its feature and milestone to work

## Acceptance criteria

- `close story`'s `claimed` step, having moved the story, moves each parent whose category is `todo` to the state `[pm.transitions.feature|milestone] parents-at-work` names, and says so.
- A parent already `in_progress` or `done` is left alone and named.
- On a tree driven only by belts, `check pm` D5 has nothing to report.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | parents at planning move; parents at work do not | amend tests/test_conveyor_close.py |
| 2 | unit | D5 clean after a belt-driven claim | amend tests/test_pm_gate.py |

## Out of scope

Moving parents DOWN. Nothing here reopens anything.
