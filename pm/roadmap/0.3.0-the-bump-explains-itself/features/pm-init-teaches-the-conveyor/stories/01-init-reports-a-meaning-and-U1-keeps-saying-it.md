---
id: 0.3.0/pm-init-teaches-the-conveyor/01-init-reports-a-meaning-and-U1-keeps-saying-it
feature: 0.3.0/pm-init-teaches-the-conveyor
milestone: "0.3.0"
name: init prints the ladder against the tree and U1 reports a declared unused state
status: done
owner:
depends_on: []
---

# init prints the ladder against the tree and U1 reports a declared unused state

`init` printed `appended the flow to devkit.toml` and a project adopted the
conveyor as a CONFIG FIX. Nobody then asked whether the tree used the states —
it used three of eight, for its whole life, with every gate green. Reporting a
WRITE and reporting a MEANING are different acts.

## Acceptance criteria

1. `pm init` prints the ladder it wrote AGAINST THE TREE: per kind, how many
   states are declared, how many are in use, and which have never been held.
2. It counts against the config it JUST WROTE, not a cached one.
3. `check pm` U1 reports a declared-but-never-used state as a WARN with the
   count — never a finding.
4. A kind with no grains at all is silent, rather than reporting every word unused.
5. An undeclared word in a file is D4's and is not counted here.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 3 | unit | `test_it_names_the_unused_states_with_the_count_in_use` | new — nothing anywhere related the declared state set to the set in use, and that gap IS the bug |
| 4 | unit | `test_a_kind_with_no_grains_at_all_is_silent_rather_than_all_unused` | new |
| 5 | unit | `test_an_undeclared_word_in_the_tree_is_D4s_and_not_counted_here` | new — keeps D4 and U1 from arguing about the same byte |
| 3 | unit | `test_off_unless_named` | mirrors `FlowChecks`' opt-in case exactly |
| 1, 2 | — | measured on a scratch tree: `pm init` prints the four-kind ladder, counting against the flow it appended in the same run | `model.reload()` is the mechanism; `skills.py` keeps no raw config door (`test_raw_config_imports_are_allowlisted`) |

## The opt-in ruling

U1 is OPT-IN, like every other flow-shaped rule. It is a WARN and could not
redden anyone, but stock-on it adds three lines to every consumer's `check pm`,
and those shapes are grepped (rule 6). The place a project MEETS this fact is
`pm init`, which prints unconditionally; U1 is how a project that wants it kept
visible afterwards asks for that.

Enabled on this repo, where it reports the truth about its own author: the
package that SHIPS the conveyor holds 3 of its 8 declared milestone states.

## Out of scope

Making this repo actually USE its eight states. That is a working-practice
change, not a code change, and the rule now says so on every run.

## Close

done: ff58c03 — the ladder at adoption, U1 afterwards, and the finding pointed
at its own author.
