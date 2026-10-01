---
id: st-pm-decide-counts-condensed-decisions
kind: story
feature: ft-a-decision-id-is-never-reused
milestone: "ms-the-open-issues-close"
name: pm decide counts pointer lines and ledger rows, not only headings
status: done
owner:
depends_on: []
changelog: pm decide numbers the next decision past every D-id the log or the ledger already holds, so a condensed log never gets D1 again.
---

# pm decide counts pointer lines and ledger rows, not only headings

https://github.com/cdowin/agentic-sdlc/issues/110. A duplicate id breaks every citation (rule 4).

## Acceptance criteria

1. `pm/inventory.py::next_entry_id` takes the max over `## D<n>` headings, `- D<n> —` pointer
   lines, and the ledger's `decision` rows for that grain.
2. A log condensed to pointers D1-D7 gets D8 next.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_pm_verbs.py (or the decide test module): a pointer-only log | new |
