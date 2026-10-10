---
name: reflect
description: Use after a wave finishes, when the lead says reflect, retro, "what did we learn", "improve the plugin" or "why did this wave go wrong". Turns the finished wave result into proposed plugin edits, filed as issues. Load it only for a wave that had escalations, rework or findings above minor. It proposes edits. It never applies them.
---

# Reflect: turn a finished wave into proposed plugin edits

Why: a wave shows where the plugin's briefs, tiers and checks failed. The lesson is lost unless someone writes it down with evidence. This skill writes it down as issues.

Reflect proposes. The lead decides. A proposed edit lands only through a normal issue, branch and wave PR. Reflect never edits a plugin file and never changes a version. It adds to the planning critic, the batched blind review and the skeptics. It does not replace them.

## Steps

1. **Collect the wave result.** The input is the object `wave.js` returns: `branch`, `sha`, `done`, `escalations[{task,state,reason}]`, `tasks[{task,issue,state,tier,branch,rounds,notes,reports,merges}]`, `reviews`, `metrics`, `transitions`. Add the wave PR comments and the review findings. State the wave, the branch and the sha first.
2. **Skip a trivial wave.** Skip when the wave was small or nothing went wrong twice. One-offs are not learnings. Write "no change" and stop.
3. **Find signals.** Look for:
   - an entry in `escalations`;
   - a task with `rework_rounds` above 0 in `metrics`;
   - a task whose tier changed;
   - a finding above minor;
   - a brief the worker misread;
   - a review finding that repeats across tasks.

   Each signal cites its evidence: task id, round, finding text. Drop a learning with no citation. A metric of "unavailable" is unknown. Never read it as 0.
4. **Read through 3 lenses.** The lead (`chief-of-staff`) reads each lens as a separate pass, or spawns 1 reviewer agent per lens. Cap: 3 agents total. Do not add a 4th lens.
   - Judgment: briefs, tiers, oracles, planning.
   - Tooling: hooks, checks, scripts, workflows.
   - Divergent: what a different approach would have avoided.
5. **Synthesize.** Sort every learning into Accepted, Rejected or Backlog. Each Accepted item names the exact plugin file and the exact edit, in one sentence. Reject a learning that has weak evidence or a one-off cause.
6. **Check structure.** Ask of each Accepted item: would a lint, hook, check or test enforce it more reliably than prose? If yes, move it to Backlog as an enforcer issue. Prose is the last resort.
7. **File issues.** File ONE GitHub issue per Accepted or Backlog item with `gh issue create`. Use the area label the repo already uses. The body holds four parts:
   - the evidence;
   - the target file;
   - the proposed edit;
   - a "done when" line.

   Cap: at most 5 issues per wave. List the rest once in the report. Do not file a duplicate: search open issues first.
8. **Report.** Use the repo reporting style, in this order:
   1. A numbered NEEDS YOU list.
   2. Issues filed: number and title.
   3. Dropped items, each with the reason.

## Does not

- Edit a plugin file.
- Change a version or cut a release.
- Run again on the same wave.
- Apply an item the lead has not accepted.

Adapted from pstack by Lauren Tan (MIT).
