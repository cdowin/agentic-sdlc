---
id: st-a-state-the-ledger-shows-held-is-not-called-never-held
kind: story
feature: ft-a-gate-verdict-is-true-of-the-tree
milestone: "ms-a-consumer-can-take-the-bump"
name: a state the ledger shows was held is not called never held
status: planning
owner:
depends_on: []
changelog:
---

# a state the ledger shows was held is not called never held

Issue: #30.

U1's WARN (`checks/pm.py:456-464`) says a declared state has *"never been held by any grain in this
tree … a flow the project is not running"*, and `pm init` prints the same census as `never held:`
(`pm/skills.py:250`). Both read `inventory.state_usage` (`pm/inventory.py:1358`), which counts only
each grain's CURRENT `status:`. On a tree at rest, every `in_progress` rung reads as never held.
Those are exactly the rungs the conveyor exists to get used. The ledger holds the rows showing
otherwise. One consumer closed four `fixed` bugs, and the next `check pm` said `fixed never held`
while the milestone ledger had just gained four `"from":"fixed"` rows. It also reported milestone
`building`/`reviewing` as never held on milestones that had been built and reviewed.

The WARN is itself an inference from a snapshot (rule 9), and one consumer narrowed its 0.4.0 ladder
because of it.

## Acceptance criteria

1. A state counts as held if any grain holds it now, OR any `status` row's `from`/`to` (or a
   `disposition` row's `state`) in the tree's ledgers names it for that kind.
2. The WARN and `pm init`'s census name only states held by neither. The wording drops "a flow the
   project is not running" and says what was read (current statuses plus the ledger).
3. A tree with no ledger rows reports exactly as today, so the census is not weakened where there is
   no history to read.
4. Probe: the #30 shape (bugs closed `fixed → closed` and nothing `fixed` now) does not report
   `fixed` as never held; a state named nowhere still does.
5. The ledger read stays cheap. `check pm` gate cost on this repo does not move by more than noise
   (`pm ledger report` gate cost, before and after).

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 4 | unit | temp tree with the #30 rows and no current `fixed`. Must fail at HEAD | amend the U1 case |
| 3 | unit | the same tree with no ledger | amend |
| 5 | — | gate-cost rows quoted in the close | n/a |

## Semver

Minor: the WARN's line shape changes (rule 6).
