---
id: ft-every-lane-merges
kind: feature
milestone: "ms-integrate-takes-the-whole-batch"
name: Every lane the lead names merges, story or not
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-integrate-merges-a-branch-with-no-story"
  - "st-a-red-proof-names-a-lane-only-when-the-output-does"
---

# Every lane the lead names merges, story or not

A lane with no `st-<slug>` already merges and closes nothing. But a lane whose branch is not `<prefix><slug>` (a second agent system's `feat/art-…`) cannot be named at all, and a red proof blames lanes the output never named (#130.2, #130.3).

## Ship criterion

`--merge-only <branch>` takes any origin branch. A red proof names only the lanes its output names, or says "no lane named".
