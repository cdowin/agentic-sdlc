---
id: ft-frontmatter-has-one-grammar-and-one-way-in
kind: feature
milestone: "ms-the-tool-agrees-with-itself"
name: frontmatter has one grammar and one way in
status: reviewing
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-rename-rewrites-through-the-storage-layer"
  - "st-a-rewritten-document-leaves-the-parse-cache"
  - "st-nothing-reaches-the-storage-layers-privates"
---

# frontmatter has one grammar and one way in

Tech debt, and no issue. `core/frontmatter.py` opens with *"The one place this package reads and
writes a frontmatter block"*, and `CLAUDE.md` names it a primitive. The review of
`ft-the-module-says-what-it-does` (0.7.0) found three ways that claim is not yet true, and filed each
as a bug, not a NIT. Each bug is bound to this milestone, and each story below closes one:

    st-rename-rewrites-through-the-storage-layer    → bg-the-rename-verb-carries-a-second-frontmatter-grammar
    st-a-rewritten-document-leaves-the-parse-cache  → bg-the-rename-write-path-never-invalidates-the-document-cache
    st-nothing-reaches-the-storage-layers-privates  → bg-the-storage-layers-privates-are-reached-from-outside-it

**The bug file is the brief's evidence; read it first.** Each one carries the symptom, the root cause
and the priced fix. A story adds only its acceptance criteria and proof. When a story closes, it
flips its bug with `pm bug fixed <id>` and then `closed`, citing the same hash.

**Serial, in this order.** `pm/rename.py` accounts for 7 of the 14 private reaches, so the rename
story shrinks the third story's census. The cache story may turn out to be free once rename writes
through the storage layer. If it is, say so in its close; do not invent work to fill it.

## Ship criterion

`pm/rename.py` imports no private name from `core/frontmatter.py`, and has no list or key grammar of
its own. After `pm rename`, a read in the same process sees the new bytes. `tests/test_boundaries.py`
fails a reach into `FRONTMATTER_INTERNALS` from outside the module, not only a re-binding, with an
empty offender list. `pm rename` over this tree's own roadmap takes no more wall-clock than it does
at HEAD, measured before and after.

## Proof budget

  cases: 4–6
  tier: unit
  lands in: `tests/test_boundaries.py` (the gate), the existing rename cases, and the frontmatter
    primitive's own module. Search before adding one (rule 10)
  what already covers this: `OneStorage` forbids re-binding the 8 internals, not reaching them.
    The rename cases prove bytes preserved, not that the read after sees them.
