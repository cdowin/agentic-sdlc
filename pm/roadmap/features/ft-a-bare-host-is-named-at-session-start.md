---
id: ft-a-bare-host-is-named-at-session-start
kind: feature
milestone: "ms-the-leader-finishes-the-job"
name: a bare host is named at session start
status: reviewing
reviewed:
depends_on: []
consumed_by: []
changelog: `preflight` gains a fifth row, `repository`: `bare` (and that `git config core.bare false` restores it) when the checkout's shared git config has `core.bare = true` under a working tree, else `ok` or `unknown`.
---

# a bare host is named at session start

Deferred from 0.11.1 (a new output row is a minor). When the host flipped to `core.bare = true` on
2026-09-12, nothing said so until a git command failed in the main checkout, hours later.

**Decided:** `agentic-sdlc preflight` gains a fifth row, `repository`. It reads the checkout's common
git config AS TEXT (the `.git` dir, or a linked worktree's `.git` file → gitdir → `commondir`; reuse
the reader `tests/conftest.py` proved, lifted into the package if needed, stdlib only). The value is
`bare` when `core.bare = true` and the checkout has a working tree, with meaning
`git config core.bare false restores it`. Otherwise it is `ok`, or `unknown` when unreadable. The
`--help` column list and the README row name it. The SessionStart hook prints it with the others.

## Ship criterion

In a temp repo with `core.bare = true` written into `.git/config`, `preflight` prints
`repository  bare  git config core.bare false …` at exit 0. In a normal repo it prints `ok`, and in a
linked worktree whose common config is bare it prints `bare`. No process is spawned (rule 2).

## Proof budget

  cases: 1 function with subtests (ok / bare / bare-via-linked-worktree / unreadable)
  tier: unit
  lands in: tests/test_preflight.py
  what already covers this: nothing reads core.bare outside the test-suite ratchet.
