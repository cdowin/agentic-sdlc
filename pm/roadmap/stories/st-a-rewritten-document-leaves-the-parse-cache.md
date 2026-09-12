---
id: st-a-rewritten-document-leaves-the-parse-cache
kind: story
feature: ft-frontmatter-has-one-grammar-and-one-way-in
milestone: "ms-the-tool-agrees-with-itself"
name: a document rewritten through a plan leaves the parse cache
status: planning
owner:
depends_on: ["st-rename-rewrites-through-the-storage-layer"]
changelog:
---

# a document rewritten through a plan leaves the parse cache

Closes `bg-the-rename-write-path-never-invalidates-the-document-cache`. Read its Fix first, because
that section is the design argument.

`core/frontmatter.py` caches parsed documents in `_DOCUMENTS`, and only `write_raw` calls
`forget_document` (`core/frontmatter.py:43`). `pm rename` stages its rewrite through
`apply.Plan.overwrite`, so a renamed document's parse survives its own rewrite.

**The priced candidates, from the bug file.** Rejected: `apply.Plan` calling `forget_document`,
because `core/apply.py` imports nothing from the package on purpose, and that would be an import
cycle. The candidate: `frontmatter.document()` consults `apply.mutations()` (`apply.py:237`), the
counter `inventory.reading_tree` already uses for this same question. That is about four lines,
with no cycle, **but it drops the whole cache on every write**. Measure it against `pm rename` over
this tree, and `pm collapse`, before choosing.

**It may be free already.** If the previous story's rewrite call invalidates what it rewrites, this
story is a regression case and a close line. Say so; do not build a second mechanism.

## Acceptance criteria

1. After a rewrite staged through `apply.Plan`, `frontmatter.document(path)` in the same process
   returns the new bytes' parse.
2. The chosen fix's cost is measured: `pm rename` wall-clock over this tree at HEAD and after,
   both numbers in the close.
3. `core/apply.py` still imports nothing from the package.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | parse, rewrite through a plan, parse again, and compare | new |
| 2 | — | two timings in the close line, not a test | — |
| 3 | unit | `tests/test_boundaries.py`'s existing apply-imports rule | existing |

## Semver

Patch.
