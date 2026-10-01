---
id: st-the-brief-adopts-a-harness-worktree
kind: story
feature: ft-a-harness-worktree-is-adopted
milestone: "ms-integrate-takes-the-whole-batch"
name: The dispatch brief adopts a harness worktree before the first edit
status: building
owner:
depends_on: []
changelog: The dispatch brief tells a builder already in a harness worktree to run agent-worktree.sh adopt before its first edit.
---

# The dispatch brief adopts a harness worktree before the first edit

## Acceptance criteria

1. The rendered brief's worktree step says: in a harness worktree on `<prefix>*`, run
   `bash tools/dev/agent-worktree.sh adopt`; otherwise run `new <slug> <base>` as today.
2. The stock `developer` agent definition carries the same sentence (installables), and this repo's
   installed copy is re-installed byte-current.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | test_dispatch.py brief-render case | amend |
| 2 | unit | test_install.py byte-current case | existing |

## Out of scope

A hook that writes the marker. 2.0.0 hooks guard and never act.
