---
id: st-l4-pm-cuts
kind: story
feature: ft-one-proof
milestone: "ms-build-wide-integrate-once"
name: Dispatch refuses nothing, and arrive, preflight and cite are gone
status: done
owner:
depends_on: []
changelog:
---

# Dispatch refuses nothing, and arrive, preflight and cite are gone

## Acceptance criteria

- `dispatch` renders the brief and refuses nothing; the guard, `parallel_stories` and `--preflight` are gone.
- Arrival questions, `preflight` and `cite` are gone, with their config keys refused by name.

## How this is proven

`make check` and `make unit` on the integrated batch; the lane's probes in its report.
