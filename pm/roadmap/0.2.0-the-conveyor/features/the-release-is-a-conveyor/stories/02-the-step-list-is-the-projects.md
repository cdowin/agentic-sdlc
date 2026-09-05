---
id: 0.2.0/the-release-is-a-conveyor/02-the-step-list-is-the-projects
feature: 0.2.0/the-release-is-a-conveyor
milestone: "0.2.0"
name: The step list and its commands are config, and a typo is exit 2
status: reviewing
owner:
depends_on: ["0.2.0/the-release-is-a-conveyor/01-the-conveyor-refuses-to-advance"]
---

# The step list and its commands are config, and a typo is exit 2

A project opens `devkit.toml`, writes `[release] steps`, and gets the conveyor it declared. A
project that writes nothing gets the shipped default, byte-identically (rule 5). A project that
misspells a step name is told so and exits 2 — it never gets a quietly shorter release.

That last sentence is the whole story. `[checks] all` already rules this way
(`cli.py:173` refuses an unknown gate rather than skipping it) because a typo that narrows a
roster in silence is the cardinal sin with a config file in front of it. A release list is the
same shape with higher stakes: the step that vanishes is `review-landed`.

## The two keys, and why the second one is a table of strings

```toml
[release]
steps = ["tree-clean", "on-milestone-branch", "…", "tag", "prove-artifact"]

[release.commands]
ci-green = "gh pr checks --required"      # the PROJECT supplies gh, not this package
```

`steps` is `core.config.str_tuple` — already correct, already refusing a bare string and an
empty list. `[release.commands]` is a table mapping a step name to ONE command string, and
**`core/config.py` has no coercion for that shape today**: `table()` returns the raw dict
unvalidated, `str_tuple_table()` produces tuples, `number_table()` produces ints. A `str_table`
belongs beside them, in the one module where what a config value may be is decided (CLAUDE.md
§ Where things live). Writing the validation inside `conveyor/config.py` instead would be the
second reader that `gates_extra.py`'s docstring already argues against.

**A command string is not sanitized into safety — it is refused or run whole.** It is the
project's own command and this package supplies no shell of its own beyond
`subprocess.run(..., shell=True)` on a string the project wrote into its own repo file. What is
refused is the shape that cannot be what it claims: a non-string, an empty string, a key naming
a step that is not in the list, a key naming a step whose kind cannot take a command.

## Refusal matrix — `[release] steps` and `[release.commands]` (SDLC.md §5)

Every row exits **2** (a config mistake is not a finding — `ConfigError`'s docstring), names
the key and the offending value, and runs **no step**.

| input | expected |
|---|---|
| `steps = "tree-clean"` (bare string) | 2 — the v0.9.0 character-iteration defect, refused by `str_tuple` |
| `steps = []` | 2 — "remove the key to take the default", the existing `str_tuple` sentence |
| `steps = ["tree-clan"]` | 2 — unknown step, names it AND the known set |
| `steps = ["gate", "gate"]` | duplicates collapse in declaration order, like `gates_extra.targets()`; the collapse is REPORTED, not silent |
| `steps = ["tree-clean", 3]` / `[["a"]]` | 2 — a list of strings, or nothing |
| `steps` naming a step 4 KB long, or with whitespace / `;` / `$(…)` / `/` / `..` inside | 2 — a step name is `[a-z][a-z0-9-]*`, anchored whole, at most 40 chars |
| `[release]` present but `steps` absent | the shipped default list, byte-identical to declaring it |
| `[release]` absent entirely | same default, same bytes — the rule-5 equivalence test |
| `[release] = "x"` (not a table) | 2 — `config_section` already refuses a non-table |
| `commands = "gh pr checks"` | 2 — a table, not a string |
| `commands.ci-green = 3` / `= []` / `= {}` | 2 — a command is one non-empty string |
| `commands.ci-green = ""` or `"   "` | 2 — an empty command is not "no command", it is a mistake |
| `commands.tree-clean = "…"` on an AUTOMATIC step | 2 — names the step and its kind; a command on a step the code performs would be two authorities over one postcondition |
| `commands.pr-open = "…"` where `pr-open` is not in `steps` | 2 — a command for a step that never runs is a belief about the release that is not true |
| a step of kind JUDGEMENT with no entry in `commands` | **not a config error** — it is a legal shape (the operator is asked, story 01). Exit 0 from config; the driver refuses at that step. Stated in the docstring, because "it passed and I do not know why" is the shape of a false PASS |

## Acceptance criteria

1. `core.config.str_table(sect, name, key, fallback)` exists beside the other coercions,
   refuses a non-table, a non-string value, and an empty/whitespace-only string, and has its own
   test row in `tests/test_config.py` for each. **Adversarial against its own docstring**: every
   "refuses" it claims gets hostile input generated against the claim.
2. `conveyor.config.steps_for(operation)` and `commands_for(operation)` read `[<operation>]` and
   `[<operation>.commands]` — one implementation, so `adopt` (its own feature) needs no edit
   here. Proven by a test that reads both `[release]` and `[adopt]` through the same call.
3. **Config equivalence (rule 5):** a repo with NO `devkit.toml` and a repo declaring exactly
   the stock `[release] steps` produce byte-identical `release --plan` output.
   `tests/test_conveyor_config.py::test_stock_default_equals_absent_section`.
4. Every row of the refusal matrix is a test asserting exit 2, the message naming key and value,
   and that no step ran and no state file was written.
5. The shipped default `[release] steps` is a single named constant, and a test asserts it is
   exactly the list in `devkit.toml` here and in `installables/project-devkit.toml` — the same
   self-hosting bar `install-agents` already meets.
6. `agentic-sdlc release <version> --plan` prints the resolved list with each step's KIND and,
   for judgement steps, whether a command is configured. This is what makes criteria 3 and 5
   checkable without running a release.

## Files this story may touch

- `src/agentic_sdlc/core/config.py` — `str_table` only
- `src/agentic_sdlc/repo/conveyor/config.py` — NEW
- `devkit.toml` — the `[release]` section for this repo
- `src/agentic_sdlc/repo/installables/project-devkit.toml` — the shipped `[release]` section
- `tests/test_conveyor_config.py` — NEW
- `tests/test_config.py` — the `str_table` rows

## Files this story must stay out of

`conveyor/driver.py` and `conveyor/state.py` (story 01), `release_steps.py` (03), `skip.py`
(04), `render.py` (05), `src/agentic_sdlc/cli.py` (01), `src/agentic_sdlc/repo/install.py`
(05), `src/agentic_sdlc/repo/pm/ledger.py` (04).

## Out of scope

- What each step DOES. This story validates names and commands; the registry is story 03. The
  known-step set is imported from `release_steps`, so until 03 lands the test fixtures declare
  their own registry (the same seam story 01 uses).
- Running a configured command. `commands_for` returns strings; the driver executes them.
- `[adopt]`'s own default list — `0.2.0/adopt-is-a-conveyor/01`. This story only makes the
  reader operation-generic.

## Close

done: 6e9388d — [release] steps and [release.commands] as config, 23 refusal rows.
