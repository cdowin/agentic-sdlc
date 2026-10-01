---
id: st-l5-checks
kind: story
feature: ft-build-wide
milestone: "ms-build-wide-integrate-once"
name: Wording warns, budget is a report
status: done
owner:
depends_on: []
changelog: check budget and the [tests] ceilings are gone (pm ledger report shows cost), grain-shape caps and headers are WARN lines, and make check names [gates] extra targets with no [gates.inputs].
---

# Wording warns, budget is a report

## Acceptance criteria

- `check budget` is deleted.
- Wording and size scans in `grain-shape` and `check pm` print WARN and exit 0; structural errors still exit 1.
- Extras with no inputs get one WARN line per `check all` (#121).

## How this is proven

`make check` and `make unit` on the integrated batch; the lane's probes in its report.
