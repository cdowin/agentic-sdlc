---
id: st-l7-integrate
kind: story
feature: ft-one-proof
milestone: "ms-build-wide-integrate-once"
name: One integrate verb merges a batch, proves once and closes its stories
status: done
owner:
depends_on: []
changelog: New verb integrate <slug>...: it merges a batch of lane branches in one worktree, runs [integrate] proof once, then fast-forwards the milestone branch, closes each lane's story and removes the lanes.
---

# One integrate verb merges a batch, proves once and closes its stories

## Acceptance criteria

- `integrate <slug>...` merges each `origin/feat/<slug>` in one worktree, runs `[integrate] per_merge` after each and `[integrate] proof` once.
- On green it fast-forwards the milestone branch, writes `done` on each merged story and deletes the lanes.
- On red it closes nothing, names the lane, and a rerun resumes.

## How this is proven

`make check` and `make unit` on the integrated batch; the lane's probes in its report.
