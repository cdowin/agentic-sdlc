---
id: ft-a-gate-reads-what-this-run-did
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: a gate reads what this run did
status: done
reviewed: docs/reviews/2026-09-27-0.15.0-gates-bucket.md
depends_on: []
consumed_by: []
changelog: check budget grades only this machine's gate rows; release reuses a green verify --milestone on the same tree; a feature's changelog line answers its stories; the commit guard reads the merge state of the tree it commits in; install-hooks wires every hook under $CLAUDE_PROJECT_DIR.
---

# a gate reads what this run did

Three issues where a gate grades a record that is not this run's: #67 grades a frozen tracked row,
#74 ignores a fresh green run and pays 18 minutes to make it again, and #77's commit guard reads
the session's tree, not the tree the command commits in.

## Decided (do not re-plan)

- **#67 — `check budget` never grades the tracked ledger.** Gate rows went to
  `ledger.local.jsonl` in 0.13. `budget.py` `_rows()` falls back to the tracked `ledger.jsonl` when
  the local file has no rows, so on a CI runner it grades rows frozen days ago and fails every PR.
  Remove the fallback for gate rows. A budgeted tier with no local row prints
  `UNMEASURED <tier> — no run recorded in <local ledger>` and does not fail. The check's census
  line says how many tiers it graded: `budget: graded 0 of N tier(s) — no local gate rows (a fresh
  checkout or a CI runner)`. That is rule 4 held by naming the zero, not by failing on it: the
  runner is ephemeral and has no history to grade. A stale LOCAL row is graded as today.
- **#74a — the release `gate` reuses a green milestone rung.** `check_gate`
  (`repo/conveyor/steps.py`) runs `[release.commands] gate` with no cache. When `gate` is the
  stock default, read its verdict through the verify cache the way the story step does
  (`_own_verdict(ctx, 'verify', '--milestone')`): a green `verify --milestone` recorded on the
  same tree state and graded-rows digest is reused and the step says so (`reused — green at <ts>
  on tree <short>`). A declared non-default `gate` command runs as today. The loop's skill text
  (`run-the-sdlc` step 10) is edited by `ft-an-arrival-names-what-it-starts`, not here.
- **#74b — a story's changelog is answered by its feature.** In `repo/pm/changelog.py`
  `unanswered`, a done story whose feature carries a non-empty `changelog:` counts as answered.
  `changelog <id>` renders nothing new for it. A story with its own line still renders it.
- **#77 — the commit guard reads the tree the command commits in.** Chris, 2026-09-27 (D5).
  `operation_in_progress` in `cc-commit-pathspec.sh` resolves the gitdir from the SESSION's cwd.
  A builder whose session sits in the main checkout and runs `cd <worktree> && git commit` or
  `git -C <worktree> commit` to finish a merge is blocked, because MERGE_HEAD is in the
  worktree's gitdir. Resolve the directory from the command itself: a `-C <dir>` on the git
  segment, else the last leading `cd <dir>` in the same command, else the session cwd. Edit the
  source under `src/agentic_sdlc/repo/installables/` and re-install with `install-hooks --force`.
  The hook stays bash 3.2 and parses its payload with bare `python3 -c` (rule 1). Also name the
  finish in the dispatch contract (`repo/dispatch.py`, the "commit only by pathspec" line): a
  merge in progress finishes with `git commit` with no pathspec, or `git merge --continue`.
- **Two hook fixes from a consumer's fork** (same theme: a hook reads the tree it runs in).
  `pre-push`: before the self-tests, unset each name `git rev-parse --local-env-vars` prints, so
  an inherited `GIT_DIR` cannot send a child test's `git init` into the real repository.
  `install.py` `_WIRING`: print hook commands as `bash "$CLAUDE_PROJECT_DIR/tools/hooks/<hook>"`,
  not a cwd-relative path, so a hook still resolves when an agent's cwd moves. Re-wire this
  repo's `.claude/settings.json` from the printed entries.

## Ship criterion

- `check budget` with no local ledger and a tracked ledger of old FAIL rows exits 0 and prints
  `graded 0 of N`.
- `release` after a green `verify --milestone` on the same tree does not run `make milestone`
  again; after one tracked edit it does.
- `release` on a milestone whose stories are blank under answered features passes
  `changelog-unreleased-nonempty`.
- With a session cwd in the main checkout and a merge in progress in a worktree,
  `cd <worktree> && git commit -m x` and `git -C <worktree> commit -m x` both pass the guard;
  the same commit with no merge in progress is still blocked.
- `install-hooks` prints every hook command under `$CLAUDE_PROJECT_DIR`.

## Proof budget

  cases: 6-7
  tier: unit, plus the hook payload cases where hook tests already run
  lands in: existing budget / conveyor steps / changelog / hook test modules
  what already covers this: search first (rule 10); amend before adding
