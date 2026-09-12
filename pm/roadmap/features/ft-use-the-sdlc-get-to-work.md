---
id: ft-use-the-sdlc-get-to-work
kind: feature
milestone: "ms-a-session-starts-knowing-what-it-can-do"
name: use the sdlc, get to work
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# use the sdlc, get to work

Chris, 2026-09-12, watching 0.9.0–0.11.0 get built in one session: *"This is exactly how the SDLC is
supposed to behave… encode this so that future projects using the SDLC just start off strong like
this. I want to be able to go into one of my other projects and just say 'use the sdlc, get to work'
and this is what it feels like."*

**The measured difference.** In 0.8.0 there were 21 builder dispatches, one story each, at 1500–2400 s
and 60–310 tool calls apiece. There was also an xhigh reviewer per feature, taking 950–1540 s each,
and a scout, a spec review and a po pass before anything was built. In 0.9.0 and 0.10.0, one
developer took a whole feature or a lane of features in one context: 513–1424 s, 39–114 tool calls,
115–211k tokens each. Eight lanes ran concurrently in their own worktrees, and all 6 of 0.9.0's
stories were built in 22 minutes. The loop that did it:

1. **No planning pass over planned work.** If a grain file (feature, story or bug with a Fix)
   outlines the work, the grain file IS the brief. There is no po or scout re-plan. An unplanned
   feature gets its open questions DECIDED by the orchestrator inline, in the dispatch.
2. **One developer per feature, or per lane of features that share files.** The whole thing goes
   in one context: write, then refine. Reviewers polish.
3. **Lanes on disjoint files run concurrently, each in its own `agent-worktree.sh new <slug> <base>`
   worktree off an explicit base.** The builder commits on its branch. The orchestrator merges each
   branch into the milestone branch when it reports (`*.jsonl merge=union` keeps ledgers
   conflict-free).
4. **The next milestone does not wait for this one's release.** Its integration branch is cut early
   from the current tip. Lanes that do not collide with in-flight work start immediately, and the
   earlier milestone merges forward when it lands.
5. **Two builders splitting one area get a written CONTRACT in both prompts**, such as a row schema,
   so they build against it concurrently rather than serially.
6. **The brief is short**: the grain path(s); what is decided; the files other lanes own; `make
   unit` only; commit on your branch; and a ≤15-line report with the changelog sentence, NEEDS YOU
   and NOT verified. It does not tell the builder to read SDLC.md, write a plan, or run a wide gate.
7. **The orchestrator decides builder questions itself** unless they are outward-facing. It runs
   each belt as the next action, and it asks for release-act permission (push, PR, merge, tag,
   issues) ONCE, up front.
8. **One reviewer per milestone, effort `high`,** writes the feature records and the milestone record
   in one pass. Nothing runs above `high`.
9. **Measure every dispatch** (duration, tool calls, tokens) against the previous milestone, in the
   ledger.

## The work

- A kit-owned skill, `run-the-sdlc`, shipped through `pm install-skills` like `writing-plans`. Its
  description triggers on "use the sdlc", "get to work", "work the milestone" and "build the next
  milestone(s)". Its body is the loop above, as imperative steps with the exact commands.
- The installed `architect` brief's loop section is rewritten to this loop. It keeps the Phase 0
  line from `ft-the-kit-ships-its-planning-skills`, and drops any step that dispatches `po`,
  `milestone-reviewer` or a scout over a grain that already outlines its work.
- `sdlc-template.md` (what `install-sdlc` renders into a consumer's SDLC) and this repo's `SDLC.md` §2
  say the same thing: one builder per feature lane, a worktree per lane, milestones stacked, and one
  review per milestone.
- The auto-loaded `pm-execution.md` gains one line naming `run-the-sdlc` where an operator stands
  (rule 11).

## Ship criterion

In a fresh consumer after `init`, "use the sdlc, get to work" matches the `run-the-sdlc` skill's
description, and its body names each of the 9 steps with the command it runs. The installed
architect brief dispatches no `po`, scout or spec review before a developer when the grain outlines
the work. `tests/test_install.py` proves the skill and the brief byte-current here.

## Proof budget

  cases: 1–2 (the install census names the new skill; a brief/skill phrase check if one exists)
  tier: unit
  lands in: tests/test_pm_guidance.py, tests/test_install.py
  what already covers this: the install currency checks cover every shipped skill and brief.
