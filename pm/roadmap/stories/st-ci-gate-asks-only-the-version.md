---
id: st-ci-gate-asks-only-the-version
kind: story
feature: ft-the-release-gate-asks-only-release-questions
milestone: "ms-the-backlog-is-empty"
name: The semver gate asks only whether the version increases
status: done
owner:
depends_on: []
changelog: The semver gate passes any PR whose version is greater than main's and reads no PM tree, so a patch with no milestone passes.
---

# The semver gate asks only whether the version increases

https://github.com/cdowin/agentic-sdlc/issues/116 part 1.

## Acceptance criteria

1. `installables/ci-semver-gate.yml` passes a PR whose version is greater than main's by semver,
   with any number of numeric components (2.3.1, 2.4.0, 2.3.0.1). An equal or lower version fails
   and names both. It reads no `pm/roadmap` (no `PM_ROADMAP`).
2. This repo's `.github/workflows/semver-gate.yml` is re-installed byte-current.
3. The header comment says what it asks, in two lines.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | integration | test_ci_workflows.py compare-step cases: patch, minor, hotfix, equal, lower | amend |
| 2 | unit | test_install.py byte-current | existing |

## Out of scope

A changelog-entry check: release notes are the grains' `changelog:` lines, rendered by
`agentic-sdlc changelog`, and the gate reads no PM tree.
