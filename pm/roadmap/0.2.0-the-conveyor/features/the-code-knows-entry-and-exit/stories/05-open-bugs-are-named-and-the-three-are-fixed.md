---
id: 0.2.0/the-code-knows-entry-and-exit/05-open-bugs-are-named-and-the-three-are-fixed
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: An open bug against the milestone is named, and the three open bugs are fixed
status: building
owner:
depends_on: []
---

# An open bug against the milestone is named, and the three open bugs are fixed

## Acceptance criteria

- `pm ready-for milestone <id>` names every bug whose `fix_milestone` is `<id>` and whose category is not `done`, as a BLOCKED line, exit 1; `release`'s check list includes it.
- `0.2.0/bugs/a-composition-has-no-slot`: `precommit` and `milestone` in `Makefile.devkit` open their own gate slot, so `verify --plan` reports a cost for the wide rungs; `make -n` still runs nothing.
- `0.2.0/bugs/a-collapsed-milestone-has-no-verb`: `pm retire` retires a milestone in any `done` state (`obe` included) and the ROADMAP row says which.
- `0.2.0/bugs/the-slot-names-are-spelled-in-six-places`: one spelling, in the config reader.
- All three at `closed`.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | an open bug blocks; a closed one does not; another milestone's is ignored and counted | amend tests/test_pm_ready_for.py (`MilestoneBelt.test_an_open_bug_against_the_milestone_blocks_and_is_named`) |
| 2 | integration | a composition run leaves a `gate` row named for it | amend tests/test_makefile_gates.py — the Makefile agent's; not in this story's commit |
| 3 | unit | retire of an obe milestone | amend tests/test_pm_verbs.py (`Retire.test_retire_of_an_obe_milestone_writes_a_row_that_says_so`) |
| 4 | unit | the slot names have one source | amend tests/test_grain_shape.py (`test_the_slot_names_have_one_source`) |

## Out of scope

New bugs. If fixing one finds another, it is filed against 0.2.0 and fixed here too.

## Close

done: 844268e 0a63a80 ef174b9 — ready-for milestone names open bugs; the composition slot, the collapsed-milestone retire and the one slot spelling landed; all three bugs closed
