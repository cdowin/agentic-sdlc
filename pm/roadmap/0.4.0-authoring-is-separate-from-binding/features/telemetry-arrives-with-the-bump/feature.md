---
id: 0.4.0/telemetry-arrives-with-the-bump
milestone: "0.4.0"
name: Telemetry arrives with the bump, in every consumer
status: planning
reviewed:
phase:
depends_on: ["0.4.0/recording-is-on-or-the-gate-is-red", "0.4.0/every-row-names-its-grain", "0.4.0/the-surface-says-telemetry"]
consumed_by: []
---

# Telemetry arrives with the bump, in every consumer

**This package is write-once, use-many.** Its consumers — NullBound, godot-devkit, whatever comes
next — get their SDLC by moving a pin. The other three telemetry features fix this tree. This one
is the only reason they matter downstream, and without it a consumer bumps to 0.4.0 and records
nothing, exactly as this tree did.

## What a bump delivers today, and what it does not

`install-hooks` writes the courier scripts into `tools/hooks/`. Then `install.py`, at the
definition of the settings block, says it outright:

    # Printed, never written: `.claude/settings.json` is hand-maintained and there is no merge.

So the run **prints** the `.claude/settings.json` entries that fire those scripts, and a human
pastes them. The reasoning is sound — settings.json is the consumer's file, it has no merge
semantics, and clobbering it would be worse. The consequence is that **the wiring is a manual step
nothing verifies**, and the failure is the silent one: files present, hooks unarmed, no rows, no
complaint.

`check hooks` does not close it. It asks five questions of the corpus under `tools/hooks/` —
`core.hooksPath` points there, the entry is a regular file, it has an exec bit, it starts, and one
replays its self-test. `core.hooksPath` is about **git** hooks. Nothing in that check reads
`.claude/settings.json`, so it goes green on a consumer where no Claude Code hook is wired at all.

## Three silent failure modes a bumping consumer can land in

Each produces zero rows and zero complaints, and they are worth naming because a fix that catches
only the first is not a fix:

1. **The entries were never pasted.** Scripts on disk, nothing firing them.
2. **The vehicle does not answer.** The courier calls `make -s pm ARGS=…`. The hook's own comment
   states the requirement: the `pm` target must be `.PHONY` (a PM tree *is* a `pm/` directory, so
   make treats the target as up to date) and must pass its environment through. A consumer whose
   Makefile misses either gets `make` exiting 0 without a word. The hook already detects and names
   this exact case — on stderr, which nobody reads.
3. **The CLI is inert.** `[pm.states.<kind>]` has no default; a tree that has not declared its flow
   has every work-moving verb refuse by name. A consumer that bumps without seeding config has no
   working `pm`, so it has no working `ledger record` either. This one has already cost a consumer
   its PM CLI once.

## What changes

**`adopt` is where this belongs.** It is already the conveyor that verifies a bump landed — its
seven checks are exactly the "did this adoption actually take" list, and
`0.3.0/adopt-runs-where-the-bump-lives` put it where the bump happens. Telemetry-live is one more
check of the same kind: **are the ledger couriers wired, does the vehicle answer, and is there a
ledger to write into.**

The check must be a real probe, not an inspection. Reading settings.json proves a string is
present; running the courier's own `--self-test` against the consumer's vehicle proves the path
works end to end. Every courier already ships `--self-test` and replays its own fail-open matrix —
**the capability exists; adopt does not call it.** That is this milestone's recurring shape for
the third time, and it should be the cheap half of this feature.

Second, `install-hooks` should make the paste harder to skip: print the entries as it does, and
then say what is not yet true — "these are not wired; `adopt` will report that until they are."
A printed block that reads as informational is how step 1 gets skipped.

## The consumer's side of the bargain, written down

A `CHANGELOG` line and a migration note that names the three failure modes above and the one
command that answers all of them. A consumer must be able to ask **"am I recording?"** and get an
answer, without reading this feature file. If `adopt`'s output does not answer it plainly, the
feature is not done.

## Ship criterion

`adopt` reports whether telemetry is live in the consumer it runs in, by probing rather than by
reading, and names which of the three failure modes it hit. `install-hooks` states that the
printed entries are not yet in force. The CHANGELOG tells a bumping consumer what to run and what
"live" means. NullBound and godot-devkit are the two real trees this is verified against before
the milestone closes — not a fixture standing in for them.

## Proof budget

  cases: 4-5
  tier: pyunit, plus one real-consumer verification that is not a test case
  lands in: `tests/test_conveyor_adopt.py`, which already parametrizes the adopt checks
  what already covers this: the adopt check registry is asserted, so adding one extends it. New:
    hooks unwired (mode 1), a Makefile whose `pm` target is not `.PHONY` (mode 2), a tree with no
    `[pm.states.*]` (mode 3), and the all-green case. `tests/test_consumer_independence.py` is the
    existing home for "does a consumer that only has the wheel still work" and is where a case
    belongs if the probe reaches for anything this tree has and a consumer does not.

## Out of scope

Writing `.claude/settings.json` on the consumer's behalf. The reasoning against it stands; this
feature makes the omission visible, it does not overturn the decision. Any change to what the
couriers record — that is the other three features.
