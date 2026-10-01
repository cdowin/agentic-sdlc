---
id: bg-milestone-skip-not-in-log
kind: bug
milestone: ms-the-backlog-is-empty
name: milestone skip not in log
status: open
caused_by:
changelog:
---

# milestone skip not in log

## Symptom

MINOR. `installables/Makefile.devkit::gdk-tiers-skipped-milestone`: the skip line goes to the console only; `milestone.log` and its verdict do not name the skipped tier. Source: 0.18.0-ci/M4 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Append the skip line to the milestone log and verdict.
