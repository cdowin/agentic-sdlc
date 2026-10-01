---
id: "ms-integrate-takes-the-whole-batch"
kind: milestone
name: integrate takes the whole batch
status: building
depends_on: []
branch: milestone/2.2.0-integrate-takes-the-whole-batch
mode:
version: 2.2.0
changelog:
order:
  - "bg-integrate-calls-a-failed-commit-a-conflict"
  - "ft-the-batch-starts-warm"
  - "ft-every-lane-merges"
  - "ft-a-rerun-reuses-the-proof"
  - "ft-a-harness-worktree-is-adopted"
  - "bg-merge-only-outside-the-prefix-escapes-the-foreign-guard"
  - "bg-a-non-conflict-merge-names-the-wrong-cause"
  - "bg-prepare-default-is-invisible-to-the-seed-test"
  - "bg-a-slug-also-named-merge-only-is-deleted"
---

# ms-integrate-takes-the-whole-batch — integrate takes the whole batch

The first real runs of 2.0.0 `integrate` cost about 15 minutes of lead time per run
(https://github.com/cdowin/agentic-sdlc/issues/130), and harness worktrees still need a hand step
(https://github.com/cdowin/agentic-sdlc/issues/124, closed in 2.0.0 with `agent-worktree.sh adopt`,
which nothing calls). The 2.1.0 release CI found a false line in `integrate`
(bg-integrate-calls-a-failed-commit-a-conflict). This milestone makes the lead's one command take
every lane it is handed, start warm, say the true cause of a stop, and not re-prove an unchanged
batch.

## Ship criterion

- `[integrate] prepare` runs once in the batch worktree before the first merge.
- `integrate --merge-only <branch>` merges and proves a branch with no story and closes nothing.
- A red proof names a lane only when its output names that lane's file.
- A rerun on a byte-identical batch reuses the recorded proof PASS.
- A failed merge that is not a conflict prints git's own cause.
- The dispatch brief runs `agent-worktree.sh adopt` when the builder already stands in a harness
  worktree.

## Risks

- Minor bump: a new config key (`[integrate] prepare`), a new flag (`--merge-only`), new output
  lines. `prepare` is a WORKFLOW key with no default (rule 5): absent means no prepare step, and the
  seed says so.
- Every story touches `src/agentic_sdlc/repo/integrate.py`. One lane builds all `integrate`
  stories; the brief story is its own lane.
