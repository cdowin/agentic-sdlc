---
id: bg-tree-state-relative-root
kind: bug
milestone: 
name: tree state relative root
status: open
caused_by:
changelog:
---

# tree state relative root

## Symptom

NIT. `repo/verify/cache.py::tree_state`: a relative `root` turns the status exclusion off (fails safe). Source: 0.18.0-reuse/F5 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Resolve `root` first.
