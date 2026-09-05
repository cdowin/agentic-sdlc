---
id: 0.2.0/the-ledger-rows-carry-categories
milestone: "0.2.0"
name: A renamed vocabulary does not silently empty the ledger
status: planning
reviewed:
phase: 8
depends_on: ["0.2.0/every-question-is-asked-of-a-category"]
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

## The ruling comes BEFORE the sizing — plan audit Q7

This feature is `size: m` and it is the plan's largest single risk. It cannot be sized until the
answer is picked, because the two live answers have different sizes:

| answer | what it costs |
|---|---|
| **migrate** | the keys become category names, and a reader understands two shapes forever — or a one-shot rewrite verb exists and every consumer runs it. Hard rule 8 says this package cannot run it in somebody else's repo. |
| **keep and extend** | the frozen keys stay, category keys land beside them, old readers keep working, and the milestone ships with a named, dated, documented opinion in one telemetry row |

**Recommended: keep and extend**, with the frozen keys marked deprecated in the row shape and
removed at the next major. The row is telemetry, not the engine. A reader that must understand two
shapes forever is a worse outcome than one deprecated key with a removal date, and it is the same
posture the 0.24.0 deprecation window took.

**Chris's call, and it is criterion 0.** Nothing here is scoped until it is a `pm decide` entry.

## Ship criterion

0. **The answer is a `pm decide` entry with the rejected alternative recorded, before any story is
   written.** The size above is provisional until then.
1. The snapshot keys come from categories, not from two literals.
2. **A row written before the migration is readable, or is disclosed as unreadable** — never
   silently counted as empty. Rule 4 over a data format rather than over a file census.
3. `pm ledger report`'s dwell columns are per CATEGORY, so a twelve-state project gets three
   columns and not twelve.
4. A test reads a ledger fixture written under the OLD key shape and asserts the report says what
   it could not attribute — vendored here, per hard rule 8.
