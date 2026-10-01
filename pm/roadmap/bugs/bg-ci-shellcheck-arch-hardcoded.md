---
id: bg-ci-shellcheck-arch-hardcoded
kind: bug
milestone: ms-the-backlog-is-empty
name: ci shellcheck arch hardcoded
status: closed
caused_by:
changelog: The stock verify.yml installs the shellcheck asset for the runner's architecture (x86_64 or aarch64).
---

# ci shellcheck arch hardcoded

## Symptom

NIT. `installables/ci-verify.yml (Install the pinned shellcheck)`: `linux.x86_64` is hard-coded, so an arm runner breaks. Source: 0.17.0-hooks-and-ci/N2 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Map `runner.arch` to the asset name.
