---
id: bg-an-uncounted-tier-passes-the-case-ceiling
kind: bug
milestone: ms-nothing-is-hand-rolled
name: check budget exits 0 on a tier it has no case count for, and make milestone never measures one
status: closed
caused_by:
changelog: `check budget` now exits 1 on a tier that declares a `[tests] cases` limit and has no census to grade it against — a case count is a fact about the source, so an unmeasured one can drift; a declared `budget` (time) with no run stays merely unmeasured.
---

# an uncounted tier passes the case ceiling

Found running `make milestone` on this tree at the start of 0.7.0: the gate was
red on a count that has been over since before 0.6.0 merged, and 0.6.0 closed
green over it.

## Symptom

`check budget` grades two things per tier — a wall-clock budget and a case
ceiling — from the newest `gate` row in the ledger. When a tier has NO row it
is reported `UNCOUNTED` and **the gate still exits 0**:

    UNCOUNTED   integration — ceiling 430 case(s), and no `gate` row for it
                in this tree's ledger
    [check:budget] PASS — ...; uncounted: integration

`make milestone` is `check matrix budget`. **`matrix` files a `matrix` row, not
an `integration` one**, so nothing inside the milestone gate ever refreshes the
integration census. The only thing that does is somebody running `make
integration` by hand.

## Root cause

The module docstring states the rule and its reason:

> A tier with no row is UNMEASURED: named, never counted as within its ceiling,
> and NOT a finding, **because a tier nobody ran has not got slower.**

That argument is correct — for the TIME budget. It does not transfer to the
CASE ceiling, and it was applied to both. **A tier nobody ran can absolutely
have grown**: the case count is a fact about the source, not about a run. So
the one column that can drift without anybody executing anything is the column
that fails open.

The whole-gate version of this guard already exists twenty lines above
(`if not gates:` → FAIL, citing rule 4 by name). The per-tier version is the
one that is missing, and rule 4 does not have a quorum clause.

## What it cost

`main` at 7f4994f collects **436 integration cases, 432 non-skipped, against a
430 ceiling**. A worktree at that commit reproduces it. The last `milestone`
gate row of 0.6.0 is PASS and there is no `deviation` row, so the release belt
was told the truth as the gate understood it. **The number was over and the
gate could not see it**, which is the first cardinal sin with the tier
unmeasured rather than the census narrowed.

## Fix — and it is two halves, because half is a trap

  * **`UNCOUNTED` on a tier with a declared CASE ceiling is a finding, exit 1.**
    The time budget keeps the current behaviour and the docstring keeps its
    reason; only the count column changes.
  * **The milestone gate must MEASURE what it grades.** On its own, the first
    half makes `make milestone` permanently red in a fresh checkout, because
    nothing in it produces an `integration` row — which is a gate that cannot
    pass, the mirror of a gate that cannot fail. Either `integration` joins
    `GDK_MILESTONE_TIERS`, or `matrix` files a census the count column accepts
    for the tiers its floor run covered.

Landing only the first half is worse than landing neither.

## Out of scope

The time budget's UNMEASURED rule, which is correct as written and argued.

## Taken into 0.7.0

Bound to `ms-nothing-is-hand-rolled` on 2026-09-10. It is a gate-semantics
change and therefore a minor bump — which 0.7.0 already is — and leaving it
would mean merging a milestone whose own full gate cannot see the thing it
grades. The ceiling this bug exposed is raised at the close with its own
argument, and the argument is only worth writing if the gate can enforce it.

## What landed

**Both halves, because the bug says landing one is worse than landing neither.**

  * `check budget` now FAILS on a tier that declares a CASE limit and carries no
    count. The time budget keeps its behaviour and its argument untouched — a
    tier nobody ran has not got slower — and the docstring now says why that
    reason stops at the clock. Probed: a `fuzz = 100` entry with no row reddens
    the gate and names itself; `test_a_declared_case_limit_with_no_count_is_a_FINDING`
    fails against HEAD and passes after.
  * `GDK_MILESTONE_TIERS` is `test matrix budget`, so the gate MEASURES what it
    grades. It was `matrix budget`, and `matrix` files a `matrix` row with no
    per-tier census, which is how the count went unread across a release.

**And the ceiling it exposed was restructured rather than raised**, because
raising it would have re-armed the same trap. 0.7.0 moved 62 cases from
`integration` to `unit` without writing or deleting one: the suite went 1,571
-> 1,586 collected, real growth of 15, while the per-tier unit ceiling read +72
over. **A per-tier count measures tier membership, not growth**, and it reddens
hardest exactly when somebody corrects a tier boundary.

The clock cannot replace it either — `unit` went 706 -> 1,212 cases (+72%) for
8.2s -> 9.6s (+17%), so a tier really can double inside its time budget. So:
**time per TIER** (what a human waits for, and it differs per tier), **count per
SUITE** (`cases = { test = 1575 }`, one run, one census, immune to a case
changing sides).

`make milestone` on this tree: CHECK 5 PASS, TEST 1575 passed, MATRIX PASS on
3.11 3.12 3.13 3.14, BUDGET 1 PASS.
