---
id: bg-install-collision-note-never-used
kind: bug
milestone: 
name: install collision note never used
status: open
caused_by:
changelog:
---

# install collision note never used

## Symptom

MINOR. `repo/install.py (the collision report)`: a `note` naming undecodable files was built and never printed, so when several files collide the undecodable ones are not named. Source: 2.4.0 ruff lane (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Print it on the collision report.
