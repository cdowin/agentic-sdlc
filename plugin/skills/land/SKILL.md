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
2. **Spawn.** The lander is the `integrator` agent on the bounded tier (Haiku in Claude), run in
   the background. Set the model on the spawn. The brief names:
   - `repo` and `base`;
   - either the pushed branches in merge order, each with its issue, or 1 assembled wave branch
     with the parent issues it finishes and the parents it only part-finishes;
   - `gate`: every lane the PR CI runs, as for a wave;
   - the regenerate command and the generated-file patterns, if the repo has them;
   - known flakes: the check name and the log line of each;
   - `merge: now`, or `merge: hold` while a review is still open.
3. **Go back to the person.** The lander reports when it is done. Read its report, not its transcript.

## Lander steps

1. **Wait your turn.** Run `gh pr list -R <repo> --state open --json number,statusCheckRollup`.
   If any PR has a pending check, run `plugin/bin/wait-ci <repo>#<n>` on it first.
2. **Pushed branches with `merge: now`:** run `plugin/bin/wave-land <branch>...` with
   `WAVE_LAND_CHECK` set to the gate, and with `WAVE_LAND_REGEN` and `WAVE_LAND_GENERATED` when the
   brief names them. It assembles the wave branch, runs the gate once, opens the PR, enables
   auto-merge, waits on CI, and cleans up after the merge. It writes `Closes #N` for each branch
   number, and `Part of #N` for a slice of a parent the brief names (`--part-of N`). Several waves
   go in 1 queue file, 1 wave per line: `plugin/bin/wave-land --queue <file>`. It lands them in
   order, 1 PR in CI at a time, stops on the first red check or conflict, and a rerun resumes at
   that wave. A PR left `BEHIND` gets the base merged, regenerated and checked again; it is not a stop.
   **Never write your own landing loop.** A feature `wave-land` lacks is a plugin issue: report it.
3. **Otherwise** (`merge: hold`, or 1 assembled wave branch), do these steps by hand. Merge the branches into a new wave branch at
   `origin/<base>` (merge commits, never rebase), using the integrator checklist. Run the gate once,
   push, and open 1 PR. The PR body lists `Closes #N` for each issue it finishes and
   `Part of #N` for each parent it only part-finishes. Never write `Refs #N`, because the
   issue-link check fails on it. Task issues that a wave has already closed are listed as closed,
   with no `Closes` line. Turn on auto-merge (`gh pr merge N --auto --merge`) only with
   `merge: now`. Auto-merge fires on green, so with `merge: hold` it stays off. Then run
   `plugin/bin/wait-ci <repo>#<n>`, or `plugin/bin/wait-ci --merge <repo>#<n>` with `merge: now`
   (`--merge` goes before the PR).
4. **On a red check:** re-run it once (`gh run rerun --failed <run-id>`) only when it matches a
   known flake, then wait again. Any other red check means a report and a stop. On
   `CONFLICTING` or `BEHIND`, merge base into the branch, resolve, push and wait again. On
   `NO_CHECKS`, check the workflow triggers and report.
5. **A fix of 10 lines or fewer** (an import, a name, a table row) is yours. A larger break goes
   back to the lead.
6. **Clean up only after a MERGED read** from `gh pr view N --json state`. Never chain cleanup on
   the merge command. Delete each merged branch on origin by its exact name, remove its worktree,
   and close any issue the PR did not close. Delete the wave branch only when the merge did not,
   and check `git ls-remote origin` for a branch left behind. Never delete `base`.
7. **Report** in 10 lines or fewer: the PR, the merge SHA or the state it stopped in, the branches
   merged and skipped, the flake re-run if there was one, your fixes, what you deleted, and what
   you did NOT verify.

## An open PR

A held PR waits for the lead. When the review reports no open CRITICAL, the lead launches the
lander again with the PR and `merge: now`. A flow's group PR goes the same way. The lander turns on auto-merge, runs
`plugin/bin/wait-ci --merge <repo>#<n>`, and cleans up after a MERGED read.

## Lessons from a long landing run

A 2.5-hour run showed 3 large costs. These rules answer them.

- **The lander never polls for worker reports.** The lead launches (or resumes) the lander only
  when every report it needs is in. A lander that finds a report missing lands what is ready and
  reports the rest as not landed.
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
