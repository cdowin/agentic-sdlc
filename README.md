# agentic-sdlc

A small, provider-neutral kit for teams that work with coding agents. It does 2 jobs:

1. It says which agent and which model to use for which work: [`AGENTS-AND-MODELS.md`](AGENTS-AND-MODELS.md).
2. It ships hooks and CI checks that keep agents safe and repos lean.

It tracks no work and reads no config file. Hooks read env vars; workflows read inputs.

## Workflow contract

`plugin/contract/` is the 1 contract that every lead and worker follows, on any provider:

- `sdlc.schema.json`: the shapes (task graph, brief, worker report, merge, review, claim,
  phase transition, metrics row) and the shared rules (tiers, roles, limits, transitions).
  It names no provider, model or tool.
- `runtimes.json`: the facts of each provider: the model per tier, agent type names,
  worktree root, concurrency and verified capabilities. A workflow takes 1 as `args.runtime`.
- `check.js`: `node check.js <shape> <file.json> [--repo <dir>]` checks the shape, then the
  meaning (no file in 2 parallel tasks, rework rounds, a SHA on the remote branch).

Docs: https://github.com/cdowin/agentic-sdlc/wiki (install, hooks, CI checks, migration from 2.x).

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
      - uses: cdowin/agentic-sdlc/checks@v3.1.0
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
      - uses: cdowin/agentic-sdlc/checks@v3.1.0
        with:
          checks: issue-link
```

The 3 reusable workflows under `.github/workflows/` still work. They are deprecated and go in v4.

## Tests

`sh tests/run.sh`. License: MIT.
