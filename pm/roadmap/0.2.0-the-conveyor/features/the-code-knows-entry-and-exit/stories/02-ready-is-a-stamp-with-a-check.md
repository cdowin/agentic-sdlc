---
id: 0.2.0/the-code-knows-entry-and-exit/02-ready-is-a-stamp-with-a-check
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: ready is stamped by a plan belt with a check behind it, at every level
status: planning
owner:
depends_on: []
---

# ready is stamped by a plan belt with a check behind it, at every level

## Acceptance criteria

- `agentic-sdlc plan story <id>` walks: `scaffolded` → `criteria-written` (a non-empty `## Acceptance criteria`) → `proof-named` (a filled row in `## How this is proven`) → `story-ready`.
- `plan feature <id>`: `scaffolded` → `criterion-written` → `stories-decomposed` (at least one story) → `feature-ready`.
- `plan milestone <id>`: `scaffolded` → `criterion-written` → `features-phased` (every feature carries `phase:`) → `branch-stamped` → `milestone-ready`.
- Every step reports and the walk finishes (D8); the `*-ready` step writes the state `[pm.transitions.<kind>]` names.
- `install-sdlc` renders the three lists; `pm vocabulary` publishes the step names.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | a fresh scaffold: every step not true, each named | amend tests/test_conveyor_close.py |
| 2 | unit | a filled grain stamps the declared ready state | amend tests/test_conveyor_close.py |
| 3 | unit | rendered protocol carries the lists | amend tests/test_install_sdlc.py |

## Out of scope

Judging whether the criteria are any good — that is the reviewer's, never a step's (rule 9).
