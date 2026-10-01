---
id: bg-without-status-drops-duplicates
kind: bug
milestone: ms-the-backlog-is-empty
name: without status drops duplicates
status: open
caused_by:
changelog:
---

# without status drops duplicates

## Symptom

NIT. `repo/verify/cache.py::_without_status`: every frontmatter `status:` line is dropped, so a duplicate key does not move the state. Source: 0.17.0-green-run/F5 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Drop only the first one.
