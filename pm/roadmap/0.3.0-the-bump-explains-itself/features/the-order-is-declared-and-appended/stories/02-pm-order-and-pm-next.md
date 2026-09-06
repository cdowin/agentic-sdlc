---
id: 0.3.0/the-order-is-declared-and-appended/02-pm-order-and-pm-next
feature: 0.3.0/the-order-is-declared-and-appended
milestone: "0.3.0"
name: pm order appends inserts removes and prints and pm next names the first unshipped
status: done
owner:
depends_on: ["0.3.0/the-order-is-declared-and-appended/01-the-list-writer-preserves-every-other-byte"]
---

# pm order appends inserts removes and prints and pm next names the first unshipped

Authoring and SCHEDULING are separate acts: a milestone declares `version:`
without joining the plan, and this verb puts it on one. Built as the thin thing
the feature record asks for — it retires into `pm add` in 0.4.0.

## Acceptance criteria

1. `pm order` appends, inserts before a named entry, removes, and bare prints
   the plan with each entry's milestone and state.
2. It does NOT interrogate the tree: `--append 9.9.9` on a tree where no
   milestone claims it is valid, and R1 reports the contradiction.
3. It refuses only facts about its INPUT — a duplicate is a no-op that says so,
   an empty or non-literal version is exit 2, an insert before an absent entry
   is refused, two edits in one invocation is exit 2.
4. `pm next` prints the first unshipped entry and the milestone claiming it.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `TheVerbWritesThePlan` (4 cases) | new module `test_pm_order.py`, per the proof budget |
| 2 | unit | `test_append_does_not_interrogate_the_tree` | new — it is the package's own split |
| 3 | unit | `TheVerbRefusesOnlyFactsAboutItsInput` (5 cases) | the version grammar REUSES `model.segment_is_literal` (SDLC §5); one case per class, no fresh matrix |
| 4 | unit | `test_next_is_the_first_unshipped_entry_and_who_claims_it` | new |

## Out of scope

`pm roadmap`, which belongs to `the-plan-and-the-tree-agree`.

## Close

done: 699ccca — `pm order` and `pm next`, thin on purpose. The verb refuses its
input and the R rules report the tree, which is the split this package states.
