---
id: ft-a-milestone-starts-and-a-lane-counts-once
kind: feature
milestone: "ms-the-filed-issues-are-answered"
name: a milestone starts and a lane counts once
status: building
reviewed:
depends_on: []
consumed_by: []
changelog: A milestone branch under the agent-worktree prefix is refused with the `milestone/…` name to use (`[pm] agent_branch_prefix`, stock `feat/`); `ledger record --grain a,b,c` files one lane as one row that `ledger report` counts once; the loop reviews each lane as it merges, then runs a milestone checkup.
---

# a milestone starts and a lane counts once

Three issues about the loop itself: its start, its ledger rows, and its review cadence.

## Decided (do not re-plan)

- **#52 — a milestone branch under the agent prefix.** No new verb in this milestone. Take the
  issue's option 2: `pm set <ms> branch <b>` and the milestone flip to its building state refuse,
  exit 1, a branch that starts with the agent-worktree prefix, naming the collision and the
  `milestone/<version>-<slug>` name to use instead. The prefix is a GATE key with a stock default of
  `feat/` (through `core/config.py`, seeded commented at the code's value, rule 5). The refusal
  touches writes only; `check pm` does not re-judge milestones already `done` (this tree has
  `feat/release-0-13-*` on two). `ship` mints a release grain on the current branch: leave it alone
  and say so in the report.
- **#59 — one lane, several stories.** `pm ledger record --grain a,b,c` writes ONE row naming every
  grain. `ledger report` counts that row once per feature and once in every total, never summed
  twice. A per-story line shows the shared row marked `*`, with a footnote that says the row is
  shared and not split. Single-grain rows read exactly as before.
- **#49 — review each lane as it merges.** Edit the sources, then re-install here: the
  `run-the-sdlc` skill, the `reviewer` agent's scope, and `SDLC.md` §0/§2. The new loop: when a
  lane merges, one `reviewer` over that lane's range writes that feature's record, and its
  MAJOR-and-worse findings land while other lanes build. The milestone pass becomes a checkup
  (ship criterion, cross-lane seams), at lower effort, writing only the milestone record. Before
  `release`, a narrow review of the commit(s) that landed findings. Confirm `ready-for milestone`
  and `release` accept records written in separate passes; fix them if not.

## Ship criterion

- `pm set <ms> branch feat/x` exits 1 and names `milestone/…`.
- One `ledger record` over three grains counts once in `ledger report` totals.
- The installed skill and reviewer describe per-lane review and a milestone checkup.

## Proof budget

  cases: 4-5
  tier: unit
  lands in: existing pm set / ledger report / install test modules
  what already covers this: search first (rule 10); amend before adding
