---
id: 0.4.0/the-tree-names-what-it-lacks
milestone: "0.4.0"
name: The tree names what it lacks, at every layer rule 11 reaches
status: planning
reviewed:
phase:
depends_on: ["0.4.0/every-row-names-its-grain"]
consumed_by: []
---

# The tree names what it lacks, at every layer rule 11 reaches

**Hard rule 11 was written after this milestone was half-planned, and it turned out to be the
milestone.** Six of the fourteen features already were it, each rediscovering the shape in its own
words:

    a-document-points-at-what-it-cannot-hold   "…and its ABSENCE is visible"
    recording-is-on-or-the-gate-is-red         "A tree that is not recording SAYS SO"
    the-surface-says-telemetry                 "…at the MOMENT OF NEED"
    the-unbound-census                         "…REPORTS both ways it can be unbound"
    the-read-verbs-compose                     "…emits EVERY FIELD you would filter on"
    every-row-names-its-grain                  "Every automatic row NAMES the grain"

This feature is the sweep for what is left: three absences the tool can already see and does not
say. Each is one line in a family that exists.

## 1. `owner:` — and this one is a live bug, not a tidy-up

`pm-execution.md` step 1: *"`pm story building <id>` when you begin editing files for a story, and
set `owner:` in the same edit."* Nothing checks it. `execlist.py:91` and `cli.py:777` READ the
field; no gate asks whether it is there.

**That silently breaks `every-row-names-its-grain`.** D2's fallback resolves a session's grain from
the tree — *which story is `in_progress`, for this owner* — and narrows by `owner:`. With `owner:`
blank on every story, the narrowing does nothing, two open stories are always ambiguous, and the
fallback degrades to "omit the key" **exactly when it was supposed to work.** Telemetry then looks
like it is running while attributing nothing, which is this milestone's founding failure wearing a
third hat.

So: a story in an `in_progress` category with no `owner:` is a WARN, in the READY family, beside
"no `branch:`" and "no `phase:`". It is the field that makes the feature it depends on function.

## 2. The Proof budget — the anti-bloat contract, never verified to exist

Every feature template carries it, and it is the milestone's stated defence against test bloat:
*"how many cases this feature should cost, named before it is built and compared after — that is
where test bloat is stopped, not at review."*

`model.empty_section` already answers "is this heading present but empty" and already runs for
`## Ship criterion` and `## Acceptance criteria`. **A feature past `todo` with an empty Proof
budget gets the same line.** One constant, one call, in the loop that already does this.

Deliberately a WARN, not a refusal: a feature whose budget is genuinely "none, this is docs" should
say so in the section rather than be blocked by a gate.

## 3. A gate on the roster that has never run

`[checks] all` names gates; the ledger records what each gate COST. Nothing joins them, so a roster
entry that never produces a row is invisible — and an inert roster entry is a real failure mode
this project has already paid for: **the toolkit is two pinned packages, and each refuses a gate
name it does not know.** A name in the roster that never runs looks exactly like a name that
passes.

`verify --plan` is the natural surface — it already reads `gate` rows and already prints `unknown`
rather than guessing, which is rule 11 working. The line to add is the other direction: *this gate
is on your roster and has produced no cost row here.* The story decides whether it belongs in
`--plan`'s output or beside it.

## Not in scope, because they are already someone's

The absences 0.4.0's own shape creates — an unbound grain, a kind in a pool that `[pm.contains]`
does not declare, a parent with children and no `order:` — belong to `the-unbound-census`,
`the-config-is-the-model` and `the-order-is-one-mechanism` respectively. **This feature must not
grow a fourth item that one of those already owns**; rule 11 is a shared standard, not a bucket.

## Ship criterion

A story `in_progress` with no `owner:` warns. A feature past `todo` with an empty `## Proof budget`
warns. A gate named in the roster with no cost row in this tree is named by `verify`. All three are
WARN lines in families that already exist — **no new rule id, no new verb, no new gate module.** If
this feature adds any of those, it has misread rule 11's "cheapest layer" clause.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_pm_gate.py` for the two READY warnings — its
    `ReadyIsAStampWithACheck` case is a roster of exactly this kind and each new line extends it
    (the handoff warning already moved that count 5 → 6) — and `tests/test_verify_main.py` for the
    roster join
  what already covers this: the READY roster case covers the family's SHAPE, so two of the three
    are one line each in a list plus a fixture field. Only the roster join is genuinely new, and it
    is new because nothing has ever read `[checks]` and the ledger together.

## Out of scope

Refusing on any of the three; all are reports (rule 9). Anything about what `owner:` should
CONTAIN — a name is the project's business, presence is the tool's.
