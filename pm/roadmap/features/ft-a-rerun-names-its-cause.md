---
id: ft-a-rerun-names-its-cause
kind: feature
milestone: "ms-the-loop-proves-itself"
name: A rung that re-runs names what changed
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-a-verify-miss-names-what-changed"
---

# A rung that re-runs names what changed

A PASS is a receipt keyed on one digest of the inputs (`verify/cache.py`). A miss prints
nothing and the target runs, so "why did it re-run" has no answer. The row must hold a digest
per input to say which one moved.

## Ship criterion

On a miss, `verify` prints one `changed: <path>` line per input whose digest differs from the
last PASS, before the target runs. A row written by 2.0.0 reads as a plain miss.

## Proof budget

  cases: 2
  tier: unit
  lands in: tests/test_verify_cache.py
  what already covers this: test_verify_cache.py covers hit and miss; nothing covers the cause.
