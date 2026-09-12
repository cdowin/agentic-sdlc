---
id: "ms-the-host-stays-a-checkout"
kind: milestone
name: the host stays a checkout
status: done
depends_on: []
branch: milestone/0.11.1-the-host-stays-a-checkout
mode:
version: 0.11.1
changelog: none
reviewed: docs/reviews/2026-09-12-0.11.1-milestone-review.md
---

# 0.11.1 — the host stays a checkout

A patch release for one bug: an agent's `git init` in a linked worktree flipped the host checkout to
bare (`bg-a-probe-in-a-linked-worktree-flips-the-host-to-bare`). The interface is unchanged: the guard's
refusal gets narrower and two briefs get one line each (rule 7, patch).

## Ship criterion

The guard refuses a bare `git init` and allows `git -C <scratch> init` outside the repository.
The shipped reviewer briefs build scratch repos with explicit paths. `preflight` names a bare flag
on a working-tree checkout, with the repair.
