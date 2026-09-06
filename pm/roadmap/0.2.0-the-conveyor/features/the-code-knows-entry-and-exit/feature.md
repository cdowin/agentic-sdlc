---
id: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: The code knows entry and exit; the config knows every state between
status: planning
reviewed:
phase: 9
depends_on: ["0.2.0/every-question-is-asked-of-a-category", "0.2.0/the-ledger-rows-carry-categories", "0.2.0/the-inner-levels-are-belts-too", "0.2.0/the-belt-reports-and-finishes", "0.2.0/the-project-declares-its-flow"]
consumed_by: []
---

# The code knows entry and exit; the config knows every state between

**Chris, 2026-09-05:** *"The code itself is just a state transition machine. It just knows an
entry and an exit state. The code sees the config defining planning, ready, packaging, etc. and
mapping those to todo, in progress, or done. The code allows the CLI to reflect back what is
configured, what transitions can look like."* And: *"Open up a milestone, stamp stamp stamp stamp
to done."* 0.2.0 is the whole MVP — no 0.3.0, no deferrals, no open bugs.

The ladder the same shape at every level: **plan → ready → build → test → review → done.** Each
stamp is ONE command (`pm <kind> <state> <id>`, or the belt step that runs it); the state a step
writes is the project's word for it, read from `[pm.transitions.<kind>]`; the engine knows only
which of the three categories it sits in. **Nothing fancy and automatic:** no move cascades, and a
tree whose levels disagree gets a warning line, not a failure and not an action.

Measured on 2026-09-05, before this feature: `ready` is a word with no verb and no check at all
three levels; one seven-word list is pasted onto three grains while the belts write a third of
it; this project declares no transitions; claiming a story leaves its parents at `planning`;
a milestone can ship over open bugs; and the review records for two built features are HOLD.

## Ship criterion

1. `pm vocabulary` prints, for every kind, each state in exactly one category and, for every
   state outside `todo`, the step that writes it. A declared state outside `todo` that no step
   writes is refused at exit 2 naming the kind and the state.
2. No state word survives in `conveyor/steps.py`, `conveyor/driver.py`, `pm/cli.py`,
   `pm/ready_for.py`, `pm/ledger.py` or `checks/pm.py` outside the config reader — phase 7's
   census test extended to the belts.
3. `ready` is stamped by `pm <kind> ready <id>` and nothing else; `check pm` WARNS, exit code
   unchanged, when a grain at or past `ready` has an empty criteria section, a feature has no
   stories, or a milestone has an unphased feature or no `branch:`.
4. Every cross-level disagreement (D2, D3, D5, D6) is a `  WARN  ` line that names both grains,
   counted in the summary, never a finding and never an exit code; no verb moves a parent on a
   child's account, and `close story`'s claim touches the story alone.
5. `pm ready-for milestone` names every open bug whose `fix_milestone` is the milestone.
6. The three bugs open against 0.2.0 are `closed`, and no bug carries another milestone.
7. Every record under `docs/reviews/` naming 0.2.0 has no finding at `open`, and the ruling on a
   callee's exit 2 is `decisions.md` D11.
8. 0.2.0's stories, features and the milestone itself close through `close story`,
   `close feature` and `release`, and the ledger's status rows say so.

## Proof budget

One test per criterion, at the cheapest tier that can fail; the belt cases live beside the
existing `tests/test_conveyor_close.py` cases and the config cases beside `tests/test_pm_flow.py`.
Criterion 8 is not a test: it is the tree, read by `pm ledger show`.
