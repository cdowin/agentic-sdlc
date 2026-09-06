---
id: 0.2.0/the-code-knows-entry-and-exit/04-open-bugs-are-on-the-conveyor
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: An open bug against the milestone is named before the milestone can be ready
status: planning
owner:
depends_on: []
---

# An open bug against the milestone is named before the milestone can be ready

## Acceptance criteria

- `pm ready-for milestone <id>` names every bug whose `fix_milestone` is `<id>` and whose category is not `done`, as a BLOCKED line, and exits 1.
- `release`'s `features-done` step therefore reports them, and the deviation row names them.
- The bug flow is declared in `[pm.states.bug]` like every kind; `pm bug <state>` is the stamp.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | an open bug blocks; a closed one does not | amend tests/test_pm_ready_for.py |
| 2 | unit | a bug against another milestone is ignored and counted | amend tests/test_pm_ready_for.py |

## Out of scope

A bug belt. Three states, stamped by hand, is the whole flow.
