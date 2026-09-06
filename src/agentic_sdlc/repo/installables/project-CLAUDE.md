# CLAUDE.md

Orientation for agents working in this repo. `agentic-sdlc init` wrote this
skeleton once and never overwrites it — **it is yours**: replace every section
below with what is true here. What it starts as is the loop the tooling
installed, so that the first agent to open the repo finds it rather than
inventing one.

The tooling is [agentic-sdlc](https://github.com/cdowin/agentic-sdlc), pinned
at `DEVKIT_VERSION` in the Makefile and configured in `devkit.toml`. It is a
reader/writer over the PM tree: `pm` writes one status, `check` reads the same
files and echoes findings, and a belt (`close story`, `close feature`,
`release`, `adopt`) runs its checks and then writes one status or refuses
cleanly — `--force` writes anyway, on the record. Bumping the pin is a
one-line diff; `agentic-sdlc install-* --diff` shows what a bump would change
in the installed files before you let it.

## What this project is

*(One paragraph: what this is, who uses it, and what it is built in. An agent
that has to infer this from the code infers it differently every time.)*

## Where things live

*(The rule, not the inventory — `ls` is the inventory and it cannot go stale.
Where a new thing goes, and which suffix means what.)*

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

`agentic-sdlc verify --plan` prints each rung with the cost it last took, from
this project's ledger — ask it rather than guessing.

**`make check` is the devkit's static roster** — `[checks] all` in
`devkit.toml` — plus this project's own gate targets, named under
`[gates] extra`. Every one reads git, markdown and shell as text: nothing
boots. **Everything heavier is yours, through the tier seam:** `precommit` and
`milestone` are `check` plus `GDK_PRECOMMIT_TIERS` / `GDK_MILESTONE_TIERS`,
set in `Makefile.tiers`. A tier list naming a target no makefile defines is a
parse-time error; with no tier file both gates are `check` alone and say so.

*(List this project's tier targets here — what each one runs, and what it
needs installed. A build toolchain, a linter and the readers that parse this
project's own file formats all live on that side of the seam.)*

## How we work

- **The PM tree is `pm/roadmap/`** — milestones, features, stories and bugs as
  markdown with frontmatter. Status moves through the CLI and never through a
  hand edit (`make pm ARGS="story building <id>"`); `agentic-sdlc check pm`
  is the drift gate. The execution loop auto-loads from
  `.claude/rules/pm-execution.md`; the operations manual is
  `.claude/skills/pm-operations/SKILL.md`; the belts' check lists are
  `docs/sdlc-protocol.md`, rendered from `devkit.toml`.
- **The agent roster is `.claude/agents/`.** Each file opens with a `Project
  config` section carrying stock values — edit them to this project's
  spellings, because the files are yours now.
- **The guards are armed by `tools/setup-hooks.sh`**, which `init` already
  ran: a `git commit` in a shared tree must name its own paths, a write
  outside the agent's confined set is refused, and a push to a protected
  branch is blocked. `agentic-sdlc check hooks` reports whether this checkout
  is armed at all.
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
- **Never claim done without the rung that proves it.** `make precommit` on
  any runtime-affecting change; `close story` when the story is done.
- *(Add the footguns this project has actually hit. A rule nobody tripped over
  is a rule nobody reads.)*
