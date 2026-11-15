# agentic-sdlc

A small kit for a lead agent that runs builder agents, for Claude Code and Codex. It is a launcher
for cloud lanes, a report protocol on the issue, and short role agents. It does not tell an agent
how to prove work beyond "run the repo's proof command, then say what you saw": the repo decides
that. Detail lives in the [wiki](https://github.com/cdowin/agentic-sdlc/wiki).

## Install

Pin it in the repo's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "agentic-sdlc": { "source": { "source": "github", "repo": "cdowin/agentic-sdlc", "ref": "v6.0.0" } }
  },
  "enabledPlugins": { "agentic-sdlc@agentic-sdlc": true }
}
```

When the running version differs from the pin (the local marketplace clone lacks the tag), the
`pin-check` hook prints 1 line at session start naming both.

The plugin sets no default agent. A repo that wants the lead as its main thread adds
`"agent": "agentic-sdlc:chief-of-staff"` to the same file.

Codex: 1 paste, see [Install for Codex](https://github.com/cdowin/agentic-sdlc/wiki/Install-for-Codex).

## The roles

| Role | Agent | Job |
|---|---|---|
| Lead | `chief-of-staff` | The main thread, when a repo opts in: answers, files work, launches builders, decides merges |
| Builder | `builder` | 1 issue, 1 branch: builds, runs the proof command, pushes each commit, reports; opens no PR |
| Reviewer | `reviewer` | 1 cold review, simplicity first; edits nothing |
| Lander | `lander` | Optional: lands reported branches through CI (see "Repos with tests and CI-gated landing") |

The brief is the task. Each agent reads the repo's `CLAUDE.md`, which wins over the agent file.

## The report protocol

A builder posts on its issue, each comment's first line exactly:

- `WORKER STARTED branch=<branch> session=<url or unknown>`: its first act.
- `WORKER REPORT branch=<branch> head=<sha> passed`: done, the proof passed, the head is pushed.
- `WORKER BLOCKED branch=<branch>`: then 1 question, or the red command and its last line.

It pushes after every commit, opens no PR and never goes silent: a hung command is a `BLOCKED`.

## Launch and watch (`plugin/bin/`)

Each script's header is its manual.

- `cloud-worker [--gate "<cmd>"]... owner/repo#N <branch> <base> <brief-file>`: cuts the branch,
  starts 1 cloud builder with the brief plus the launcher tail (`worker-tail.md`: the protocol and the
  proof command, nothing else), and posts `WORKER LAUNCHED`. `--dry-run` prints the prompt.
- `wait-reports owner/repo#N[@branch] ...`: wakes on a `WORKER REPORT`, a `WORKER BLOCKED`, a stall,
  a lane that never started, or a close. `--status` prints each.

A host with its own session tool can start the lane itself with the same brief and tail. Work
someone must see in a window goes to a local `builder` instead.

## Repo config: the settings env block

The repo config is the `env` block of `.claude/settings.json`; the kit reads no config file.

| Key | Read by | Meaning |
|---|---|---|
| `LAND_CHECK` | the builder, `cloud-worker`'s tail, `land` | The proof command, for example `make check` |
| `CLOUD_WORKER_START` | `cloud-worker` | The command that starts a cloud session (prompt on stdin) and prints its URL |
| `CLOUD_WORKER_TAIL` | `cloud-worker` | A tail file to use instead of `worker-tail.md` |
| `WAIT_REPORTS_START`, `WAIT_REPORTS_STALL` | `wait-reports` | Minutes to `NOT-STARTED` (10) and to `STALL` (60) |

A proof can be a command plus "then a look": the builder runs the command and says what it saw,
and the lead or a person looks. Hook switches go in the same block; each hook's header lists its own.

## Skills

- `session-pickup`: resume an issue a prior agent left, from its branch and `WORKER` comments.
- `project-verify`: create or fix a repo's `verify-<app>` skill, the scripted way to launch,
  drive and capture the real product (a Godot game, a CLI, a book build).

## Hooks

- `git-denylist` (on): refuses git that destroys local work, such as a force-push or `reset --hard`.
- `pin-check` (on): the version line above.
- `commit-pathspec` and `write-confine` (opt in by env var): commit by path; write only in the
  session's own repo or worktree.

## CI checks

1 composite action for a repo's CI: `uses: cdowin/agentic-sdlc/checks@v6.0.0`. It runs
`context-budget` (line budgets of `CLAUDE.md`, `AGENTS.md`, `.claude/rules/`), `test-budget`,
`comment-budget`, `issue-link` and the opt-in `ratchet`. Inputs:
[CI checks](https://github.com/cdowin/agentic-sdlc/wiki/CI-checks).

## Repos with tests and CI-gated landing

Optional. A repo with a test suite and a required CI check can opt into the heavier loop: 1 builder
per ready issue, a lander merging each passed report into 1 draft PR, CI as the gate, a blind
batched review. None of it runs unless the lead starts it.

- `flow` (`plugin/workflows/flow.js`): runs the ready issues with the tracker as the state; safe to
  re-run. Args: `repo`, `base` (`{ref, sha}`), `queue`, `gate` (the fast check), and optional
  `group_pr`, `setup`, `review_every`, `rules`, `runtime`, `agent_types`. Start it through
  `name-workflow`. Each read is `queue-state`.
- `review-batch`: 1 blind reviewer over several results; 2 skeptics check each major finding.
- The `lander` agent and `land`: land finished branches in 1 PR, wait on CI with `wait-ci`, clean
  up after a MERGED read; `fix-attempt` caps automatic CI-fix pushes.
- `plugin/contract/`: the provider-neutral shapes the workflows use, each runtime's facts
  (`runtimes.json`) and the checker.

Its config keys, in the same env block:

| Key | Read by | Meaning |
|---|---|---|
| `AGENTIC_SDLC_RUNTIME` | the lead, as flow `runtime` | A runtime profile (JSON) when builders do not run local-like |
| `CI_FIX_MAX` | `fix-attempt` | Automatic CI-fix pushes per PR (default 2) |
| `LAND_BASE`, `LAND_REGEN`, `LAND_GENERATED`, `LAND_PARENTS`, `LAND_MIRRORS`, `LAND_WORKDIR`, `LAND_REPO` | `land` | Base branch, regenerate step, generated files and the rest; the script header lists them |

Map a role to your own agent type with flow `agent_types`, for example `{"builder": "<name>"}`;
an agent type of the repo's own can carry its test rules.

Tests: `sh tests/run.sh`. License: MIT.
