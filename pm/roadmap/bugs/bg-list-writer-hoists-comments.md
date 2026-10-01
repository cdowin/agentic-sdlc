---
id: bg-list-writer-hoists-comments
kind: bug
milestone: ms-the-backlog-is-empty
name: list writer hoists comments
status: open
caused_by:
changelog:
---

# list writer hoists comments

## Symptom

MINOR. `core/frontmatter.py::set_list_field`: comments inside an `order:` list are moved to the top of the list. Source: 1.0.0-dangling/F2 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Keep each comment ahead of the item it preceded.
