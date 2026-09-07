---
id: ft-a-lesson-surfaces-where-you-stand
kind: feature
milestone: "ms-a-move-is-an-event"
name: a lesson surfaces where you stand
status: done
reviewed: docs/reviews/2026-09-07-0.5.0-a-lesson-surfaces-where-you-stand.md
depends_on: []
consumed_by: []
---

# a lesson surfaces where you stand

**This is the feature that stops the lesson store being decoration.** D1 records why it exists: the
namesake package captures patterns faithfully, never reads them back in any way that changes an
outcome, and nothing in its architecture reports that.

Hard rule 11's second half is the standard: *a capability this package HAS is named in the surface
someone is standing in when they need it.* A lesson in `ledger.jsonl` that surfaces only when someone
runs a verb they would have to already know about is a capability nobody has.

## Where someone is standing

The moment a lesson is worth reading is the moment the same grain or the same rule comes up again:

    a belt runs a check that has a lesson against its rule
    a move touches a grain that has a lesson against it
    ready-for names a blocker whose check carries one

At each, it is printed with its source path and emitted on `rung.enter` / `check.verdict`, so a human
reading stdout and an agent reading the stream get the same fact at the same instant.

## What it must not become

**A lesson is never a gate.** It does not block, refuse, or change a verdict — a check's exit code is
the check's business and a recorded observation has no vote. It is printed beside the verdict, always
with `source`, so the reader goes to the record rather than trusting a paraphrase.

**And never a nag.** A lesson surfacing on every unrelated run is noise, and noise is how rule 11's
surfaces get muted by the people they are for. Scope is exact: the grain named, or the rule named. No
fuzzy matching and no "related" — that is the inference edge this package does not have.

## Ship criterion

A lesson recorded against a grain or a rule is printed and emitted at the next belt operation that
touches that grain or runs that rule, with its source path, and at no other time. It never changes an
exit code.

**Amended at close (B3, 2026-09-07).** The criterion originally required
`agentic-sdlc lesson show [--grain <id> | --rule <id>]` here. It moves to
`ft-a-lesson-is-a-row-bound-to-a-grain`, which owns `lesson record` and the row kind itself: one verb
module, one `--help`, one place a reader learns both halves. Nothing in this package can WRITE a
lesson row yet, so a read verb landing here would ship a surface with no producer — and splitting the
two across features is the second-scoreboard shape this package deletes everywhere else.

The amendment is honest about what it costs: **until that feature lands, a lesson is still only
readable at a belt moment.** A row naming neither a grain nor a rule surfaces nowhere and is
unreachable for the life of the tree — the reviewer's sharpest case, recorded here rather than closed
over.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_ledger.py` and `tests/test_belts.py`
  what already covers this: the belt harness already asserts what each belt PRINTS per check; the
    surfacing cases are rows on it. The never-changes-exit-code case is the one that must exist.

## Out of scope

Ranking which lesson matters most when several match. Print them all in recorded order — choosing is
inference, and the caller has the source paths.
