---
id: ft-the-kit-says-one-loop
kind: feature
milestone: "ms-a-session-starts-knowing-what-it-can-do"
name: the kit says one loop
status: planning
reviewed:
depends_on: ["ft-use-the-sdlc-get-to-work"]
consumed_by: []
changelog:
---

# the kit says one loop

Chris, 2026-09-12: *"be mindful of any crud leftover that would have you run the SDLC in the old
way… prune out any text that's pointing to bad patterns or wrong patterns. CLAUDE.md audit,
agents/skills audit, docs/comments audit… fast, but on the rails. Build features, review, close,
move move move. Close milestone, move."*

`ft-use-the-sdlc-get-to-work` shipped the loop as `run-the-sdlc`, which is the single source of truth
(`src/agentic_sdlc/repo/pm/guidance/run-the-sdlc.md`). Every other surface an operator or agent reads
must agree with it, or point at it, or say nothing. **Old patterns to remove wherever they are
prescribed, not just mentioned as history:**

1. One builder dispatch per STORY, where the loop says one developer per feature or lane.
2. A reviewer dispatched per FEATURE as it goes ready, where the loop has one reviewer per milestone
   writing every record in one pass.
3. A scout, spec review (`milestone-reviewer` before execution) or `po` decomposition over work a grain
   already outlines, and "decomposition happens after X ships, by a scout, then stories".
4. Builders told to READ CLAUDE.md, SDLC.md or rule files before the first edit.
5. Any effort above `high`, or "the reviewer always runs at the strongest setting".
6. Serial "builders never commit" as the default. Now each lane has a worktree and a branch it
   commits on, and the orchestrator merges.
7. A builder merging into the milestone branch or tearing down its own worktree.
8. Simplifier, test-writer or tech-writer as a MANDATORY pass in the loop. They are optional tools.
9. "The leader never writes code". The orchestrator fixes small things itself.
10. Stop-and-ask where the rule is file-and-continue (`executing-plans`).
11. `GDK_LEDGER_GRAIN` export presented as how attribution works. Now the `dispatch` stamp line
    does it, plus `pm ledger record --agent-id … --outcome …` on return.
12. Batching: closes, reviews or flips saved for the end. Every belt runs as the next action.

**Out of scope (history, append-only):** decisions logs, review records, `releases.md`, closed grains,
and `improvements.md`'s dated entries. CLAUDE.md's hard-rule numbering is append-only (a rule is
trimmed inside itself). Rule 11 still holds: cut prescriptions, never a capability's only mention.

## Ship criterion

`git grep` over the shipped surfaces (installables, guidance, CLAUDE.md, SDLC.md, README.md,
docs/ excluding reviews) finds none of the 12 patterns prescribed. Each surface that describes the
dispatch/review loop agrees with `run-the-sdlc` or points at it. The installers' self-hosted copies
are byte-current, and `make check` and `make unit` pass.

## Proof budget

  cases: 0–1 (prose; the install currency and doc gates are the proof)
  tier: unit
  lands in: tests/test_install.py, tests/test_pm_guidance.py only if a pinned phrase moves
  what already covers this: the currency and doc gates.
