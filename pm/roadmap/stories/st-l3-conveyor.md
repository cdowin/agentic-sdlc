---
id: st-l3-conveyor
kind: story
feature: ft-one-proof
milestone: "ms-build-wide-integrate-once"
name: The belts collapse to status writes and a short release
status: done
owner:
depends_on: []
changelog: release checks facts and writes the milestone without running a gate, a close is pm story|feature <done-state> <id>, [verify] has spot and milestone, and every retired verb and key is refused by name with its replacement.
---

# The belts collapse to status writes and a short release

## Acceptance criteria

- The conveyor framework, `ready-for`, `verdict`, `land`, `ship`, `lesson` and `install-sdlc` are gone.
- `release` and `adopt` are short check lists; `release` runs no gate.
- `[verify]` has `spot` and `milestone`; `story` and `feature` are refused by name with their replacement.

## How this is proven

`make check` and `make unit` on the integrated batch; the lane's probes in its report.
