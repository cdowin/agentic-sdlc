---
id: ft-the-guard-lets-the-leader-keep-house
kind: feature
milestone: "ms-the-leader-finishes-the-job"
name: the guard lets the leader keep house
status: reviewing
reviewed: docs/reviews/2026-09-12-0.12.0-features.md
depends_on: []
consumed_by: []
changelog: The git guard allows routine upkeep — `pull --ff-only`, `merge --ff-only <remote>/<branch>`, `branch -d`, `switch`/`switch -c`, `symbolic-ref <ref>`, `stash list` — and `agent-worktree.sh done` deletes a lane branch merged into the mainline and carries a lane's uncommitted `pm/roadmap/*.jsonl` rows to the main checkout (new header key `CARRY_ROWS`).
---

# the guard lets the leader keep house

Chris, 2026-09-12: *"Can we loosen the guard? You should be able to manage all of this for me."*
After 0.11.1 the orchestrator could not sync `main` (`git pull` and `git merge --ff-only origin/main`
refused), could not delete merged branches (`git branch -d` refused), and could not read
`git symbolic-ref`. Each refused operation is safe BY CONSTRUCTION, and each is routine upkeep. The
guard exists to stop work being lost, not to stop housekeeping.

**Decided. The stock `cc-git-allowlist.sh` allows, with corpus rows proving each:**
- `git pull --ff-only [<remote> [<branch>]]` (a fast-forward cannot lose work). A plain `pull`,
  `pull --rebase` or `pull --no-ff` stays refused, with `--ff-only` as the alternative.
- `git merge --ff-only <remote>/<branch>` for any remote-tracking ref, alongside today's
  `milestone/*` and `feat/*` merges.
- `git branch -d <names…>` (the safe delete refuses unmerged work), and the read forms `git branch`,
  `-a`, `-r`, `--list`, `--merged`, `--no-merged`, `--show-current`. `-D`, `-f`, `-m` and `-M` stay
  refused.
- `git symbolic-ref` with only a ref argument (a read), `git worktree list`, `git stash list`. Every
  write form stays refused.
- `git switch <branch>` and `git switch -c <new> [<start>]` (switching or creating never discards;
  git refuses over conflicting edits).

**`agent-worktree.sh done`:** a branch merged into the MAINLINE (`<remote>/<mainline>`, read the
same way `new` reads its fallback) is deleted like one merged into the integration branch. Today it
checks only the in-progress milestone's branch, and after a release there is none, so every merged
lane branch was "retained". Uncommitted rows in `pm/roadmap/**/*.jsonl` of a lane worktree are
appended to the same path in the main checkout, and the lane's file is reset from HEAD. It still
refuses any OTHER uncommitted file. That is issue #48's worktree half. `ft-a-commit-leaves-the-tree-clean`
removes the cause.

Re-install into this repo (`install-hooks --force`) so the self-hosted guard carries it. The header does
not carry `switch` (decision D1: stock allows the safe forms).

## Ship criterion

From the main checkout, with the armed guard: `git switch main && git pull --ff-only`,
`git merge --ff-only origin/main`, `git branch -d feat/x` and `git symbolic-ref refs/remotes/origin/HEAD`
pass. `git pull`, `git branch -D x` and `git reset --hard` are refused. `agent-worktree.sh done` on a
lane merged into `origin/main`, with gate rows dirtying its ledger, removes the worktree, deletes the
branch, and leaves those rows in the main checkout's ledger.

## Proof budget

  cases: corpus rows (both directions) + 1–2 agent-worktree cases (existing module)
  tier: the corpus replays in `check hooks`; agent-worktree in its existing test module
  lands in: cc-git-allowlist.sh --self-test; tests/test_hooks_payloads.py; the agent-worktree tests
  what already covers this: the corpus refuses these today; nothing proves the safe forms pass.
