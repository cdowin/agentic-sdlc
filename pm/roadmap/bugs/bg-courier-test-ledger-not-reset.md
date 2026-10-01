---
id: bg-courier-test-ledger-not-reset
kind: bug
milestone: ms-the-backlog-is-empty
name: courier test ledger not reset
status: closed
caused_by:
changelog: none
---

# courier test ledger not reset

## Symptom

NIT. `tests/test_hooks_payloads.py (the cannot-file case)`: the ledger is not emptied between fires, so the message blames the wrong payloads. Source: 1.0.0-suite/N4 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Reset the ledger per fire.
