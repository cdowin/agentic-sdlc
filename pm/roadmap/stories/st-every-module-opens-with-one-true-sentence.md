---
id: st-every-module-opens-with-one-true-sentence
kind: story
feature: ft-the-module-says-what-it-does
milestone: "ms-nothing-is-hand-rolled"
name: every module opens with one true sentence
status: building
owner: architect
depends_on: []
changelog:
---

# every module opens with one true sentence

Every module under `src/agentic_sdlc/` opens with one sentence, a gate says so, and the sentence has
been read against the module it describes. Where the FILENAME does not say which layer a module is
in, the story says whether it was renamed or kept and why.

This is the feature's last story and it grades what the four before it landed. It moves no code.

## What the tree actually holds, measured 2026-09-10

**43 of the 46 modules already have a module docstring.** The three that do not — `core/__init__.py`,
`repo/__init__.py`, `repo/checks/__init__.py` — are zero-length package markers. So the gate is cheap
and the WORK here is the audit: a docstring that exists is not a docstring that is true.

Two findings the census already turned up:

- **`repo/conveyor/__init__.py` and `repo/conveyor/driver.py` open with the SAME sentence** — *"the
  conveyor: every check, then at most one write (D12)"*. Two modules cannot both be the one place.
  One of them is wrong and this story says which.
- `repo/pm/model.py`'s *"the PM-tree invariants, single-sourced for the CLI and the gate"* describes
  none of its jobs. **`st-the-work-provider-leaves-the-config-module` retires it; this story does not
  re-litigate it**, it grades the two sentences that replaced it.

## Re-measured 2026-09-11, at the end of the feature — and criterion 4 no longer fails

The five sibling stories landed between the reading above and this one. **The tree now holds 50
modules, 47 with a docstring**; the same three zero-length package markers are the only ones
without. `model.py` is gone, `vocabulary.py`, `inventory.py`, `frontmatter.py`, `spawn.py` and
`cite.py` are new, and `ledger.py` took seven row renderers from `cli.py`.

**The collision this story was written to catch does not collide any more, and the reason is the
finding.** `conveyor/__init__.py` opens *"conveyor — the belts: every check, then at most one write
(D12)"* and `conveyor/driver.py` opens *"driver.py — the conveyor: every check, then at most one
write (D12)"*. Same CLAIM, different words. An exact-sentence test — including one that strips the
`<name> — ` prefix 20 of the 47 carry — passes over both, which is rule 4's first sin sitting inside
the gate this story is adding.

So criterion 4 is answered in two halves rather than dropped: the GATE catches exact collisions,
which is cheap and lasts and fails the day someone copy-pastes a header; the near-duplicate is the
AUDIT's to fix, in criterion 5, because "these two sentences make the same claim" is judgement and a
test asserting it would be the second scoreboard. **The story must show the gate failing on a
PLANTED collision instead of on this one**, and say so rather than quietly restating criterion 4.

## The naming question, per module the feature names

`model.py`, `driver.py`, `steps.py`, `verdict.py`, `report.py` — a reader cannot tell from the name
which layer any of them is in. Each gets a verdict:

    model.py     retired by the sibling story; this story grades the replacements
    driver.py    the belt RUNNER; its docstring is its package's, duplicated
    steps.py     the four check registries the driver runs (1,784 lines)
    verdict.py   the machine-readable block at the end of a review record
    report.py    `pm ledger report` — a name that reads as "reporting" in general

**A rename is expensive and the story must price it**: every importer, plus any spelling of the
module inside `tests/test_boundaries.py`'s primitive constants (`WALK_MODULE`, `APPLY_MODULE`,
`APPEND_ONLY_MODULE`, `EMIT_MODULE`, `CONFIG_OWNER`, `CONFIG_IMPORT_ALLOWLIST`) and
`tests/test_verify_rules.py`'s `ALLOWED_IMPORTS`. **A name that is merely imperfect is kept, with the
reason written down.** The bar is the ship criterion, not taste.

## The `print()` question, answered in writing and not by refactoring

The feature's ship criterion requires an answer, and this is where it lands. Measured 2026-09-10:
**307 `print()` sites across 23 modules**, 67 in `pm/cli.py`, 39 in `init.py`, 38 in `pm/skills.py`,
25 in `verify/main.py`, 21 each in `checks/pm.py` and `checks/repo_hygiene.py`. That LOOKS like a
missing renderer and may not be: printing at the edge is often right, the shapes are already pinned
by `test_cli_surface.py`'s column declarations and each gate's `--help`, and rule 6 makes any change
to one a minor bump at least. **This story writes the answer down. It does not refactor on a hunch,
and "we should have a renderer" without a named defect it would have prevented is not an answer.**

## Files this story may touch

- every module under `src/agentic_sdlc/` — DOCSTRINGS ONLY, plus a rename where the audit calls for
  one.
- `tests/test_boundaries.py` — the docstring gate.
- importers, only where a rename forces it.

## Files it must stay out of

Any function body, any constant, any control flow. If a sentence cannot be made true without moving
code, that is a finding to report — the code moves in one of the four sibling stories or in a bug,
not here.

`tests/conftest.py`. `tools/hooks/**`. `devkit.toml`.

## Acceptance criteria

1. Every module under `src/agentic_sdlc/` has a module docstring whose FIRST LINE is one sentence,
   gated over the census `tests/test_boundaries.py::_sources()` already produces.
2. The three empty `__init__.py` files either carry a sentence or are a NAMED exemption with a
   written reason, and the exemption fails the build when the file gains content — the property the
   `UNCOVERED` roster already has in both directions (`tests/test_guard_corpus.py:397`).
3. The gate declares `CORPUS` and `catches()` with at least one clean row and one violation row: a
   module with no docstring, a docstring whose first line is a heading rather than a sentence, and a
   docstring that opens with a true sentence (clean).
4. **No two modules under `src/` open with the same sentence.** `conveyor/__init__.py` and
   `conveyor/driver.py` do today, so this criterion fails at HEAD and the story shows it failing.
5. The audit is written: one row per module — its opening sentence, and whether the filename says
   which layer it is in. 46 rows, and a row that says "kept, imperfect" carries the reason.
6. Each of the five modules the feature names carries a verdict: renamed and what that touched, or
   kept and why.
7. The `print()` question is answered in writing — one renderer, or printing at the edge is correct
   and here is why — with the measured numbers and, if the answer is a renderer, the named defect it
   would have prevented.
8. No function body, constant or control-flow statement changed. Proven by the per-module
   `ast.unparse` comparison against HEAD **with docstrings stripped**, which must come back
   character-identical for every module this story touched — this is the one story in the feature
   where the residual is expected to be ZERO, and a non-zero residual is a defect rather than a
   thing to read.
9. The `src/` prose census is reported before and after. Sentences that got longer are prose, and
   the ratio is at 0.3153 of a 0.3333 ceiling.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 3 | unit | `tests/test_boundaries.py::EveryModuleSaysWhatItDoes` — `test_every_module_opens_with_a_sentence`, over `_sources()`, with the exemption roster failing both ways | new; `_package_docstring` (line 1644) already reads a module docstring by AST for `agentic_sdlc/__init__.py` and is the reader to widen, not to re-invent |
| 4 | unit | the same class: sentences are collected into a dict and a collision is named by both paths | new — same guard, one more assertion, so one `CORPUS` covers it |
| 5, 6, 7 | — | the written audit in the close, graded by the feature review against the changeset | not a test — "is this sentence true of this module" is judgement, and a test asserting it would be a second scoreboard |
| 8 | — | the AST comparison, by hand, reported in the close; residual expected zero | not a test |
| 9 | unit | `test_prose_census.py::test_comments_and_docstrings_are_under_a_third_of_the_code` | existing |

## Out of scope

Moving any code. Every split in this feature belongs to a sibling story that landed before this one.

A length rule on a docstring, a line-count gate on a module, or a required section inside a
docstring. The ship criterion is one TRUE sentence, and 0.6.0's ruling against size gates stands.

`tests/` — its docstrings are `ft-the-suite-is-measured-like-the-source`'s.
