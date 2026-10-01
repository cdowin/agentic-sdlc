---
id: st-the-loop-runs-end-to-end
kind: story
feature: ft-the-loop-is-one-test
milestone: "ms-the-loop-proves-itself"
name: init, new, dispatch, spot, integrate and release run in one temp tree
status: building
owner:
depends_on: []
changelog: none
---

# init, new, dispatch, spot, integrate and release run in one temp tree

## Acceptance criteria

1. One case, in a temp git repo with a bare origin: `init`, `pm new` a milestone, feature and
   story, `dispatch --grain`, a lane branch with one commit that passes `[verify] spot`,
   `integrate <slug>`, then `release <version>`.
2. After each step the case asserts the one status or file that step writes, and nothing else.
3. The case fits the integration tier; `verify --plan` shows its cost.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | integration | test_fresh_project.py: extend the fresh project through the loop | amend |
| 3 | integration | `verify --plan` before and after | - |

Broken probe: make `integrate` skip its status write in a scratch copy; the case must FAIL.

## Out of scope

Running a real agent. `dispatch` renders a brief; the case reads it and makes the commit.
