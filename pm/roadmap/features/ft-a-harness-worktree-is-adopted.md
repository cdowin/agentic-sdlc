---
id: ft-a-harness-worktree-is-adopted
kind: feature
milestone: "ms-integrate-takes-the-whole-batch"
name: A harness worktree gets its scope marker without a hand step
status: done
reviewed:
depends_on: []
consumed_by: []
changelog: The dispatch brief tells a builder in a harness worktree to run agent-worktree.sh adopt.
order:
  - "st-the-brief-adopts-a-harness-worktree"
---

# A harness worktree gets its scope marker without a hand step

A builder the Agent tool starts lands in `.claude/worktrees/agent-<id>` with no `.agent-scope`. 2.0.0 shipped `agent-worktree.sh adopt` (#124), but no brief, hook or agent definition calls it, so the marker is still a hand step.

## Ship criterion

The rendered dispatch brief tells a builder already in a harness worktree to run `agent-worktree.sh adopt` before the first edit, and `new` otherwise.
