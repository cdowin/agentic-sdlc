---
id: bg-ruff-waives-44-findings
kind: bug
milestone: 
name: ruff waives 44 findings in 22 files
status: open
caused_by:
changelog:
---

# ruff waives 44 findings in 22 files

## Symptom

`[tool.ruff.lint.per-file-ignores]` in `pyproject.toml` waives 44 findings in 22 files: F401 17, F541 12, F811 9, F841 5, F821 1. Each code stays active for every other file and for new code.

## Root cause

The tree predates the lint gate (st-ruff-is-a-pinned-dev-gate).

## Fix

Fix the findings file by file and delete each waiver line as its file goes clean. F811 (redefinition) and F841 (unused variable) first: they can hide a dead test. The F821 is bg-a-readme-test-checks-nothing.
