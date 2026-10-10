# agentic-sdlc

A small, provider-neutral kit for teams that work with coding agents. It does 3 jobs:

1. The model guide: which agent and which model to use for which work. [`AGENTS-AND-MODELS.md`](AGENTS-AND-MODELS.md).
2. The safety hooks and CI checks that keep agents safe and repos lean.
3. The SDLC as Claude Code workflows: `/agentic-sdlc:plan`, `/agentic-sdlc:wave`,
   `/agentic-sdlc:split`, `/agentic-sdlc:review-batch` and `/agentic-sdlc:doc-sdlc`, on a provider-neutral contract for
   Claude and Codex.

It tracks no work and reads no config file. Hooks read env vars; workflows read inputs.

## Scripts

`plugin/bin/wait-ci owner/repo#N ...` polls `gh` and exits as soon as any listed PR has a failed check (fail fast) or no pending
check. It prints each finished PR with its state and check conclusions. A merged or closed PR is
finished. `WAIT_CI_INTERVAL` sets the poll seconds (default 30). The lead runs it in the background.

## Skills

`ui-patterns` gives the `developer`, `architect` and `reviewer` agents a UI pattern checklist. The 5 lens skills serve `doc-sdlc`.

The playbook skills are invoked by the `chief-of-staff` agent or named in a brief. The agent has a
routing table for them.

- `project-verify`: creates or maintains a project-local verify skill that launches, drives and captures proof of the real product (a Godot game, a TypeScript CLI, a book build).
- `correct`: finds the mistakes agents repeat and makes each class impossible at the highest level that works.
- `bug-fix`: reproduce on the real surface, find the cause, commit the failing repro first, fix, prove, report.
- `prototype`: settles an open design question with throwaway variants behind 1 switcher.
- `hillclimb`: sustained improvement of one measurable thing against a target.
- `reflect`: turns a finished wave into proposed plugin edits, filed as issues. It applies none.
- `eval`: a blind A/B of an edited skill, agent file or brief template against the plugin on main.
- `blast-radius`: finds the 1 fact a change is safe because of, and proves it by running code.
- `session-pickup`: continues an issue that already has a branch, claims or commits.

## Agents

10 agents, each with its model set. Opus: `chief-of-staff`, `architect`, `reviewer`.
Sonnet: `brief-writer`, `integrator`, `developer`, `simplifier`, `test-writer`, `tech-writer`.
Haiku: `worker`. The tier of a task follows oracle coverage: see the model guide.

`chief-of-staff` is the plugin's default main thread (`plugin/settings.json`). It works on a cold
start and offers a short setup; the `chief-of-staff-setup` skill writes a starter `work-intake` skill
from your answers. Your workspace `CLAUDE.md` and `work-intake` skill win over the agent's defaults.
To use another main thread, set `agent` in your user, project or local settings, or pass `--agent`.

## Workflows

- `wave`: one task graph. Many small workers build from the issues as written, and 1 review runs at
  the end. First 1 agent reads what an earlier run left on the remote (see answers below). Then,
  before any build, 1 agent runs each oracle in list mode (Playwright: `--list`). An
  oracle that selects 0 tests refuses the graph, unless the task, or a task it waits on, writes the oracle file.
  The same agent runs each oracle once on the base: a test red there is no task's, so it stops no worker
  and no merge. The brief of a task is its issue body, as written
  (`args.issues`), when the body has Outcome, Done when, Files, Proof and Decisions. Then no
  brief-writer runs. For an issue that lacks a part, a brief-writer writes that part only. The lead's
  answers (`args.answers`) come last in every brief, and nothing overrides them. A brief that widens
  a task's files into a parallel task makes the 2 tasks run one after the other; it stops nothing.
  A worker picks each how-to choice itself and names it. An escalation with no quote from the issue
  goes back to the worker once. Each task starts when its blockers are integrated, and merges into
  the wave branch 1 at a time. A clean merge whose tree is the tree the worker proved runs only the
  gate (`reproved: false` in the metrics row). Tasks with the same `chain` build on 1 branch,
  `<wave>-<chain>`; 2 chains may edit the same file. When every chain task has ended, 1 integrator
  merges the chains into the wave branch, in the order each chain first appears in the graph, and runs
  the gate once. The wave then logs "open the wave PR now". After the last merge, 1 lead-tier reviewer reads the whole wave head.
  A CRITICAL or major finding gets 1 rework round on its task. The minor findings return as 1
  follow-up issue draft. `args.review: "batch"` keeps the old batched review beside the build, with
  2 skeptics per finding. A task with `resume_from` (a SHA or a remote branch) continues that work.
  To answer a question, add it to `args.answers` and run the same graph again: a task merged by an
  earlier run is skipped, and a task whose branch is on the remote resumes from its head.
  The blast-radius lens: 1 check for each task the plan marks risky (in batch mode, also for each
  finding above minor), at most 4 in a wave. It adds the regression lane: with `args.regression`, 1 agent
  runs the one load-bearing scenario on the base commit and 1 on the wave head. A pass on the base
  and a fail on the head escalates the wave. With no merge, the lane is skipped.
  It builds only a task that has a claim comment URL in `args.claims`. The runtime forbids the
  clock, so the lead passes `args.started_at` (ISO UTC; the run fails without it) and `args.claimed_at`
  (task id to claim time); the agents report their finish time as `at`. It writes 1 metrics row per
  task, with `browser_s` and `lock_wait_s`; the run summary sums them. Each merge deletes the scaffold spec tests its task added, when the oracle and gate pass without them.
  It opens no PR and deletes no branch. Claude Code runs at most min(16, CPUs - 2) agents of 1
  workflow at once: 2 on a 4-CPU container. Pass `args.cpus` and the wave logs the cap, the CPU count
  and the chains at start. On fewer than 8 CPUs with more than 3 chains, it warns that browser runs will
  queue. For a graph too large to pass
  inline, write the args to a file: `plugin/bin/name-workflow --args args.json wave "<goal>"`.
- `split`: one issue, parallel workers on part branches, then an integrator. It works under the
  lead's claim and posts no claim. It opens no PR.
- `review-batch`: one blind reviewer scores several results; 2 skeptics check each major finding.
- `plan`: an architect drafts the task graph, brief-writers expand each task, a critic lists the
  gaps. It returns a contract graph, 1 brief and 1 issue draft per task, and the wave args. It
  files nothing. It runs a spec step for a task whose oracle does not cover the behaviour: a judgment
  agent writes stubs, failing tests and a caller usage sketch on its own `spec/<task-id>` branch, cut
  from the wave base (1 spec round). The task is re-checked for the bounded tier. A task never edits
  its own oracle. The spec marks each test `keep` or scaffold; a scaffold test guides the build only.
  A one-way door gets 2 designs and 1 judge first.

- `doc-sdlc`: the document SDLC. A brief that records a source precedence list, a base draft, one
  layer per lens, parallel review, up to 2 fix rounds, then `validated` (true when no check blocks;
  remaining should-fix items are listed in `shouldFix` for you). The 5 lens skills are
  `plain-language`, `accessible-content`, `visual-layout`, `multimedia-design` and `usability-review`.
  Every reviewer checks numbers and facts against the precedence list. The `visual-layout` reviewer
  has no browser: take screenshots at 375, 1000 and 1440 px yourself and pass the files, or its
  screenshot checks score n/a. The `humanizer` layer is optional and is not in this plugin: install
  [blader/humanizer](https://github.com/blader/humanizer) (MIT) and pass its path, or the layer is skipped.

  ```
  /agentic-sdlc:doc-sdlc {"brief": "A post on what we shipped this month", "kind": "post",
    "target": "posts/shipped.md", "screenshots": ["shots/375.png", "shots/1000.png", "shots/1440.png"],
    "humanizerPath": "~/.claude/skills/humanizer/SKILL.md"}
  ```

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

## Install for Claude Code

```sh
claude plugin marketplace add cdowin/agentic-sdlc
claude plugin install agentic-sdlc@agentic-sdlc
```

## Install for Codex

1 paste: see the wiki page [Install for Codex](https://github.com/cdowin/agentic-sdlc/wiki/Install-for-Codex).

## CI checks

3 checks: `context-budget`, `test-budget`, `issue-link`. The composite action `checks` runs
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
      - uses: cdowin/agentic-sdlc/checks@v4.5.0
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
      - uses: cdowin/agentic-sdlc/checks@v4.5.0
        with:
          checks: issue-link
```

The 3 reusable workflows under `.github/workflows/` still work. They are deprecated. Use the composite action.

## Tests

`sh tests/run.sh`. License: MIT.
