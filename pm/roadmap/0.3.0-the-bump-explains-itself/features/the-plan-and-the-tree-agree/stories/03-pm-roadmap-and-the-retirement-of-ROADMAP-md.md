---
id: 0.3.0/the-plan-and-the-tree-agree/03-pm-roadmap-and-the-retirement-of-ROADMAP-md
feature: 0.3.0/the-plan-and-the-tree-agree
milestone: "0.3.0"
name: pm roadmap prints the plan and ROADMAP.md retires
status: building
owner:
depends_on: ["0.3.0/the-plan-and-the-tree-agree/02-history-is-a-prefix"]
---

# pm roadmap prints the plan and ROADMAP.md retires

`ROADMAP.md` was two things wearing one name: a hand-maintained index of
milestones still in the tree — the second scoreboard this tool forbids one grain
down — and the only record of what `pm retire` deleted. The first is derivable;
the second needs no file.

## Acceptance criteria

1. `pm roadmap` prints every scheduled release with its milestone and state,
   then the backlog, and writes nothing.
2. An unreadable plan is refused rather than printed as empty.
3. A version two milestones claim is NAMED, never picked.
4. `pm retire` no longer appends to `ROADMAP.md`, and says what outlives the
   directory — `order` keeps the version, or nothing does and it says so.
5. `pm init` no longer seeds the file. An existing one is left alone, not deleted.
6. The CHANGELOG names the file retired and `pm roadmap` as its replacement.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_it_prints_every_scheduled_release_then_the_backlog`, `test_it_writes_nothing` | new |
| 2 | unit | `test_an_unreadable_plan_is_refused_rather_than_printed_as_empty` | new — same rule-4 shape as R5's F3 |
| 3 | unit | `test_a_version_two_milestones_claim_is_named_rather_than_picked` | new |
| 4 | unit | `test_the_plan_is_what_outlives_the_directory`, `test_retire_writes_no_roadmap_file_and_needs_none` | amends the whole `Retire` class, which asserted the row |
| 5 | unit | `test_init_stands_up_a_usable_tree_from_nothing` amended; `test_init_verb.WRITES` roster | amended, both |

Also landed here: `core.apply` now refuses a DELETE_TREE whose parent is not
writable. Removing the index step left the plan one step long, and the walk
could empty the directory then fail to unlink it — a gutted grain. `DELETE_FILE`
had the check; `DELETE_TREE` did not.

## Out of scope

Deleting a consumer's existing `ROADMAP.md`. This release stops WRITING to it.

## Close

done: in-place — `pm roadmap` derives the index, `retire` says what outlives the
directory, and the apply primitive stopped being able to gut a grain.
