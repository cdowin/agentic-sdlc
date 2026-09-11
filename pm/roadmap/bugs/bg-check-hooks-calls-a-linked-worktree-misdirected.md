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

## Root cause: the agent-worktree harness, not this repo's arming

**First reading, wrong, and corrected here rather than silently.** It was closed at first as a local
config trap: the stock `tools/setup-hooks.sh` sets the RELATIVE `tools/hooks`, which resolves per
worktree. Re-arming made it pass. Within the hour the value was ABSOLUTE again. Nothing in this repo
writes that, and `.git/config`'s mtime (11:28 local) matched the moment the Claude Code harness created
two agent worktrees (`isolation: worktree`). **The harness writes an absolute `core.hooksPath`
naming the main worktree's corpus into the SHARED config.** Every consumer that runs agents in
worktrees gets the same red line, and no repair clears it, because the harness re-writes it.

## Fix — 8571e36

`checks/hooks.py`: when this checkout is a LINKED worktree and `core.hooksPath` resolves to the MAIN
worktree's `tools/hooks`, it is armed, not misdirected. It is named on a `note` line, because git then
runs the main worktree's corpus, which may differ from this checkout's copy (rule 11). Anything else
that points elsewhere is still MISDIRECTED. Paths are compared resolved, because git answers
`/private/var` where the config says `/var`. The case
`test_a_linked_worktree_armed_at_the_main_worktrees_corpus_is_not_misdirected` fails at HEAD.
