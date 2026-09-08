---
id: bg-a-hand-recorded-dispatch-cannot-carry-a-total
kind: bug
milestone: ms-the-rule-reaches-the-work
name: pm ledger record takes a token split it cannot honestly fill
status: closed
caused_by:
changelog: `pm ledger record --tokens-total N` records a dispatch that reported one number instead of a split (exclusive with `--tokens-in`/`--tokens-out`), and `pm ledger report` sums it in a new `tokens_total` column, never into `in`/`out`, naming how many rows reported which.
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

## What it decided, as built

`report.py` sums the reported total into its own `tokens_total` column, in every spend table, and
folds it into `in`/`out` nowhere. The summary line still says `<n> out`, which is the MEASURED
split — so beside it, and only when a total was actually reported, the report says how many rows
carried one and how many tokens that was. Exclusivity is checked on the whole verb rather than in
the hand form, so `--tokens-total` with `--from-transcript` (which MEASURES a split) is refused too
rather than parsed and dropped.

## How this is proven

| claim | case |
|---|---|
| a total lands in its own key, with no `usage` beside it | `tests/test_pm_ledger_record.py::test_a_hand_row_carries_exactly_what_it_was_given` (amended) |
| both-at-once is refused and writes nothing, all three spellings | `tests/test_pm_ledger_record.py::test_the_record_flags_refuse_and_write_nothing` (amended) |
| the column exists and stays absent-not-zero when nothing reported a total | `tests/test_pm_ledger_report.py::test_the_seeded_ledger_prints_this_exact_table` / `…_produces_this_exact_json_object` (amended) |
| the two sums do not touch, and the summary says which it used | `tests/test_pm_ledger_report.py::test_a_reported_total_is_summed_apart_from_the_split_and_says_so` |
