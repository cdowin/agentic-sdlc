---
id: st-the-ledger-binds-to-the-release
feature: ft-the-ledger-binds-to-the-current-release
milestone: "ms-0.3.0"
name: the ledger is keyed by the current release not by a status flag
status: done
owner:
depends_on: []
kind: story
---

# the ledger is keyed by the current release not by a status flag

Every gate run in this repo during the whole of the 0.3.0/0.4.0 design work
printed `REFUSED — no milestone in pm/roadmap is in progress`. Gate cost is a
fact about a RUN, and the run happened whether or not anybody had flipped a
status.

## Acceptance criteria

1. A cost row is filed against the current release resolved from `order` and
   `version_at`, and is never refused for want of an in-progress milestone —
   neither none nor several.
2. `check budget` and `verify --plan` read the same file by the same
   resolution, so the number a human sees and the number the gate grades cannot
   disagree.
3. A tree that can answer from neither the plan nor a single in-progress
   milestone refuses, naming `pm order`. (Narrowed from the criterion —
   decision D1 on this feature.)

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_a_tree_at_rest_with_a_plan_files_the_row` | new — this IS the bug |
| 1 | unit | `test_several_milestones_in_progress_is_no_longer_a_question` | amends the old exit-2 "which one owns this" param |
| 3 | unit | `test_the_verb_names_what_it_cannot_answer_and_writes_nothing` | amended: two of its three rows change what they refuse FOR |
| 2 | — | one resolver, `model.release_ledger_dir`, called by all three sites | structural: the two readers cannot diverge because there is one function |

Measured on this tree: before, every `make check` printed the REFUSED line and
dropped the row; after, `make check` is clean and the row lands.

## Out of scope

Where the file sits. 0.4.0's pools move it to `ledgers/<version>.jsonl`; this
story changes what it is KEYED BY.

## Close

done: a17b5c0 — one resolver replaces four `in_progress_milestones` call sites,
and the REFUSED line that printed on every gate run of this session is gone.
