---
id: 0.2.0/the-kit-owns-the-gates-that-scan-its-own-artifacts/02-a-guard-nobody-wired-is-not-there
feature: 0.2.0/the-kit-owns-the-gates-that-scan-its-own-artifacts
milestone: "0.2.0"
name: The self-tests for this kit's own artifacts run by default
status: building
owner:
depends_on: []
---

# The self-tests for this kit's own artifacts run by default

A consumer that pins this package gets the self-tests over the artifacts this package installs,
without wiring a make target and without remembering to add a line to `[gates] extra`.

Today `hooks-self-test` and `runners-self-test` invoke scripts this kit ships, and each consumer
must independently wire a target and register it. **A guard nobody wired is a guard that is not
there** — the same failure mode as a hook that fails open, which this package has already
shipped once: installed, executable, and stopping nothing.

If the artifact is ours, its gate belongs in `[checks] all`, where a consumer opts **out**,
rather than in twenty per-consumer make targets where a consumer must opt **in** and can
silently never do so.

## The four, and the fourth changed

The feature named `pm-shape-scan`, `hooks-self-test`, `runners-self-test`, `hermetic-scan`.
`0.2.0/the-middle-tier-splits` rules `cc-godot-sandbox.sh` and `hermetic_run_scan.sh` out of this
kit — they act on Godot artifacts. So the set here is:

1. the grain prose cap (story 01),
2. the self-test replay over **this kit's** hooks — `cc-commit-pathspec.sh`, `cc-stop-gate.sh`,
   `cc-write-confine.sh`, and the two ledger couriers,
3. `check hooks`, already shipped and already in this repo's roster — the argument is whether it
   joins the STOCK default,
4. `runners-self-test` follows `install-runners` to `godot-devkit`.

**Two moves, not four.** Say so plainly rather than reporting four; the feature's count was
taken before the ownership rule was written, and a story that reports the planned number instead
of the true one is the second scoreboard this repo bans.

## Acceptance criteria

1. The hook self-test replay runs as a check, in-process where it can be, and its census is
   **loud on zero** — an empty corpus list must FAIL, because it cannot tell an uninstalled tree
   from a passing one.
2. Each gate added to the stock `[checks] all` default carries, in `cli.py`'s roster comment,
   the answer to *does every consumer want it?* — the feature's own test. Feature risk 3: four
   is the argued set, a fifth needs the same argument in writing.
3. A gate joining the default that could redden an existing tree ships reporting-only or
   config-ceilinged (feature risk 1).
4. `roster == dispatchable` still holds — the census from
   `0.2.0/the-extraction-finishes` story 01 is what this story grows through, and it must not be
   edited to accommodate the growth.
5. This repo's own `devkit.toml` `[checks] all` and its `Makefile` shrink by whatever now runs
   by default. Self-hosting is the proof: if the stock roster covers it, this repo stops naming
   it twice.

## Out of scope

- `hermetic-scan` and `runners-self-test` — they leave with the Godot half.

## Files
Touch: `src/agentic_sdlc/repo/checks/`, `src/agentic_sdlc/cli.py`, `devkit.toml`, `Makefile`,
`tests/`, `README.md`, `CHANGELOG.md`.
Depends on story 01 and on `0.2.0/the-middle-tier-splits` story 03.

## Close

done: 6e9388d — check hooks replays each installed hook's own corpus, and an empty corpus
list FAILS. Two roster moves, not the four planned: hermetic-scan and runners-self-test act
on engine artifacts and left under D2. Reported the true number, not the planned one.
