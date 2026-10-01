---
id: bg-matrix-legs-oversubscribe
kind: bug
milestone: ms-the-backlog-is-empty
name: matrix legs oversubscribe
status: open
caused_by:
changelog:
---

# matrix legs oversubscribe

## Symptom

NIT. `Makefile.tiers::matrix`: each parallel leg runs `-n auto`, giving legs x cores workers. Source: 0.18.0-ci/N5 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Divide `PYTEST_N` by the leg count.
