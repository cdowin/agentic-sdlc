---
id: bg-reused-warn-stale-age
kind: bug
milestone: 
name: reused warn stale age
status: open
caused_by:
changelog:
---

# reused warn stale age

## Symptom

NIT. `repo/checks/pm.py::_age_of`: reused `check pm` WARNs replay a frozen age. Source: 1.0.0-static/F5 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Stamp the age as of the recorded run.
