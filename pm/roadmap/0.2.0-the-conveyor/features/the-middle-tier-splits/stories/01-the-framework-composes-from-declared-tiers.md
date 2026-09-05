---
id: 0.2.0/the-middle-tier-splits/01-the-framework-composes-from-declared-tiers
feature: 0.2.0/the-middle-tier-splits
milestone: "0.2.0"
name: precommit and milestone compose from tiers a language kit declares
status: reviewing
owner:
depends_on: []
---

# precommit and milestone compose from tiers a language kit declares

A project installs `Makefile.devkit`, and `make precommit` runs the gate framework plus whatever
tiers its language kit declared — with no Godot target name anywhere in the framework file.

Today `Makefile.devkit:310` reads `precommit: check parse lint unit integration-diff` and `:314`
reads `milestone: check parse lint warnings unit integration-all`. Those two prerequisite lists
are the entire coupling; the rest of the file already separates cleanly at line 147.

## The mechanism

```make
GDK_TIERS_MK        ?= Makefile.tiers
GDK_PRECOMMIT_TIERS ?=
GDK_MILESTONE_TIERS ?=
-include $(GDK_TIERS_MK)

precommit: check $(GDK_PRECOMMIT_TIERS)
milestone: check $(GDK_MILESTONE_TIERS)
```

## Acceptance criteria

1. `Makefile.devkit` defines the framework — `gdk_gate`, `help`, `check`, `precommit`,
   `milestone`, `pm`, `doctor` — and **no** `parse`/`lint`/`warnings`/`unit`/`integration*`/
   `scenario`/`smoke`/`capture`/`import-cache`/`uid-scan`/`hermetic-scan`/`hooks-self-test`
   target, and none of the five scene aliases.
2. With **no** `Makefile.tiers`: `make precommit` runs `check` alone, exits 0, and its output
   says the tier list is empty. A silent one-gate run that looks like a five-gate run is the
   cardinal sin; **the empty case must announce itself**.
3. With a `Makefile.tiers` defining two targets and setting both variables: `make -n precommit`
   and `make -n milestone` each list `check` plus that kit's targets, in declaration order.
4. `--warn-undefined-variables` stays on and neither path warns. Both variables are defined
   before use in the include-absent case too.
5. `make -n check` still executes nothing — the `$${MAKE:-make}` spelling at line 305 exists
   because `$(MAKE)` runs under `-n`; do not "tidy" it.
6. `tests/test_makefile_include.py` proves 2, 3 and 5 by running real `make` against a temp
   project, the way the existing tests in that module already do.

## Out of scope

- Where the removed targets GO. That is story 03 and it is a different repo's problem to
  receive them; this story's job is that the framework no longer names them.
- `[gates] extra` and `gates_extra.py` — untouched. A project's own gates arrive exactly as they
  do today, and adding a third writer to that list is explicitly rejected in the feature file.

## Files
Touch: `src/agentic_sdlc/repo/installables/Makefile.devkit`, `tests/test_makefile_include.py`.
Stay out of: `src/agentic_sdlc/repo/gates_extra.py`, `devkit.toml`, the repo's own `Makefile`.

## Close

done: b9cf082 — Makefile.devkit 314->243 lines, no language target; precommit/milestone
compose from GDK_*_TIERS via -include. 13 tests watched failing against the pre-change file.
