---
id: st-l1-docs
kind: story
feature: ft-build-wide
milestone: "ms-build-wide-integrate-once"
name: The SDLC, CLAUDE.md, agents and skills describe build wide, integrate once
status: building
owner:
depends_on: []
changelog:
---

# The SDLC, CLAUDE.md, agents and skills describe build wide, integrate once

## Acceptance criteria

- SDLC.md is about 80 lines and describes the roles, the loop, validate once, hooks and reviews.
- CLAUDE.md keeps rules 1–11 by number and its ladder is spot / integrate / release.
- The agents and skills are rewritten at their sources and installed byte-current.
- docs/parallel-development.md is gone.

## How this is proven

`make check` and `make unit` on the integrated batch; the lane's probes in its report.
