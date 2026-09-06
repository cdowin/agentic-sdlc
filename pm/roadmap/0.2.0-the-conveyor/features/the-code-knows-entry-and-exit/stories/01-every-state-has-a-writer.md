---
id: 0.2.0/the-code-knows-entry-and-exit/01-every-state-has-a-writer
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: Every declared state is in one category and, past todo, has the step that writes it
status: planning
owner:
depends_on: []
---

# Every declared state is in one category and, past todo, has the step that writes it

## Acceptance criteria

- `devkit.toml` here and the shipped seed declare per-kind states that match what the belts write: story `planning ready building done`; feature adds `reviewing`; milestone `planning ready building reviewing accepted packaging done`; bug `open fixed closed`. `obe` stays in `done` where a kind can hold it.
- `[pm.transitions.<kind>]` names, for every step that writes a state, the state it writes — here and in the seed.
- The config reader refuses at exit 2 a declared state outside `todo` that no declared step writes, naming kind and state.
- Every belt step that writes a state writes the one the table names; the literal leaves `steps.py`.
- `pm vocabulary` prints the table.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | refusal: a state with no writer | amend tests/test_pm_flow.py |
| 2 | unit | the seed parses and every non-todo state has a writer | amend tests/test_fixture_flows.py |
| 3 | unit | a step writes the configured word on a renamed vocabulary | amend tests/test_conveyor_close.py |
| 4 | unit | phase-7 census test extended to conveyor/ | amend the census test |
| 5 | unit | `pm vocabulary` output | amend tests/test_pm_verbs.py |

## Out of scope

Hand moves (`pm story <state>`) stay free — `pm` moves and reports (rule 9).
