---
id: bg-a-hand-recorded-dispatch-cannot-carry-a-total
kind: bug
milestone: ms-the-rule-reaches-the-work
name: pm ledger record takes a token split it cannot honestly fill
status: open
caused_by:
---

# a hand-recorded dispatch cannot carry a total

Carries `E6` from `docs/reviews/2026-09-07-0.5.0-wiring-is-one-act-and-it-is-portable.md`, which is
the reason this grain exists rather than a `rejected:` on that record.

## Symptom

`pm ledger record --grain <id> --tokens-total 1234` is refused. The verb offers `--tokens-in` and
`--tokens-out` only, so a subagent completion — which reports ONE total — can be recorded as a
guess split two ways, or not at all. Every hand-written `dispatch` row in this milestone carries no
token data for exactly that reason.

## Root cause

The paragraph asking for it is duplicated **verbatim** in two feature files —
`ft-wiring-is-one-act-and-it-is-portable.md:60` and
`ft-telemetry-proves-the-path-not-the-config.md:49` — so neither declared who owned it and neither
listed it out of scope. It shipped nothing under either.

## Fix

Two files, both outside the wiring/telemetry surface:

  * `src/agentic_sdlc/repo/pm/ledger.py` — a `tokens_total` key in `ROW_KEYS`, beside the existing
    split, so a reader can tell "one total was reported" from "a split was measured". `usage_row`
    already drops unknown keys, so nothing else moves.
  * `src/agentic_sdlc/repo/pm/cli.py` — a `--tokens-total` flag on `ledger record`, mutually
    exclusive with `--tokens-in`/`--tokens-out`: accepting both is how a total and a split come to
    disagree in one row.

`pm ledger report` then has to decide which number it sums, and say which it used — a total and a
split are not the same measurement and adding them is the lie this flag exists to avoid.

**It is not evidence a courier ran.** `check pm` U4 requires the courier's `session_id` as well as
the row kind (`checks/pm.py::_hook_written`), so the hand-recording path this flag serves stays
correctly outside the recording count.
