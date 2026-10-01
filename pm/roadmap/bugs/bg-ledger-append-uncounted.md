---
id: bg-ledger-append-uncounted
kind: bug
milestone: 
name: ledger append uncounted
status: open
caused_by:
changelog:
---

# ledger append uncounted

## Symptom

NIT. `repo/pm/ledger.py::append_to`: the append is not counted by `apply.mutations()`; harmless today. Source: 1.0.0-walk/N1 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Count it or call `apply.outside_wrote()`.
