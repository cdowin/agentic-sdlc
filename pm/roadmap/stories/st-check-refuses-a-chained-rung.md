---
id: st-check-refuses-a-chained-rung
kind: story
feature: ft-check-reads-the-verify-rungs
milestone: "ms-the-open-issues-close"
name: check refuses a [verify] rung the readers would refuse
status: done
owner:
depends_on: []
changelog: check pm D15, on by default, names a [verify] rung that dispatch, integrate or verify would refuse, at the first check rather than the first run.
---

# check refuses a [verify] rung the readers would refuse

https://github.com/cdowin/agentic-sdlc/issues/103.

## Acceptance criteria

1. `check pm` (or `check repo-hygiene`, whichever already reads devkit.toml workflow sections)
   runs `verify/rules.py::read` and prints its refusal as one FAIL line.
2. No `[verify]` declared prints nothing new (a WORKFLOW key has no default; readers refuse it).

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_pm_gate.py: a chained rung; none declared | new |
