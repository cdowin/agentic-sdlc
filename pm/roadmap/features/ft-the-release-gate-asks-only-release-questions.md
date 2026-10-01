---
id: ft-the-release-gate-asks-only-release-questions
kind: feature
milestone: "ms-the-backlog-is-empty"
name: The release gate asks only release questions
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-ci-gate-asks-only-the-version"
  - "st-r5-is-a-warning"
---

# The release gate asks only release questions

https://github.com/cdowin/agentic-sdlc/issues/116. The gate accepts only a `done` milestone's version or a hotfix component, so a plain
patch with no milestone is refused, and R5 fails `check pm` on the same drift. Chris: a release is
not tied to a milestone. The PM tree points at releases, not the reverse.

## Ship criterion

A patch release with no milestone passes the gate and `check pm`.
