---
id: bg-reused-warn-stale-age
kind: bug
milestone: ms-the-backlog-is-empty
name: reused warn stale age
status: closed
caused_by:
changelog: A reused check pm WARN line says its age as of the time it was measured.
---

# reused warn stale age

## Symptom

NIT. `repo/checks/pm.py::_age_of`: reused `check pm` WARNs replay a frozen age. Source: 1.0.0-static/F5 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Stamp the age as of the recorded run.
