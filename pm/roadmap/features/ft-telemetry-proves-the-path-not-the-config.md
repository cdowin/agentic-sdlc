---
id: ft-telemetry-proves-the-path-not-the-config
kind: feature
milestone: "ms-a-move-is-an-event"
name: telemetry proves the path not the config
status: done
reviewed: docs/reviews/2026-09-07-0.5.0-the-recording-rules.md
depends_on: []
consumed_by: []
---

# telemetry proves the path, not the config

GitHub issue #11, **found by this milestone's own build recording nothing.**

`adopt`'s `telemetry-live` reads `.claude/settings.json`, confirms both couriers are wired, and
passes. Whether the harness ever LOADS that file depends on the session's project root — and a
session rooted at a parent directory of the repo loads none of it. Seven dispatches against this tree
produced zero `SubagentStop` rows while every surface said telemetry was live.

`gate` rows still landed: those come from the make wrapper INSIDE the repo, not from a harness hook.
So the ledger is not empty, which is exactly why U2 does not fire — U2 asks whether ledgers are
empty, and **no rule counts row KINDS**.

**This is 0.3.0's failure wearing its third hat.** Recording was off for a whole release and nobody
could tell; the fix was a fail-loud counterpart; the counterpart tests the CONFIGURATION rather than
the PATH, so it passes on a tree that records nothing.

## The shape

A check cannot answer "does recording work" by reading a file. It can report what the tree holds:

    couriers wired; last hook-written row: never
    couriers wired; last hook-written row: dispatch, 4m ago

The first is a true sentence a consumer can act on. `wired` alone is the tool asserting an outcome it
did not observe — rule 4's first sin at the one surface meant to catch it.

Rule 9 holds: this READS rows the ledger already has and reports their age. It decides nothing and
never refuses — a tree that opted out is quiet, not broken.

## Ship criterion

`telemetry-live` and a U-family rule in `check pm` both report the last hook-written row's kind and
age beside the wiring. A tree whose couriers are wired and whose hook-written kinds are absent gets a
NAMED line — never `PASS` alone. A tree with no couriers wired stays quiet. A `gate` row is not
evidence a courier ran, because the make wrapper writes those from inside the repo.

`pm ledger record --grain` accepts `--tokens-total`, explicitly not a split, because a subagent
completion reports one total and today that number can only be recorded as a lie or not at all. Every
hand-written dispatch row in this milestone carries no token data for exactly that reason.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_pm_gate.py` beside U2, and `tests/test_conveyor_adopt.py`
  what already covers this: U2's "wired and empty" case is the nearest shape and its fixture is
    reusable — the new assertion is on row KIND rather than row COUNT.

## Out of scope

Making the harness load the settings file, and choosing where a consumer roots a session. Rule 8 —
this package knows nothing about its consumers. Making the wiring work from any scope is
`ft-wiring-is-one-act-and-it-is-portable`; this feature makes the silence VISIBLE.

`pm ledger record --grain --tokens-total`, named in the criterion above and duplicated verbatim
in the sibling feature, so neither declared an owner and it shipped under neither. It lives in
`pm/ledger.py` + `pm/cli.py`, which is neither feature's surface — deferred by name to
`bg-a-hand-recorded-dispatch-cannot-carry-a-total`.
