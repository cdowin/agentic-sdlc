# CLAUDE.md

Orientation for agents working in this repo. `agentic-sdlc init` wrote this
skeleton once and never overwrites it — **it is yours**: replace every section
with what is true here. The tooling is
[agentic-sdlc](https://github.com/cdowin/agentic-sdlc), pinned at
`DEVKIT_VERSION` in the Makefile and configured in `devkit.toml`: `pm` writes
one status, `check` reads the same files and echoes findings, and a belt
(`close story`, `close feature`, `release`, `adopt`) runs its checks and then
writes one status or refuses; `--force` writes anyway, on the record.
`agentic-sdlc install-* --diff` shows what a pin bump would change.

## What this project is

*(One paragraph: what this is, who uses it, and what it is built in.)*

## Where things live

*(The rule, not the inventory — where a new thing goes, and which suffix means
what.)*

## The ladder

**`make help` is the authoritative target list.** Every gate prints ONE verdict
line naming its transcript under `.gate-reports/`; `VERBOSE=1` streams it.
Never hand-roll an incantation, and never run a rung wider than the thing you
changed — if the check you need is not a target, add the target.

| you changed | run |
|---|---|
| the PM tree, or a doc | `make check` |
| code, inner loop | `agentic-sdlc verify --story` — the paths decide |
| code, before a commit | `make precommit` — `check` + this project's `GDK_PRECOMMIT_TIERS` |
| closing a story | `agentic-sdlc close story <id>` |
| closing a feature | `agentic-sdlc close feature <id>` — what `[verify] feature` names |
| closing a milestone | `agentic-sdlc release <version>` — its `gate` check is `make milestone` |
| bumping the devkit pin | `agentic-sdlc adopt <version>` |

`agentic-sdlc verify --plan` prints each rung with the cost it last took.
`make check` is `[checks] all` plus this project's `[gates] extra`, and boots
nothing; `precommit` and `milestone` add `GDK_PRECOMMIT_TIERS` /
`GDK_MILESTONE_TIERS` from `Makefile.tiers`.

*(List this project's tier targets here — what each runs and what it needs
installed.)*

## How we work

- **The PM tree is `pm/roadmap/`.** Status moves through the CLI, never a hand
  edit (`make pm ARGS="story building <id>"`); `agentic-sdlc check pm` is the
  drift gate. The loop auto-loads from `.claude/rules/pm-execution.md`; the
  manual is `.claude/skills/pm-operations/SKILL.md`; the belts' check lists
  are `docs/sdlc-protocol.md`, rendered from `devkit.toml`.
- **The agent roster is `.claude/agents/`.** Each file opens with a `Project
  config` section — edit it to this project's spellings.
- **The guards are armed by `tools/setup-hooks.sh`**: a `git commit` names its
  own paths, a write outside the agent's tree is refused, a push to a
  protected branch is blocked. `agentic-sdlc check hooks` says whether this
  checkout is armed.
- *(Your branching, review and release flow goes here.)*

## Architecture invariants

*(The cross-cutting rules every change must respect, each with a pointer to
its spec. Short enough to be read.)*

## Don'ts

- **Never hand-roll what a target already does.**
- **Never claim done without the rung that proves it.** `make precommit` on
  any runtime-affecting change; `close story` when the story is done.
- *(Add the footguns this project has actually hit.)*
