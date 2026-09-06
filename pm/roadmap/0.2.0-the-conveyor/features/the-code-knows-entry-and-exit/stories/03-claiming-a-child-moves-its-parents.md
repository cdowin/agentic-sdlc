---
id: 0.2.0/the-code-knows-entry-and-exit/03-claiming-a-child-moves-its-parents
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: A parent behind its child is a warning, not a finding, and nothing moves it
status: planning
owner:
depends_on: []
---

# A parent behind its child is a warning, not a finding, and nothing moves it

## Acceptance criteria

- **Chris, 2026-09-05:** *"If I do a check on a feature and it shows to-do and a story in progress, that's a warn. Not a fail, no action, just messaging."*
- Every cross-level disagreement `check pm` reports is a `  WARN  ` line, never `  DRIFT  `, and never moves the exit code: D5 (a child at work, its parent in `todo`), D2 (every story done, the feature not advanced), D6 (every feature done, the milestone not advanced), D3 (the milestone done, a feature not). The line names both grains and both categories.
- The summary line counts warnings separately from findings: `[check:pm] PASS — … 3 warning(s)`.
- No verb moves a parent on a child's account. `close story`'s `claimed` step touches the story and nothing else; that is asserted.
- The rules that stay findings are facts about the INPUT (rule 9): D1 a dangling record, D4 a state outside the declared set, D8/D9/D10 the branch flow, V1–V6 integrity.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | each of D2/D3/D5/D6 prints WARN and exits 0; D1/D4 still DRIFT and exit 1 | amend tests/test_pm_gate.py |
| 2 | unit | claimed writes the story and nothing else | amend tests/test_conveyor_close.py |

## Out of scope

Any automatic move. Any rule that decides what a disagreement means.
