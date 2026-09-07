---
id: bg-the-seed-census-drops-a-kwargs-call
kind: bug
milestone: 
name: the seed census skips a coercer invoked with kwargs
status: open
caused_by:
---

# the-seed-census-drops-a-kwargs-call

## Symptom

## Root cause

## Fix

`tests/test_config_seed.py`'s AST census skips any `core.config` coercer
call with keyword arguments (`len(node.args) < 3`), BEFORE the dynamic
bookkeeping that would otherwise name it. So a default declared with kwargs is
invisible to the seed-vs-code comparison — the one census hole in the case
whose whole job is that it cannot pass vacuously.

Deferred from `the-config-and-the-census` M3. No call site uses kwargs today,
which is why it has never bitten.
