---
id: bg-the-bump-belt-does-not-run-the-gate-a-consumer-armed
kind: bug
milestone: ms-a-consumer-can-take-the-bump
name: adopt reports checks-pass while an opt-in gate the consumer armed exits 1
status: open
caused_by:
changelog: 
---

# the bump belt does not run the gate a consumer armed

Found by the 0.7.0 milestone review (R3), reproduced on a scratch consumer.

## Symptom

A consumer declaring `[tests] cases = { test = 900, unit = 500 }` whose gate run censuses only
`test`:

    0.6.0   [check:budget] PASS — … uncounted: test, unit                          exit 0
    0.7.0   [check:budget] FAIL — 2 tier(s) with a declared case limit and no count exit 1

That tightening is correct and `bg-an-uncounted-tier-passes-the-case-ceiling` classifies it as the
minor bump it is. **The gap is the belt a consumer runs to GRADE the pin.** On the same tree:

    agentic-sdlc adopt 9.9.9   →  ok: checks-pass
    agentic-sdlc check budget  →  exit 1

`adopt` says the bump is clean while a gate the consumer armed is red.

## Root cause

**`budget` is opt-in and is not in the stock `[checks] all`**, so `adopt`'s `checks-pass` never runs
it. The consumer who arms `budget` the documented way — as a make target in their own tier file —
has armed it for their commit gates and NOT for the verb that exists to tell them what a version
bump will do to those gates.

So the bump belt grades a roster instead of grading the consumer's tree. It is right about the
roster; the roster is the wrong question.

## Fix, and it is a config-seed decision rather than a patch

Two shapes, and the choice needs the argument written down:

  * **`budget` joins stock `[checks] all`.** One line, and it changes what `adopt` runs for every
    consumer — including one who never declared `[tests]` at all, where `budget` has nothing to
    grade and passes. Simple, and it makes `adopt` slower by whatever `budget` costs.
  * **`checks-pass` runs every gate the CONSUMER declared**, reading their own `[checks]` plus
    anything their tier file arms. Correct in principle and it means the belt reads a make file,
    which is a new kind of input for a verb that today reads `devkit.toml` and markdown.

Rule 5 constrains the first: adding a key to the seed means `tests/test_config_seed.py` compares it
key by key, and a stock default that changes belt behaviour is exactly the class the rule cares
about. Neither is free; pricing them is this grain's work.

## How to see it fail

The scratch tree above, as a case: declare two tiers under `[tests] cases`, census one, run `adopt`
and `check budget`, assert they agree. They do not today.

## Out of scope

The tightening itself. `check budget` failing an ungraded declared ceiling is the fix
`bg-an-uncounted-tier-passes-the-case-ceiling` shipped, and it is right.

`check doc`'s matching tightening — same class, and its aggregate line is in
`ms-nothing-is-hand-rolled`'s `changelog:`. `doc` IS in stock `[checks] all`, so `adopt` catches it.

## The option this bug missed (0.8.0 spec scout, M6) — the one to take

`[adopt.commands] checks-pass` ALREADY overrides the command (`steps.py:1321-1323`, `commands_for`
at `:466`, documented at `README.md:275-279`). The cheapest rule-11 fix: `checks-pass`'s `ok:` detail
names what it did NOT run. That means the `[gates] extra` targets (already read at `steps.py:1052`),
the `KNOWN_GATES` that are off, and the `[adopt.commands] checks-pass` override that would run them.
Reading a make file to find the armed gates is rejected (rule 9). Serialized after the changelog bug
on `steps.py`.
