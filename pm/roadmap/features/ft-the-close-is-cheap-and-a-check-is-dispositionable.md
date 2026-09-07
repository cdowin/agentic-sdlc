---
id: ft-the-close-is-cheap-and-a-check-is-dispositionable
kind: feature
milestone: "ms-a-move-is-an-event"
name: the close is cheap, and a check is dispositionable
status: done
reviewed: docs/reviews/2026-09-07-0.5.0-the-close-is-cheap.md
depends_on: []
consumed_by: []
---

# the close is cheap, and a check is dispositionable

**The hard requirement CAUSED the batching.** `close feature` refuses without a `reviewed:` record.
A review is expensive. So closing is expensive, so closing gets deferred, so grains sit open — and
the only escape hatch, `--force`, writes a `deviation` row that reads as a breach of the belt.

Faced with "pay for a review, or file a deviation against yourself", an operator does neither. It
opens another grain instead. **This milestone's build did exactly that thirteen times.**

## The correction

Nothing is required. A check is a QUESTION the belt asks and the caller answers. Today there are two
answers — true, or `--force` — and one of them is an admission of guilt. There should be three:

    true          the check passed
    dispositioned the caller answered it: skipped, and why. A first-class close.
    false         it is not true and nobody said anything — the belt writes nothing

A skipped review is a JUDGEMENT, not a deviation. *"Small, obvious, I read the diff, no review"* is a
legitimate engineering call and the tree should record it as one — with the reason, against the grain,
forever — not brand it a breach.

    close feature ft-x --skip review-recorded "one-line fix, read inline"

    ok: stories-done — 3 of 3
    ok: feature-verified — make test, reused from 4m ago
    skipped: review-recorded — "one-line fix, read inline"
    ok: findings-landed — no open finding
    feature ft-x: building -> done

`--force` stays, and keeps its meaning: writing ANYWAY, with the false checks named, no reason given.
`--skip <check> "<why>"` is different in kind — the caller answered the question. A skip with no
reason is refused, because an unexplained skip IS a deviation and already has a verb.

## This revises D12, deliberately

D12 says *"a belt is its checks, then one write or a clean error."* That stands. What changes is what
counts as a check being answered: a disposition is an answer. The belt still writes exactly one thing,
still names every check, still refuses when a check is false and nobody spoke.

**Which checks are dispositionable is a DECLARATION, not the tool's opinion** — `[feature] skippable =
["review-recorded"]`. A project that wants review mandatory declares nothing and gets today's
behaviour. Rule 9: the tool reads what the project declared.

`tree-clean` and `on-milestone-branch` are facts about the world, not judgements, and a project that
lists them is making a mistake the tool will let it make — because that is what rule 9 means.

## The disposition is the record

A skip is a FIELD on the arrival the close makes — `skipped: [{check, why}, …]` on that arrival's
one `{ts, kind: "disposition", grain, state, answer, value?}` row (0.5.0/D6) — and the grain's close
evidence names it. `pm ledger show <grain>` prints it beside the status flips. So "which closes
skipped a review, and why" is a question the tree answers, and a milestone review can sweep them: the
review that did not happen per-feature happens once, at the milestone, over a list the tool produced.

**`ts`, never `at`.** Every reader in the package — `ledger.read_rows`, `parse_ts`, `pm ledger
show`'s sort — keys the stamp as `ts`, and a second spelling files a row at the beginning of time.

That is the honest version of what an operator does anyway.

## Ship criterion

`close story|feature` and `release` accept `--skip <check> "<reason>"` for any check the project
declared skippable, print `skipped: <check> — "<reason>"` in the check list, write the status, and
carry the judgement in the `skipped` field of the arrival's own `disposition` row. A skip with no
reason, or of a check the project did not declare skippable, is refused by name. A close that is
REFUSED leaves no `skipped` behind it: the row is minted by the write, not during the check run.

`--force` is unchanged and still mints a `deviation`. A close is never blocked by a check the caller
has answered.

`pm ledger show <grain>` reports dispositions; `pm list` gains a column or the milestone review has to
grep for them (rule 11's read side).

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_conveyor_close.py` beside the belt's existing check-list cases
  what already covers this: `--force`'s deviation cases are the nearest shape and the disposition row
    is a sibling of that row kind — these are rows on that harness, not a new family.

## Out of scope

Deciding WHICH checks a project should make skippable. That is the project's declaration and the tool
does not get an opinion (rule 9). Stock declares nothing, so stock behaviour is unchanged.
