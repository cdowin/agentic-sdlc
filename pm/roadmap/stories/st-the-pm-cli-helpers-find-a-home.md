---
id: st-the-pm-cli-helpers-find-a-home
kind: story
feature: ft-the-module-says-what-it-does
milestone: "ms-nothing-is-hand-rolled"
name: the pm CLI helpers find a home
status: building
owner: agent
depends_on: []
changelog:
---

# the pm CLI helpers find a home

`repo/pm/cli.py` routes. What is left in it after this story is the router, the flag parsing, the 24
verb bodies and the helpers that exist because a verb needs them — and the helpers that were doing
somebody else's job have moved to the module that already owns the concern.

Measured 2026-09-10: 3,136 lines, **24 `cmd_*` bodies (1,208 lines) and 75 module helpers (1,129
lines)**. The helpers are as large as the verbs they serve, which is the observation; it is not on
its own a reason to move any particular one.

## The defect this story found before it moved anything

**`_slugify` is defined twice — `pm/cli.py:549` and `pm/cli.py:1720` — with identical bodies and
different docstrings.** The first has been unreachable since the moment the second was written, and
it is the only duplicated top-level binding in the module. Nothing in a 1,253-case suite could see
it, because nothing asks the question. That is rule 11's test with a worked example: somebody
hand-rolled a helper this file already had, and nothing stopped them.

## Gotchas

1. **Rule 6 makes an output line a contract, and this file holds 67 of the package's 307 `print()`
   sites.** `test_cli_surface.py`'s help corpus and `pm_cli.LIST_COLUMNS` pin the shapes; every one
   must come back byte-identical, including column order and the `-` an empty cell renders as.
2. **`0.6.0/D7` counts a published `--help` docstring as CODE, not prose** — `test_prose_census.py`
   derives the exclusion by running every `--help` and asking which docstrings came back. Moving a
   module whose docstring is printed moves lines between the two columns of the `src/` census, and
   that census is at 0.3153 against a 0.3333 ceiling. Report the census before and after.
3. **Nothing moves for tidiness.** 0.6.0 ruled against line-count gates on files and functions and
   the milestone brief restates it: a helper with one caller in one verb stays where its caller is.
   The test for a move is that another module ALREADY OWNS the concern — not that `cli.py` is long.
4. **A move that makes `cli.py` import a module to call one function it already reaches is a loss.**
   Say so per candidate.
5. **No re-export.** A helper that moves is called at its new home by every caller.
6. The router's own surface — `main`, `commands`, `ledger_commands`, `_take_flags`, `_ok`,
   `_unresolved`, `_movable` — is the layer it is in and stays.

## The candidate families, measured, with the module that already owns each

Named so the story is dispatchable, not so every row moves. Each row needs a verdict.

    ledger row builders   _ledger_id _ledger_of _stamp _row_ledger _tree_snapshot
                          _record_gate _gate_name _gate_verdict _from_transcript
                          _by_hand _count_flag _event_kind      -> repo/pm/ledger.py
    row renderers         _lesson_cells _enter_cells _verdict_cells _leave_cells
                          _arrival_cells _disposition_cells _gap _emit_rows
                          _age_cell _open_for                  -> repo/pm/report.py
    plan and order        _plan_path _mint_plan _resolve _parent _sequence
                          _placed _where _roadmap_row          -> the plan readers
    grain resolution      _grain_file _binding_defect _shaped _short
                          _known_milestone_ids _known_feature_ids -> the work provider
    minting               _mint _mint_path _slugify _scaffold _stamp_field
                          _claim _name_required _check_slug _retired_id -> pm/templates or the router

## Files this story may touch

- `src/agentic_sdlc/repo/pm/cli.py`.
- the receiving modules, whichever the audit names: `repo/pm/ledger.py`, `repo/pm/report.py`,
  `repo/pm/templates/__init__.py`, the work-provider module.
- `tests/test_boundaries.py` — the duplicate-binding gate.
- `tests/test_cli_surface.py` — only if a column declaration moves module.

## Files it must stay out of

`src/agentic_sdlc/cli.py` at the root: it only routes, it is 256 lines, and it is correct. The
storage module and the two halves of `model.py` — three sibling stories own them. `core/`.
`devkit.toml`.

## Acceptance criteria

1. **No module under `src/` binds a top-level name twice**, gated by AST over the census
   `tests/test_boundaries.py::_sources()` already produces. It FAILS at HEAD on
   `pm/cli.py::_slugify`, and the story shows it failing before the fix.
2. The dead `_slugify` at `pm/cli.py:549` is gone and the surviving one is the one that was already
   running — proven by the behaviour, not by picking the nicer docstring.
3. Every one of the five candidate families above carries a written verdict: moved and where, or
   stayed and why. A family with no verdict is an unfinished story.
4. Each move names the module that ALREADY owns the concern. A new module is a decision with an audit
   line saying which existing module cannot serve and why.
5. Nothing is re-exported from `pm/cli.py`, and `test_boundaries.py::NoImportIsDead` (line 940) is
   green — a stranded import is what a half-finished move leaves.
6. **`--help` for every `pm` verb and sub-verb is byte-identical**, and every `LIST_COLUMNS`
   declaration still matches the columns its help names.
7. The `src/` prose census is reported before and after, and the ratio has not crossed the ceiling in
   either direction for a reason nobody chose.
8. **Behaviour preservation is mechanical**: the per-module `ast.unparse` comparison against HEAD
   with docstrings stripped and moved names mapped, residual reported and read.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `tests/test_boundaries.py::NoNameIsBoundTwice` with `CORPUS`/`catches()` — a planted double `def`, a planted double assignment, a conditional re-binding under `if TYPE_CHECKING` (clean), a method sharing a module function's name (clean) | new; the classifier is `_sources()` + `ast.Module.body`, the harness every primitive there uses |
| 2 | unit | the same case, over the shipped file | covered by 1 |
| 3, 4 | — | the written verdict in the close. Not a test: "which module owns this concern" is a judgement | not a test — the reviewer grades it against the changeset |
| 5 | unit | `test_boundaries.py::NoImportIsDead` | existing |
| 6 | integration | `test_cli_surface.py::test_every_help_surface_asked_for_exits_0_and_prints_something` and `test_the_help_names_the_columns_the_rows_carry` | existing — they spawn the real CLI, so they fail on any drift |
| 7 | unit | `test_prose_census.py::test_comments_and_docstrings_are_under_a_third_of_the_code` | existing |
| 8 | — | the AST comparison, by hand, reported in the close | not a test |

## Out of scope

Splitting `cli.py` by verb, or any target for its length. 0.6.0 ruled against line-count gates on
files and functions and the milestone brief forbids a split whose only argument is size.

A renderer for the 307 `print()` sites. The feature measures that question and answers it in writing;
`st-every-module-opens-with-one-true-sentence` carries the answer.

`repo/pm/model.py`, the storage module, and anything under `core/`.
