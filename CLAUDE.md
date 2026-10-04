# agentic-sdlc

A public Claude Code plugin and Codex adapter: the model guide, 6 agents, 4 hooks and 3
reusable CI checks. `README.md` says what each part does.

Process: cdowin/signalandecho (README, skills work-intake and branch-plan).

## Rules for this repo

- The tree is small on purpose. A new file needs a reason a reader of `README.md` would
  accept. No Python, no PM tree, no config file the kit reads.
- `AGENTS-AND-MODELS.md` is the single source for model guidance. Other files point at it.
- Hooks are POSIX sh (awk, sed, grep, git only). Stdin is the hook JSON. Exit 0 allows;
  exit 2 with a 1-line reason on stderr refuses. Any error fails open. Settings come from
  `AGENTIC_SDLC_*` env vars.
- Every hook has fixtures under `tests/fixtures/<hook>/`: an allowed case and a refused
  case at least. Run `sh tests/run.sh` before you push.
- The repo is public. Name no private repo, person or path in a committed file.
- A version bump changes `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  the `v<version>` pins in `plugin/skills/`, `codex/` and `README.md`, and `CHANGELOG.md`.
  `tests/run.sh` checks the pins agree.

## CI

`.github/workflows/ci.yml`, job `ci`: the 1 required check. It runs the 3 reusable
workflows and `tests/run.sh` (skipped on a docs-only change).

## Reporting

ASD-STE100. A numbered NEEDS YOU list first, then outcome first, one fact per sentence,
numbers not adjectives.
