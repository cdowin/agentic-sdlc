---
id: "ms-the-rules-hold-everywhere"
kind: milestone
name: the rules hold everywhere
status: planning
depends_on: []
branch: milestone/0.16.0-the-rules-hold-everywhere
mode: parallel
version: 0.16.0
changelog: The flow's rules now hold where the work happens: CI confirms once per PR, install-ci prints the GitHub ruleset that enforces merge-commit-only main and immutable tags, and the git allowlist judges the repository a command touches.
order:
  - "ft-ci-confirms-once-and-the-server-holds-the-flow"
  - "ft-the-allowlist-judges-the-repo-a-command-touches"
---

# ms-the-rules-hold-everywhere — the rules hold everywhere

Found wiring five consumer repos on 2026-09-28. The flow's rules were enforced only by client
hooks, which only an armed agent runs; CI ran the full gate on every push and used up a private
repo's Actions minutes (802 runs in 30 days); and the allowlist blocked cross-repo work it already
permits, so the operator hand-rolled a GitHub API commit. Issues #81, #82, #83.

## Ship criterion

- A fresh `install-ci` writes a verify workflow that runs once per PR, cancels a stale run and
  times out.
- `install-ci --ruleset` prints the two ruleset payloads a consumer applies with one `gh api` line.
- `git -C ~/<other repo> …` and `git clone <url> <path outside>` pass the allowlist; a refusal of
  a command naming an outside path names the absolute-`-C` route.
- `make milestone` green on this tree.

## Risks
