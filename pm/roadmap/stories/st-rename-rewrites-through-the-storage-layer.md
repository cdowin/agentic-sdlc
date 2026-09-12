---
id: st-rename-rewrites-through-the-storage-layer
kind: story
feature: ft-frontmatter-has-one-grammar-and-one-way-in
milestone: "ms-the-tool-agrees-with-itself"
name: pm rename rewrites a document through the storage layer, in its grammar
status: done
owner:
depends_on: []
changelog: `pm rename` rewrites a block list over exactly the lines the reader reads.
done: 1a55d18 — rename rewrites through core/frontmatter.renamed_in
---

# pm rename rewrites a document through the storage layer, in its grammar

Closes `bg-the-rename-verb-carries-a-second-frontmatter-grammar`. Read its Symptom and Fix first.

`pm/rename.py:72-127` builds a document rewrite out of `core/frontmatter.py`'s private parts
(`_split`, `_fence_bounds`, `_LIST_ITEM`, `_without_trailing_comment`). It also carries its own
key grammar and its own inline-list reader for the same syntax. The storage layer gets the one call
rename needs: a document-level rewrite, given a mapping of old id to new, that preserves every byte
it was not asked to change (rule 3). Rename's own grammar is deleted.

**Decide the inline-list question first, and record it.** Nothing this package writes emits an inline
list (`pm set` writes the block form). So either the inline form is a stated input format in
`core/frontmatter.py`'s docstring ("we read what git or a human left behind"), or it is not
accepted. If the answer changes what a consumer's tree may contain, it is a `pm decide` entry.

## Acceptance criteria

1. `pm/rename.py` imports none of `FRONTMATTER_INTERNALS`, and has no regex or parser of its own for
   a key line or a list item.
2. `pm rename` over a fixture tree produces the same bytes as it does at HEAD, line endings included.
   Capture HEAD's output before changing anything.
3. The inline-list decision is written where the bug file says it belongs, and a case covers
   whichever answer was chosen.
4. Idempotent: the same rename twice is a no-op the second time.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `st-nothing-reaches-the-storage-layers-privates` widens `OneStorage` to forbid reaches, and this story leaves it no rename site to list. Until then, the bug's own count, re-run | the gate is story 3's |
| 2, 4 | unit | the existing rename byte-preservation cases | existing |
| 3 | unit | an inline-list document through the new call | new |

## Semver

Patch, unless the inline-list answer narrows what a consumer's tree may hold. Then it is a minor.
