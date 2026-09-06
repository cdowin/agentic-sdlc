---
id: 0.2.0/bugs/the-repo-forks-the-framework-it-ships
milestone: "0.2.0"
name: This repo hand-writes the gate framework it installs, instead of including it
status: closed
caught_in: "0.2.0"
fix_milestone: 0.2.0
caused_by: 0.2.0/the-middle-tier-splits
---

# This repo hand-writes the gate framework it installs, instead of including it

**Chris, 2026-09-05:** *"This repo and anyone that pins it should be doing exactly the same
things, no difference."*

## Symptom

`agentic-sdlc/Makefile` does not `include Makefile.devkit`. It is a parallel implementation.

| | this repo's `Makefile` | the shipped `Makefile.devkit` |
|---|---|---|
| targets | `help pm check gates unit integration test matrix fuzz budget hooks hooks-self-test precommit milestone` | `help pm check precommit milestone` + the two tier stubs |
| `precommit` | `gates hooks-self-test unit` | `check $(GDK_PRECOMMIT_TIERS)` |
| `milestone` | `gates hooks-self-test matrix budget` | `check $(GDK_MILESTONE_TIERS)` |
| the gate capture | a local `define gate` | the same idea, written again |

So `make precommit` HERE and `make precommit` in a consumer are two different programs that
share a name, and the composition mechanism this milestone exists to build — `-include` plus
`GDK_PRECOMMIT_TIERS` / `GDK_MILESTONE_TIERS`, decision D1 — is the one thing this repo does
not use.

**It was found through a symptom, not by looking.** The guidance this package INSTALLS told a
consumer to run `make check` after a PM-tree edit; `check doc` failed here because this repo had
no `check` target. A `check: gates` alias was added to make the shipped instruction true, and
that alias is a stopgap sitting on top of this bug — it makes one name agree while the
compositions underneath still differ.

## Root cause

CLAUDE.md §Self-hosting says *"this package runs its own tooling on its own tree, and that is a
gate, not a demo."* That is TRUE of the checks — `make gates` really does run
`agentic-sdlc check all` over this tree — and FALSE of the framework: the composition, the tier
seam and the gate-capture plumbing are all forked.

Nothing catches it, because every self-hosting test asserts that an INSTALLABLE is byte-current
with its source (`test_install.py`) or that a gate runs (`test_makefile_gates.py`). No test asks
whether this repo's own gate composition IS the one it ships.

## Fix

`Makefile` becomes the two lines a consumer's is — a `DEVKIT_VERSION` pin and
`include Makefile.devkit` — plus a `Makefile.tiers` contributing this project's Python tiers the
way a language kit contributes its own:

    GDK_PRECOMMIT_TIERS := unit
    GDK_MILESTONE_TIERS := matrix budget

    .PHONY: unit integration test matrix fuzz budget
    unit: …

That is D1's mechanism used by its own author, and it would make `the-middle-tier-splits`
provable rather than argued: a framework that composes for somebody else and not for itself has
not been shown to compose.

**What has to be decided first**, and it is why this is a bug rather than a story: some of this
repo's Makefile is genuinely project-specific (`PY_MATRIX`, the pytest summary and census
commands, the ledger recorder wiring) and some is framework that `Makefile.devkit` should have
carried all along (`define gate`, the `$(5)` census argument added in 0.2.0). **Splitting those
two is the work.** Doing it wrong ships a framework carrying one project's pytest assumptions,
which is the Godot roster all over again with a different language.

## Until then

The `check: gates` alias stays, and its comment names this bug. One name agreeing is better than
an instruction the author cannot follow — and worse than not needing the alias at all.
