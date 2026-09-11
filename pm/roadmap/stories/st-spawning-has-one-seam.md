---
id: st-spawning-has-one-seam
kind: story
feature: ft-the-module-says-what-it-does
milestone: "ms-nothing-is-hand-rolled"
name: spawning has one seam
status: building
owner: agent
depends_on: []
changelog:
---

# spawning has one seam

`core/` holds three sentences instead of two. `apply.py` opens *"the one place this package mutates a
filesystem"*, `walk.py` *"the one place this package enumerates a filesystem"*, and a third module
opens *"the one place this package starts a process"* — for hard rule 2, the rule this tree cares
most about and the one with no home.

Measured 2026-09-10: **16 `subprocess` call sites across 9 modules**, each importing `subprocess` for
itself — `core/project.py` (1), `checks/hooks.py` (4), `checks/repo_hygiene.py` (1),
`checks/shell.py` (1), `conveyor/steps.py` (5), `init.py` (1), `pm/report.py` (1),
`verify/cache.py` (1), `verify/main.py` (1). The property is already enforced from the TEST side —
`tests/conftest.py` derives the `shell` mark from a module's source and fails an unmarked spawn by
nodeid — so what is missing is not the rule. It is the seam.

## The two ways this story silently unarms the suite

Both are gates that stop being able to fail, which is rule 4's first cardinal sin, and both happen
by doing the obvious thing.

1. **`tests/conftest.py:230` does `monkeypatch.setattr(subprocess, 'Popen', refused)`** — it rebinds
   the module attribute, on the argument that "this is the class every caller constructs". A seam
   written as `from subprocess import run` or `from subprocess import Popen` holds its OWN reference
   and the rebinding never reaches it. The runtime tier guard then stops firing **for the entire
   suite**, and the only symptom is `make unit` getting slower. **The seam must
   `import subprocess` and call `subprocess.run(...)` / `subprocess.Popen(...)` attribute-style.**
2. **`test_boundaries.py::TheToolEmitsAndNeverExecutes::test_the_emit_path_never_spawns_a_process`
   (line 1101) asks `module_spawns(SRC / 'repo/emit.py')`, which means *does this module's source
   import `subprocess`*.** Once exactly one module in `src/` imports it, that question answers False
   for every other module in the package and the case passes over an emit path that calls
   `spawn.run(...)` forty times. It has to be re-pointed at *"does the emit path import or call the
   spawn seam"*, and a planted case must show the new form catches what the old one did.

## More gotchas

3. **Bytes, not text.** `report.py:395` runs git with `capture_output=True` and no `text=True`,
   deliberately: "`text=True` would apply newline translation and the locale's encoding", which is
   rule 3 one layer down. A seam that normalises every result to `str` corrupts the rev reader.
4. **One of the 16 touches the network.** `checks/repo_hygiene.py:35` runs `git fetch`. It is the one
   call in this package that can hang, and its timeout/failure handling is not the seam's to
   redesign here.
5. **`OS_SPAWNERS` already exists** (`tests/test_boundaries.py:755`) — the 21 `os.*` spellings that
   start a process without importing `subprocess`, and therefore without the `shell` derivation
   seeing them. The primitive bans those everywhere, not just on the emit path.
6. **`test_verify_rules.py::TheModuleReadsNoFileAndSpawnsNothing` (line 158) declares
   `ALLOWED_IMPORTS`** — `verify/rules.py` must not gain an import of the spawn seam. It bans by CALL
   NAME too, so it stays alive; the import roster is what would need a deliberate change, and it
   should not get one.
7. `core/` imports nothing from `repo/` (`LAYER_RULES`, `tests/test_boundaries.py:713`), so the seam
   takes its argv from the caller and knows no gate, no belt and no config key.

## Files this story may touch

- the new `src/agentic_sdlc/core/spawn.py`.
- the 9 spawning modules listed above.
- `tests/test_boundaries.py` — the new primitive and the repair to primitive 5.
- `tests/test_shell_mark.py` — only if the derivation's census moves.

## Files it must stay out of

`tests/conftest.py`. The derivation and the runtime guard are the thing under test here; a story that
edits them to make itself pass has removed the evidence. If the seam cannot be built without changing
`conftest.py`, that is a finding to report, not a file to edit.

`src/agentic_sdlc/repo/pm/model.py`, the storage module and `pm/cli.py` — none of them spawns, and
they belong to the three sibling stories.

## Acceptance criteria

1. One module under `core/` owns process start-up and opens with one sentence saying so.
2. All 16 call sites reach a process through it, and `import subprocess` appears in exactly one
   module under `src/` — an exact allowlist over `_sources()` asserting an EMPTY offender list, with
   the `OS_SPAWNERS` spellings banned in the same pass.
3. Not vacuously satisfiable: a companion case proves the owner still spawns, in the shape of
   `test_the_walk_module_does_enumerate`.
4. The guard declares `CORPUS` and `catches()`, with at least one clean row and one violation row —
   `test_every_corpus_holds_a_violation_and_a_clean_case` refuses a corpus that cannot fail.
5. **The runtime tier guard still fires.** A case proves that a unit-tier test reaching the seam
   fails by nodeid with the existing message — the scratch-suite harness in
   `test_shell_mark.py::ScratchSuite` (line 280) runs a real pytest against a copy of the conftest
   and is the shape for it.
6. **Primitive 5's spawn case can still fail.** `test_the_emit_path_never_spawns_a_process` is
   re-pointed at the seam, and its corpus holds a planted emit path that reaches the seam and IS
   caught.
7. `pm ledger report --from <rev>`, `check hooks`, `check shell`, `check repo-hygiene`, `verify` and
   the release belt behave identically — same stdout, same exit codes. Bytes stay bytes.
8. **Behaviour preservation is mechanical**: the per-module `ast.unparse` comparison against HEAD
   with docstrings stripped, residual reported and read. Every call-site rewrite that changed more
   than the receiver is named.
9. `core/` gains no `repo/` import.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 3, 4 | unit | `tests/test_boundaries.py::OneSpawn` — `test_only_the_spawn_module_starts_a_process` plus its companion | new; primitives 1 and 2 are the same three cases for two other concerns and the harness is reused whole |
| 5 | integration | `test_shell_mark.py::DerivationEndToEnd` (line 301) already runs a real pytest over a scratch suite; the seam is one more scratch module on it | amend — it exists precisely because "a refusal that has never been raised is a message, not a gate" |
| 6 | unit | `test_boundaries.py::TheToolEmitsAndNeverExecutes` — its `CORPUS` gains the planted reach and its spawn case changes question | amend; the class already carries a corpus, so nothing new is invented |
| 7 | integration | `test_check_hooks.py`, `test_gates_extra.py`, `test_conveyor_steps.py` and `test_pm_ledger_report_git.py` already spawn these paths end to end | existing — if any of them changes, the seam changed behaviour |
| 8 | — | the AST comparison, by hand, reported in the close | not a test |
| 9 | unit | `test_boundaries.py::LayersPointDownward` (line 996) | existing |

## Out of scope

Any change to WHAT is spawned, to a timeout, to error handling, or to `check repo-hygiene`'s network
call. Sixteen call sites change their receiver and nothing else.

`tools/hooks/**` — those are `bash` and `python3 -c` under a consumer's system interpreter (hard rule
1), reached by no import from this package.

Making the tool RUN a consumer-named command. `0.5.0/D1` rejected the plugin design and primitive 5
holds it shut; a seam that spawns is a place, not a permission.
