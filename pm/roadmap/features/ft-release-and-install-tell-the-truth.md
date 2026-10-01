---
id: ft-release-and-install-tell-the-truth
kind: feature
milestone: "ms-the-open-issues-close"
name: release and install --force say what is true
status: done
reviewed:
depends_on: []
consumed_by: []
changelog: release refuses a milestone on no plan, and install --force drops header keys the new file never mentions, naming each.
order:
  - "st-release-refuses-a-milestone-on-no-plan"
  - "st-install-force-drops-retired-header-keys"
---

# release and install --force say what is true

https://github.com/cdowin/agentic-sdlc/issues/127 and https://github.com/cdowin/agentic-sdlc/issues/128 (with #118 folded in). `release` prints ok over a milestone `check pm` R5/R6 calls unplanned, and `install --force` carries header keys the new file no longer reads. Both lanes touch `belts.py`.
