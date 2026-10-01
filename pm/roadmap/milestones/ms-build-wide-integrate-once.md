---
id: "ms-build-wide-integrate-once"
kind: milestone
name: Build wide, integrate once
status: done
depends_on: []
branch: milestone/2.0.0-build-wide-integrate-once
mode:
version: 2.0.0
changelog: Build wide, integrate once: builders spot-check and stop, one integrate verb proves a batch once, close and release write status and run no gate, hooks guard and never run a gate, and about 7,800 lines of belts, guards and ceremony are gone.
---

# ms-build-wide-integrate-once — Build wide, integrate once

The plan is `docs/design/2.0.0-build-wide-integrate-once.md`, approved by Chris on 2026-10-01.
Builders spot-check, push `feat/<slug>` and stop. The lead merges a batch in one worktree and
proves it once. A close, a push and a release write status and run no gate. Hooks guard
irreversible acts and never run a gate.

## Ship criterion

- A builder's whole proof is one spot command under 30 s.
- `agentic-sdlc integrate <slug>...` merges a batch, proves it once, closes its stories and
  deletes its lanes.
- No hook runs a gate. The stop gate, agent isolation, commit-pathspec, session preflight and
  the git allowlist are gone; a short denylist replaces the allowlist.
- The cut list in the plan is deleted, with its tests.

## Risks

- Major bump: every consumer changes its hooks, `[verify]` rungs and Makefile targets.
  `adopt 2.0.0` must name each refused key and its replacement.
- Batch 2 (integrate, pm cuts) touches `cli.py` and the conveyor together.
