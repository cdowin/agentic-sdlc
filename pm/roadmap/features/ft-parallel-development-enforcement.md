---
id: ft-parallel-development-enforcement
kind: feature
milestone: "ms-fast-parallel-development"
name: Parallel development enforcement
status: done
reviewed: pm/roadmap/features/ft-parallel-development-enforcement-decisions.md
depends_on: []
consumed_by: []
changelog: External isolated checkouts, guarded dispatch, resumable landing, reusable scoped verification, and release-only wall-time budgets bound parallel development close cost.
---

# Parallel development enforcement

Parallel lanes use external isolated checkouts. Close refusal records an actionable blocker.
Dispatch observes declared close-first and feature ownership policies. Landing resumes after failure without deleting unfinished work.
Performance grading belongs to explicit release context. History-independent evidence is opt-in and retains declared inputs.

## Ship criterion

Blocked belt recovery, dispatch refusal before side effects, resumable landing, cache invalidation, and release-only timing regressions pass.
Publish immutable version 1.1.0 and validate installer synchronization.

## Proof budget

Extend existing belt, dispatch, hook, budget, and verification cases. Add bounded landing transaction fixtures because no existing verb coordinates phases.
No extra engine boots. One final release gate after review.
