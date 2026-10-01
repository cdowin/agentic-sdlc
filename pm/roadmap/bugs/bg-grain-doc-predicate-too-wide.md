---
id: bg-grain-doc-predicate-too-wide
kind: bug
milestone: ms-the-backlog-is-empty
name: grain doc predicate too wide
status: closed
caused_by:
changelog: none
---

# grain doc predicate too wide

## Symptom

NIT. `repo/verify/cache.py::_is_grain_doc`: matches every `.md` under the roadmap, not only grains, against its docstring. Source: 0.18.0-reuse/F4 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Restrict it to grain kinds or fix the docstring.
