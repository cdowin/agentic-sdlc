---
id: st-a-red-proof-names-a-lane-only-when-the-output-does
kind: story
feature: ft-every-lane-merges
milestone: "ms-integrate-takes-the-whole-batch"
name: A red proof names a lane only when its output names a lane file
status: done
owner:
depends_on: []
changelog: A red integrate proof names only the lanes whose files its output names, or says no lane named.
---

# A red proof names a lane only when its output names a lane file

## Acceptance criteria

1. When the proof output names a file a lane changed, the stop line names that lane only.
2. When it names no lane file, the stop line says `no lane named` and lists no lane.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_integrate.py: the line builder with and without a lane file in the output | amend or new |

Files: `integrate::_run` (the `proof failed; lanes to look at` line).

## Out of scope

Guessing a lane from a test name.
