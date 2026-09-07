---
id: ft-the-conveyor-pushes-back
kind: feature
milestone: "ms-a-move-is-an-event"
name: the conveyor pushes back
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# the conveyor pushes back

**Every surface this package has is PULL. `pm status` answers when asked. `check pm` warns when run.
The breadcrumb prints at a move — so a grain nobody moves prints nothing, forever.**

An open grain is silent. That is the defect. Silence is the DEFAULT state of work in progress, so
leaving a thing open costs nothing and closing it costs a review — and an operator under a clock will
batch every single time. This milestone's own build did it three times, having written the rule down
twice: thirteen grains built, zero closed, seven features sitting `planning` with finished code in the
tree and not one review dispatched until somebody shouted.

The framework did not fail to be read. **It never spoke.**

## Why the existing pieces do not cover it

    pm status              answers if you run it
    check pm               WARNs if you run it, and only about tree SHAPE
    the breadcrumb (0.4.0) prints AT a move — a grain nobody moves is silent
    ready-for              answers if you ask it
    every-grain-is-on-a-stopwatch (0.4.0)   MEASURES age; nothing surfaces it unbidden

Each is a reader waiting to be called. There is no back-pressure anywhere in the conveyor, and
back-pressure is the whole idea of a conveyor.

## The shape — three encodings, none of them a daemon

Rule 2 forbids booting anything, so this cannot poll. It does not need to: **the verbs already run.**
An operator invokes `pm`, `check`, `close`, `ledger record` dozens of times an hour. Every one of
those is a surface the tree is already standing in.

**1. Every WRITE reports the tree's open work.** Not the grain you named — the whole tree, one line:

    [pm] feature ft-x: planning -> building
    next: `close feature` asks stories-done, feature-verified, review-recorded, findings-landed
    open: 7 in_progress, oldest ft-the-tool-emits 41m — 0 of 7 carry a review record

Derived entirely: the count from `[pm.states.*]` categories, the age from the stopwatch's own status
rows, the review count from `reviewed:` resolving. No opinion, no advice — a census, in the surface
the operator is already looking at, every single time they write.

**2. A CROSSING is announced at the moment it happens.** 0.3.0 recorded *"dispatch a feature's review
the moment `ready-for feature` goes READY"* and made it prose in a document. It is derivable: when a
`close story` makes its parent's last story done, the belt KNOWS the feature just became reviewable
and says nothing. It should say it, on the write that caused it:

    next: `close feature ft-x` — this close made it READY (4 of 4 stories done)

READY stops being a question you must remember to ask and becomes an event you are told about.

**3. A DECLARED work-in-progress limit, reported when exceeded.** `[pm] wip = 3` — the project's own
number, never the tool's. Over it, every write says so and names the oldest. Rule 9 holds: the tool
reads a declaration and reports a fact; it never refuses, because `--force` is the deviation and this
is not even a gate.

## What it must not become

**Never a refusal.** A conveyor that blocks you from opening work is a conveyor people route around.
It reports; the caller decides. Rule 9.

**Never advice.** `open: 7 in_progress, oldest 41m` is a census. *"You should close something"* is an
opinion and must not ship — the same line D1 draws between `next_checks` and `suggested_action`.

**Never noise.** A tree with nothing open prints nothing. One line, only when there is something to
say, and `[pm] pressure = false` turns it off for a consumer parsing output strictly (rule 6).

## Ship criterion

Every `pm` write, every belt write and every `check pm` run reports the tree's open work when there is
any: how many grains sit in an `in_progress` category, the oldest with its age, and how many lack the
artifact their close requires. Silent when nothing is open.

A close that makes a parent READY says so on that write, naming the belt that closes the parent.

`[pm] wip` is honoured when declared and absent when not; exceeding it is a reported line and never a
refusal.

A test asserts every number in the line traces to `[pm.states.*]`, the ledger's status rows, or a
frontmatter field — the same derived-only guard `ft-every-move-breadcrumbs-the-next-step` already
carries.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: `tests/test_pm_verbs.py` on the `StatusVerbQuartet`, and `tests/test_conveyor_close.py`
  what already covers this: the quartet covers what a write PRINTS for all four kinds, and the
    breadcrumb already extended it — the pressure line is another row on it. The crossing case
    belongs with the close belt's existing tests.

## Out of scope

Measuring per-state time — `ft-time-is-measured-per-state-and-rolls-up` owns that, and this feature
READS it. Building one without the other gives a pressure line with no age in it.
