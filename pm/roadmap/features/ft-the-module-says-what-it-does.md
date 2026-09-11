---
id: ft-the-module-says-what-it-does
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: the module says what it does
status: building
reviewed: docs/reviews/2026-09-11-0.7.0-the-module-says-what-it-does.md
depends_on: []
consumed_by: []
changelog: none
---

# the module says what it does

**The standard already exists in this repo and is applied to two files.** `core/apply.py` opens
*"The one place this package mutates a filesystem."* `core/walk.py` opens *"The one place this
package enumerates a filesystem."* One sentence, exactly true, enforced by `tests/test_boundaries.py`
with a named exemption roster.

Nothing under `repo/` meets that bar. This feature is that standard, applied.

## What the tree actually holds

**`repo/pm/model.py` is 2,817 lines doing four unrelated jobs**, and its docstring — *"the PM-tree
invariants, single-sourced"* — describes none of them:

    1,070   config + flow + arrival           the SDLC vocabulary
      385   frontmatter parse, cache, byte-exact write   PURE STORAGE
       54   id grammar
    1,308   grain index + pool layout         the work provider

**`repo/pm/cli.py` is 3,136 lines**: 24 `cmd_*` verb bodies (1,208 lines), **75 module helpers
(1,129 lines)** and 32 module-level constants. The helpers are as large as the verbs they serve.

**Three seams are missing, and the rules that need them already exist.**

1. **Storage.** 164 direct calls into the frontmatter mechanics from 13 modules outside `model.py`,
   against 71 to the semantic grain layer — the engine reaches THROUGH the abstraction 2.3x more
   often than it uses it. `field_of(path: Path, key: str)` at **89 call sites** means that many
   places hard-code *a grain is a file on disk*, including `dispatch.py`, `conveyor/steps.py` and
   `conveyor/driver.py`, none of which has any business knowing it. `unquote` — stripping quotes off
   a YAML scalar, a detail of one storage format — is called 51 times across the engine.

2. **Spawning, which is rule 2's own seam and does not exist.** 16 `subprocess` call sites across
   9 modules. `core/` has "the one place we mutate" and "the one place we enumerate" and **no "the
   one place we spawn"** — for the rule this tree cares most about. `tests/test_boundaries.py` and
   `tests/conftest.py` police it from the test side (a spawn outside the tier fails by nodeid), so
   the property is enforced and the SEAM was never written. Enforcement without a home is why
   `arrive.census()` could acquire a `git rev-list` and take 235 cases down before anyone noticed.

3. **Naming.** `model.py`, `driver.py`, `steps.py`, `verdict.py`, `report.py` — a reader cannot tell
   from the name which layer they are in, and in `model.py`'s case the name is wrong four ways at
   once.

## What is NOT in scope, and why this is not a line-count exercise

**No module is split to hit a number.** 0.6.0 deferred this split and ruled against line-count gates
on files and functions, and that ruling stands: `driver.main` at 184 lines may read worse split. The
target is the SIGNATURE and the SENTENCE — a module you can describe in one true line, and an engine
that does not take a `Path` to ask a grain a question. Where a split falls out of that, it falls
out; where it does not, nothing moves for tidiness.

**Output is measured, not moved.** ~250 `print()` sites, 67 in `pm/cli.py` alone, and rule 6 says a
line shape is contract. That LOOKS like a missing renderer and may not be: printing at the edge is
often right, and the shapes are already pinned by `test_cli_surface.py`'s column declarations and by
each gate's `--help`. **This feature measures it and writes the answer down; it does not refactor it
on a hunch.**

**`[work]` is not declared and no second backend is admitted.** An abstraction with one
implementation is a tax with no payer
([`docs/research/2026-09-08-the-sdlc-as-an-engine.md`](../../../docs/research/2026-09-08-the-sdlc-as-an-engine.md)).
What this buys is REACHABILITY: at 89 `Path` call sites a second backend is not expensive, it is
impossible.

## Ship criterion

Every module under `src/agentic_sdlc/` opens with one sentence that is exactly true of it, and its
filename says which layer it is in. No module has a docstring describing fewer jobs than it does.

The storage layer is its own module with a stated contract, and `tests/test_boundaries.py` forbids
its internals being reached from outside it — the same primitive that already owns `walk` and
`apply`, with the same named exemption roster that can only shrink.

No module outside the storage layer and that roster passes a `Path` to ask what a grain says.

**Spawning has one seam**, named in `core/` beside the other two, and the test-side guard points at
it rather than at a list of modules.

**Behaviour-preserving, proven mechanically** — the AST comparison
`ft-the-vocabulary-is-constants-not-literals` used, not a reviewer's confidence. Hard rule 3's
byte-exact guarantee is the thing most at risk and its residual is read line by line.

The `print()` question is answered in writing: one renderer, or printing at the edge is correct and
here is why.

## How this is decomposed

Stories, deliberately — 0.6.0 shipped ten features with 0/0 stories and `check pm` warned about it
every run. A split lands one module at a time, each behaviour-preserving on its own, each committable
and revertable alone.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_boundaries.py` — it holds primitives 1 (one walk) and 2 (one apply) already;
    storage and spawn are primitives 3 and 4 on the same harness with the same roster shape
  what already covers this: the walk and apply primitives ARE this feature for two concerns. Nothing
    new is invented — two more members of a family that exists, plus the docstring census.

**Landed at 17 against 4, and the budget is not amended — it is ANSWERED here** (0.7.0 feature
review, F7; `checks/pm.py:263` calls an empty budget *"how a feature ships twice its budget with
nobody able to say so"*, and a budget written and then silently exceeded is that sentence one step
on). 15 cases across the six story commits (`bb78a49` 2, `302ef1f` 6, `3267075` 4, `cdce244` 1,
`2198600` 1, `f106d27` 1) and 2 more landing this review's M1 and F2. **The 4 priced TWO primitives
— 9 (one storage) and 11 (one spawn) — on the argument that they are `OneWalk`/`OneApply` with a
different name. Three more arrived that no line above names**, and each is a seam the work found
rather than a case added to feel safe: **10** (the engine asks by id, not by path — 102 `Path` call
sites had hard-coded *a grain is a file on disk*, and moving them needed a gate or they come back),
**12** (one module-level name, one binding — the split put two modules where one was, and a name
bound in both is the drift it was done to prevent), and **13** (one module, one opening sentence,
and NO TWO THE SAME — the budget named a docstring census, not the duplicate half, and the
duplicate half is what caught a copied sentence). Each of the three carries its own `CORPUS` and
`catches`, so the cost is 3 gates rather than 13 assertions, and every story's
`## How this is proven` answered its `existing?` column before adding one.

## Out of scope

`cli.py` at the root (`src/agentic_sdlc/cli.py`) — it only routes, it is 200 lines, and it is
correct.

Moving the SDLC vocabulary (`Flow`, `PmConfig`, `Arrival`). 1,070 lines in the right place; only the
storage layer and the work provider are misplaced.

Anything about agents, phases, dispatch or the ledger's dispatch rows — that is the conveyor
milestone and it is a different thing to plan.

## Close

**Criterion 5 landed as HALF of what it says, and this is the half.** It asks that
`tests/test_boundaries.py` *"forbids its internals being reached from outside it"*. What ships is
`OneStorage`, and it forbids a module outside `core/frontmatter.py` **BINDING** one of the eight
names in `FRONTMATTER_INTERNALS` — a `def`, a `class`, an assignment or a re-export, which is the
whole of how a SECOND IMPLEMENTATION arrives, and the file's own comment says that is what it is
for. It does not forbid CALLING one. **14 live sites call one** — `_split`, `_fence_bounds`,
`_LIST_ITEM`, `_FENCE`, `_without_trailing_comment` — and they are TWO populations, which the
review counted as one:

* **9 predate the split and only changed receiver**: `pm/rename.py:53,76,77,96,110,111,119` and
  `checks/grain_shape.py:181,192`, each spelled `model._split` at `412301c` (`grain_shape` at
  `:182,193`, one line up since). This feature introduced none of them.
* **5 are `pm/inventory.py`'s (808, 984, 989, 1423, 1490), and the split MADE them reaches.** At
  `412301c` every one was an intra-module call inside `model.py` — `_FENCE.match` at `:2128` and
  `:2311` are now `inventory.py:808` and `:984`. The call text is pre-existing; the BOUNDARY it
  crosses is not, because `core/frontmatter.py` did not exist to be crossed. **So this feature did
  manufacture 5 of the 14 reaches the criterion's own words would forbid**, and the gate it shipped
  cannot see them.

All 14 reach the OWNER and inherit its preservation rules, which is why rule 3's residual came back
clean through ten hostile encodings — the risk is low and the record is what is at stake. The gate
is a ban on a second implementation; the criterion's words claim a ban on reaching; the words are
what did not land (0.7.0 feature review, F3, with its 13/all-pre-existing re-measured here).

**Criterion 7 did not hold as shipped and now does.** *"No module outside the storage layer and
that roster passes a `Path` to ask what a grain says"* was green over eight live sites, because the
by-id primitive graded five names while the grain layer exposed more that answer the same question
— `read_grain` is `doc_grain` plus a `None` filter, three lines below it in the same file (F-review
M1). Landed: `Grain.section_defect(heading)` so a caller holding a grain never hands `.path` back to
storage; `feature_view(cfg, grain)` in place of `read_feature(cfg, path)`; `check pm`'s pool walk
moved to `every_grain`, which already existed. The gate no longer keeps its graded names by hand —
`test_every_by_path_read_an_owner_exposes_is_named` DERIVES, from each owner's own source, every
module-level function that hands a document read one of its own parameters, and fails on one that
is neither graded nor excused with a reason. It is asserted in both directions, so a blinded reader
fails on it rather than passing over an empty census.
