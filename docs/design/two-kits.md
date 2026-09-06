# Two kits — splitting this package in half

**Status: a shape, ruled but not scheduled. Chris and the architect, 2026-09-04.** Chris: *"Godot
dev kit is probably doing two things now, and I think it's two separate utility repos."*

## The code already agrees — measured, not asserted

There are ZERO imports between `repo/` and `godot/` in either direction, and the checks sorted
themselves by side with nobody enforcing it.

| | lines | the checks it owns |
|---|---|---|
| **`repo/`** — the agentic kit | 9,334 | `doc`, `hooks`, `pm`, `repo_hygiene`, `shell` |
| **`godot/`** — the Godot utilities | 6,844 | `defaults`, `props`, `rng`, `test_shape`, `tres`, `tres_comment`, `uid`, `unit_disk` |
| **`core/`** — shared substrate | 981 | — |

Of `core/`, `apply` and `markdown` are repo-only; the shared surface is ~440 lines (`config`, `walk`).

## The ruling: duplicate it

A third `devkit-core` package costs three repos and a version matrix for 440 lines; a dependency
edge from the Godot utilities to the agentic kit drags a PM tree into a scene parser. Chris ruled
duplication: *"it's small enough that hand-duplicating isn't a big deal right now."* If the shared
surface grows, the answer is a published shared config utility. The copies must be asserted
identical by something that runs.

## Open question, invariants, sequencing

- Whether `[checks] all` can compose a check from another package is unverified; `[gates] extra`
  looks like the seam.
- Rule 8 applies to both kits: neither knows anything about a consuming project.
- Sequence: after the tag and after the release conveyor, because releases should be cheap before
  there are two things to release.

## Who provides each piece of the SDLC

**Moved here from `0.2.0/milestone.md` on 2026-09-05.** The line: a thing belongs to the KIT whose
artifact it scans, drives or installs; a project's own rules are its own.

| phase | the piece | provider |
|---|---|---|
| **Plan** | grain schema, the state vocabulary, `pm` verbs, `check pm`, templates | **agentic-sdlc** |
| | the milestones, features, stories and bugs themselves | **the project** |
| **Claim** | agent definitions (stock roster) | **agentic-sdlc** |
| | forked/configured agents, project-specific roles | **the project** |
| **Build** | commit-pathspec, write-confine, stop-gate guards; worktree tooling | **agentic-sdlc** |
| | language runners — parse, lint, unit, integration, scenario, capture | **godot-devkit** |
| **Verify** | the gate FRAMEWORK — `gdk_gate`, `Makefile.devkit`, `[checks]`, `[gates] extra` | **agentic-sdlc** |
| | checks over SDLC artifacts — grain prose, hooks, runners, sandbox | **agentic-sdlc** |
| | checks over Godot artifacts — uid, tres, props, defaults, rng, test-shape, unit-disk | **godot-devkit** |
| | the project's own architecture scans | **the project** |
| **Review** | the review record, N-pass verdict parsing, reviewer agents | **agentic-sdlc** |
| **Release** | the protocol, version sync, changelog discipline, tag | **agentic-sdlc** |
| **Telemetry** | the ledger, the two couriers, `pm ledger report` | **agentic-sdlc** |
| **Adopt** | `install-*` verbs and their installables | **each kit, for its own** |

### The consumer's shape, in one line

> A project pins **agentic-sdlc** for how it works, pins **godot-devkit** for what it builds with,
> and owns its own rules about its own code.

`godot-devkit` is itself a consumer of `agentic-sdlc`, as a CONSUMER PIN, never a library import.
