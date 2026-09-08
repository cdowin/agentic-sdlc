---
id: ft-the-storage-layer-is-named-and-the-engine-stops-reaching-through-it
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: the storage layer is named, and the engine stops reaching through it
status: planning
reviewed:
depends_on: []
consumed_by: ["ft-a-phase-declares-what-it-hands-an-agent"]
changelog:
---

# the storage layer is named, and the engine stops reaching through it

**Is the markdown handling separated from the SDLC?** Measured, and the answer is no. This feature
is that measurement turned into a boundary.

## What the tree actually holds

`core/markdown.py` is **65 lines** — fence and code-span scanning, used by `check doc`. It is not
the markdown layer and never was.

The real one is buried mid-file in `repo/pm/model.py`, **2,817 lines doing four unrelated jobs**:

    1,070   config + flow + arrival           the SDLC vocabulary
      385   frontmatter parse, document cache, byte-exact write   PURE STORAGE
       54   id grammar
    1,308   grain index + pool layout         the WORK provider

**And the storage layer has leaked.** Direct calls into it from outside `model.py`: **164, across 13
modules.** Calls to the semantic grain layer: **71.** The engine reaches THROUGH the abstraction 2.3
times more often than it uses it.

    field_of  89    unquote  51    read_raw  8    set_field  6    list_field_of  3
    write_raw  3    set_list_field  2    field_in  1    sequence_defect  1

    58 pm/cli.py   16 checks/pm.py   12 pm/report.py   12 pm/ready_for.py   9 pm/validate.py
     4 checks/grain_shape.py   3 pm/templates   3 pm/changelog.py   2 pm/rename.py
     1 each: pm/skills.py, dispatch.py, conveyor/steps.py, conveyor/driver.py

**The tell is the signature.** `def field_of(path: Path, key: str)` — so 89 call sites hard-code
*a grain is a file on disk with frontmatter*, including `dispatch.py`, `conveyor/steps.py` and
`conveyor/driver.py`, none of which has any business knowing that. `unquote` — stripping quotes off
a YAML scalar, a detail of one storage format — is called 51 times across the engine.

## What is already right, and is the pattern to copy

**The one-way rule holds.** `core/` imports nothing from `repo/` — zero violations. And
`core/apply.py` is the model: *"The one place this package mutates a filesystem"*, with
`tests/test_boundaries.py` forbidding the raw mutators everywhere else.

**That pattern was applied to WRITES and never to READS.** One enforced boundary for `os.replace`;
none for "how do I read a field off a grain". This feature is `apply.py`'s rule, pointed at the
other direction.

## The shape

**Not "split `model.py`".** 0.6.0 deferred that and ruled against line-count goals; a 2,817-line
module is a symptom, not the defect. The defect is that **the engine takes a `Path` to ask a grain a
question.**

So the target is the SIGNATURE, not the file: a caller that wants a field asks for it by grain id
through the semantic layer, and only the storage module knows there is a path. Where the split falls
out of that, it falls out; where it does not, nothing moves for tidiness.

**Callers that legitimately hold a Path keep it, and are NAMED.** `check doc` and `check grain-shape`
walk files because files are their subject — a document with no `id:` is exactly what `grain_shape`
must see. That is an exemption CLASS with a written reason, the way `UNCOVERED` and the vocabulary
seed exemptions already work, not a hole.

**This is not `[work]`.** It does not build a provider, declare `[work]`, or admit a second backend —
`docs/research/2026-09-08-the-sdlc-as-an-engine.md` is explicit that an abstraction with one
implementation is a tax with no payer. It makes a provider REACHABLE later, which at 89 `Path` call
sites it currently is not: the question is not whether a Jira backend is expensive, it is that it is
impossible.

## Ship criterion

The storage layer — frontmatter parse, document cache, byte-exact writer — is a named module with a
stated contract, and `tests/test_boundaries.py` forbids its internals being reached from outside it,
the way it already forbids raw filesystem mutation outside `core/apply.py`.

No module outside the storage layer and the named exemption class passes a `Path` to ask what a
grain says; the engine asks by grain id.

The exemption class is enumerated with a reason per member and can only shrink.

**Behaviour-preserving, proven mechanically** — the AST comparison
`ft-the-vocabulary-is-constants-not-literals` used, not a reviewer's confidence. The byte-exact
guarantee (hard rule 3) is the thing most at risk here and the residual must be read line by line.

The residual count is reported: how many direct calls survive, where, and why each one does.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_boundaries.py` — it is the home for source-shaped layer rules and already
    holds the write-side version of exactly this
  what already covers this: the raw-mutator guard in `test_boundaries.py` IS this feature for
    writes. This is a second rule on the same harness with the same exemption-roster shape, not a
    new family.

## Out of scope

Declaring `[work]` or admitting a second backend. Named as the thing this unblocks, deliberately not
built.

Splitting `cli.py`. Deferred with `model.py` in 0.6.0 and it is a different argument — `cli.py` is
argument parsing and per-verb logic, which is size, not a layering violation.

Moving the SDLC vocabulary (`Flow`, `PmConfig`, `Arrival`) anywhere. It is 1,070 lines and it is in
the right module; only the storage layer is misplaced.
