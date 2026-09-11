---
id: bg-verdict-names-three-unrelated-things
kind: bug
milestone:
name: verdict names three unrelated things, and a reader cannot tell which one a line is about
status: open
caused_by:
changelog: none
---

# verdict names three unrelated things

Found by the 50-module docstring audit in `st-every-module-opens-with-one-true-sentence`, which
could name the defect and not fix it: the story's contract is DOCSTRINGS ONLY with a zero AST
residual, and this fix renames code.

## Symptom

**`verdict` names three things with nothing in common but the word.**

    src/agentic_sdlc/repo/pm/verdict.py   the machine-readable block at the end of a
                                          review record — `verdict: SHIP`, then one row
                                          per finding
    conveyor/driver.Verdicts              a belt run's check results: what `close story`
                                          collected before it decided to write
    conveyor/driver.verdict_row()         the ledger row that records the above
    checks/pm._verdict()                  a GATE's closing PASS/FAIL census line

A reader holding `verdict_row` cannot tell from the name whether it files a review's verdict or a
belt's, and the answer is neither of the two a `pm` user would guess: it is the belt's.

## Root cause

**Three layers each named their own output after the same English word**, at three different times,
and no surface puts the three in one view where the collision would be visible. Every one is
locally reasonable — the review record's keyword really is `verdict:`, a belt really does reach a
verdict, a gate really does print one — which is exactly why nothing caught it. The docstring gate
this milestone added catches a module whose SENTENCE repeats another module's; it cannot see a NAME
used three ways across three packages, and its `PROTECTS` says so.

## Fix

Rename, and the cheapest split is by layer rather than by a new word for all three:
`pm/verdict.py` keeps the name (it is named after the artifact's own keyword, and at 5 imports / 64
qualified refs it is the cheapest of the three to leave alone), and the BELT's pair takes a name
that says whose verdict it is — `driver.CheckResults` / `driver.belt_verdict_row()` or similar.
`checks/pm._verdict()` is module-private and one function; it is the cheapest to rename and the
least confusing to leave.

**Price it before doing it.** `pm/verdict.py` is 5 imports / 64 refs; `conveyor/driver.py` is 23
imports / 175 refs across 10 src and 13 test modules, though only the two names here move, not the
module. The ledger row's `kind` is a SHIPPED key (`rule 6`), so if `verdict_row` writes
`kind: verdict` that string is a consumer contract and the rename stops at the Python name.

## Out of scope

Any other name used twice in this tree. That is a census, and the reader for it does not exist —
`test_boundaries.py::NoNameIsBoundTwice` finds a name bound twice in ONE module, which is a
different question and was the right one for the defect that prompted it.
