---
id: bg-a-gate-compares-a-rendered-clock
kind: bug
milestone: "ms-nothing-is-hand-rolled"
name: a gate compares a rendered clock across two CLI calls and flakes at the second boundary
status: open
caused_by:
changelog: none
---

# a gate compares a rendered clock

Found by a dispatched agent whose first `make test` went red and whose next three went green —
reported rather than retried away, which is the only reason it is written down.

## Symptom

`tests/test_pm_verbs.py::AnArrivalIsTheOneEvent::test_a_declared_answer_is_recorded_as_it_was_typed`
captures the `open:` census line from one `pm feature building` call and asserts the NEXT call
prints the same string. That line carries `, oldest <id> <age>` (`arrive.py:243`), rendered through
`ledger.human_duration` at the moment of the call — so a pair of calls straddling a second boundary
renders `0s` and then `1s`, and the assertion fails on a tree nothing wrote to.

**The verdict is a coin flip whose odds depend on how busy the machine is.** It went red once in
~1,600 cases on a loaded box and green on the three runs after it.

## Root cause

**A gate asserted a rendered STRING where it meant to assert a COUNT.** The test's own comment says
what it is for — *"The census counted the shadow too, and went `1 of 2` -> `2 of 2`"* — and that
claim is about the clauses after the em dash. The age was collateral: it came along because the
whole line was the cheapest thing to compare.

This is rule 4's first sin with the sign flipped. A gate that FAILS at random trains the operator
to re-run it, and an operator who re-runs a gate until it passes is an operator who cannot tell a
flake from a regression. The tool's own rule is already written for the other direction — `pm ledger
report` keeps a running clock in `open_s` and never folds it into a closed total, *"because a running
clock and a finished one are different facts"*. A test that compares two readings of a running clock
is the same mistake one layer up.

## Fix

`_census()` in that class strips the `, oldest <id> <age>` segment before the comparison, so what is
compared is the census the comment describes. Landed with this bug, because a flaky gate in
`make test` — the feature rung and half the milestone gate — blocks every close behind it.

**Not fixed, and deliberately:** the renderer. `arrive.py` is right to print the age, and freezing
the clock for this one assertion would hide the race rather than remove it.

## Out of scope

Any other clock in the suite. This is the one that was WATCHED failing; a sweep for siblings is a
census, and `grep -n "oldest\|human_duration" tests/` is how somebody would start it.
