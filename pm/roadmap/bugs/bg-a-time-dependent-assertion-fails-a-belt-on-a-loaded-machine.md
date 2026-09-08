---
id: bg-a-time-dependent-assertion-fails-a-belt-on-a-loaded-machine
kind: bug
milestone: "ms-the-rule-reaches-the-work"
name: a time-dependent assertion fails a belt on a loaded machine
status: closed
caused_by:
changelog: none
---

# a time-dependent assertion fails a belt on a loaded machine

**Found by `agentic-sdlc close feature ft-the-vocabulary-is-constants-not-literals` failing its
`feature-verified` check**, two minutes after the same target passed:

    [feature] error: feature-verified: `agentic-sdlc verify --feature` exited 1:
    E AssertionError: 'last hook-written row: dispatch, 1h ago' not found in …

## Symptom

`tests/test_pm_gate.py::test_a_courier_row_counts_wherever_the_wiring_lives` plants a courier row at
`hours_ago(1)` and asserts U4 renders `dispatch, 1h ago`. It passes in isolation and passes most
full runs. It failed one.

## Root cause

`hours_ago(1)` writes `now - 1h`, truncated to whole seconds by `TS_FORMAT`. The gate measures the
age LATER, so what it computes is `1h + however long the run took to get there`, and
`ledger.human_duration` renders two units: `1h` becomes `1h 1s` the moment that gap crosses a
second. `'1h ago'` is then not a substring and the case fails.

Under `make test` — 1560 cases, `-n auto --dist loadgroup` — a second between the fixture write and
the gate read is ordinary, not exceptional. It is not an xdist race on shared state
(`bg-a-ledger-reading-test-is-racy-under-xdist` is that, on a different case); it is an exact match
against a value that is a function of elapsed time.

**The sibling case forty lines above already knew.** It asserts `dispatch, 2h`, with the comment:

    # The KIND and the magnitude, not the exact rendering: the stamp
    # is truncated to the second and the age is measured later, so
    # `2h` and `2h 1s` are the same fact and one of them is a race.

So the lesson had been learned and written down, in the same class, and the neighbour kept the
strict form. That is the finding — not the one flake.

## Why it is worth a grain

**A flaky test in a BELT is the worst place for one.** `close feature` is a gate whose failure a
reader learns to re-run, and re-running is exactly what makes a real regression invisible next time
(rule 4's first sin, arrived at by habit rather than by code). The cost here was one failed close;
the cost of the habit is unbounded.

## Fix

The assertion drops the `ago` suffix and matches the kind and magnitude, like its sibling: `1h` and
`1h 1s` are the same fact.

Swept for the class across `tests/`: three other assertions mention an age, and none is exposed —
`test_check_budget` asserts only that the word `ago` is present, `test_verify_main` matches a
suffix carrying no number, and `test_verify_cache` passes `now=NOW`, a frozen clock. This was the
only live one.

## Out of scope

Making `human_duration` render one unit, or freezing the clock across the suite. Both are larger than
the defect, and the sibling's form already works.
