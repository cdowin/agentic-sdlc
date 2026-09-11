---
id: st-the-work-provider-leaves-the-config-module
kind: story
feature: ft-the-module-says-what-it-does
milestone: "ms-nothing-is-hand-rolled"
name: the work provider leaves the config module
status: building
owner: agent
depends_on: []
changelog: `pm config --seed` prints one changed comment line: the seed's own note about where its bytes come from now names `vocabulary.render_seed()`, because the module it used to name no longer exists.
---

# the work provider leaves the config module

`model.py` is gone as a name, and the two jobs it was still doing after the storage layer left are
two modules, each opening with a sentence that is exactly true of it. One holds what a PROJECT
DECLARES — the flow, the categories, the arrival table, `PmConfig` and the config refusals. The other
holds what a TREE CONTAINS — the grain, the pools, the index, the children, the plan and the release
readers. Neither docstring describes fewer jobs than its module does.

Measured 2026-09-10 by section banner: the vocabulary half is `model.py:1-1062`
(`contains_defect` .. `config_complaints`) and the work provider is `model.py:1449-2817`
(`# --- id <-> path ---` .. `append_heading`). The current sentence — *"the PM-tree invariants,
single-sourced for the CLI and the gate"* — describes neither, and it is retired rather than
inherited by whichever half keeps the most lines.

## The split is already almost one-directional, and the two exceptions are the story

77 top-level definitions in the work-provider half reference a name from the vocabulary half
(`PmConfig`, `FLOW_KINDS`, the `FIELD_*` and `GRAIN_*` constants). That direction is correct and
becomes an import. **Exactly two references run the other way**, and each has to be resolved rather
than papered over with a late import:

- **`contains_defect` (`model.py:65`) reads `BINDS_TO` (`model.py:1504`).** `BINDS_TO` is the
  per-kind mapping of *which field names my parent* — a declaration, not a layout — so it belongs
  with the vocabulary and the reference inverts to nothing.
- **`_arrive_node_defect` (`model.py:679`) calls `pointer_escapes` (`model.py:2203`).** That function
  is a pure string predicate whose own docstring says it is *"the shapes `core.config.relpath`
  refuses, as a predicate"*. It is in NEITHER half: it is `core/config.py`'s, beside the guard it
  mirrors, and it has six callers across four modules that all get the same answer.

## Gotchas

1. **`CONFIG_IMPORT_ALLOWLIST` (`tests/test_boundaries.py:660`) names `repo/pm/model.py`, and after
   the split exactly one entry may survive.** The vocabulary half is the obvious keeper — except that
   `mainline_branch` (`model.py:2243`) reads `config_section('repo_hygiene')` and sits in the WORK
   PROVIDER. Three ways out and the story picks one in writing: move `mainline_branch` to the
   vocabulary half, give it a `sect=None` parameter the way `all_config_defects` already has
   (`model.py:918`), or grow the roster by one. **The roster's stated property is that it can only
   shrink**, so the third answer needs an argument, not a line.
2. **The id grammar is not contiguous and must not be left split by accident.**
   `id_is_literal`/`segment_is_literal`/`mint_id` are at `model.py:1456-1493`; `id_defect` and
   `kind_of` are at `model.py:1754-1774`, 270 lines later with the pool layout in between. They land
   in one place or the story writes down why two.
3. **`load` caches and `reload` clears it** (`model.py:415`, `model.py:504` calling
   `load_config.cache_clear()`). Every test fixture that builds a tree depends on that pair being
   reachable under the name it has now.
4. **A module rename is not free.** Each one costs its importers, plus any name of it inside
   `tests/test_boundaries.py`'s primitive constants and `test_verify_rules.py`'s `ALLOWED_IMPORTS`.
   List what each rename touched in the close.
5. **Neither new name may be `model.py`.** The feature's whole complaint is that the name says
   nothing about the layer.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/model.py` — it ends this story as two files.
- the two new modules, and `src/agentic_sdlc/core/config.py` if `pointer_escapes` lands there.
- every importer of `model`: `pm/cli.py`, `report.py`, `ready_for.py`, `validate.py`, `changelog.py`,
  `rename.py`, `skills.py`, `arrive.py`, `ledger.py`, `templates/__init__.py`, `checks/pm.py`,
  `checks/grain_shape.py`, `checks/doc.py`, `checks/hooks.py`, `conveyor/driver.py`,
  `conveyor/steps.py`, `conveyor/lessons.py`, `dispatch.py`.
- `tests/test_boundaries.py`, and the test modules that import `model` by name.

## Files it must stay out of

The storage module (`st-the-storage-layer-is-one-module`). `core/walk.py`, `core/apply.py`,
`core/spawn.py`. `pm/cli.py`'s helper BODIES — this story rewrites its imports and nothing else.
`devkit.toml`'s `[pm.states.*]` and `[pm.arrive.*]`: the vocabulary MOVES, the declaration does not.

## Acceptance criteria

1. `model.py` no longer exists. Two modules stand in its place, each opening with one sentence that
   is exactly true of it, and neither is named `model`.
2. Each filename says which layer it is in — a reader who has never opened the file can tell whether
   it holds what a project DECLARES or what a tree CONTAINS.
3. The two upward references are resolved by moving the name, not by a deferred import: `BINDS_TO`
   sits with the vocabulary, `pointer_escapes` sits beside the guard it mirrors, and no module-level
   import cycle exists between the two halves.
4. `CONFIG_IMPORT_ALLOWLIST` holds exactly one of the two, and the story states which and why. If it
   holds both, the argument for growing a roster that can only shrink is written down and is about
   the code, not the calendar.
5. The id grammar is in one module, or the story says why it is in two.
6. `check pm`, `pm status`, `pm validate`, `pm vocabulary` and every belt produce byte-identical
   output on this repo's own tree — the numbers, the order, and the words.
7. A malformed `[pm.states.*]` or `[pm.arrive.*]` is still refused at exit 2 naming the section
   (hard rule 5), and `RETIRED_KEYS`/`RETIRED_SECTIONS`/`RETIRED_CHECKS` still name a retired key
   rather than answering "unknown".
8. **Behaviour preservation is mechanical**: the per-module `ast.unparse` comparison against HEAD
   with docstrings stripped and moved names mapped, residual reported as a line count and read line
   by line.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | `st-every-module-opens-with-one-true-sentence`'s docstring gate, which lands after this story and grades both halves | deferred by design — this story writes the sentences, that one gates them |
| 3 | unit | `test_boundaries.py::LayersPointDownward` (line 996) plus a case that imports each half alone in a fresh interpreter | amend — `LayersPointDownward` covers `core`/`repo`; a sibling cycle is the new question |
| 4 | unit | `test_boundaries.py::ConfigGoesThroughTheGuards::test_raw_config_imports_are_allowlisted` (line 882) — it fails on a raw read outside the roster AND on a roster entry nothing matches | existing; both halves of it fire here |
| 5 | unit | `test_grain_shape.py::test_the_slot_names_have_one_source` and the id-grammar refusal matrix already assert one home per vocabulary | amend — name the matrix's module, do not copy it |
| 6 | integration | `test_makefile_gates.py` runs `make check` against this tree; `test_fixture_flows.py` replays the vendored trees | existing — a split that changed an output line reddens them |
| 7 | unit | `test_pm_flow.py` and `test_config_seed.py` hold the seed key-by-key and the retired rosters by name | existing |
| 8 | — | the AST comparison, by hand, reported in the close | not a test |

## Out of scope

`[work]`, a provider interface, or a second backend. This is a rename and a partition; nothing
becomes pluggable.

Moving the SDLC vocabulary out of `repo/pm/` — 1,062 lines in the right package, wrongly named.

The `print()` question and the docstring GATE — `st-every-module-opens-with-one-true-sentence`.

## Close

**`vocabulary.py` (1,071 lines) DECLARES; `inventory.py` (1,505) CONTAINS.** The filenames are
criterion 2: one holds the categories, the state words, the arrival table, the rule ids, the document
slots and `PmConfig`; the other the grains, the pools, the index, the children, a grain document's
sections and the plan. `inventory` imports 28 names from `vocabulary`; `vocabulary` imports nothing
from `repo/`, which `LayersPointDownward::test_each_sibling_half_imports_with_the_other_absent`
EXECUTES rather than reads — purge the package from `sys.modules`, import each half alone, and the
DECLARES half must leave the other unimported. Probed both ways before it was trusted.

**Criterion 4 — one entry, and the argument is a measurement.** `mainline_branch` went with the
vocabulary because `[repo_hygiene] mainline` is a config read, not a tree read; with it gone the work
provider's config-guard usage is ZERO, so `repo/pm/vocabulary.py` replaces `repo/pm/model.py` in
`CONFIG_IMPORT_ALLOWLIST` and the roster neither grows nor grows a `sect=None`.

**Criterion 5 — one module, two banners, and the second is not grammar.** Both clusters are in
`inventory.py`. `id_defect` stays immediately above `grain()`, its first caller, and `kind_of` reads
`grain_index`: moving them up would be a re-order, and this was a move.

**A third name moved for the same reason as the other two.** `dir_entries`/`case_variants` read a
DIRECTORY, so they went with CONTAINS — which is what makes the vocabulary docstring's last sentence
true: it imports `core.config` and `core.project` and nothing else. No walk, no frontmatter, no apply.

**AST residual (criterion 8): ZERO lines inside the move.** 217 top-level units in HEAD's `model.py`,
217 across the two halves plus `config.pointer_escapes`, every one byte-identical under `ast.unparse`
with docstrings stripped and the owner name mapped; no name only in HEAD, none only in NOW. 164 lines
over 21 modules OUTSIDE it, read line by line: a function-local `import model` repointed (23), the
string annotation `'model.PmConfig'` (5), `pointer_escapes` now unqualified at its 4 callers and 2
cases, one roster/corpus/message per module naming the owner, and this story's one new case.

**Behaviour, measured rather than asserted:** 28 verb runs over this tree, HEAD's `src/` against this
one on the same data, same second. 20 byte-identical: `pm status`, `validate`, `vocabulary`
(+`--json`), `list` ×4, `roadmap`, `next`, `get`, `changelog`, `check pm`/`grain-shape`/`doc`, `cite`,
`dispatch`, `verify --plan`, `ledger show`, `ready-for feature`. Four belts refused identically and
wrote nothing (`close story`, `close feature`, `release`, `adopt`; `release` is byte-identical once it
is not racing my own `make`). Everything left is a CLOCK, and each was shown to drift the same way
between two runs of the SAME code: elapsed ms inside a quoted gate line, U4's row age, a feature's
`open` age, `ledger report`'s `open_seconds`. With the numbers masked every one is identical,
`--from HEAD~5` included, so history still reads through git blobs.

finding: one REAL output byte. `installables/project-devkit.toml` said *"THESE BYTES ARE
`model.render_seed()` VERBATIM"*, so `pm config --seed` and `init` printed a module that no longer
exists; it reads `vocabulary.render_seed()` now. One comment line, and the only consumer-visible
change this story makes.
finding: `make budget` FAILS at `test 1596 of 1575` (+21), as handed over. HEAD was 1595: this story
adds exactly ONE case.
finding: the rename lengthened lines it did not reflow — `checks/pm.py:151` is 120 characters where it
was 106. A reflow is a body edit.
finding: `changelog:` is still empty. The sentence it owes is the first finding above.
