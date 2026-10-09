---
name: hillclimb
description: Load this skill for sustained, iterative improvement of one measurable thing against a target (speed, size, memory, score, frame time, build time). A one-off fix is the bug-fix playbook, not this one.
---

# Hillclimb: one metric, one change, keep or revert

You own the metric and the integrity of the experiment.
You supervise and review. Workers make the attempts.

## When to use

1. Use it when one number must move toward a target over many attempts.
2. Examples: Godot game frame time, TypeScript CLI start time, book build time.
3. Do not use it for a single known defect. That is a bug fix.

## The rule

1. Fix 1 metric.
2. Freeze the harness before the first change.
3. Make 1 change per measurement.
4. Keep the change or revert it in full.
5. Make 1 commit per kept win.

Never stack untested changes. Never claim a win from reading code.

## Steps

1. **Ground the workload.**
   - Pick a case that reproduces the complaint.
   - If no case reproduces it, fix the repro first. Do not climb.
   - Fix 1 metric and the direction that is better.
   - Write a stop predicate. It pairs a target with a floor on attempts.
   - Example: at least 50% better than baseline and at least 10 iterations.
   - Use the user's numbers when given. Else agree them.
2. **Build the harness, then freeze it.**
   - Run a slow case and a fast case. Prove the harness tells them apart.
   - Vet it with `benchmark-checklist.md` (same folder) before the freeze.
   - It prints its error count and a count of work done.
   - One repeatable command emits the metric as a median of N runs.
   - Record the baseline.
   - Record a green run of the regression gate (the tests that must keep passing).
   - Do both before any change.
3. **Keep a decision log.**
   - File: `decision.tsv`. Keep it out of the tree (gitignored).
   - One row per attempt: id, hypothesis, change, before, after, delta, tests, verdict (kept or reverted), note.
   - Read it before each attempt.
4. **Name a mechanism.**
   - Each hypothesis says why the change helps.
   - Good: "defer X off the boot path because it blocks first paint".
   - Bad: "try caching".
5. **Loop. 1 hypothesis per iteration.**
   1. Hand the change to a worker with a tight scope. Review the diff.
   2. Measure before and after with the frozen harness.
   3. Run the regression gate.
   4. Keep the change only if the metric moves past noise and the gate is green. Else revert in full.
   5. Commit each kept win once. Stage only the files changed: `git add <files>`. Never `git add -A`.
   6. Log the row, kept or reverted.
   7. Send rework of a rejected attempt to the same worker.
6. **Parallel attempts.**
   - Cap: 3 live hypotheses at once.
   - Each one runs in its own worktree.
   - Merge kept wins one at a time. Re-measure after each merge.
7. **Plateau.**
   - After 3 rejects in a row, change category, combine near-misses, and re-read the source.
   - Correctness and simplicity outrank the number.
   - Revert a win that breaks behaviour.
   - Keep a simplification that holds the number.
8. **Stop.**
   - Stop when the predicate is met.
   - Stop when the remaining ideas are marginal.
   - Never relax the predicate to meet it.
   - If you are stuck, report it. Do not spin.
9. **Finish.**
   - Workers push every commit to the issue branch. Push does not start CI.
   - The kept commits ride the wave PR with the other work.

## Reply format

1. Metric and target.
2. Baseline to final, with percent delta.
3. Iterations: kept and reverted.
4. Each kept fix, one line.
5. The `decision.tsv` path.
6. The best next idea.

Adapted from pstack by Lauren Tan (MIT).
