---
id: st-r5-is-a-warning
kind: story
feature: ft-the-release-gate-asks-only-release-questions
milestone: "ms-the-backlog-is-empty"
name: R5 version drift is a WARN line, never a release blocker
status: done
owner:
depends_on: []
changelog: R5 version drift is a WARN line and never sets exit 1.
---

# R5 version drift is a WARN line, never a release blocker

https://github.com/cdowin/agentic-sdlc/issues/116 part 3.

## Acceptance criteria

1. R5 drift prints a `WARN` line and does not change the exit code.
2. `check pm --help` says R5 warns.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_pm_gate.py R5 cases | amend |
