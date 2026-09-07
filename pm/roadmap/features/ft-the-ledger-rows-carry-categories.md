---
id: ft-the-ledger-rows-carry-categories
milestone: ms-0.2.0
name: A renamed vocabulary does not silently empty the ledger
status: done
reviewed: docs/reviews/2026-09-05-the-ledger-rows-carry-categories.md
phase: 8
depends_on: ["ft-every-question-is-asked-of-a-category"]
consumed_by: []
risk: high
size: m
kind: feature
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

## The ruling comes BEFORE the sizing — plan audit Q7

This feature is `size: m` and it is the plan's largest single risk. It cannot be sized until the
answer is picked, because the two live answers have different sizes:

| answer | what it costs |
|---|---|
| **migrate** | the keys become category names, and a reader understands two shapes forever — or a one-shot rewrite verb exists and every consumer runs it. Hard rule 8 says this package cannot run it in somebody else's repo. |
| **keep and extend** | the frozen keys stay, category keys land beside them, old readers keep working, and the milestone ships with a named, dated, documented opinion in one telemetry row |

**RULED 2026-09-05 — keep and extend.** Chris: *"Keep and extend."* The frozen keys stay, category
keys land beside them, old rows stay readable by old readers, and the frozen keys are deprecated in
the row shape with removal at the next major — the posture the 0.24.0 deprecation window took. D7
carries both rejected alternatives.

The milestone that exists to remove hardcoded state opinions therefore ships one, in a telemetry
row, dated and deprecated. That is the honest version of the trade: the row is telemetry, and every
question the ENGINE asks is a category after phase 7.

## Ship criterion
1. Every dispatch snapshot row carries **category keys alongside** the frozen `stories_wip` /
   `features_review` ones, and the frozen pair is marked deprecated where the row shape is
   documented — never silently kept.
2. **A row written before the migration is readable, or is disclosed as unreadable** — never
   silently counted as empty. Rule 4 over a data format rather than over a file census.
3. `pm ledger report`'s dwell columns are per CATEGORY, so a twelve-state project gets three
   columns and not twelve.
4. A test reads a ledger fixture written under the OLD key shape and asserts the report says what
   it could not attribute — vendored here, per hard rule 8.
