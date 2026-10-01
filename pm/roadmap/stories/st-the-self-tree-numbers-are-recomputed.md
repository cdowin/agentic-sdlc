---
id: st-the-self-tree-numbers-are-recomputed
kind: story
feature: ft-the-loop-is-one-test
milestone: "ms-the-loop-proves-itself"
name: Every count pm status and check pm print about this repo is recomputed
status: building
owner:
depends_on: []
changelog: none
---

# Every count pm status and check pm print about this repo is recomputed

## Acceptance criteria

1. For this repo's `pm/roadmap`, every per-milestone `N/M feature(s) done` and per-feature
   `stories N/M done` that `pm status` prints equals a count made by reading the frontmatter
   directly in the test.
2. The census lines `check pm` prints (counts of grains, unbound, UNVERIFIABLE) equal the same
   direct count.
3. The test reads the tree; it never writes to it.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_pm_gate.py: call the verbs in-process on the repo root | new |

Broken probe: in a scratch copy of the tree, flip one story's status by hand and see the counts
disagree with a frozen expectation.

## Out of scope

`verify --plan` numbers; they are machine-local cost.
