---
id: bg-ci-shellcheck-arch-hardcoded
kind: bug
milestone: 
name: ci shellcheck arch hardcoded
status: open
caused_by:
changelog:
---

# ci shellcheck arch hardcoded

## Symptom

NIT. `installables/ci-verify.yml (Install the pinned shellcheck)`: `linux.x86_64` is hard-coded, so an arm runner breaks. Source: 0.17.0-hooks-and-ci/N2 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Map `runner.arch` to the asset name.
