---
id: ms-0.4.0/bugs/the-seed-census-drops-a-kwargs-call
kind: bug
milestone: "ms-0.4.0"
name:
status: open
caught_in: "ms-0.4.0"
fix_milestone:
caused_by:
---

# the-seed-census-drops-a-kwargs-call

<!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it
     was found. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

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
