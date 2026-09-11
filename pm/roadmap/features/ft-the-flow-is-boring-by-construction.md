---
id: ft-the-flow-is-boring-by-construction
kind: feature
milestone: "ms-the-ledger-is-a-stamp"
name: the flow is boring by construction
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the flow is boring by construction

Chris, 2026-09-11, mid-0.8.0: *"I want sanity and determinism… this should be almost the dumbest
`git add`, `git commit`, `git merge`… How do we stop the leader agent from doing unnecessary
nonsense?"*, and then: *"if the problem was all yours just violating the contract everywhere, then we
don't really have knowledge of whether or not the contract works. I bet it will."*

**0.8.0's failures were the orchestrator breaking the contract, not the contract failing.** The
orchestrator:

- ran parallel builders in one shared tree, which starved the story belt;
- used the harness's `isolation: "worktree"`, which bases a worktree on the default branch, instead
  of the kit's own `tools/dev/agent-worktree.sh`, which bases on the milestone's `branch:`;
- did an agent's debugging itself, in a worktree, with `git bisect run`, which flipped the repo to
  `core.bare = true`;
- hand-wrote about 25 dispatch briefs, each a fresh chance to get the git flow, base or scope wrong.

The one guard it met, the pathless-commit guard, stopped it correctly. **Prose and memory did not
bind the leader, and hooks did.** So this feature removes the leader's choices and guards the rest. It
is proven by running 0.9.0 itself PARALLEL, by contract, under these guards, and reading its own
telemetry.

## The work: four stories

1. **The dispatch is rendered, not written.** `agentic-sdlc dispatch --grain <id> --role <role>`
   renders the WHOLE brief: the grain, its criteria and files, the git surface, and for
   `--mode parallel` the agent-owned loop (`agent-worktree.sh new <slug>` on the milestone branch →
   build → commit by pathspec → merge back into the milestone branch → `agent-worktree.sh done`). The
   leader passes it verbatim and appends only what the brief cannot know. The installed architect
   brief says: run `dispatch`, never write a brief.
2. **A git allowlist guard** (a PreToolUse Bash hook in the `cc-commit-pathspec.sh` family: stdlib,
   bash-3.2-safe, with a `--self-test` corpus). It allows `add`, `commit` with paths, `push` (never
   to the mainline, as `pre-push` already enforces), reads (`status|diff|log|show|rev-parse|config
   --get`), the milestone merge, and `agent-worktree.sh`'s own worktree calls. It blocks `bisect`,
   `stash`, `reset`, `checkout -- .`, `restore`, `clean`, `rebase`, ad-hoc `worktree add`, `commit
   --amend` and `push --force`, each with the reason and the boring alternative. A project widens the
   list in the project-config header, never silently.
3. **The leader is confined to leading.** A guard on the Agent tool refuses `isolation: "worktree"`
   and names `agent-worktree.sh`. In the leader's session (a declared scope, as `cc-write-confine.sh`
   already does for agents), writes to source and test paths are refused: code goes through a builder,
   and the leader writes the tree, review records and docs.
4. **A ready close stops the leader from stopping.** The leader's Stop gate surfaces `check pm`'s
   `CLOSE` lines (shipped in 0.8.0), so "you have a close ready" is answered before the session ends,
   not read later. Whether that blocks or informs is a project knob, and stock informs.

## Ship criterion

In a consumer with the corpus installed and armed: `git bisect run …`, `git stash` and `git reset
--hard` from an agent session are each blocked with a named reason; `add <path>` + `commit -m … --
<path>` + `push origin <milestone-branch>` pass; an Agent dispatch with `isolation: "worktree"` is
refused naming `agent-worktree.sh`; a leader-scope write to `src/` is refused. `dispatch --grain <id>
--mode parallel` renders the agent-owned worktree loop against the milestone's `branch:`. And 0.9.0
itself is built in parallel under these guards, and its telemetry is in its close.

## Proof budget

  cases: each guard's `--self-test` corpus (a row per allowed and blocked shape), a dispatch render
    case per mode, and one `check hooks` census case
  tier: the corpora replay in `check hooks`; unit for dispatch rendering and self-host byte-current
  lands in: the hooks' own corpora; tests/test_dispatch.py; tests/test_check_hooks.py
  what already covers this: `cc-commit-pathspec.sh` blocks pathless commits, and nothing else binds
    the leader. SDLC.md's rules are prose, and prose did not stop the bisect.
