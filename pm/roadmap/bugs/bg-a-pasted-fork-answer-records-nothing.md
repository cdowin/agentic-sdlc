---
id: bg-a-pasted-fork-answer-records-nothing
kind: bug
milestone: 
name: a pasted arrival fork answer on a no-op move records nothing
status: open
caused_by:
changelog:
---

# a pasted arrival fork answer on a no-op move records nothing

From the 0.8.0 vehicle review, M7 (`docs/reviews/2026-09-11-0.8.0-every-printed-command-runs-in-a-stock-consumer.md`).
It has been in v0.7.0 since `dbf6506`, outside that changeset, so it is filed to the pool rather than
held against 0.8.0.

## Symptom

Arrive at `feature reviewing ft-delta`, then paste the rendered fork answer
`make pm ARGS='feature reviewing ft-delta --skip review '"'"'…'"'"''`. It prints "already reviewing
(no-op)" and exits 0, and the last disposition row is still `"answer":"none"`. The direct call does
the same.

## Root cause

`pm/cli.py:769-772`: `answered = bool(said) or …` makes `not answered` false exactly when an answer
is given, so a no-op move WITH an answer writes no disposition row. The docstring says the opposite:
"With an answer it still records: that is how a skipped fork is answered". **Rule 4's second sin**, a
write that should have happened and silently did not.

## Fix

`if moved or skipped or said or not answered:`, plus the review's paste as a case that fails first.
