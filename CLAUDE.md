# agentic-sdlc

A public Claude Code plugin and Codex adapter: the model guide, 10 agents, 3 workflows, the
workflow contract, 4 hooks and 3 CI checks (1 composite action). `README.md` says what each
part does.

Process: cdowin/signalandecho (README, skills work-intake and branch-plan).

## Rules for this repo

- The tree is small on purpose. A new file needs a reason a reader of `README.md` would
  accept. No Python, no PM tree, no config file the kit reads.
- `AGENTS-AND-MODELS.md` is the single source for model guidance. Other files point at it.
- `plugin/contract/sdlc.schema.json` is the single source for workflow shapes. It names no
  provider, model or tool; those go in `runtimes.json`. A workflow copies a shape inline (it
  cannot import); `tests/workflows.js` fails when a copy drifts.
- Hooks are POSIX sh (awk, sed, grep, git only). Stdin is the hook JSON. Exit 0 allows;
  exit 2 with a 1-line reason on stderr refuses. Any error fails open. Settings come from
  `AGENTIC_SDLC_*` env vars.
- Every hook has fixtures under `tests/fixtures/<hook>/`: an allowed case and a refused
  case at least. Run `sh tests/run.sh` before you push.
- Docs for people live in the wiki, https://github.com/cdowin/agentic-sdlc/wiki. You may read it.
  Only a local session publishes there; a cloud session drafts the text in its PR body. This repo
  keeps no docs/ and no .md outside the allowlist in ci.yml.
- The repo is public. Name no private repo, person or path in a committed file.
- A version bump changes `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  and the `v<version>` pins in `plugin/skills/`, `codex/AGENTS.md` and `README.md`.
  `tests/run.sh` checks the pins agree. Cut the Release with `gh release create --generate-notes`.
  There is no CHANGELOG.

## CI

`.github/workflows/ci.yml`, job `ci`: the 1 required check and the only job. It runs `./checks`, the docs ratchet
and `tests/run.sh` (skipped on a docs-only change). A draft PR runs nothing.

## Reporting

ASD-STE100. A numbered NEEDS YOU list first, then outcome first, one fact per sentence,
numbers not adjectives.
