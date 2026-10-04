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

3 reusable workflows: `context-budget`, `test-budget`, `issue-link`. Inputs and behaviour: [CI checks](https://github.com/cdowin/agentic-sdlc/wiki/CI-checks).

```yaml
jobs:
  issue-link:
    uses: cdowin/agentic-sdlc/.github/workflows/issue-link.yml@v3.0.0
```

## Tests

`sh tests/run.sh`. License: MIT.
