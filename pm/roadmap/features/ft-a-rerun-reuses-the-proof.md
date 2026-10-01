---
id: ft-a-rerun-reuses-the-proof
kind: feature
milestone: "ms-integrate-takes-the-whole-batch"
name: A rerun on an unchanged batch reuses its PASS
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-integrate-reuses-a-proof-receipt"
---

# A rerun on an unchanged batch reuses its PASS

After a stop, the same command resumes and runs `[integrate] proof` from the start even when the batch tree is the one already proven. `verify` keys a PASS on the tree; `integrate` keys nothing.

## Ship criterion

A rerun whose batch tree matches a recorded proof PASS prints the reuse line and runs no target.
