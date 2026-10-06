# agentic-sdlc

A small, provider-neutral kit for teams that work with coding agents. It does 2 jobs:

1. It says which agent and which model to use for which work: [`AGENTS-AND-MODELS.md`](AGENTS-AND-MODELS.md).
2. It ships hooks and CI checks that keep agents safe and repos lean.

It tracks no work and reads no config file. Hooks read env vars; workflows read inputs.

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
them as 1 step of a job you already have, so they bill no job minute of their own. On a PR
`edited` event only `issue-link` runs. Inputs and behaviour: [CI checks](https://github.com/cdowin/agentic-sdlc/wiki/CI-checks).

```yaml
on:
  pull_request:
    types: [opened, edited, synchronize, reopened, ready_for_review]
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
      - if: github.event.action != 'edited'   # your build and tests
        run: make test
```

The 3 reusable workflows under `.github/workflows/` still work. They are deprecated and go in v4.

## Tests

`sh tests/run.sh`. License: MIT.
