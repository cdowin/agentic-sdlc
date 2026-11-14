# agentic-sdlc

A small kit for teams that build with coding agents, for Claude Code and Codex. The tracker is the
only state: a ready issue goes in, a merged PR comes out. The kit owns what models cannot do alone:
knowing when they are done (the oracle), noticing silence, landing shared work, and spending a
person's attention well. Models brief themselves. Detail lives in the
[wiki](https://github.com/cdowin/agentic-sdlc/wiki).

## The loop

1. A **ready issue** has an outcome, a done-when and a proof command. No oracle, not ready. Order
   is `blocked-by` links.
2. `flow` opens a **draft PR** for the work when it starts (intent first), and starts 1
   **builder** per issue, on its own branch, local or in a cloud session.
3. The builder posts `WORKER STARTED`, runs only narrow tests, pushes, and posts 1
   `WORKER REPORT branch=<b> head=<sha> passed` when green (else `WORKER BLOCKED` with 1 question).
4. A **lander** merges each green report into the PR branch with the fast check. Every push runs
   the **fast CI lane**.
5. After the last issue lands, the PR is marked **ready**: the **heavy lane** runs once, and the PR
   merges itself on green. Cleanup runs only after a MERGED read.
6. Every few merged PRs, a **review spin** (a blind reviewer, simplicity first) files findings as issues.

The `flow` workflow runs this loop and is safe to re-run: it reads the tracker and picks up where it says.

## Install

Claude Code, pinned in the repo's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "agentic-sdlc": { "source": { "source": "github", "repo": "cdowin/agentic-sdlc", "ref": "v5.2.0" } }
  },
  "enabledPlugins": { "agentic-sdlc@agentic-sdlc": true }
}
```

Codex: 1 paste, see [Install for Codex](https://github.com/cdowin/agentic-sdlc/wiki/Install-for-Codex).
The 4 roles and the report protocol are the same.

## Adopt it in 3 steps

1. **Pin the plugin** (above).
2. **Run the `chief-of-staff-setup` skill.** It writes a starter `work-intake` skill, writes the
   repo config (below) from your CI, and checks that your CI has the shape the loop needs: the fast
   lane runs on draft and ready PRs, the heavy lane only when a PR is ready, and branch protection
   requires 1 aggregate check. It says what to change when it does not.
3. **Say "work the queue".** Mark issues ready; the chief of staff runs `flow` over them.

## Repo config: the settings env block

The repo config is the `env` block of `.claude/settings.json`. It is not a new file: the kit reads
no config file. Hooks and scripts read these env vars; the chief of staff reads the rest and passes
them on.

| Key | Read by | Meaning |
|---|---|---|
| `LAND_CHECK` | `land`; the lead passes it as flow `gate` and `cloud-worker --gate` | The fast check: narrow tests and lint, seconds |
| `AGENTIC_SDLC_GATE_WIDE` | `wide-gate` hook | An ERE naming the wide (full-suite) command; an agent that runs it is refused |
| `AGENTIC_SDLC_MAX_LOAD` | `gate` | Load per core above which `gate wide` will not start (default 2) |
| `AGENTIC_SDLC_VERIFY` | the lead | The smoke command that proves the real product (`project-verify`) |
| `AGENTIC_SDLC_RUNTIME` | the lead, as flow `runtime` | A runtime profile (JSON) when builders do not run local-like: capabilities and `environment` |
| `REVIEW_DUE_EVERY` | `review-due` | Merged PRs between review spins (default 4) |
| `CI_FIX_MAX` | `fix-attempt` | Automatic CI-fix pushes per PR (default 2) |
| `WAIT_REPORTS_START`, `WAIT_REPORTS_STALL` | `wait-reports` | Minutes to `NOT-STARTED` (10) and to `STALL` (60) |
| `CLOUD_WORKER_START` | `cloud-worker` | The command that starts a cloud session and prints its URL |
| `LAND_BASE`, `LAND_REGEN`, `LAND_GENERATED`, `LAND_PARENTS`, `LAND_MIRRORS`, `LAND_WORKDIR`, `LAND_REPO` | `land` | Base branch, regenerate step, generated files and the rest; the script header lists them |

Hook switches (`AGENTIC_SDLC_WRITE_CONFINE` and the others) go in the same block; each hook's header lists its own.

## The 4 roles

| Role | Agent | Model | Job |
|---|---|---|---|
| Lead | `chief-of-staff` | Opus | The main thread: ready issues, launches, each merge decision, NEEDS YOU |
| Builder | `builder` | by oracle coverage | 1 issue, 1 branch, 1 report; brief and spec are its modes |
| Lander | `lander` | Haiku first, Sonnet on a conflict | Merge, fast check, the 1 PR, CI, cleanup |
| Reviewer | `reviewer` | Haiku per landing, Opus for a blind batch | Simplicity first, then lenses; edits nothing |

`chief-of-staff` is the default main thread (`plugin/settings.json`). Which model for which work:
[`AGENTS-AND-MODELS.md`](AGENTS-AND-MODELS.md). Map a role to your own agent type with flow
`agent_types`, for example `{"builder": "<name>"}`.

## Workflows

- `flow`: the loop above. Args: `repo`, `base` (`{ref, sha}`), `queue` (issue numbers, or a command
  that prints them 1 per line), `gate` (the fast check, required), and optional `group_pr` (1 PR for the
  whole queue), `setup`, `review_every`, `rules`, `runtime`, `agent_types`. Each read is `queue-state`. Start it through `name-workflow`.
- `review-batch`: 1 blind reviewer over several results; 2 skeptics check each major finding.

## Scripts (`plugin/bin/`)

Each script's header is its manual.

- `cloud-worker`: cuts the branch, starts 1 cloud builder with the brief and the standard tail, posts `WORKER LAUNCHED`.
- `queue-state`: prints the tracker read of a flow as JSON, by fixed rules (trusted authors, `passed` reports, group PR Closes and holds).
- `wait-reports`: waits for a `WORKER REPORT`, `WORKER BLOCKED`, a stall, a not-started or a close; `--status` prints each.
- `wait-ci`: waits for a PR's checks; `--merge` merges green PRs 1 at a time.
- `land`: lands finished branches in 1 PR, waits on CI, cleans up after a MERGED read; `--queue` lands in order.
- `fix-attempt`: counts automatic CI-fix pushes on a PR and stops at `CI_FIX_MAX`.
- `review-due`: counts merged PRs since the last review spin and prints `REVIEW DUE` at `REVIEW_DUE_EVERY`.
- `gate wide`: runs a wide command CI cannot run, 1 at a time per machine; above `AGENTIC_SDLC_MAX_LOAD` it exits 75.
- `name-workflow`: copies a workflow with its goal in its name.

## Skills: lenses on demand

Skills load only when a task calls for one. Lenses (`security`, `robustness`, `privacy-compliance`,
`code-quality`, `code-patterns`, `ui-patterns`, `visual-layout`, `usability-review`,
`accessible-content`, `plain-language`, `multimedia-design`, `design-system`) are picked by a
change's paths and risk; [`LENSES.md`](plugin/skills/LENSES.md) is the index. Playbooks (`bug-fix`,
`prototype`, `hillclimb`, `project-verify`, `blast-radius`, `correct`, `reflect`, `eval`,
`session-pickup`, `land`, `quality-setup`, `chief-of-staff-setup`) are named by the chief of staff
or a brief.

## Protections: 4 layers, the cheapest that holds wins

Anything a script can check is a check, not a prompt or an agent pass.

1. **A rule in the builder prompt** (soft, free): comments say why, never what; tests are
   contracts; a new test fails without the change.
2. **A hook at write time** (hard, local): `git-denylist`, `commit-pathspec`, `write-confine`,
   `wide-gate` and `context-budget`.
3. **A CI check in 1 step** (hard, every PR): the `checks` action runs `context-budget`,
   `test-budget`, `comment-budget`, `issue-link` and the opt-in `ratchet`. Add it to your fast lane:
   `uses: cdowin/agentic-sdlc/checks@v5.2.0`. Inputs: [CI checks](https://github.com/cdowin/agentic-sdlc/wiki/CI-checks).
4. **Sampled review** (judgment): the review spin's blind reviewer scores what a ratio cannot see:
   over-testing, bloat and comment noise.

Tests run in rungs: a builder runs its proof and the fast check, every PR runs the CI lanes, a
nightly runs the full suite.

## Contract

`plugin/contract/`: the provider-neutral shapes, each provider's facts (`runtimes.json`) and the
checker. Upgrading from v4: the [wiki](https://github.com/cdowin/agentic-sdlc/wiki).

Tests: `sh tests/run.sh`. License: MIT.
