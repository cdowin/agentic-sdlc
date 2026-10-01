---
id: "ms-fast-parallel-development"
kind: milestone
name: Deterministic parallel development
status: done
depends_on: []
branch: milestone/1.1.0-release-parallel-development
mode:
version: 1.1.0
changelog: Parallel development uses isolated worktrees, deterministic close recovery, resumable land, and scoped verification without load-driven close failures.
order:
  - "ft-parallel-development-enforcement"
---

# Deterministic parallel development

Implement the bounded close model and mechanical enforcement specified in docs/parallel-development.md.
The release covers isolated external worktrees, failed-belt recovery, dispatch guards, coordinated landing,
release performance context, and explicitly history-independent verification.

## Ship criterion

Release 1.1.0 as an immutable locked wheel after regression gates and review.
Installer outputs remain current. Functional checks remain hard under parallel load.

## Risks

Journal recovery must reject changed frozen commits and unexpected work. Dispatch policy must not serialize declared independent lanes.
