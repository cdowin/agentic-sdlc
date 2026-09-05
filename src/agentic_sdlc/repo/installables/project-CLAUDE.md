# CLAUDE.md

Orientation for agents working in this repo. `agentic-sdlc init` wrote this
skeleton once and never overwrites it — **it is yours**: replace every section
below with what is true here. What it starts as is the scaffolding `init`
installed, so that the first agent to open the repo finds the loop rather than
inventing one.

The tooling is [agentic-sdlc](https://github.com/cdowin/agentic-sdlc), pinned
at `DEVKIT_VERSION` in the Makefile and configured in `devkit.toml`. Bumping
the pin is a one-line diff; `agentic-sdlc install-* --diff` shows what a bump
would change in the installed files before you let it.

## What this project is

*(One paragraph: what this is, who uses it, and what it is built in. An agent
that has to infer this from the code infers it differently every time.)*

## Project structure

*(Where things live and WHY — the rule, not the inventory. `ls` is the
inventory and it cannot go stale.)*

## Verification loop

**`make help` is the authoritative target list.** Every gate prints ONE verdict
line naming its full transcript under `.gate-reports/`; `VERBOSE=1` streams the
whole thing. Never hand-roll an incantation — if the check you need is not a
target, add the target.

| When | Run |
|---|---|
| per change | `make precommit` — `check` plus this project's `GDK_PRECOMMIT_TIERS` |
| slicing while you work | *(the narrowest tier target that covers what you touched)* |
| before a release | `make milestone` — the full gate, and what CI runs |

**`make check` is the devkit's static roster** — `doc`, `shell`,
`repo-hygiene`, `pm` and `hooks` — plus this project's own gate targets, named
in `devkit.toml` under `[gates] extra`. Every one of them reads git, markdown
and shell as text: nothing boots, so they are safe anywhere, in parallel.

**Everything heavier than that is yours to supply, through the tier seam.**
`make precommit` and `make milestone` are `check` plus the target lists
`GDK_PRECOMMIT_TIERS` and `GDK_MILESTONE_TIERS`, which a language kit sets in
`Makefile.tiers` — the file `Makefile.devkit` `-include`s. A tier list naming a
target no makefile defines is a hard error at parse time, not a quietly shorter
gate. With no tier file, both gates are `check` alone and say so out loud.

*(List this project's tier targets here — what each one runs, and what it
needs installed. A build toolchain, an engine, a linter and the readers that
parse this project's own file formats all live on that side of the seam.)*

## How we work

- **The PM tree is `pm/roadmap/`** — milestones, features, stories and bugs as
  markdown with frontmatter. Status moves through the CLI and never through a
  hand edit (`make pm ARGS="story building <id>"`); `agentic-sdlc check pm` is
  the drift gate. The execution loop auto-loads from `.claude/rules/pm-execution.md`,
  and the operations manual is `.claude/skills/pm-operations/SKILL.md`.
- **The agent roster is `.claude/agents/`.** Each file opens with a `Project
  config` section carrying stock values — edit them to this project's
  spellings, because the files are yours now.
- **The guards are armed by `tools/setup-hooks.sh`**, which `init` already ran:
  a `git commit` in a shared tree must name its own paths, a write outside the
  agent's confined set is refused, and a push to a protected branch is blocked.
  Each installed hook replays its own block/allow corpus; `agentic-sdlc check
  hooks` reports whether this checkout is armed at all.
- *(Your branching, review and release flow goes here — the installed files
  carry only what the tooling itself enforces.)*

## Architecture invariants

*(The cross-cutting rules every change must respect: the ones that are true
everywhere, with a pointer to the spec for each. Keep this list short enough
that it is read.)*

## Don'ts

- **Never hand-roll what a target already does.** The tier targets carry this
  project's sandboxing, environment and arguments; a raw invocation carries
  none of them and answers differently.
- **Never skip verification before claiming done.** `make precommit` on any
  runtime-affecting change.
- *(Add the footguns this project has actually hit. A rule nobody tripped over
  is a rule nobody reads.)*
