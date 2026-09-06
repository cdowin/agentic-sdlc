---
id: 0.3.0/adopt-runs-where-the-bump-lives/01-the-belt-runs-where-the-bump-is-tracked
feature: 0.3.0/adopt-runs-where-the-bump-lives
milestone: "0.3.0"
name: the belt runs wherever the project tracks the bump
status: building
owner:
depends_on: []
---

# the belt runs wherever the project tracks the bump

`adopt` refused before running any check, because it wanted a milestone
directory named for the version. A project that folds toolkit work into an open
milestone as a feature could not run the belt at all — so all seven checks got
done by hand, in an invented order, and the flow was missed.

## Acceptance criteria

1. `adopt <version>` runs its checks on a tree that tracks the bump anywhere —
   a feature, a story, or no grain at all.
2. `adopt` writes nothing, so the milestone directory is only where a ledger row
   would land; the run says which it found, or that there is nowhere.
3. `release` and `close story|feature`, which DO write a status, still refuse
   without it.
4. The `--help` line says it adopts a devkit PIN, so it reads differently from
   `release <version>` beside it.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | integration | `test_adopt_runs_every_check_where_the_bump_is_tracked_as_a_feature` — at HEAD it asked ZERO of seven checks | new; nothing covered the entry condition because until a differently-shaped consumer tried it, there was no reason to think it was one |
| 2 | integration | `test_adopt_names_the_ledger_when_the_bump_is_tracked_as_a_milestone` | new |
| 3 | integration | `test_a_belt_that_writes_still_needs_the_milestone_directory` | the regression guard for the branch deliberately left refusing |
| 4 | integration | `test_the_help_line_says_adopt_takes_a_pin_not_a_grain` | new |

Verified by the orchestrator against the tree: `adopt 0.2.0` on this repo now
runs its checks and prints where a row would land. 22 cases green.

## Out of scope

Whether a bump SHOULD be a milestone. Several projects will want it to be, and
this does not take that away — it stops the belt requiring it.

## Close

done: 1285784 — the entry condition is gone for a belt that writes nothing, and
the help line says what it adopts.
