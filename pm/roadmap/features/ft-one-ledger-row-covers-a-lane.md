---
id: ft-one-ledger-row-covers-a-lane
kind: feature
milestone: 
name: one ledger row covers a lane
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# one ledger row covers a lane

Filed 2026-09-27 from a consumer's fork. One developer now builds a whole feature (0.14.0,
#49), but a ledger row names one grain. The consumer's orchestrator splits a lane's tokens across
its stories by hand, so `pm ledger report` per story is a guess someone typed.

Open questions, not decided: a row that names the feature and lets the report roll up without
a split; or a row that lists several grains with one total, and the report states it as shared,
never divides it (rule 9: express, never infer).

## Ship criterion

- A lane's dispatch writes one row, and `pm ledger report` shows its cost against the feature
  with no per-story split typed by hand.
- No report line divides a shared total by guess.

## Proof budget

  cases: 2-3
  tier: unit
  lands in: the existing ledger test module
  what already covers this: per-grain rows only
