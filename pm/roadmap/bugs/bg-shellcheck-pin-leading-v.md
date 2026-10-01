---
id: bg-shellcheck-pin-leading-v
kind: bug
milestone: ms-the-backlog-is-empty
name: shellcheck pin leading v
status: closed
caused_by:
changelog: A shellcheck_version pin with a leading v is refused at exit 2 by name.
---

# shellcheck pin leading v

## Symptom

NIT. `repo/checks/shell.py::pinned`: a pin written `"v0.11.0"` never matches, and CI builds a `vv0.11.0` URL. Source: 0.17.0-hooks-and-ci/N1 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Strip a leading `v`, or refuse it at exit 2.
