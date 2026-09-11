---
id: st-the-engine-asks-by-id-not-by-path
kind: story
feature: ft-the-module-says-what-it-does
milestone: "ms-nothing-is-hand-rolled"
name: the engine asks by id, not by path
status: done
owner:
depends_on: []
changelog: A frontmatter scalar is unquoted ONCE rather than twice — `pm get` and `pm list` disagreed about the same line and neither said so, and only the single strip makes `pm set` then `pm get` a round trip — and `pm decide` mints a decisions log carrying the grain's name, which every log minted since 0.4.0 has been missing.
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

## Close

**`Grain` grows the read; a reader object cannot serve.** `model.grain(cfg, gid, kind)` resolves an
id to the `Grain` the index already holds and `Grain.field(key)` asks it — address and read in one
object, from one `document()` call. At ~40 of the converted sites the caller ALREADY held a `Grain`;
a reader object would have made them convert back to an id to ask a question the object in hand
answers. Four methods: `field`, `list_field`, `declares(key)` (PRESENCE — `RETIRED_FIELDS`,
`arrive`'s record pointer) and `sequence_defect(key)`.

**102 → 0.** `frontmatter.field_of` is called 16 times in `src/` now, all inside the roster (14 in
`model.py`, 2 in `report.py`'s two `Source` implementations); it was 128, 102 of them outside
`model.py`. The walkers grew grain-returning siblings — `feature_grains`/`story_grains`/`bug_grains`,
`every_grain`, `story_grain`, `known_milestone_grains`, `stray_documents` — and the path-returning
`*_files` are DERIVED from them, because `report.Source` declares those three by signature and a rev
source hands back handles that are not files.

**`doc_grain` is the one file-to-grain adapter, and the guard grades it too** — otherwise every
`field_of(p, k)` becomes `doc_grain(p).field(k)`, the gate goes green and nothing changed. It is also
the TOTAL read where `read_grain` is partial: a document declaring no `id:` comes back with an empty
one rather than as `None`, which is what keeps it in the census (criterion 7).

**The roster opens at THREE and `ROSTER_OPENED_AT` fails the build on a fourth.** `repo/pm/model.py`
(the grain layer owns the seam); `repo/pm/report.py` (a git blob at a rev has no `stat`, is not a
file, is in no index); `repo/checks/grain_shape.py` (`_repair_verb` finds the grain BESIDE a shared
doc by taking the slot suffix off its filename — there is no id to ask with). `repo/checks/doc.py`
was expected on it and is NOT: its one read had a grain in hand. `core/frontmatter.py` is excluded
structurally — it IS the storage module, which primitive 9 pins to one file.

**The `unquote` decision: ONE strip, and `pm get` is the argument.** 68 of the 70 calls outside the
storage module wrapped a reader that had already unquoted (`field_of` → `Document.field` →
`parse_document`); all 68 are gone. The two that stay strip a COMMAND-LINE value nothing has
stripped yet — `cli._binding_defect` and `pm/rename.py`; three more live inside the storage parse
and were never in scope. The difference is one input class: `name: "'x'"` now reads `'x'` where the
double strip read `x`, because `unquote` only asks whether the first and last characters match and
was never a YAML parser. **One strip is what makes `pm set` then `pm get` a round trip**: `cmd_get`
single-stripped all along, so it and `pm list`'s name column answered differently about one line and
neither said so. 0 of 2,237 frontmatter values across 309 documents under `pm/roadmap/`,
`tests/fixtures/`, the templates and the installables read differently — free on this tree and every
fixture, which is why it is a decision and not a migration. `test_pm_verbs.py::FieldMutation` pins
the new answer through `get` AND `list`; the `list` half prints `quoted` the moment the second strip
returns.

**The second non-address change: `pm decide` mints a log carrying the grain's NAME.**
`_decision_log` filled the template's `{name}` by joining `milestone.md`/`feature.md` onto the log's
own parent — the grain's directory when nested, the POOL when pooled. Every log minted since 0.4.0
got the empty string; this repo's `ms-nothing-is-hand-rolled-decisions.md` reads
`# ms-nothing-is-hand-rolled  — decisions`, double space and all. It is `grain.field(name)` now, and
`Decide::test_the_log_is_minted_on_the_FIRST_decision_and_not_before` pins `# 0.1 Demo — decisions`.
Existing logs are not rewritten.

**AST residual (criterion 8): 669 lines over 13 modules** — `cli.py` 260, `model.py` 168,
`checks/pm.py` 72, `ready_for.py` 51, `validate.py` 50, `report.py` 14, `grain_shape.py` 10,
`steps.py` 10, `changelog.py` 9, `arrive.py` 7, `driver.py` 5, `doc.py` 4, `dispatch.py` 3. Read
line by line, every line is one of: an ADDRESS change (`field_of(x.path, k)` → `x.field(k)`;
`milestone_file(cfg, id)` → `grain(cfg, id, 'milestone')`; a parameter retyped `Path` → `Grain`; a
walker renamed; a dead `import frontmatter`; one dead local, `mdir = mfile.parent`), one of the 68
`unquote` removals, or one of the two changes above. Three f-strings were re-wrapped; `ast.unparse`
normalises a `JoinedStr` to one line, so the residual shows them equal, which they are.

**Behaviour equality, measured rather than asserted:** 781 lines from twelve read verbs (`pm status`,
`pm list` × 4, `roadmap`, `next`, `validate`, `vocabulary`, `changelog`, `get`, `check pm`) over this
repo's own tree are byte-identical to HEAD's, the one difference being the wall-clock age on U4's
`RECORDING` line. `check pm` and `check grain-shape` print the same census to the character.

**Ten probes, each watched to FAIL before it was trusted.** Six at the guard: a path-addressed
`field_of` planted in `dispatch.py`; `model.doc_grain` called from `changelog.py`; an `unquote`
re-wrapped around `grain.field` in `validate.py`; a fourth roster entry; an entry naming
`repo/pm/reportt.py`; `STORAGE_FIELD_READS` renamed so the classifier sees nothing. Four at the
behaviour: HEAD's double strip printed `…\tquoted` where the case wants `…\t'quoted'`; HEAD's
path-derived decisions name printed `# 0.1  — decisions`; and the two findings below.

finding: criterion 7's proof row was half right. The damaged-story case asserted the substring
``declares no `id:` ``, which BOTH the `unkeyed_documents` line and V1's carry — so swapping
`every_grain`'s `doc_grain` for `read_grain` dropped the document out of `pm validate`'s walk
(`1 problem(s) across 172 grain(s)` where it printed `2 … across 173`) with the unit tier green. The
case now asserts V1's own wording and the violation COUNT, and reddens on that swap.

finding: `report.py`'s roster entry is load-bearing and was measured. Routing `GitSource.field_of`
through `model.doc_grain` fails `test_the_report_at_the_tag_is_the_report_before_the_retire` with
*"no document in v9.9.9:pm/roadmap/milestones declares `id: 0.1`"* — and only in the `shell` tier.

finding: `make budget` FAILS on `[tests] cases.test`, and it was already failing. HEAD (7e94ab3)
runs 1577 against the 1575 ceiling; this story's six cases take it to 1583 (+8). Not narrowed —
raising the ceiling is a decision with a written argument beside the others in `devkit.toml`.

finding: `changelog:` is still empty here. The sentence the close owes: *"a frontmatter scalar is
unquoted once rather than twice, and `pm decide` mints a decisions log carrying the grain's name"* —
both are output shapes a consumer may grep, so **minor** at least (rule 6).

done: 302ef1f — `frontmatter.field_of` 128 -> 16 in `src/`; none of the 102 sites outside `model.py`
survives off a three-module roster the guard holds both ways. Residual 669 lines, read; twelve read
verbs byte-identical over 234 grains. Two behaviour changes, both defects fixed.
