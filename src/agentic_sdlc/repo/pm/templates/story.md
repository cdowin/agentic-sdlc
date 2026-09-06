---
id: {id}
feature: {feature}
milestone: "{milestone}"
name: {name}
status: planning
owner:
depends_on: []
---

# {name}

<!-- What is observable when this ships. A story is an observation, not a task. -->

## Acceptance criteria

<!-- What must be TRUE. One line each, and each one able to fail. -->

## How this is proven

<!-- ONE ROW PER CRITERION ABOVE, and the suite IS this table.

     A criterion says what must be true; it does not say what demonstrates it.
     That gap is where a test suite grows without anyone deciding to grow it:
     a builder proving a criterion writes as many cases as feels safe, each
     cheap on its own, expensive only in aggregate, and nothing downstream ever
     asks how many. Measured once, in this package: 7,241 executable statements
     of source against 13,023 of tests, and one test function per 4.9
     statements of source.

     `existing?` IS THE COLUMN THAT DOES THE WORK. Before a new test is
     written, say which test already covers this — or which one could be
     AMENDED to. A new case is warranted only when neither answer exists, and
     "I could not find one" is an answer that has to have been looked for.

     TIER is `unit` (no subprocess, no git, no make) or `integration`. Default
     to unit; hard rule 10 is why. Reaching for integration is a claim that the
     thing under test IS a process, and it is a claim the review will read.

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 |  |  |  |
-->

## Out of scope
