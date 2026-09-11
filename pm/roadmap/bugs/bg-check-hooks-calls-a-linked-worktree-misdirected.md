---
id: bg-check-hooks-calls-a-linked-worktree-misdirected
kind: bug
milestone: "ms-a-consumer-can-take-the-bump"
name: check hooks calls every linked worktree MISDIRECTED
status: fixed
caused_by:
changelog: `check hooks` in a linked worktree whose `core.hooksPath` is the MAIN worktree's `tools/hooks` — what an agent-worktree harness writes — is armed, named on a `note` line saying git runs the main corpus there, instead of failing MISDIRECTED.
---

# check hooks calls every linked worktree MISDIRECTED

Reported by three isolated builders on 2026-09-11. In every linked worktree, `check hooks` failed with
`MISDIRECTED core.hooksPath is '/Users/…/agentic-sdlc/tools/hooks'`, and 7 `test_makefile_gates` cases
failed with it.

## Root cause: this checkout's config, not the kit

The stock arming, `tools/setup-hooks.sh`, sets `core.hooksPath` to the RELATIVE `tools/hooks`. Git
resolves that against each worktree's own root, so a linked worktree runs its own corpus and the check
passes. This repo's shared `.git/config` held an ABSOLUTE path, set by something other than the stock
script, which pointed every linked worktree at the main checkout's hooks.

## Fix

Re-armed with `bash tools/setup-hooks.sh` (2026-09-11): `core.hooksPath` is `tools/hooks` again and
`check hooks` passes. No code change. A code change to accept the absolute form was written and then
backed out, because the stock path never produces it. Closed as a local-config trap. It is recorded
here, and in the milestone handoff's traps, so the next session re-arms rather than patches.
