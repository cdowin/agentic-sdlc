---
id: bg-ledger-append-uncounted
kind: bug
milestone: ms-the-backlog-is-empty
name: ledger append uncounted
status: closed
caused_by:
changelog: none
---

# ledger append uncounted

## Symptom

NIT. `repo/pm/ledger.py::append_to`: the append is not counted by `apply.mutations()`; harmless today. Source: 1.0.0-walk/N1 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Count it or call `apply.outside_wrote()`.
