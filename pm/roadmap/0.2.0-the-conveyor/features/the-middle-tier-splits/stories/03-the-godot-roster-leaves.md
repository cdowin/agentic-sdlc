---
id: 0.2.0/the-middle-tier-splits/03-the-godot-roster-leaves
feature: 0.2.0/the-middle-tier-splits
milestone: "0.2.0"
name: No installable in this kit names a Godot artifact
status: done
owner:
depends_on: []
---

# No installable in this kit names a Godot artifact

`grep -ril godot src/agentic_sdlc/` returns nothing but comments explaining the rule, and a gate
asserts it.

The rule the feature settles: **an installable belongs to the kit whose ARTIFACT it acts on, not
to the kit whose STRUCTURE it borrows.**

| installable | acts on | this story |
|---|---|---|
| `cc-godot-sandbox.sh` (501 lines, 51 Godot mentions) | Godot engine boots | **remove** — it is `godot-devkit`'s |
| `doctor.sh` (272 lines, 38) | the Godot toolchain | **remove**; the framework `doctor` target becomes a tier hook |
| `ci-verify.yml` (23) | the workflow shape | **keep**, engine/linter steps become tier-provided |
| `project-devkit.toml`, `project-CLAUDE.md`, the agent files | shapes | **keep**, Godot examples generalised to a SHAPE |
| `model.py` D8 `version_file` default | `project.godot` | **default becomes `pyproject.toml`** |

The Godot runners (`parse.sh`, `lint.sh`, `unit.sh`, `integration.sh`, `scenario.sh`,
`warnings.sh`, `capture.sh`, `import_cache.sh`, `hermetic_run_scan.sh`, `compile_sweep.gd`,
`ci-uid-guard.yml`) go with them, and `install-runners` goes with those — it becomes a
`godot-devkit` verb.

## Acceptance criteria

1. `tests/test_consumer_independence.py` grows a Godot-name assertion over `src/`, `tools/`,
   `.github/` and every installable, with the same one-exact-path exemption discipline the
   `MIGRATION_DOC` entry already uses.
2. `install-runners` and its plan are gone from `PLANS`, `USAGE` and the post-install notes; a
   test asserts `PLANS` keys equal the dispatched `install-*` verbs — the same
   roster-equals-dispatchable shape story 01 of `the-extraction-finishes` ships for gates.
3. `model.py`'s D8 default is `pyproject.toml`. **This changes a shipped default**, so: a
   consumer that set `version_file` explicitly is unaffected, one that relied on the default and
   IS a Godot project now needs one config line, and that goes in `CHANGELOG.md` as the line a
   consumer greps for. Rule 7 makes this a **minor** bump at least — confirm 0.2.0 is one.
4. `make gates`, `make hooks-self-test` and the full suite pass afterwards. `HOOKS_WITH_CORPUS`
   in the repo `Makefile` currently names `cc-godot-sandbox.sh`; it narrows to the two ledger
   couriers, and `make hooks-self-test`'s census must still be **loud on zero** — a corpus list
   that empties out and passes is this story's own worst failure.

## Out of scope

- **Landing anything in `godot-devkit`.** This story removes; the receiving repo's 0.25.0
  milestone accepts. Do not edit another checkout — rule 8, and the files are recoverable from
  this repo's git history, which is what makes removal safe.
- `Makefile.devkit`'s target list — stories 01 and 02.

## Files
Touch: `src/agentic_sdlc/repo/installables/` (deletions), `src/agentic_sdlc/repo/install.py`,
`src/agentic_sdlc/repo/pm/model.py` (one default), `tests/test_consumer_independence.py`,
`tests/test_install.py`, `tests/test_runners_installable.py`, `Makefile`, `CHANGELOG.md`.

## Three more, found 2026-09-05 while story 04 of the extraction was landing

Each is the same rule with a different file in front of it, and none was in the plan:

1. **`src/agentic_sdlc/repo/init.py` refuses in a directory with no `project.godot`**
   (`init.py:45,77,124`). `README.md` documents that accurately, which means a Godot-less
   consumer of a Godot-less package **cannot run `init` at all** — the verb that exists to
   stand a project up. This is the worst of the three: it is not a stale word, it is a working
   refusal pointed at the wrong fact.
2. **`Makefile.devkit` ships `scene`, `scene-diff`, `refs`, `orphans`, `autoloads` and
   `uid-scan` targets** that shell out to verbs `cli.py` no longer routes. Story 01 removes the
   targets; naming them here so the count is not discovered twice.
3. **`[pm] version_file` still defaults to `project.godot`** (`repo/pm/model.py:265,329`) — the
   D8 rule's stock default names a Godot file. Already in this story's table; the line numbers
   are here now.

Ordering note: (3) edits `model.py`, which `bugs/the-deprecation-window-must-close` is also
rewriting. **The bug lands first**; this story's one-line default change goes after it.

## Close

done: 8f4e9c1 b9cf082 f504ab5, each hash against what it actually carries (T4 corrected the
first line, which credited the split to two commits touching neither file).
- 8f4e9c1 — gdk_runners.sh split 881->405 into gdk_gate.sh, gdk_gate_capture byte-for-byte.
- b9cf082 — install-runners became install-gates; init stopped refusing every engine-less repo;
  test_consumer_independence.py bans OPERATIVE TOKENS, never the word, tombstone dict EMPTY.
- f504ab5 — the installable prose stops describing one engine. Its MESSAGE narrates the split
  too, which is where the wrong attribution came from; `git show --name-status` is the authority.
