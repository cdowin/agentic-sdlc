---
id: 0.2.0/the-extraction-finishes/01-roster-equals-dispatchable
feature: 0.2.0/the-extraction-finishes
milestone: "0.2.0"
name: The gate roster a stock consumer sees is the set that actually runs
status: building
owner: orchestrator
depends_on: []
---

# The gate roster a stock consumer sees is the set that actually runs

A `git init` repo with no `devkit.toml` runs `agentic-sdlc check all` and gets gate verdicts —
never `exit 2` over a gate name the tool itself advertises.

Today it gets three of those. `cli.py:145` `KNOWN_GATES` holds 13 names; `cli.py:232`
`_check_module` dispatches 5. Eight are phantoms and `uid`/`tres`/`props` are `True` in the
default roster, so the DEFAULT path — the one a new adopter takes — is the broken one, and the
error message names the gate it just refused as a known one.

**The deliverable is the census, not the pruning.** Nothing asserts the declared roster equals
the dispatchable set, which is exactly why eight phantoms survived an extraction that touched
every other surface. Prune without the census and this recurs, in the same shape, on the next
removal.

## Acceptance criteria

1. In a scratch repo with no `devkit.toml`: `agentic-sdlc check all` exits **0 or 1**. Proven by
   a test that builds the repo in a `tempfile`, not by a hand run.
2. A test asserts **`set(KNOWN_GATES) == {names _check_module resolves}`**, derived by asking
   `_check_module` for every name rather than by a second literal list. A new gate added to one
   side and not the other fails it.
3. `_unknown_check`'s message lists only names that dispatch.
4. `FIXABLE_CHECKS` no longer names `uid`. Removing it must not delete the `--fix` PLUMBING —
   `_run_check`'s "an unknown flag is exit 2, never silently ignored" behavior is a shipped
   contract with its own test. If the frozenset is left empty, the docstring says why it exists
   empty.
5. `all_roster()`'s docstring stops claiming "five of the eight gates read `.tscn`/`.tres`".

## Out of scope

- **Do not design the extension point.** The roster is where a check from another package would
  eventually register; prune to what dispatches TODAY. Feature risk 1 is explicit about this,
  and `0.2.0/the-kit-owns-…` grows the roster afterwards, through the census this story ships.
- The `--help` docstring — that is story 02, and both stories touch `cli.py`, so they are
  **serialized, not parallel**.

## Files
Touch: `src/agentic_sdlc/cli.py`, `tests/` (a new or extended module for the census).
Stay out of: `devkit.toml`, `README.md`, `CLAUDE.md`, `src/agentic_sdlc/repo/**`.

## Close

done: 268fa44 — KNOWN_GATES pruned 13->5; _check_module DERIVED from it so the two cannot
disagree; tests/test_gate_roster.py asserts roster == dispatchable by asking the function.
5 of its 6 cases fail with one phantom re-introduced.
