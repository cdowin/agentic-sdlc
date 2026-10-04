# agentic-sdlc

A small, provider-neutral kit for teams that work with coding agents. It does 2 jobs:

1. It says which agent and which model to use for which work: [`AGENTS-AND-MODELS.md`](AGENTS-AND-MODELS.md).
2. It ships hooks and CI checks that keep agents safe and repos lean.

It tracks no work and reads no config file. Hooks read env vars; workflows read inputs.

## Install for Claude Code

```sh
claude plugin marketplace add cdowin/agentic-sdlc
claude plugin install agentic-sdlc@agentic-sdlc
```

You get 6 agents with their model set (`developer`, `simplifier`, `test-writer`,
`tech-writer` on Sonnet; `reviewer`, `architect` on Opus), the skill
`agents-and-models`, and 4 hooks:

| Hook | Default | What it does |
|---|---|---|
| `git-denylist` | ON (`AGENTIC_SDLC_GIT_DENYLIST=0` turns it off) | Refuses force push, `reset --hard`, `clean -f`, whole-tree discard, `git -c`, `GIT_CONFIG_*=`, `config --global`. |
| `commit-pathspec` | OFF (`AGENTIC_SDLC_COMMIT_PATHSPEC=1`) | Refuses a `git commit` that names no paths, for trees shared by agents. |
| `write-confine` | OFF (`AGENTIC_SDLC_WRITE_CONFINE=1`) | Refuses a file write into another git repo. |
| `context-budget` | ON, warns only | Warns when `CLAUDE.md` > 200, `AGENTS.md` > 100, or `.claude/rules/*.md` > 400 lines. |

Set an env var in `.claude/settings.json` under `"env"`.

## Install for Codex

1 paste: see [`codex/README.md`](codex/README.md). It also lists which hooks Codex runs.

## The 3 CI checks

Reusable workflows. Call each from a job in your own workflow:

```yaml
jobs:
  context-budget:
    uses: cdowin/agentic-sdlc/.github/workflows/context-budget.yml@v3.0.0
  test-budget:
    uses: cdowin/agentic-sdlc/.github/workflows/test-budget.yml@v3.0.0
  issue-link:
    uses: cdowin/agentic-sdlc/.github/workflows/issue-link.yml@v3.0.0
```

- `context-budget`: fails when an always-loaded doc is over budget. Inputs: `claude_md_max`, `agents_md_max`, `rules_max`, `warn_only`.
- `test-budget`: warns when a PR adds more than `ratio` (1.5) test lines per code line, or tests with no code. Never fails. Inputs: `test_globs`, `ratio`.
- `issue-link`: fails when the PR body has no `Closes #N`, `Fixes #N`, `Part of #N`, `Part of owner/repo#N` or `Issue: none (`. Add `edited` to your `pull_request` types.

The hooks are early warnings inside each tool. The CI checks enforce the rules for every provider.

## Tests

`sh tests/run.sh`. License: MIT.
