---
id: ft-the-flow-is-boring-by-construction
kind: feature
milestone: "ms-the-ledger-is-a-stamp"
name: the flow is boring by construction
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the flow is boring by construction

Chris, 2026-09-11, mid-0.8.0: *"I want sanity and determinism… this should be almost the dumbest
`git add`, `git commit`, `git merge`… Should we just work in serial by default right on the branch?
Super boring?"* Yes. This repo's SDLC.md §2 says so as of `be08eea`. **This feature makes the KIT
say it and enforce it**, so every consumer's orchestrator gets the boring flow by construction rather
than by remembering it.

What 0.8.0 paid, in order: parallel builders in one tree starved the story belt; worktrees traded
that for merges, wrong-base worktrees and a harness-rewritten `core.hooksPath`; and an orchestrator
`git bisect` in a linked worktree flipped the repo to `core.bare = true`. None of it was the work.
All of it was improvised git.

**Two pieces:**

1. **The installed architect brief carries the serial loop** (`installables/architect.md`): one
   builder at a time, directly on the milestone branch; claim → build → `make unit` → commit by
   pathspec → `close story` → … → review → land MAJOR+ → `close feature` → close issues → next.
   Parallelism is an opt-in the operator names. The same banned-git list binds the orchestrator as
   binds builders.
2. **A git allowlist guard hook** in the `cc-commit-pathspec.sh` family (a PreToolUse Bash guard,
   stdlib, bash-3.2-safe, with a `--self-test` corpus). An agent session may run `git add`,
   `git commit` with paths, `git push` (never to the mainline, as `pre-push` already enforces),
   `git status|diff|log|show|rev-parse|config --get`, and the release's one `git merge`. Anything
   that rewrites or rewinds state (`bisect`, `stash`, `reset`, `checkout -- .`, `restore`, `clean`,
   `rebase`, `worktree add`, `commit --amend`, `push --force`) is blocked with the reason and the
   boring alternative. The project can widen the list in its project-config header, never silently.

## Ship criterion

In a consumer with the corpus installed and armed, an agent's `git bisect run …`, `git stash` and
`git reset --hard` are each blocked with a named reason, and `git add <path>` + `git commit -m … --
<path>` + `git push origin <milestone-branch>` pass. `check hooks` replays the guard's corpus, and it
is one of the hooks that can BLOCK (exit 2). The installed architect brief states the serial loop, and
`install-agents --diff` shows it.

## Proof budget

  cases: the guard's `--self-test` corpus (one row per allowed and blocked shape), plus one
    `check hooks` census case
  tier: the corpus replays in `check hooks`; unit for the install/self-host byte-current check
  lands in: the new hook's own corpus; tests/test_check_hooks.py
  what already covers this: `cc-commit-pathspec.sh` blocks pathless commits and nothing else;
  SDLC.md's rule is prose, and prose did not stop the bisect.
