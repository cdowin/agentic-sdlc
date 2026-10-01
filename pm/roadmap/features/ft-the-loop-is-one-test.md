---
id: ft-the-loop-is-one-test
kind: feature
milestone: "ms-the-loop-proves-itself"
name: The whole loop is one test, and the self-tree's numbers are true
status: building
reviewed:
depends_on: []
consumed_by: []
changelog: none
order:
  - "st-the-loop-runs-end-to-end"
  - "st-the-self-tree-numbers-are-recomputed"
---

# The whole loop is one test, and the self-tree's numbers are true

`test_fresh_project.py` stops at `make check`. `test_integrate.py` and `test_release.py` test
each verb alone. No test chains the loop a consumer runs every day. And no test recomputes the
counts `pm status` and `check pm` print about this repo; fixtures answer "yes" by construction
(improvements.md, `_slot_named`). Rule 4.

## Ship criterion

One integration case runs the whole loop in a temp tree. One case recomputes this repo's printed
counts from the files and compares.

## Proof budget

  cases: 2
  tier: integration (the loop), unit (the counts)
  lands in: tests/test_fresh_project.py, tests/test_pm_gate.py
  what already covers this: each verb alone; the self-tree only for `verify --check` and
  `pm vocabulary`.
