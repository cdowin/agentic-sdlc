# agentic-sdlc

A small, provider-neutral kit for teams that work with coding agents. It does 3 jobs:

1. The model guide: which agent and which model to use for which work. [`AGENTS-AND-MODELS.md`](AGENTS-AND-MODELS.md).
2. The safety hooks and CI checks that keep agents safe and repos lean.
3. The SDLC as Claude Code workflows: `/agentic-sdlc:flow` (the one loop over ready, claimed
   issues) and `/agentic-sdlc:review-batch` (the review spin), on a provider-neutral contract for
   Claude and Codex.

It tracks no work and reads no config file. Hooks read env vars; workflows read inputs.

## Adopt the kit

The kit has 3 layers. Each layer has 1 owner.

| Layer | Owner | Holds |
|---|---|---|
| Kit | this repo | agents, workflows, hooks, CI checks, the lens skills ([`LENSES.md`](plugin/skills/LENSES.md)), the stack packs and skill `quality-setup` |
| Org overlay | your organization | a named owner for each lens, your data classes, which lenses always run, your scanners and your design tokens |
| Repo overlay | each team | lint config, `Makefile` targets, `.quality-ratchet`, `CONSTITUTION.md`, repo lenses in `.agents/skills/lens-*` |

To onboard a repo, run skill `quality-setup` once. It finds the stack, measures `main`, turns the
gates on at today's counts, adds `make lint`, `make validate`, `make ratchet` and the CI step, and
lists what the team must write. After that, each count can only go down. The full guide, with a
TypeScript and a Python example: [Adopting](https://github.com/cdowin/agentic-sdlc/wiki/Adopting).

## Scripts

`plugin/bin/wait-ci owner/repo#N ...` polls `gh` and exits as soon as any listed PR has a failed check (fail fast) or no pending
check. It prints each finished PR with its state and check conclusions. A merged or closed PR is
finished. A green PR finishes only when every required check of its base has registered, or, with
none required, when its check set is the same for 2 polls. `WAIT_CI_INTERVAL` sets the poll seconds (default 30). The lead runs it in the background.
With `--merge`, it waits for every listed PR and merges the green ones 1 at a time. A PR whose head
lacks the base tip gets GitHub's update-branch first, and merges only when its new checks are green.

`plugin/bin/review-due owner/repo base` prints `PRs since the last spin: N`: the PRs merged into base after the
close time of the newest closed issue titled `Review spin: ...` (all of them when there is none). At
`REVIEW_DUE_EVERY` (default 4) it adds a `REVIEW DUE` line. The count comes from GitHub, never a local file.

`plugin/bin/fix-attempt owner/repo#N "what changed"` runs before each automatic CI-fix push. It counts the
PR's `ci-fix-attempt` marker comments. Under the cap (`CI_FIX_MAX`, default 2) it posts the next one, naming the
failing checks and the change, and exits 0. At the cap it posts nothing, prints the failing check names and each
attempt, and exits 1: push nothing and ask for a decision.

`plugin/bin/cloud-worker [--dry-run] [--gate "<cmd>"]... owner/repo#N <branch> <base> <brief-file>` cuts
the branch from the base and pushes it, then starts 1 cloud worker. Its prompt is the brief, then the
standard tail in `plugin/bin/worker-tail.md`: how to work, the gates the project passes, and the
report formats. A report's first line is exactly `WORKER REPORT branch=<branch> head=<sha>` (or
`WORKER BLOCKED branch=<branch>`), and its **Done when** section marks each done-when line of the issue met or not met. The worker's
first act is a `WORKER STARTED branch=<branch> session=<url>` comment. `CLOUD_WORKER_START` is the command that starts the worker
(the prompt on stdin); the project sets it. It waits until the session exists, prints the session URL and exits 0, or exits
non-zero when no session was created. A start counts only when it prints a URL; then cloud-worker posts
`WORKER LAUNCHED branch=<branch> session=<url>` on the issue. `--dry-run` pushes and starts nothing, and prints the prompt.

`plugin/bin/wait-reports owner/repo#N[@branch] ...` is the twin of wait-ci for workers. It exits on the
first poll with a new `WORKER REPORT` or `WORKER BLOCKED` comment, a close, a stall (no commit and no
comment for `WAIT_REPORTS_STALL` minutes, default 60), or `NOT-STARTED` (a `WORKER LAUNCHED` with no
`WORKER STARTED`, report or branch commit after it for `WAIT_REPORTS_START` minutes, default 10), and prints
each one. Silence counts from the latest commit, comment or launch, so a relaunch does not stall at once.
The issue's comments and the branch are its only state, so any session can watch any worker. A seen file keeps it from
printing an event twice, whenever the watcher started. With `@branch`, only a report whose first line
names `branch=<branch>` counts, so 2 workers on 1 issue each wake only their own watcher. A report with
no `branch=` (from an older tail) counts when its body has a `**Branch**` line naming the branch, or when
that branch is the only one watched on its issue. A watched branch that does not exist exits 2. It exits 0
on each event; only a stopped (killed) watcher shows another non-zero exit. Run it as the background
command itself, then again after each wake.
`--status` prints 1 line per issue (per branch with `@branch`): reported, blocked, not started, silent or closed, the minutes since, and the
branch's ahead count. For a PR, use wait-ci: it exits on merged, conflicting, a failed check or green.

`plugin/bin/land <issue-branch>...` lands finished issue branches in 1 command. It merges them
into a new landing branch in its own worktree, runs the project's regenerate step and quick checks,
pushes, opens 1 PR that closes each issue, enables auto-merge and runs `wait-ci --merge` as the
fallback. When the PR merged, it deletes the merged branches, their worktrees and the session mirror
branches the base contains. A conflict in a generated file keeps the landing branch's side, then the regenerate step adds the
incoming inputs. A conflict outside the generated files stops it: it names the files and
pushes nothing. A branch of a parent named with `--part-of N` (or `LAND_PARENTS`) writes
`Part of #N`, so the parent stays open. A PR left BEHIND gets the base merged, regenerated and
checked, and land waits again. A red check stops it with the check named; the PR stays open.
`--part-of` also takes `owner/repo#N` (written as given) and `#N`. land runs from the main checkout,
so the issue worktree it removes may be its starting point; a failed cleanup step is named and the exit is 1.
The landing worktree sits beside the main checkout (`<checkout>-land`) so a containerized gate that
mounts `$HOME` sees it; `LAND_WORKDIR` names another directory. A progress line prints each minute
of the CI wait. Never chain landings with `pgrep -f`; land every report that is in together, in 1 run.
`land --queue <file>` lands 1 line per run, in order, 1 PR in CI at a time. It stops at the
first line that stops, and a rerun resumes there. `--branch <name>` names the landing branch
(`--wave` is a deprecated alias for 1 release). `LAND_REGEN`, `LAND_GENERATED`,
`LAND_CHECK`, `LAND_BASE` and `LAND_MIRRORS` set the hooks (the v4 `WAVE_LAND_*` names still work for 1 release); the script header lists them.

## Skills

`ui-patterns` gives the `builder` and `reviewer` agents a UI pattern checklist. The 5 lens skills load on demand when a task calls for one.
`plugin/skills/LENSES.md` is the index of the lens skills: the shape of a lens (rule IDs, a severity
and gate or review per rule, a closing checklist) and the change that loads each. The `reviewer`
loads a lens by its trigger, and a repo lens in `.agents/skills/lens-*` the same way.
The kit also ships 5 draft lenses (`code-quality`, `design-system`, `security`, `privacy-compliance`, `robustness`) that the `reviewer` loads by trigger.

The playbook skills are invoked by the `chief-of-staff` agent or named in a brief. The agent has a
routing table for them.

- `project-verify`: creates or maintains a project-local verify skill that launches, drives and captures proof of the real product (a Godot game, a TypeScript CLI, a book build).
- `correct`: finds the mistakes agents repeat and makes each class impossible at the highest level that works.
- `bug-fix`: reproduce on the real surface, find the cause, commit the failing repro first, fix, prove, report.
- `prototype`: settles an open design question with throwaway variants behind 1 switcher.
- `hillclimb`: sustained improvement of one measurable thing against a target.
- `reflect`: turns a finished run into proposed plugin edits, filed as issues. It applies none.
- `eval`: a blind A/B of an edited skill, agent file or brief template against the plugin on main.
- `blast-radius`: finds the 1 fact a change is safe because of, and proves it by running code.
- `session-pickup`: continues an issue that already has a branch, claims or commits.
- `land`: a `lander` agent (bounded tier, in the background) lands pushed branches in 1 PR, waits on CI and cleans up. The lead keeps the decision to merge. 1 PR per repo in CI at a time.

## Agents

4 agents, 1 per role: `chief-of-staff` (the lead, Opus), `builder`, `lander` and `reviewer`.
The lead sets the model of each spawn; the tier of a task follows oracle coverage: see the model guide.

`chief-of-staff` is the plugin's default main thread (`plugin/settings.json`). It works on a cold
start and offers a short setup; the `chief-of-staff-setup` skill writes a starter `work-intake` skill
from your answers. Your workspace `CLAUDE.md` and `work-intake` skill win over the agent's defaults.
To use another main thread, set `agent` in your user, project or local settings, or pass `--agent`.

## Workflows

- `flow` (`/agentic-sdlc:flow`): a loop over ready, claimed issues, with no graph or chain.
  It briefs each task just in time (a task with no issue body briefs itself in its worker) and starts
  a worker when a slot frees and the load allows. Each task
  leases its files from its start to its landing; a task whose files are leased waits, then starts from the
  new head. Each green report lands at once in the group branch of its parent issue (`<parent>-<slug>`),
  over a green gate and reach; the issue closes and its branch goes. A base red holds only its group
  branch. When every task of a parent has landed, it merges main into the group branch (a merge commit),
  runs `converge_gate` (the full suite; default `gate`) once there and, on green, opens 1 PR that closes
  the parent and merges itself on green. Red: no PR, 1 `sev:holds` finding, and the group stays open.
  It never pushes to main.

  Findings: a worker reports each problem outside its task with a kind (`bug`, `convergence`,
  `test-gap`, `tests`, `perf`, `design-question`, `feel`, `docs`), a severity (`holds`, `major`, `minor`) and the
  minutes it cost. 1 agent at a time searches the open findings: on a match it votes (1 comment naming
  the task and the minutes lost, and a +1 reaction); else it files 1 issue labelled `kind:<kind>` and
  `sev:<severity>`. A major or minor finding never delays a landing. Only `holds` (main would break: a red
  gate, a crash, data loss, a broken save, a shipped feature that stops working) stops a landing: it gets
  exactly 1 fix agent at once, and no task of its group lands until that agent ends. Other groups land on.
  A queue entry with `finding` (`severity`, `votes`, `minutes`) is a queued finding; queued findings
  start in priority order, severity weight (`x-severity-weights`: holds 9, major 3, minor 1) x votes x
  minutes lost, in the places findings hold in the queue.

  Reviews: each landing gets 1 diff review of its merge on the bounded tier (role `diff_reviewer`). Each
  `review_every` landings (default 6) get 1 blind batched review on the lead tier: it reads their diffs
  together, not the issues or the worker reports; the landings left at the end get 1 more. A review
  reports classified findings (`landing_review`) and files nothing: each goes to the finding agent, which
  votes or files. No landing waits on a review. Only a `holds` finding stops anything: it gets 1 fix agent
  before the next landing of its group. A group ships after the diff reviews of its landings end.

  ```
  /agentic-sdlc:flow {"repo": "owner/repo", "base": {"ref": "main", "sha": "<sha>"},
    "queue": [{"issue": 21, "parent": 20, "group": "20-save", "tier": "judgment", "files": ["src/save.ts"],
      "oracle": {"command": "npm test -- save", "files": [], "uncovered": []}, "body": "<issue body>"}],
    "claims": {"21": "<claim url>"}, "gate": "make check", "converge_gate": "make test", "max_load": 1.5, "cpus": 8, "review_every": 6, "started_at": "<date -u>"}
  ```

  `queue` may also be a gh command; the first agent runs it. `max_load` is the load average per core.
- `review-batch`: one blind reviewer scores several results; 2 skeptics check each major finding.

The PR, the CI gate and the merge to main stay with the main agent.

## Workflow contract

`plugin/contract/` is the 1 contract that every lead and worker follows, on any provider:

- `sdlc.schema.json`: the shapes (task graph, brief, worker report, merge, review, claim,
  phase transition, metrics row) and the shared rules (tiers, roles, limits, transitions).
  It names no provider, model or tool.
- `runtimes.json`: the facts of each provider: the model per tier, agent type names,
  worktree root, concurrency and verified capabilities. A workflow takes 1 as `args.runtime`.
- `check.js`: `node check.js <shape> <file.json> [--repo <dir>]` checks the shape, then the
  meaning (no file in 2 parallel tasks, rework rounds, a SHA on the remote branch). Its shared
  blocks are copied into each workflow by `node tests/workflows.js --write`.

Docs: https://github.com/cdowin/agentic-sdlc/wiki (install, hooks, CI checks, workflows, agents, migration from 2.x).

## Use it without GitHub issues

You can use the kit with Jira, with another tracker or with no tracker. Most parts need no
GitHub. This table shows what each part needs.

| Part | Tracker | GitHub | git remote `origin` |
| --- | --- | --- | --- |
| `chief-of-staff` | Your `work-intake` skill names it | No | No |
| Playbook skills | No | No (`reflect` and `session-pickup` read and file GitHub issues; `land` opens a PR) | No (`land`: yes) |
| `flow` | No, with `args.claims: "solo"` | Yes: it files findings, closes issues and opens PRs with `gh` | Yes: workers push task branches |
| `wait-ci` | No | Yes: it polls PR checks with `gh` | No |
| `land` | No | Yes: it opens and merges the PR with `gh` | Yes |
| Auto-merge (`gh pr merge --auto`) | No | Yes | No |
| The claim takeover (`check.js claim`) | No | Yes: claims are GitHub issue comments | Yes |

The remote `origin` can be on any git host. For 1 lead, or with no GitHub issues, run `flow`
with `claims: "solo"`. Post no claim comments. 2 or more leads on 1
queue need the claim comments: without them, 2 leads can build the same task.

## Change it for your team

Change the kit with these inputs. Do not fork it.

- `work-intake` and `CLAUDE.md` or `AGENTS.md`: they say where work lives and how to report. They
  win over the `chief-of-staff` defaults.
- The `agent` setting: set another main thread in your user, project or local settings.
- Workflow args: `rules` (your code rules as text), `decisions` (choices the reviewer does not
  report), `gate` (the fast per-merge check; it covers every lane the repo's PR CI runs), `converge_gate` (the full check, run once on each group branch before its PR), `runtime` (a
  provider profile), `claims`, and `setup` (a command each agent runs once in a fresh worktree before
  any oracle or gate; the lander runs it again after each merge, before the gate).
- The review lens files: `CONSTITUTION.md` and `.claude/review-lens.md` in your repo. Every
  reviewer reads them. `args.lens` names other paths; `[]` turns the lens off.
- The test caps: the `test-budget` inputs (`ratio`, `suite_max`, `suite_ratio`,
  `test_data_max`) and "Tests" in `AGENTS-AND-MODELS.md`.

Workflows spawn the plugin agent types by name: `agentic-sdlc:builder`, `agentic-sdlc:reviewer`
and the others in `runtimes.json`. They do not spawn an agent file of your repo. A changed agent
file in `.claude/agents/` does not change a run. To use your own agent types, pass
`args.agent_types` (see "Tools per role") or `args.runtime` with your own `agent_types`.
The lead chooses where agents run (the plugin is the car, the lead is the driver). An `agent_types`
entry may be a dispatcher that runs the work elsewhere and returns the same schema: set
`args.runtime.remote` true. Workflows name the work, not the place; `max_load` and the slot cap
then limit where the agents run.

`name-workflow` copies the installed workflow for each run. If you copy a workflow script, edit
it and run it by `scriptPath`, that is a fork. It gets no fixes from new releases, and no test
checks it against the contract.

## Tools per role

The lead (`agentic-sdlc:chief-of-staff`) has no `tools:` line. It inherits every tool of the session, including MCP connector tools, ToolSearch and the tools your host app adds.
Each delegate agent has a `tools:` or `disallowedTools:` line. A delegate gets only the tools its role needs.
To point a role at your own agent, put a file in `.claude/agents/<name>.md` and pass `args.agent_types`, for example `{"builder": "<name>"}`. It maps a role to an agent type and is merged over the built-in map. A key must be a role: `lead`, `builder`, `lander` or `reviewer`; a value must be a non-empty string. Any other key or value is refused with a line naming the key.
To forbid something everywhere, add it to `permissions.deny` in your settings. It applies to subagents too. Examples: `Agent(Explore)`, `Bash(git push --force*)`.
A `tools:` line cannot limit spawn types without also limiting the lead's other tools, so use `permissions.deny` for that.
Your own `agent` setting replaces the default main agent. The plugin's `settings.json` sets `agentic-sdlc:chief-of-staff`; set `agent` in your project or user settings to use another.

## Install for Claude Code

```sh
claude plugin marketplace add cdowin/agentic-sdlc
claude plugin install agentic-sdlc@agentic-sdlc
```

## Install for Codex

1 paste: see the wiki page [Install for Codex](https://github.com/cdowin/agentic-sdlc/wiki/Install-for-Codex).

## CI checks

5 checks: `context-budget`, `test-budget`, `issue-link`, `comment-budget`, and the opt-in `ratchet`
(per-file counts of lens rules that may only go down; skill `quality-setup` turns it on). The composite action `checks` runs
them as steps of a job you already have, so they bill no job minute of their own. Inputs and
behaviour: [CI checks](https://github.com/cdowin/agentic-sdlc/wiki/CI-checks).

`context-budget` counts only root `CLAUDE.md`, `AGENTS.md` and `.claude/rules/*.md`. It does not
count `plugin/agents/`, `plugin/skills/` or `codex/AGENTS.md`, so a green check says nothing about them.

`test-budget` also adds up the tracked bytes of generated test data: goldens, snapshots,
fixtures, baselines and recordings (input `test_data_globs`). It prints the total and the 10
largest files. It fails when the total is over `test_data_max` (default 5,000,000 bytes).
It warns when a PR adds over `ratio` test lines per code line (default 0.5). It fails when the
suite is over `suite_max` test lines or `suite_ratio` test lines per code line; unset means no cap.
The rule for tests is "Tests" in `AGENTS-AND-MODELS.md`.

Each ratio has a warning level, which prints a warning and passes, and a limit, which fails the
check. `suite_warn_ratio` warns and `suite_ratio` fails on suite test lines per code line.
`comment-budget` counts 2 kinds of line: comments and doc comments (the language's documentation
syntax). It checks comment lines in code files per code line (`comment_warn_ratio`, `comment_ratio`),
doc lines in code files per code line (`doc_comment_warn_ratio`, `doc_comment_ratio`) and comment
lines in test files per test line (`test_comment_warn_ratio`, `test_comment_ratio`). With none set it
passes silently. A line is the kind of the longest marker it starts with, after blanks. A marker
that starts with `/*` opens a block: each line up to the one with `*/` is that kind. A `#!` line is
not a comment. Python docstrings are not counted. The built-in marker table:

| Extensions | Comment | Doc |
|---|---|---|
| `sh bash py rb yml yaml toml` | `#` | none |
| `gd` | `#` | `##` |
| `rs` | `//` | `///`, `//!` |
| `cs swift` | `//` | `///` |
| `js ts mjs cjs jsx tsx` | `//` | `/**` block |
| `c h cpp java kt` | `//`, `/*` block | `/**` block |
| `go` | `//`, `/*` block | none |
| `lua sql` | `--` | none |
| `lisp el clj scm` | `;` | none |

`comment_markers` adds a row or replaces one: space-separated entries
`ext=comment[,comment][|doc[,doc]]`, for example `lua=--` or `gd=#|##`. `code_globs` makes code only the non-test files that match
it; empty keeps every file that is not a test or docs.

Set a CI time budget of about 3 minutes with `timeout-minutes` on the required job. GitHub
cancels a job at its timeout and the check fails, so a slow suite shows as a red check, not
as a slow queue. A short budget keeps the feedback loop of each agent short and forces
samples instead of sweeps. The kit adds no check for it: GitHub already enforces the timeout.

Run `issue-link` in its own workflow, not in a required check. A required check must not run on
the PR `edited` event: a re-run with the build skipped turns the check green over a red run.

```yaml
# check.yml: the required check
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
jobs:
  check:
    if: github.event.pull_request.draft != true   # a draft PR runs nothing
    runs-on: ubuntu-latest
    timeout-minutes: 3   # the CI time budget
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - uses: cdowin/agentic-sdlc/checks@v4.22.0
        with:
          checks: context-budget test-budget
      - run: make test   # your build and tests
```

```yaml
# issue-link.yml: not required; a body edit re-checks only the body
on:
  pull_request:
    types: [opened, edited, reopened, ready_for_review]
jobs:
  issue-link:
    if: github.event.pull_request.draft != true
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: cdowin/agentic-sdlc/checks@v4.22.0
        with:
          checks: issue-link
```

The 3 reusable workflows under `.github/workflows/` still work. They are deprecated. Use the composite action.

## Tests

`sh tests/run.sh`. License: MIT.
