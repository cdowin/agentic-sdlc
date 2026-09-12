---
id: "ms-the-leader-finishes-the-job"
kind: milestone
name: the leader finishes the job
status: planning
depends_on: []
branch: milestone/0.12.0-the-leader-finishes-the-job
mode: parallel
version: 0.12.0
changelog:
order:
  - "ft-a-patch-release-is-a-milestone-of-bugs"
  - "ft-the-guard-lets-the-leader-keep-house"
  - "ft-a-bare-host-is-named-at-session-start"
  - "ft-a-commit-leaves-the-tree-clean"
---

# 0.12.0 — the leader finishes the job

Chris, 2026-09-12: *"You should be able to manage all of this for me."* The three kit gaps that 0.11.1
hit, plus the one open issue (#48): a patch release could not pass its own belt, the guard blocked
routine repo upkeep, a bare host was found by a failed command rather than named at session start,
and every commit dirtied the tree it had just cleaned. Built by the `run-the-sdlc` loop, four lanes
in parallel.

## Ship criterion

Each feature's own criterion holds. From a fresh session in this repo, the orchestrator can release,
sync `main`, delete merged branches and tear down lanes with the armed guard and no `--force` or
`--no-verify`. #48 is closed citing its hash.
