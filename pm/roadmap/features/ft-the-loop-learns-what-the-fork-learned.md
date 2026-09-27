---
id: ft-the-loop-learns-what-the-fork-learned
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: the loop learns what the fork learned
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the loop learns what the fork learned

The skill text is the loop an orchestrator runs. A consumer rewrote its copy (inside the kept
`## Project config` block) and wrote five rules and three skills of its own. Most of that is
generic, and each part was measured on real milestones. This feature makes the generic part
canonical, and it owns every edit to the three guidance files this milestone, #66 included.

## Decided (do not re-plan)

All edits go in `src/agentic_sdlc/repo/pm/guidance/`; re-install with `pm install-skills
--force`. Leave out anything that names a language, engine, product or person (rule 8).

- **#66 — a feature closes when it lands; review is a judgment** (moved here from
  `ft-an-arrival-names-what-it-starts`). 0.14.0 (#49) already moved review to one pass per lane
  as it merges. `run-the-sdlc.md` step 8: close a lane's stories and its feature the same day it
  merges. Review is a per-feature judgment: no reviewer for a pure layout or cosmetic change; one
  for any lane that touches state, a schema, a persisted format or input. Two or three related
  landed features may share one reviewer (a bucket), each block keyed `feature: <id>` (#79, D6).
  Never one reviewer over a whole milestone. A feature not sent to review gets an
  orchestrator-written record (one line on what was read, plus the fenced verdict block with no
  findings) as its `reviewed:` target, which `close feature` already accepts. Show that minimal
  record, and a two-block bucket record, in the skill. Step 10: run `make sdlc ARGS='verify
  --milestone'` before `release`, because `release` reuses a green one on the same tree (#74).
- **Findings return cold.** Chris, 2026-09-27 (D8). The orchestrator lands a finding of 10 lines
  or fewer itself. The rest goes to a NEW developer in a fresh worktree off the milestone branch,
  briefed by `dispatch --grain <feature>` plus the review record, one commit per finding. Never a
  warm resume of the old builder.
- **Dispatch discipline.** The orchestrator is the only dispatcher; an agent never dispatches an
  agent. A dispatch past 200k tokens is a warning in the orchestrator's report; past 300k, stop it
  and re-dispatch smaller. One precommit per merge batch, not per story (pm-execution already says
  it; run-the-sdlc repeats it at the merge step).
- **Friction is recorded when it happens.** Three writes, at the moment it costs time: `lesson
  record`, a GitHub issue on the kit with the minutes it cost, and a memory note. A lesson recorded
  twice is a kit defect: file it.
- **pm-execution folds.** No dispatch and no status move while the milestone is in a
  planning-category state. The "who needs it?" test before a note is promoted to a grain. Shared
  tree: history moves forward only, no broad `pkill`, re-derive line numbers before an edit. A
  decision lives at one grain. A review is sized to its feature. A grain's `changelog:` line: the
  hook plus the why, read the source before writing it, invisible work gets `none`.
- **pm-operations folds** (§ Decomposing work). What to cut from a story; only the load-bearing
  gotchas; cite `file::symbol`, never a line number; a self-review checklist before handoff.

## Ship criterion

- The installed `run-the-sdlc` says close-as-it-lands, review-by-judgment, findings-return-cold,
  and friction-three-writes, and shows the minimal record and a keyed bucket record.
- The installed `pm-execution` carries the planning-state freeze and the changelog-line rules.
- `tests/test_install.py` reports every installed skill byte-current after the re-install.

## Proof budget

  cases: 1
  tier: unit
  lands in: the existing install / skills test module
  what already covers this: the byte-current install check covers the text; add one case only if
  a skill section is asserted by name
