---
id: 0.2.0/the-code-knows-entry-and-exit/01-each-kind-declares-its-own-states
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: Each kind declares its own states, and there is no transitions table
status: building
owner:
depends_on: []
---

# Each kind declares its own states, and there is no transitions table

## Acceptance criteria

- `devkit.toml` here and the shipped seed declare per-kind states that match what the belts write: story `planning ready building done`; feature adds `reviewing`; milestone `planning ready building reviewing accepted packaging done`; bug `open fixed closed`. `obe` stays in `done` where a kind can hold it.
- `[pm.transitions.<kind>]` is deleted — the key, its reader, its `pm vocabulary` section and its mention in the seed. A belt writes the FIRST state of its kind's `done` list; nothing else needs a step-to-state table.
- `pm vocabulary` echoes each kind's states with their category and nothing else about flow.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | the seed parses per kind; a leftover transitions key is refused by name | amend tests/test_pm_flow.py |
| 2 | unit | `pm vocabulary` output | amend tests/test_pm_verbs.py |
| — | unit | the `reopens` column is gone: golden table + JSON | amend tests/test_pm_ledger_report_sections.py |
| — | unit | `pm list --kind milestone` prints id/status/category/branch, `--category` filters | amend tests/test_pm_verbs.py (ListFindsTheNail) |
| — | integration | the worktree script bases off the in-progress milestone under a RENAMED status word, and falls back loudly when the CLI cannot answer | amend tests/test_hooks_payloads.py |

## Out of scope

Hand moves (`pm <kind> <state>`) stay free — `pm` moves and reports (rule 9).

## Close

done: 1e01518 c1bffb5 — per-kind states in the seed and here, the transitions table deleted, 26 stories migrated to building, the reopens and after_review columns gone, the worktree script asks the CLI
