---
id: ft-a-green-run-is-bought-once
kind: feature
milestone: "ms-the-mistake-surfaces-where-it-is-made"
name: a green run is bought once
status: building
reviewed: docs/reviews/2026-09-29-0.17.0-green-run.md
depends_on: []
consumed_by: []
changelog: pre-push gates only commits the remote does not have yet; `close story <id> <id> …` runs the grain-blind checks once and writes each id; and an unscoped story rung leaves out the `status:` lines and ledger rows a close writes, so two closes on one commit reuse its PASS (the state tag moves to v4, so every rung runs once more after the bump; a story target that reads statuses should declare `[verify.inputs] story`).
---

# a green run is bought once

Issues: #93, #95.

Two gates re-buy a verdict they already have. The pre-push hook runs the full gate for a branch
created at a commit the remote already has (nine lane branches cost 13 minutes). `close story`
over six stories on one commit ran the check six times (about 10 minutes), although the rule
text says an unchanged rung is reused.

## Decided (do not re-plan)

- **pre-push gates only new commits.** In `src/agentic_sdlc/repo/installables/pre-push`, Stage 2
  sets `has_real_push` only when `git rev-list <local_sha> --not --remotes=<remote>` names a
  commit. A new branch at a pushed commit, a fast-forward to a pushed commit and a tag-only push
  skip Stage 2; a push with one new commit still pays. An unreadable rev-list (exit non-zero)
  counts as a real push: fail closed (rule 4). Self-test row for each case. Re-install
  `install-hooks --force`.
- **Find why the story rung was not reused, first.** Reproduce in a temp tree: two `close story`
  runs on one commit, each a different story. The second must print the reuse line. Likely cause
  to test first: each close writes a status row and a `done:` line, which moves a whole-tree
  digest (`verify/cache.py`), so a story rung with no `[verify.inputs]` scope never repeats.
  Fix the cause at its layer. If the fix is "the story rung's stock scope excludes the roadmap
  directory", that is a gate-semantics change: plant drift under `src/` between two closes and
  confirm the second close RE-RUNS.
- **`close story <id> <id> …`.** One invocation takes many ids. Checks that do not read the grain
  (`story-verified`, `committed`) run once; per-grain checks (`story-exists`,
  `evidence-written`) run per id. Each id gets its own verdict and its own write, and each id is
  printed with its lines. Exit 1 when any id is refused, 0 when all wrote. `--force` applies to
  every id named, one `deviation` row each. Idempotent: a `done` id reports and is skipped.
- `close story` `--help` names the many-id form; the pm-execution guidance line that says "close
  story for each story by name" names it too (rule 11), then `pm install-skills --force`.

## Ship criterion

- `git push origin <pushed-sha>:refs/heads/lane/x` skips Stage 2; a push with a new commit runs it.
- `close story a b c` on one green commit runs the story rung once and writes three `done`s.
- Two single `close story` runs on one commit: the second reuses, printed.

## Proof budget

  cases: 3 pre-push self-test rows; 2 pytest cases (many-id close, reuse across closes) + 1 drift probe
  tier: hook self-test; temp-tree integration for the belt (it spawns)
  lands in: installables/pre-push, tests for conveyor/driver.py
  what already covers this: the single-id close and the verify cache unit cases; nothing crosses two closes.
