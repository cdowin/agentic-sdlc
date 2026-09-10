---
id: st-the-storage-layer-is-one-module
kind: story
feature: ft-the-module-says-what-it-does
milestone: "ms-nothing-is-hand-rolled"
name: the storage layer is one module
status: planning
owner:
depends_on: []
changelog:
---

# the storage layer is one module

One module opens with *"the one place this package reads and writes a frontmatter block"*, and that
sentence is exactly true: the parse, the per-process document cache, the field readers and the three
byte-exact writers live there and nowhere else. `tests/test_boundaries.py` holds it the way it
already holds `core/walk.py` and `core/apply.py` — an exact module allowlist, an empty offender list,
and a companion case proving the owner still does the thing.

This is a MOVE. The 385 lines between `# --- frontmatter ---` (`model.py:1065`) and `set_list_field`
(`model.py:1446`) change address and nothing else, and the two remaining jobs in `model.py` are
`ft-the-module-says-what-it-does`'s later stories.

## Where it goes, and the audit that decides

The block imports `re`, `Path`, `Sequence` and `core.apply` — and exactly one name from the PM
layer: `ORDER_KEY`, read by `sequence_defect` alone (`model.py:1334`). So `core/frontmatter.py`,
beside its two siblings, is reachable the moment `sequence_defect` takes its key as an argument or
stays behind in `repo/pm/`. **Decide that in the story and write the sentence down**; a storage
module that keeps a `repo/` import cannot live in `core/` at all (`LAYER_RULES`,
`tests/test_boundaries.py:713`).

## Gotchas

1. **Rule 3 is five function bodies, and every one of them looks like it wants tidying.** `_split`
   is `text.split('\n')` and NOT `splitlines()`, because `splitlines()` also breaks on U+2028,
   U+2029, form feed and lone CR and would rewrite them on join (the comment is at `model.py:1066`).
   `read_raw`/`write_raw` open with `newline=''` to disable universal-newline translation both ways.
   `_eol` carries the CR half of a CRLF so a rewritten line keeps the file's convention. **No body in
   the moved block is edited, reflowed or renamed in this story** — a diff that shows anything but
   an address change inside those five is the failure this story exists to avoid.
2. **The cache and the writer move together or the invalidation crosses a seam.** `write_raw` calls
   `forget_document(path)` in a `finally` (`model.py:1088`) precisely because the parse it holds is a
   claim about bytes that may be gone. A gate answering off stale bytes is rule 4's first cardinal
   sin wearing a speedup, and that is `bg-check-pm-reopens-every-file-per-field`'s own note.
3. **`document()` already serves things that are not on disk.** `_stamp` returns `None` when the
   handle has no `.stat` (`model.py:1185`), because `pm ledger report --from <rev>` reads git BLOBS
   through these same functions. A storage module that narrows the parameter to `Path` and calls
   `path.stat()` unconditionally breaks `--from`, and it breaks it only in the `shell` tier, because
   `report.GitSource` spawns `git`.
4. **`report.py` already has a source seam and this must not become a third spelling of it.**
   `report.Source` declares fourteen reads including `field_of` and `read_raw` (`report.py:271-323`);
   `DiskSource` delegates them to `model` (`report.py:325`) and `GitSource` reads a rev. Repoint
   `DiskSource` at the new owner; do not widen, rename or reimplement `Source`.
5. **No re-export.** `model.field_of` does not survive as a second name for one fact; every one of
   the 15 caller modules imports the owner. Measured 2026-09-10: 181 calls into these mechanics from
   15 modules outside `model.py`.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/model.py` — the block leaves; the imports it still needs stay.
- the new storage module (`core/frontmatter.py` or `repo/pm/frontmatter.py`, per the audit above).
- the 15 callers: `repo/pm/cli.py`, `report.py`, `ready_for.py`, `validate.py`, `changelog.py`,
  `rename.py`, `skills.py`, `arrive.py`, `templates/__init__.py`, `repo/checks/pm.py`,
  `checks/grain_shape.py`, `checks/doc.py`, `repo/conveyor/driver.py`, `conveyor/steps.py`,
  `repo/dispatch.py`.
- `tests/test_boundaries.py` — the new primitive, beside 1 and 2.

## Files it must stay out of

`core/walk.py`, `core/apply.py`, `core/config.py` — three primitives that already hold. Anything
under `tools/hooks/`. `pm/cli.py`'s helper bodies (`st-the-pm-cli-helpers-find-a-home`). The
`field_of` SIGNATURE (`st-the-engine-asks-by-id-not-by-path`).

## Acceptance criteria

1. One module owns frontmatter I/O, opens with one sentence in the `apply`/`walk` shape, and holds
   every name currently in `model.py:1065-1446` under the name it has today.
2. `tests/test_boundaries.py` carries it as a primitive: an exact module allowlist over `_sources()`
   asserting an EMPTY offender list for the internals (`_split`, `_fence_bounds`, `_eol`, `read_raw`,
   `write_raw`, `parse_document`, `_remember`, `_DOCUMENTS`).
3. The allowlist is not vacuously satisfiable: a companion case proves the owner still reads AND
   writes, in the shape of `test_the_walk_module_does_enumerate` and `test_the_apply_module_does_write`.
4. The guard declares `CORPUS` and `catches()`, or it is added to `UNCOVERED` with a written reason —
   `tests/test_guard_corpus.py` names an AST-shaped guard that declares neither, and this is one.
5. Any exemption is a NAMED roster entry with its reason, and an entry no module matches fails the
   build — the stale-entry half `test_raw_config_imports_are_allowlisted` already does for
   `CONFIG_IMPORT_ALLOWLIST` (`tests/test_boundaries.py:882`).
6. **Byte-exactness survives the move, proven on the inputs that can break it**: a CRLF grain file, a
   file whose body holds U+2028, and a file with no trailing newline each round-trip through a
   one-field `pm set` with every other byte identical.
7. `pm ledger report --from <rev>` still reads a retired milestone from history.
8. **Behaviour preservation is mechanical**: parse HEAD and the working tree per module, strip every
   docstring, map each moved name to its new home, and diff the canonical `ast.unparse` — the
   comparison `ft-the-vocabulary-is-constants-not-literals` used. The residual is reported as a line
   count in the close AND read line by line; a story that cannot show one does not land.
9. No name is re-exported from `model.py`, and `model.py`'s own docstring is not repaired here —
   `st-every-module-opens-with-one-true-sentence` owns the sentence.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 3 | unit | `tests/test_boundaries.py::OneStorage` — `test_only_the_storage_module_parses_frontmatter` and `test_the_storage_module_does_read_and_write` | new; primitives 1 and 2 ARE this case for two other concerns and the harness (`_sources`, `_tree`, the census floor) is reused unchanged |
| 4 | unit | `test_guard_corpus.py::test_every_ast_shaped_guard_declares_a_corpus_or_is_named` | existing — it fails BY NAME on a new AST-shaped guard, so this criterion needs no case of its own |
| 5 | unit | the stale-entry half of the same class, in `test_raw_config_imports_are_allowlisted`'s shape | amend — only if the roster is non-empty; an empty roster needs nothing |
| 6 | unit | `tests/test_fuzz_markdown.py` already round-trips markdown shapes; the CRLF/U+2028/no-final-newline trio is three rows on it | amend — prove it once (rule 10): name what it already covers before adding |
| 7 | integration | `tests/test_pm_ledger_report_git.py` — it already builds a real repo and reads a rev | existing; it fails if `document()` stops serving a blob handle |
| 8 | — | the AST comparison, run by hand and reported in the close. Not a case: it compares two working trees, and a test cannot hold HEAD | not a test — `ft-the-vocabulary-is-constants-not-literals` set the precedent and its limits |
| 9 | unit | `test_boundaries.py::NoImportIsDead` (line 940) reports an import nothing uses, which is what a stranded re-export leaves behind | existing |

## Out of scope

`field_of`'s signature and its 102 call sites — `st-the-engine-asks-by-id-not-by-path`. Splitting
the SDLC vocabulary from the work provider — `st-the-work-provider-leaves-the-config-module`.
`[work]`, a provider declaration, or any second backend: an abstraction with one implementation is a
tax with no payer, and what this story buys is reachability, not a seam anybody crosses.

Any change to what the storage layer DOES. Not one refusal, one default or one return type moves.
