---
id: 0.3.0/a-config-error-names-its-namespace/01-the-key-names-the-namespace-it-reads-in
feature: 0.3.0/a-config-error-names-its-namespace
milestone: "0.3.0"
name: the key names the namespace it reads in
status: done
owner:
depends_on: []
---

# the key names the namespace it reads in

`[gates] extra` takes MAKE TARGETS. The adjacent `[checks] all` takes GATE
NAMES. Nothing in either key or either error said which, so a real gate name in
`extra` reached GNU make as `No rule to make target 'budget'` — three layers
below the config that caused it.

## Acceptance criteria

1. An entry in `[gates] extra` that is a known GATE name is exit 2, naming the
   entry, the namespace it is not, and the target that WOULD run it.
2. A target that merely CONTAINS a gate name (`budget-check`) is unaffected.
3. The shape grammar still runs first on a mixed roster.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_a_gate_name_is_refused_by_namespace_naming_the_target_that_runs_it` — loops `gate_universe()`, so a gate added later is covered the day it ships | new; the exit-2 paths were covered by key NAME, never by value SHAPE |
| 2 | unit | `test_the_targets_are_printed_one_per_line_in_declaration_order` (amended with `budget-check`) | AMENDED, not added |
| 3 | unit | `test_every_bad_value_is_named_in_one_refusal_not_the_first_one` (amended) | AMENDED |

SDLC §5: the 29-row refusal matrix over the `TARGET` grammar is untouched — the
namespace rule layers on top of it rather than re-spelling it.

## Out of scope

Re-homing `gate_universe()`, which now has two readers and lives in the belt's
step registry. Raised by the builder; a simplifier's call, not this story's.

## Close

done: 2b40b0e — `[gates] extra` names its namespace and the target that would run
a gate. Verified independently on a scratch consumer: `budget` is exit 2 with the
full message, `budget-check` passes.
