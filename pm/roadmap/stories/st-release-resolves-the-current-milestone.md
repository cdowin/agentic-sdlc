---
id: st-release-resolves-the-current-milestone
feature: ft-the-order-is-declared-and-appended
milestone: "ms-0.3.0"
name: release with no argument takes the current milestone from the plan
status: done
owner:
depends_on: ["st-pm-order-and-pm-next"]
kind: story
---

# release with no argument takes the current milestone from the plan

The plan already knows which version is current; making the human retype it is
how a typo ships the wrong number. And shipping OUT of order is what a belt
should stop.

## Acceptance criteria

1. `release` with no argument resolves the current version from `order` and
   says which entry it took and why.
2. A version that is not the current one is refused naming BOTH, and writes
   nothing.
3. A tree with no plan still honours an explicit version — adopting the plan is
   not a precondition for releasing.
4. No plan and no argument is refused naming `pm order`.
5. An EMPTY positional is graded, never read as absent.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_release_with_no_argument_takes_the_current_version_from_the_plan` | new, in the belt's own module per the budget |
| 2 | unit | `test_a_version_that_is_not_current_is_refused_naming_both` | new; extends the belt's refusal shape |
| 3, 4 | unit | `test_no_plan_at_all_still_honours_an_explicit_version`, `test_no_plan_and_no_argument_is_refused_naming_pm_order` | new |
| 5 | unit | `test_the_version_refusal_matrix_is_exit_2` (existing, `''` row) | the EXISTING matrix caught it |

Criterion 5 is the defect this story introduced and fixed inside itself:
reading `release ''` as "no argument" resolved a version from the plan and ran
the belt — whose `gate` check is `make milestone` — inside the unit tier. Filed
as `0.3.0/bugs/a-unit-test-can-spawn-the-full-gate`, which is why the tier is now
enforced at runtime and not merely derived.

## Out of scope

`release` resolving a milestone by its id rather than its version, which breaks
the moment an id becomes a slug. Raised by the feature review; it belongs to the
milestone reviewer.

## Close

done: 699ccca — the plan supplies the version and refuses one out of order. The
empty-positional fall-through it introduced is fixed with the existing matrix as
its proof.
