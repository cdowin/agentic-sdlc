---
id: bg-live-dependents-skip-caused-by
kind: bug
milestone: 
name: live dependents skip caused by
status: open
caused_by:
changelog:
---

# live dependents skip caused by

## Symptom

NIT. `repo/pm/cli.py::_live_dependents`: scans `REF_KEYS` only, so a `caused_by` naming a removed feature gets no `noticed:` line. Source: 1.0.0-dangling/F3 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Include `CAUSED_BY`.
