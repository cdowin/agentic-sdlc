---
id: st-release-refuses-a-milestone-on-no-plan
kind: story
feature: ft-release-and-install-tell-the-truth
milestone: "ms-the-open-issues-close"
name: release refuses a milestone that is on no plan
status: done
owner:
depends_on: []
changelog: release refuses a milestone that is not in releases.md, and names the pm add roadmap command that schedules it.
---

# release refuses a milestone that is on no plan

https://github.com/cdowin/agentic-sdlc/issues/127. Rule 4: a false ok.

## Acceptance criteria

1. `belts.py::release_checks` gains a 6th check, `on-plan`, true when the milestone id is in
   `releases.md` `order`. False prints `error: on-plan: <id> is on no plan; pm add roadmap <id>`.
2. The check reads the same plan `check pm` R1 reads; no second parser.
3. `release --help` lists it.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1-3 | unit | test_release.py: a milestone off the plan; one on it | new |
