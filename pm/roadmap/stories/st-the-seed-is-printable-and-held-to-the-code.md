---
id: st-the-seed-is-printable-and-held-to-the-code
feature: ft-the-config-is-the-model
milestone: "ms-0.4.0"
name: pm config --seed prints the model, and a test holds it to the defaults
status: planning
owner:
depends_on: []
kind: story
---

# pm config --seed prints the model, and a test holds it to the defaults
A bumping consumer can read the model in one command, and the file it reads cannot drift from the
tool. `init` serves a new repo; nothing served the other ninety-nine percent of a tool's life,
which is bumps — and the seed is the surface that actually taught one adopting agent what the
conveyor is.

## Acceptance criteria

1. `pm config --seed` prints the current seed with its arguments and **writes nothing**. Exit 0.
2. A test compares every COMMENTED default in the seed to the code's actual default, failing **by
   name** on the first that drifts. This case is the feature: individual defaults are covered one
   key at a time by the gates that read them, and nothing has ever compared the two.
3. The declarations/knobs split is stated in the seed itself — a declaration is spelled out with
   its argument, a knob stays commented at its stock value — so it decides the next key rather
   than being re-argued per key.
4. **The byte-identical guarantee is restated as GATES-ONLY**, in `CLAUDE.md` and the CHANGELOG,
   with the workflow carve-out named: every gate key has a real default, and the FILE is not
   optional, because `[pm.states.*]` has nothing behind it and a tree without it has no working
   `pm`. The existing byte-identical test narrows to gates, which is what it was always asserting.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_config_seed.py::test_pm_config_seed_prints_the_seed_and_writes_nothing` — exit 0, stdout byte-equal to the seed, every file under the tree unchanged (hashed, not `git status`: this tier spawns nothing) | new |
| 1 | unit | `::test_pm_config_is_reachable_from_the_cli` — rule 11's half. RED until `pm/cli.py` routes the verb, and its message IS the diff | new |
| 2 | unit | `::test_every_commented_default_in_the_seed_is_the_codes_own_default` — the census of every `(section, key)` read through `core/config.py`, compared to the seed in BOTH directions | new — this IS the feature |
| 2 | unit | `::test_the_census_reads_every_module_that_reads_config` — the floor it stands on: an empty census, an unnamed dynamic reader or an unfoldable fallback FAILS rather than shrinking the comparison (rule 4) | new |
| 3 | unit | `::test_the_seeds_declarations_are_the_keys_with_nothing_behind_them` — the seed's `DECLARATION` marks are read back and the CODE is asked whether each is true | new |
| 4 | shell | `test_init_verb.py::test_the_config_template_carries_every_section_the_gates_read` — narrowed to gate keys, plus both declaration readers REFUSING an absent section | amend |

## Out of scope

Making any currently-optional key required. A new required key still has to earn it the way
`[pm.states.*]` did.
