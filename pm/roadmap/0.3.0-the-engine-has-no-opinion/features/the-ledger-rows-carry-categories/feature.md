---
id: 0.3.0/the-ledger-rows-carry-categories
milestone: "0.3.0"
name: A renamed vocabulary does not silently empty the ledger
status: planning
reviewed:
phase: 1
depends_on: []
consumed_by: []
risk: high
size: m
---

# A renamed vocabulary does not silently empty the ledger

**The biggest thing 0.3.0 did not know it contained**, found by the plan review.

`pm/cli.py:1524-1557` builds the dispatch snapshot with FROZEN KEYS matched against the literals
`building` and `reviewing`. Its own docstring already says what that costs:

> *"a project with a genuinely renamed vocabulary records empty lists."*

`report.py:104-112` consumes them.

## Why this is not the same job as the rest of 0.3.0

Every other item in the inference census is a **rendering** or a **predicate** — change the code
and the next run is right. **These keys are inside JSONL rows already written, in every consumer
tree, and rows are never rewritten.** `pm ledger report`'s `reopens` column already prints `-`
for a story whose rows predate a migration; that is the shape of the problem and the precedent
for an answer.

So it is a data question with three candidate answers, and the milestone must pick one in
writing: rows carry a category alongside the state from now on; the reader maps old rows through
the CURRENT declaration and says where it could not; or old rows are read as-is and the report
discloses the boundary. **Milestone criterion 6 covers dwell-column RENDERING and reaches none of
this.**

## Ship criterion

1. The snapshot keys come from categories, not from two literals.
2. **A row written before the migration is readable, or is disclosed as unreadable** — never
   silently counted as empty. Rule 4 over a data format rather than over a file census.
3. The chosen answer is a `pm decide` entry with the two rejected.
