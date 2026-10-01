---
id: bg-index-url-spelled-five-times
kind: bug
milestone: ms-the-backlog-is-empty
name: index url spelled five times
status: open
caused_by:
changelog:
---

# index url spelled five times

## Symptom

NIT. `installables/Makefile.devkit::GDK_KIT_INDEX`: the index URL is in 5 places, and no test holds them equal. Source: 1.0.0-wheel/F5 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Add one equality test.
