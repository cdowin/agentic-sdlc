---
id: ft-the-allowlist-fails-closed
kind: feature
milestone: "ms-the-mistake-surfaces-where-it-is-made"
name: the allowlist fails closed
status: building
reviewed: docs/reviews/2026-09-29-0.17.0-hooks-and-ci.md
depends_on: []
consumed_by: []
changelog: The git allowlist hook now blocks a word it cannot read (a shell variable) as a merge source, push remote or destination, subcommand, or `branch`/`switch` name — so `git push origin "$BRANCH"` now blocks; type it literally — and a `-c`/`--config`/`--config-env` location key (`core.worktree`, `core.bare`, `core.hooksPath`, `core.gitdir`, `include.*`, `includeIf.*`) or a `GIT_CONFIG*` variable no longer gets the scratch-probe exemption.
---

# the allowlist fails closed

Issues: #85, #94.

Two spellings pass `cc-git-allowlist` that should block: a merge source holding a shell variable
(`git merge origin/lane/$b`), and a `-c <location key>` that redirects git past the scratch-probe
exemption (`git -c core.worktree=/r -C /tmp/x reset --hard`).

## Decided (do not re-plan)

All in `src/agentic_sdlc/repo/installables/cc-git-allowlist.sh`; re-install with
`install-hooks --force`. bash 3.2, payload parsed with bare `python3 -c` (rule 1).

- **An unknowable merge source fails closed.** In `merge()`, a positional that `unknowable()`
  flags blocks, with an `instead:` line that says to type the branch name literally.
- **Audit every other `unknowable()` caller** for the same fail-open shape (`push` destination,
  `switch`, `branch`, the subcommand check). Each one that fails open is fixed the same way; each
  one that stays open gets a one-line comment saying why it is safe.
- **A `-c` location key is a location flag.** Top-level `-c` and clone's `-c`/`--config` whose key
  is `core.worktree`, `core.bare`, `core.hooksPath`, `core.gitdir`, or any `include.*` /
  `includeIf.*` key blocks the scratch-probe exemption, as `--work-tree` does. Key match is
  case-insensitive (git config keys are).
- Corpus rows in `--self-test`: `git merge origin/lane/$b` exit 2; `git merge --ff-only
  origin/$b` exit 2; `git merge feat/x` exit 0; the two #85 commands exit 2; a harmless
  `git -c color.ui=never -C /tmp/x status` exit 0.

## Ship criterion

- The #94 loop and both #85 commands replay to exit 2; `bash cc-git-allowlist.sh --self-test`
  passes with the new rows; `check hooks` green here.

## Proof budget

  cases: about 8 corpus rows, no new pytest case
  tier: the hook's own --self-test (replayed by check hooks)
  lands in: src/agentic_sdlc/repo/installables/cc-git-allowlist.sh
  what already covers this: rows for `-C`, `--work-tree`, `GIT_*`; none for `-c` keys or a variable merge source.
