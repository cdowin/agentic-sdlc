---
id: ft-the-flow-is-boring-by-construction
kind: feature
milestone: "ms-the-ledger-is-a-stamp"
name: the flow is boring by construction
status: reviewing
reviewed: docs/reviews/2026-09-12-0.10.0-features.md
depends_on: []
consumed_by: []
changelog: `dispatch` reads a milestone's new `mode: serial|parallel` (or `--mode`) and under parallel renders the agent-owned worktree loop on its `branch:`; its preamble inlines the builder git and scope rules instead of a READ-THESE file list; `install-hooks` ships `cc-git-allowlist.sh` (refuses bisect/stash/reset/checkout/restore/clean/rebase/amend/force-push, each with the alternative) and `cc-agent-isolation.sh` (refuses `isolation: "worktree"`, naming `agent-worktree.sh`); the Stop gate names `check pm`'s CLOSE lines (`CLOSE_READY = inform|block`).
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
is proven by running 0.10.0 itself PARALLEL, by contract, under these guards, and reading its own
telemetry.

## The work: four stories

1. **The dispatch is the verb's output, verbatim.** It already exists: `agentic-sdlc dispatch --grain
   <id> --role <role>` renders the grain and its brief file, the contract files to read first
   (CLAUDE.md, SDLC.md, whose §2 holds the builder git rules, and the pm rule), the ladder, the gate
   roster, the vocabulary, the exit-code contract and the recording line. The subagent TYPE is the
   installed role brief. In 0.8.0 the orchestrator ran it once and then hand-wrote ~25 briefs
   anyway, which is exactly what 0.7.0 ("nothing is hand-rolled") exists to stop. **The one real gap
   is the mode:** the milestone declares `mode: serial|parallel`, and under parallel `dispatch`
   renders the agent-owned loop (`agent-worktree.sh new <slug>` on the milestone's `branch:` → build →
   commit by pathspec → merge back → `agent-worktree.sh done`). The installed architect brief says:
   pass `dispatch`'s output verbatim, and add only what the grain file cannot know.
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
--mode parallel` renders the agent-owned worktree loop against the milestone's `branch:`. And 0.10.0
itself is built in parallel under these guards, and its telemetry is in its close.

## Proof budget

  cases: each guard's `--self-test` corpus (a row per allowed and blocked shape), a dispatch render
    case per mode, and one `check hooks` census case
  tier: the corpora replay in `check hooks`; unit for dispatch rendering and self-host byte-current
  lands in: the hooks' own corpora; tests/test_dispatch.py; tests/test_check_hooks.py
  what already covers this: `cc-commit-pathspec.sh` blocks pathless commits, and nothing else binds
    the leader. SDLC.md's rules are prose, and prose did not stop the bisect.

## Close note — what was not built (0.10.0 W3)

Story 3's second half, the leader write-confinement (refusing a leader-scope write to `src/`), was
**withdrawn at dispatch on 2026-09-12**. The owner's direction that day was a leaner loop, in which
the orchestrator fixes small things itself (review fixes, merge conflicts, one-line gaps) rather than
dispatching a builder for each. A hook that forces every source edit through a builder is the heavy
flow this milestone set out to remove. The Agent-isolation guard, the git allowlist, the dispatch
mode and the Stop gate's CLOSE lines shipped.

