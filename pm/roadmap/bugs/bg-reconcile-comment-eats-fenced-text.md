---
id: bg-reconcile-comment-eats-fenced-text
kind: bug
milestone: ms-the-backlog-is-empty
name: reconcile comment eats fenced text
status: closed
caused_by:
changelog: A <!-- inside a code fence no longer hides text in a reconcile record.
---

# reconcile comment eats fenced text

## Symptom

MINOR. `repo/pm/reconcile.py::_sections`: the DOTALL `_COMMENT.sub` runs before `non_fenced_lines`, so a `<!--` inside a code fence deletes text up to the next `-->`. Source: 0.17.0-milestone/C3 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

A fence-aware comment reader in `core/markdown.py`.
