---
id: ft-init-ends-on-the-loop
kind: feature
milestone: "ms-the-loop-proves-itself"
name: init ends on the loop, in the tree's own states
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-init-prints-the-loop"
---

# init ends on the loop, in the tree's own states

`init.py` prints 8 fixed next steps. It does not show the loop or the states the tree declares.
Rule 11: a capability is named where its operator stands, and a fresh `init` is where a new
consumer stands.

## Ship criterion

The last block `init` prints is the loop (new, dispatch, spot, integrate, release), spelled
with the declared `[pm.states.*]` names, and names `adopt <version>` as the setup check.

## Proof budget

  cases: 1 amended
  tier: unit
  lands in: tests/test_init_verb.py
  what already covers this: test_init_verb.py asserts the next-steps block; amend it.
