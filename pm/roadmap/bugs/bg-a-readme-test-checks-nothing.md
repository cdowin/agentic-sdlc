---
id: bg-a-readme-test-checks-nothing
kind: bug
milestone: "ms-the-loop-proves-itself"
name: a README test in test_install.py checks nothing
status: open
caused_by:
changelog:
---

# a README test in test_install.py checks nothing

## Symptom

ruff F821 (found by st-ruff-is-a-pinned-dev-gate): `tests/test_install.py` sets `README = REPO / 'README.md' if 'REPO' in dir() else None`. `REPO` is not defined in that scope, so `README` is always `None`.

## Root cause

A guard written to tolerate a missing name hides that the name is missing. The case that reads `README` may pass while it checks nothing (rule 4).

## Fix

Define the path from the module's repo root, drop the `dir()` guard, and remove the F821 waiver for `tests/test_install.py` in `pyproject.toml`. Broken probe: break the README claim the case checks and see it FAIL.
