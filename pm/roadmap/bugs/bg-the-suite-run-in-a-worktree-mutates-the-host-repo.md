---
id: bg-the-suite-run-in-a-worktree-mutates-the-host-repo
kind: bug
milestone: "ms-a-consumer-can-take-the-bump"
name: the suite run inside a linked worktree can flip the host repo bare and commit into it
status: closed
caused_by:
changelog: none
---

# the suite run inside a linked worktree can flip the host repo bare and commit into it

Found building 0.8.0 on 2026-09-11, the day the flow started running reviewers and builders in
linked worktrees (`git worktree add`, and the harness's own agent worktrees under
`.claude/worktrees/`).

## Symptom, observed

At 10:38 local, while reviewers ran `make unit` / `make test` in detached worktrees and the
orchestrator ran `git bisect run pytest …` in another:

- the MAIN checkout's `.git/config` gained `bare = true`, so every git command in it failed with
  `fatal: this operation must be run in a work tree`. Linked worktrees share the common config
  (no `extensions.worktreeConfig`), so one flip reaches every checkout;
- a commit `2dc6514 scratch`, author `t` (the suite's identity), parent `65b7a5e`, deleting the
  tree's `.claude/` and more, became the HEAD of a linked worktree. It is on no branch: dangling.

Restored by `git config core.bare false`; no branch was touched. **Which test did it is not yet
proven.** The candidates are every git spawn that runs `init --bare`, `commit`, or `config` WITHOUT
`cwd=` inside its temp tree and WITHOUT scrubbing `GIT_DIR` / `GIT_WORK_TREE` / `GIT_INDEX_FILE` /
`GIT_COMMON_DIR` from the environment it inherits. `git bisect run` and git hooks export those.
`tests/test_conveyor_adopt.py:140` and `tests/test_conveyor_steps.py:64` commit `-qm scratch` as
`user.name=t`, which is exactly the stray commit's shape. `bg-the-suite-can-flip-the-host-repo-to-bare`
(closed, 0.6.0) fixed one `cwd`, not the class.

**Rule 4 in the test layer:** a suite that can rewrite the repository it is gating.

## Fix

1. One conftest-level guard, not per-call discipline: an autouse session fixture that removes
   `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY` and
   `GIT_CEILING_DIRECTORIES`-bypassing vars from `os.environ` for the run, and sets
   `GIT_CEILING_DIRECTORIES` to the temp root, so a spawn whose temp tree is not a repo can never
   walk up into a real one.
2. A ratchet: the session snapshots the host repo's `core.bare`, `HEAD` and the checked-out branch
   ref at start, and FAILS the session by name if any of them moved.
3. Reproduce first: run the suspect modules from a linked worktree and under an exported `GIT_DIR`,
   and show which one mutates the host at HEAD.
