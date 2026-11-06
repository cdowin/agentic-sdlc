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
   brief names them. It assembles the wave branch, runs the gate once, opens the PR with
   `Closes #N` lines, enables auto-merge, waits on CI, and cleans up after the merge.
3. **Otherwise,** do these steps by hand. Merge the branches into a new wave branch at
   `origin/<base>` (merge commits, never rebase), using the integrator checklist. Run the gate once,
   push, and open 1 PR. The PR body lists `Closes #N` for each issue it finishes and
   `Part of #N` for each parent it only part-finishes. Never write `Refs #N`, because the
   issue-link check fails on it. Task issues that a wave has already closed are listed as closed,
   with no `Closes` line. Turn on auto-merge (`gh pr merge N --auto --merge`) only with
   `merge: now`. Auto-merge fires on green, so with `merge: hold` it stays off. Then run
   `plugin/bin/wait-ci` (add `--merge` only with `merge: now`).
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
`wait-ci --merge`, and cleans up after a MERGED read.
