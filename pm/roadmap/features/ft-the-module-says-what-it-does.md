---
id: ft-the-module-says-what-it-does
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: the module says what it does
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
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

## Out of scope

`cli.py` at the root (`src/agentic_sdlc/cli.py`) — it only routes, it is 200 lines, and it is
correct.

Moving the SDLC vocabulary (`Flow`, `PmConfig`, `Arrival`). 1,070 lines in the right place; only the
storage layer and the work provider are misplaced.

Anything about agents, phases, dispatch or the ledger's dispatch rows — that is the conveyor
milestone and it is a different thing to plan.
