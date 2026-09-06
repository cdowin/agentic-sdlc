---
id: 0.2.0/the-middle-tier-splits/02-a-named-tier-that-resolves-to-nothing-is-loud
feature: 0.2.0/the-middle-tier-splits
milestone: "0.2.0"
name: A gate list cannot get quietly shorter
status: building
owner:
depends_on: []
---

# A gate list cannot get quietly shorter

A tier named in `GDK_PRECOMMIT_TIERS`/`GDK_MILESTONE_TIERS` that resolves to no make target
fails the gate by name. It never runs a shorter gate that reports success.

This is rule 4 applied to a composition. `-include` of a missing file is **silent by design** —
that is what makes the no-tiers shape work — and it is also exactly how a typo'd `GDK_TIERS_MK`
turns a five-gate `precommit` into a one-gate `precommit` that exits 0. An empty tier list is
fine and expected. A NAMED tier that does not exist is not.

## Acceptance criteria

1. `GDK_PRECOMMIT_TIERS := parse nonexistent-tier` → `make precommit` fails naming
   `nonexistent-tier`, and says which variable named it.
2. The failure is **before** the gates run, not after: an operator should not pay for `check`
   to be told the list was wrong. Make's own "No rule to make target" is acceptable ONLY if the
   message names the variable; otherwise the check is explicit.
3. `GDK_TIERS_MK` naming a file that does not exist, while both tier variables are empty, is
   the supported no-tiers shape and stays quiet.
4. `GDK_TIERS_MK` naming a file that does not exist **while a tier variable is non-empty** is a
   failure — that is the typo case, and it is distinguishable from case 3 by exactly this
   condition.
5. Each case is a test in `tests/test_makefile_include.py` against a real `make` run.

## Out of scope

- Validating tier names as strings (a shell-metacharacter grammar). They are make goals in a
  make file the project's own kit wrote, not config a stranger supplied — `gates_extra.py`'s
  refusal matrix exists because `[gates] extra` comes from TOML. Do not import that grammar
  here; say so in a comment so the asymmetry reads as a decision.

## Files
Touch: `src/agentic_sdlc/repo/installables/Makefile.devkit`, `tests/test_makefile_include.py`.
Depends on story 01 landing first — same file.

## Close

done: b9cf082 — an EMPTY tier list is quiet and announces itself; a NAMED tier that resolves
to nothing stops at parse time naming both the tier and the variable, before .gate-reports/
exists. Telling those two apart is the story.
