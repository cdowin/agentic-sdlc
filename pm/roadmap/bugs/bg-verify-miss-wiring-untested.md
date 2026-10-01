---
id: bg-verify-miss-wiring-untested
kind: bug
milestone: "ms-the-loop-proves-itself"
name: verify miss wiring and inputs_state exclusion untested
status: open
caused_by:
changelog:
---

# verify-miss-wiring-untested

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-verify-miss-wiring-untested` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR: no test fails if the two lines in `verify/main.py::_run_rung` that print `cache.miss_lines(...)` are deleted or moved after the target runs, and no test covers the new `is_inputs_file` skip in `cache.inputs_state` (static gates) — a regression there would make every static-gate key move on each PASS (cache never hits).

## Root cause

tests/test_verify_cache.py tests `miss_lines`/`record`/`tree_state` directly; nothing drives `_run_rung` on a miss, and nothing calls `inputs_state` with the inputs file listed.

## Fix

Add one in-process case: PASS, edit one file, run the rung path with the target stubbed, assert `changed: <path>` precedes the target. Add an `inputs_state` case with the inputs file listed, asserting the digest does not move after a PASS (rule 10: a cheap case that bites).
