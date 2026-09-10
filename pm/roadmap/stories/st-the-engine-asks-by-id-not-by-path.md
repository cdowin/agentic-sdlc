---
id: st-the-engine-asks-by-id-not-by-path
kind: story
feature: ft-the-module-says-what-it-does
milestone: "ms-nothing-is-hand-rolled"
name: the engine asks by id, not by path
status: planning
owner:
depends_on: []
changelog:
---

# the engine asks by id, not by path

Nothing outside the storage layer and a named roster hands a `Path` to a function to find out what a
grain says. A caller that knows a grain's id asks for the field; a caller that knows a FILE — the
walkers, the shape gate that measures bodies, the rev reader — is on the roster with its reason
written beside it.

Measured 2026-09-10: `field_of(path, key)` is called at **102 sites outside `model.py`** across 13
modules, including `conveyor/steps.py`, `conveyor/driver.py` and `dispatch.py`, none of which has
any business knowing a grain is a file on disk. The feature brief says 89; the tree says 102, and
the higher number is the argument.

## The shared abstraction already exists — extend it, do not mint a second one

`model.Grain` (`model.py:1510`) is *"one grain document, read once: what it says it is and what it
says it belongs to. Nothing here is derived from `path`."* It already carries `gid`, `kind`,
`status`, `binding`, built from ONE `document()` call in `read_grain` (`model.py:1623`), and
`grain_index(cfg)` (`model.py:1711`) already resolves id -> `Grain`. **The reach-through is not a
missing abstraction, it is an abstraction nobody uses** — 102 storage calls against 69 to this layer.
State in the story whether `Grain` grows the read or a reader object owns it, and why the other
cannot serve.

## Gotchas

1. **68 of the 73 `unquote(...)` calls in `src/` are already redundant, and removing them is the
   single largest edit here.** `field_of` -> `Document.field` -> `parse_document`, which calls
   `unquote` on every scalar as it parses (`model.py:1169`); `field_in` calls it too
   (`model.py:1117`). So `model.unquote(model.field_of(path, key))` strips twice. **It is not a
   no-op**: `unquote('"a" or "b"')` returns `a" or "b`, because the function only asks whether the
   first and last characters match. Removing the outer call is behaviour-preserving on every value
   whose unquoted form is not itself quote-wrapped, and a behaviour CHANGE on the rest. Say in the
   close whether any document under `pm/roadmap/` or `tests/fixtures/` holds one.
2. **Five `unquote` sites are legitimate and stay**: `pm/cli.py:1408` and `pm/rename.py:54` strip a
   value that came off the COMMAND LINE, and three are inside the storage module's own parse. A
   sweep that deletes by name rather than by argument takes those with it.
3. **`report.GitSource` resolves a grain by the `id:` it declares and its paths never reach the
   filesystem** (`report.py:372`). An id-addressed read routed through `grain_index(cfg)` walks the
   DISK, so `pm ledger report --from <rev>` would silently start answering about the working tree.
   That failure is invisible to `make unit`: `GitSource` spawns `git`, so every case that could see
   it is in the `shell` tier.
4. **`checks/grain_shape.py` measures FILE BODIES, not fields**, and `checks/doc.py` resolves path
   claims. Both legitimately hold a `Path`. They are roster entries with a reason, not call sites to
   convert.
5. **`read_grain` is not the same question as `field_of`.** It returns `None` for a document that
   declares no `id:`, and `check pm` counts those as SKIPPED rather than dropping them
   (`ft-identity-lives-in-frontmatter`). A conversion that turns "no id" into "no such field" loses
   a finding.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/model.py` — `Grain`, `read_grain`, `grain_index` and whatever the read
  is called.
- the 13 modules holding the 102 sites: `pm/cli.py` (45), `pm/report.py` (17), `checks/pm.py` (16),
  `pm/ready_for.py` (12), `pm/validate.py` (9), `pm/changelog.py` (3), `checks/grain_shape.py` (2),
  and one each in `pm/skills.py`, `dispatch.py`, `conveyor/steps.py`, `conveyor/driver.py`,
  `checks/doc.py`.
- `tests/test_boundaries.py` — the roster and its guard.

## Files it must stay out of

The storage module's internals (`st-the-storage-layer-is-one-module` landed them; this story calls
them, it does not edit them). `core/walk.py`, `core/apply.py`. `report.Source`'s fourteen-read
interface. `tools/hooks/**`.

## Acceptance criteria

1. A read addressed by ID exists on the grain layer, with one sentence saying so, and every module
   that knows an id uses it.
2. `tests/test_boundaries.py` names the modules that may still pass a `Path` into a storage read, as
   an exact allowlist asserting an EMPTY offender list, with a written reason per entry. An entry no
   module matches fails the build.
3. The roster **shrinks only**: it opens at the modules that legitimately hold a file rather than an
   id, and the story states the count. A convenience entry added to make the gate green is the
   defect this criterion exists to stop.
4. Every `unquote(...)` whose argument is a call that already unquoted is gone — 68 sites, measured
   2026-09-10. The five that strip a command-line value or sit inside the storage parse remain, and
   are named in the close.
5. The double-strip's one behaviour difference is stated: a value whose unquoted form is itself
   quote-wrapped now keeps its quotes. A case pins the new answer so the change is a decision rather
   than a discovery.
6. `pm ledger report --from <rev>` still reads a retired milestone from history, and no id-addressed
   read reaches the working tree while serving a rev.
7. A document that declares no `id:` is still reported and counted as skipped, not dropped.
8. **Behaviour preservation is mechanical**: the per-module `ast.unparse` comparison against HEAD
   with docstrings stripped and moved names mapped, residual reported as a line count and READ. The
   68 `unquote` removals are the part of the residual that is not a pure address change and every one
   is checked by eye.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 3 | unit | `tests/test_boundaries.py::TheEngineAsksByIdNotByPath` — an AST scan for a storage read whose first argument is a `Path`-shaped name, plus the roster's stale-entry half | new; `OneWalk`/`OneApply` are the harness and `CONFIG_IMPORT_ALLOWLIST`'s prune (line 882) is the roster shape |
| 4 | unit | the same class: a call to `unquote` whose argument is a call to a reader that already unquotes is an offender | new — same guard, one more classifier, so one `CORPUS` covers both |
| 5 | unit | `tests/test_pm_verbs.py` already reads fields off minted grains; a quote-wrapped `name:` is a row on it | amend — prove it once (rule 10) before minting a case |
| 6 | integration | `tests/test_pm_ledger_report_git.py` — a real repo at a rev, already built there | existing |
| 7 | unit | `tests/test_pm_gate.py` already holds "a document declaring no `id:` is reported by name and counted as skipped" from `ft-identity-lives-in-frontmatter` | existing — it fails if the conversion loses the distinction |
| 8 | — | the AST comparison, by hand, reported in the close | not a test |

## Out of scope

`[work]`, a provider declaration, or a second backend. What this story buys is REACHABILITY: at 102
`Path` call sites a second backend is not expensive, it is impossible — and that is the whole
argument for doing it without one.

`report.Source`'s fourteen reads. It is already an interface with two implementations and it is not
this story's to widen, narrow or rename.

Anything about where the SDLC vocabulary lives — `st-the-work-provider-leaves-the-config-module`.
