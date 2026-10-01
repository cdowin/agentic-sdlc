---
id: ft-the-batch-starts-warm
kind: feature
milestone: "ms-integrate-takes-the-whole-batch"
name: The batch worktree starts warm
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-integrate-runs-a-declared-prepare"
---

# The batch worktree starts warm

`integrate::_add_worktree` makes the batch worktree with a bare `git worktree add`. A Godot consumer then has no import cache, and the proof fails on a class cache it never built (#130.1). `agent-worktree.sh new` warms; `integrate` does not.

## Ship criterion

A tree that declares `[integrate] prepare` gets those make targets run once, after the worktree exists and before the first merge.
