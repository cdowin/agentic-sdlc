---
id: ft-the-loop-is-fast
kind: feature
milestone: "ms-the-loop-is-fast"
name: The loop is fast
status: done
reviewed:
depends_on: []
consumed_by: []
# Optional story ids allowed to build concurrently within this feature.
parallel_stories:
changelog: The stock pre-push hook gates nothing, a PASS verify receipt is reused by every worktree of a clone, and gates-extra --run batches declared extras.
---

# The loop is fast

The stock pre-push hook runs no gate. A PASS verify row is also kept in `<git-common-dir>/agentic-sdlc/receipts.jsonl`, so every worktree reuses it.
`gates-extra --run t1 t2 ...` runs all declared extras in one session, and `Makefile.devkit` check batches them. Closes #114.

## Ship criterion

A push runs no gate. A second worktree reuses a PASS receipt for the same tree. Batched extras hash the tree once.

## Proof budget

  cases: 1 new case
  tier: unit
  lands in: tests/test_hooks_payloads.py
  what already covers this: the verify cache and gates-extra cases; the new case pins the stock pre-push payload.
