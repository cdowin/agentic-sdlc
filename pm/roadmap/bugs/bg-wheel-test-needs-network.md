---
id: bg-wheel-test-needs-network
kind: bug
milestone: ms-the-backlog-is-empty
name: wheel test needs network
status: open
caused_by:
changelog:
---

# wheel test needs network

## Symptom

NIT. `tests/test_makefile_include.py (the built-index case)`: `uv build` needs hatchling from PyPI, so the test fails offline instead of skipping. Source: 1.0.0-wheel/F7 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Skip when the build cannot reach an index.
