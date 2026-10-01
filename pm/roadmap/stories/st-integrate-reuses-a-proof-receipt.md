---
id: st-integrate-reuses-a-proof-receipt
kind: story
feature: ft-a-rerun-reuses-the-proof
milestone: "ms-integrate-takes-the-whole-batch"
name: A rerun on a byte-identical batch reuses the recorded proof
status: building
owner:
depends_on: []
changelog: A rerun of integrate on a batch tree that already passed its proof reuses that PASS and runs no target.
---

# A rerun on a byte-identical batch reuses the recorded proof

## Acceptance criteria

1. A proof PASS is recorded keyed on the batch tree's state, through `verify/cache.py` (the one
   receipt store; no second one).
2. A rerun whose batch tree state matches prints the reuse line `verify` prints and runs no proof
   target; the close and the fast-forward proceed.
3. A FAIL is never reused. Any changed path in the batch makes it a miss.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1-3 | integration | test_integrate.py: green run with `--keep-lanes` then rerun; edit then rerun | new |

## Out of scope

Reusing a PASS recorded by `verify --milestone` on a different tree.
