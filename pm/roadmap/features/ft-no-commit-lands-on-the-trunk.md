---
id: ft-no-commit-lands-on-the-trunk
kind: feature
milestone: 
name: no commit lands on the trunk
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# no commit lands on the trunk

Filed 2026-09-27 from a consumer's fork (stage 1 of its own `pre-commit` hook). The package's
guards cover an AGENT's git commands (`cc-git-allowlist.sh`, `cc-commit-pathspec.sh`). Nothing
covers a person, or a tool that is not Claude Code, committing on the trunk. The fork's hook
refuses three things: a commit on `main`; a commit in a worktree to any branch but its own; a
commit in the main checkout to a `feat/*` branch (the trunk checkout commits the milestone
branch only).

Open questions, not decided: a new installable `pre-commit` beside `pre-push`, or a stage in an
existing one; whether the protected branch list reads the same `PROTECTED_BRANCHES` the
allowlist hook declares, so one list serves both.

## Ship criterion

- A git commit on a protected branch exits non-zero and names the branch and the flow.
- A worktree commit to a branch other than its own is refused by name.
- An install with no protected branches declared refuses nothing.

## Proof budget

  cases: 3
  tier: shell (a scratch repo; the hook is a real git hook)
  lands in: the existing hook test module
  what already covers this: the allowlist hook covers agents only
