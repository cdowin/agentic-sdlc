---
id: 0.2.0/the-code-knows-entry-and-exit/02-ready-is-a-stamp-with-a-check
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: ready is one command, and an empty ready is a warning
status: building
owner:
depends_on: []
---

# ready is one command, and an empty ready is a warning

## Acceptance criteria

- **Chris, 2026-09-05:** *"Nothing fancy and automatic. If I want a feature to go in progress, I move it. One CLI command."* The stamp for `ready` is the command that already exists — `pm story|feature|milestone ready <id>` — and nothing else writes it.
- What leaving `todo` MEANS is a warning, not a gate: `check pm` prints `  WARN  ` naming a story that has left `todo` (its status is in the `in_progress` or `done` category, under whatever words the project declared) whose `## Acceptance criteria` is empty, a feature that has left `todo` with no stories or an empty `## Ship criterion`, a milestone that has left `todo` with a feature carrying no `phase:` or with no `branch:`. Asked of the category only — the order of words within `todo` is the project's presentation and changes no count. Exit code unaffected.
- The three sections it reads are the ones `pm new` scaffolds; nothing new is parsed.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | each WARN fires on the scaffold and is silent on a filled grain; exit 0 either way | amend tests/test_pm_gate.py |
| 2 | unit | a grain in either `todo` word is not asked; swapping the two `todo` words changes no WARN count (`test_left_todo_is_the_category_not_the_order_within_it`) | amend tests/test_pm_gate.py |

## Out of scope

A `plan` belt, a readiness verb, anything that stamps `ready` for you. One command, by hand.
