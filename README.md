# agentic-sdlc

A small, provider-neutral kit for teams that work with coding agents. It does 3 jobs:

1. The model guide: which agent and which model to use for which work. [`AGENTS-AND-MODELS.md`](AGENTS-AND-MODELS.md).
2. The safety hooks and CI checks that keep agents safe and repos lean.
3. The SDLC as Claude Code workflows: `/agentic-sdlc:plan`, `/agentic-sdlc:wave`,
   `/agentic-sdlc:split`, `/agentic-sdlc:review-batch` and `/agentic-sdlc:doc-sdlc`, on a provider-neutral contract for
   Claude and Codex.

It tracks no work and reads no config file. Hooks read env vars; workflows read inputs.

## Scripts

`plugin/bin/wait-ci owner/repo#N ...` polls `gh` and exits as soon as any listed PR has no pending
check. It prints each finished PR with its state and check conclusions. A merged or closed PR is
finished. `WAIT_CI_INTERVAL` sets the poll seconds (default 30). The lead runs it in the background.

## Agents

10 agents, each with its model set. Opus: `chief-of-staff`, `architect`, `reviewer`.
Sonnet: `brief-writer`, `integrator`, `developer`, `simplifier`, `test-writer`, `tech-writer`.
Haiku: `worker`. The tier of a task follows oracle coverage: see the model guide.

## Workflows

- `wave`: one task graph. Each task starts when its blockers are integrated, merges into the wave
  branch 1 at a time, and gets a batched blind review beside the build and rework from its findings.
  It builds only a task that has a claim comment URL in `args.claims`. The runtime forbids the
  clock, so the lead passes `args.started_at` (ISO UTC; the run fails without it) and `args.claimed_at`
  (task id to claim time); the agents report their finish time as `at`. It writes 1 metrics row per
  task. It opens no PR and deletes no branch.
- `split`: one issue, parallel workers on part branches, then an integrator. It works under the
  lead's claim and posts no claim. It opens no PR.
- `review-batch`: one blind reviewer scores several results; 2 skeptics check each major finding.
- `plan`: an architect drafts the task graph, brief-writers expand each task, a critic lists the
  gaps. It returns a contract graph, 1 brief and 1 issue draft per task, and the wave args. It
  files nothing.

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
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - uses: cdowin/agentic-sdlc/checks@v4.0.0
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
      - uses: cdowin/agentic-sdlc/checks@v4.0.0
        with:
          checks: issue-link
```

The 3 reusable workflows under `.github/workflows/` still work. They are deprecated. Use the composite action.

## Tests

`sh tests/run.sh`. License: MIT.
