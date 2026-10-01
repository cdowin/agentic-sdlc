---
id: "ms-the-loop-is-fast"
kind: milestone
name: The loop is fast
status: done
depends_on: []
branch: speed-the-loop-is-fast
mode:
version: 1.2.0
changelog: A push runs no gate, verify receipts are shared across worktrees, and declared extras run in one batched session.
order:
  - "ft-the-loop-is-fast"
---

# The loop is fast

A push costs no gate, and a gate that passed in one worktree passes in every worktree of the clone.
Declared extras run in one session. Issue #114.

## Ship criterion

Release 1.2.0 as an immutable locked wheel. CI verify and the version gate pass on PR #115.

## Risks

A shared receipt must key on the tree it proved. A stale receipt must never pass a changed tree.
