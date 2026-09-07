---
id: st-a-milestone-declares-a-version
feature: ft-a-milestone-declares-its-version
milestone: "ms-0.3.0"
name: the milestone carries version: and the plan is read as a list
status: done
owner:
depends_on: []
kind: story
---

# the milestone carries version: and the plan is read as a list

A milestone declares `version:` and the id goes back to being a name. The plan
that orders those versions is read here; `the-order-is-declared-and-appended`
adds the verbs that WRITE it.

## Acceptance criteria

1. `version:` is read off a milestone, optional, any non-empty string.
2. `order` in `pm/roadmap/releases.md` is read as a BLOCK list, in declared order.
3. A scalar on the `order:` line reads as no list, never as a one-element one.
4. The current release is a POSITION: the first unshipped entry under
   `version_at = "start"`, the last shipped under `"ship"`.
5. `[pm] version_at` refuses a value outside `start`/`ship` at exit 2.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 4 | unit | `test_current_is_the_first_unshipped_at_start_and_the_last_shipped_at_ship` | new — nothing related a milestone to a release |
| 2, 3 | unit | `test_block_list_reads_in_order_and_a_scalar_is_not_a_list` | new — the reader handled scalars only |
| 4 | unit | `test_an_entry_no_milestone_claims_has_not_shipped` | new |
| 4 | unit | `test_no_plan_at_all_is_no_current_release` | new |
| 5 | unit | `test_version_at_refuses_a_value_it_does_not_know` | amends the `[pm]` exit-2 family |

## Out of scope

Writing `order` — that is `the-order-is-declared-and-appended`. R5 itself is story 02.

## Close

done: ac18ca2 — `version:` on a milestone, `order` read as a block list, and
`current_release` as a position in it. The resolver reads no status field, so it is
never zero-or-several the way "the one milestone in progress" was.
