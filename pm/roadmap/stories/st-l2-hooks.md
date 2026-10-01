---
id: st-l2-hooks
kind: story
feature: ft-build-wide
milestone: "ms-build-wide-integrate-once"
name: Hooks guard and never run a gate
status: building
owner:
depends_on: []
changelog:
---

# Hooks guard and never run a gate

## Acceptance criteria

- The stop gate, agent isolation, commit-pathspec and session preflight hooks are deleted.
- A denylist under 120 lines replaces the git allowlist.
- `agent-worktree.sh adopt` and `done` handle harness worktrees (#124).
- `check hooks` is deleted (#122).

## How this is proven

`make check` and `make unit` on the integrated batch; the lane's probes in its report.
