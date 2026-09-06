---
id: 0.4.0/every-grain-is-on-a-stopwatch
milestone: "0.4.0"
name: every grain is on a stopwatch, and the tool says so
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# every grain is on a stopwatch, and the tool says so

**The finding, measured on 0.3.0.** Eleven features were built in 64 minutes and
took 93 more to review and land, because nine reviews that could have overlapped
the build were batched at the end. Every one of those features sat `building`
the whole time. Nothing anywhere said so.

The ledger already holds what is needed: a `status` row per move, timestamped,
and `ledger.total_seconds` computes first-row-to-terminal for a CLOSED grain.
What is missing is the number that creates pressure — **how long the grains that
are still open have been open**, said out loud, on a surface an agent already
reads.

0.3.0 wrote the doctrine into SDLC.md and the shipped `reviewer.md` (dispatch at
`ready-for feature`, one pass, severity gates the hold). This is the measurement
that makes the doctrine self-enforcing rather than remembered — the same move
`a-unit-test-can-spawn-the-full-gate` made when prose in three places failed to
stop a wide gate.

## Ship criterion

`pm status` names, per open grain, how long it has been open, read from its
first `status` row in the ledger. `pm ledger report` gains the same figure as a
distribution — median and worst open-duration per kind — so "what is aging" is a
question the tree answers rather than one somebody reconstructs. A grain with no
status row yet is reported as such, never as zero (rule 4: a census that cannot
see something says so).

Nothing is gated on the number. It is a REPORT: the tool expresses, and the
caller decides (rule 9). A ceiling on how long a feature may stay open would be
this package having an opinion about somebody's week.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: the ledger report module's test, beside the existing `total_seconds` cases
  what already covers this: `total_seconds` is covered for CLOSED grains; the
    open case is the one it deliberately returns None for, so these extend it
    rather than arriving.

## Out of scope

Any gate, ceiling or refusal on the duration.
