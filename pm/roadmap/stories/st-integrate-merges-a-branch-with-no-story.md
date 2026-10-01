---
id: st-integrate-merges-a-branch-with-no-story
kind: story
feature: ft-every-lane-merges
milestone: "ms-integrate-takes-the-whole-batch"
name: integrate --merge-only takes any origin branch and closes nothing for it
status: done
owner:
depends_on: []
changelog: integrate --merge-only <branch> merges and proves any origin branch with the batch and closes nothing for it.
---

# integrate --merge-only takes any origin branch and closes nothing for it

## Acceptance criteria

1. `--merge-only <branch>` (repeatable) names an origin branch by its full name, prefix or not.
   It merges after the slug lanes, in the order given, and is proven with the batch.
2. It closes no story and is never deleted, even without `--keep-lanes`: the lead did not make it.
3. A conflict in it stops the batch the same way a slug lane does, naming the branch.
4. A branch that is not on origin is exit 1 by name, before any merge.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1-4 | integration | test_integrate.py: a `feat/art-x` branch merged with one slug lane; a missing one | new |

## Out of scope

Resolving a conflict for the lead.
