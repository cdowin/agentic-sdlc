---
id: ft-a-lesson-is-a-row-bound-to-a-grain
kind: feature
milestone: "ms-a-move-is-an-event"
name: a lesson is a row bound to a grain and a rule
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# a lesson is a row bound to a grain and a rule

Capture, and only capture. A lesson is an append-only ledger row naming the grain it came from, the
rule or check it is about, and the record it was derived from.

    {ts, kind: "lesson", grain, rule, source, text}

`source` is a path — a review record, a `.gate-reports/` transcript, the deviation row that prompted
it. The stamp is `ts`, the one every reader in this package keys on: spelled `at`, a row sorts as
the empty string and files at the beginning of time.

**The row points at its source; it never restates it.** A lesson store that paraphrases the
record it came from is a second scoreboard, and it drifts the way every duplicate in this package's
history has.

## Where they come from

Three inputs the tree already produces and currently discards at the moment of the move:

    a gate verdict       check.verdict, from ft-one-event-shape-serves-three-readers
    a review finding     the below-MAJOR findings the severity rule says to "record and carry"
    a --force deviation  the checks that were false, already a row

The middle one is why this feature exists. 0.3.0's severity rule says findings below MAJOR are
*recorded and carried* — and "carried" currently means a human remembers between sessions. Rule 11's
operator has no memory of last week.

## Not a model, and the counter-example is specific

The unrelated PyPI package's `Learner` ranks by a `frequency` it never increments, pinning confidence
at `0.1` forever (D1). The lesson is not that ranking is hard — it is that **anything inferred needs
a feedback edge, and a reader/writer has nowhere to put one.** So: no ranking, no scoring, no
similarity, no confidence. A lesson is recorded and reported verbatim; the caller decides what it is
worth. Rule 9.

## Ship criterion

`agentic-sdlc lesson record --grain <id> --rule <id> --source <path> <text>` appends one row, routed
by the grain the way every other row is, refusing a `--source` resolving to nothing exactly as
`--review-record` already does. `pm ledger show <grain>` prints lessons in the same stream as its
status and dispatch rows.

Nothing is inferred, scored or ranked, and a test asserts the row's fields are the ones written with
no derived field among them.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_ledger.py`, beside the row-kind cases
  what already covers this: the row-routing and unresolvable-pointer cases both exist; this is a new
    row kind on both harnesses.

## Out of scope

Reading them back — `ft-a-lesson-surfaces-where-you-stand`. Capture alone does not satisfy this
milestone's ship criterion, and shipping this without that one is the failure mode D1 names.
