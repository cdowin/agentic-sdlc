---
name: land
description: Use when pushed branches are ready to merge and the lead has decided to merge them, or when a wave branch is ready for its PR. Covers work from cloud sessions, scripts and Codex, as well as the PR step after a wave. The lead launches 1 lander agent in the background. The lander opens the 1 PR, waits on CI and cleans up. The lead keeps the decision.
---

# Land: a lander agent does the merge mechanics

Why: landing by hand takes up the lead's evening, and several PRs at once starve shared CI
runners until all of them go red. The lead decides what merges. A lander does the rest.

## Launch

1. **Batch.** Put every branch that is ready for a repo into 1 land. **Only 1 PR per repo may be
   in CI at a time.** Never start a second lander on a repo while one is running.
2. **Spawn.** The lander is the `lander` agent on the bounded tier (Haiku in Claude), run in
   the background. Set the model on the spawn. The brief names:
   - `repo` and `base`;
   - either the pushed branches in merge order, each with its issue, or 1 assembled wave branch
     with the parent issues it finishes and the parents it only part-finishes;
   - `check`: the repo's fast check (CI runs every lane);
   - the regenerate command and the generated-file patterns, if the repo has them;
   - known flakes: the check name and the log line of each;
   - `merge: now`, or `merge: hold` while a review is still open.
3. **Go back to the person.** The lander reports when it is done. Read its report, not its transcript.

## Lander steps

The lander follows its agent file, `agents/lander.md`: merge, the fast check, the PR, CI, the
fix-attempt cap, cleanup after a MERGED read and the report with the `review-due` line.

## An open PR

A held PR waits for the lead. When the review reports no open CRITICAL, the lead launches the
lander again with the PR and `merge: now`. A flow's group PR goes the same way. The lander turns on auto-merge, runs
`plugin/bin/wait-ci --merge <repo>#<n>`, and cleans up after a MERGED read.

## Lessons from a long landing run

A 2.5-hour run showed 3 large costs. These rules answer them.

- **The lander never polls for worker reports.** The lead launches (or resumes) the lander only
  when every report it needs is in. A report's first line is `WORKER REPORT branch=<branch>
  head=<sha>` (`plugin/bin/worker-tail.md`). The brief names that branch, never a session mirror
  branch. A lander that finds a report missing lands what is ready and reports the rest as not landed.
- **Count budget lines before the merge.** See the table below. A failure found after the merge
  cost about 6 full gate runs. A worker that touches a generated catalog (a translation template,
  an index) regenerates it before it pushes.
- **Set up the wave worktree once.** Run the project's import or cache step right after creating
  it. A stale cache cost about 25 minutes together with the collisions below.
- **Split colliding test files.** When 2 branches add a test file of the same name, give each its
  own file.
- **Regenerate once, last.** After the last merge, regenerate every generated index once. Never
  resolve those files by hand.
- **A headed gate is the lead's.** A gate that needs a headed (windowed) capture is never stamped
  by the lander. It stops and asks the lead. The lead batches all such changes into 1 headed run.
- **End every report with a TIMING section,** per wave: assemble, gates, PR open to merge, cleanup.

## First principles: check the combined tree

CI tests the PR merged with main, so branches that pass alone can fail together. Every step runs
the project's fast static pre-PR check (for example `make precheck`: budgets, PR body, version rule;
seconds, no engine boot) on the combined tree.

| Step | Who | Action |
|---|---|---|
| Last push | Worker | Merge current main, run the fast check, then push. |
| Each merge into the wave branch | Lander | Run the fast check after every branch, so the breaking branch is named at once. |
| Before the PR | Lander | Merge current main into the wave branch; run the fast check with the PR body. |
| Budget overflow | Lander | A combined budget delta above the headroom left splits the wave into 2 PRs, landed one after the other. |
| Budget report | Check | Report the lines left; fail when a branch adds more than the headroom left. |
