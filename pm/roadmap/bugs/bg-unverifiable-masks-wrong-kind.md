---
id: bg-unverifiable-masks-wrong-kind
kind: bug
milestone: ms-the-backlog-is-empty
name: unverifiable masks wrong kind
status: open
caused_by:
changelog:
---

# unverifiable masks wrong kind

## Symptom

NIT. `repo/pm/validate.py::_unverifiable`: a `caused_by` naming a retired story reads UNVERIFIABLE, not wrong-kind. Source: 1.0.0-dangling/F4 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Check the kind before excusing it.
