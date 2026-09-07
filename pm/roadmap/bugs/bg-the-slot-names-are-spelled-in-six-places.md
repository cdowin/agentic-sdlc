---
id: bg-the-slot-names-are-spelled-in-six-places
milestone: ms-0.2.0
name:
status: closed
caught_in: "0.2.0"
fix_milestone: 0.2.0
caused_by: ft-the-kit-owns-the-gates-that-scan-its-own-artifacts
kind: bug
---

# `stories` and `bugs` are spelled as literals in six places

Filed from the 0.2.0 release review as **L5**, deferred because the finding is smaller than the
fix and the fix is the interesting part.

`checks/grain_shape.py`'s `_kind_of` says in its docstring that it reads a document's kind "from
`model`'s names and slots", and that is **half true**: the FILE names come from `model` constants
(`MILESTONE_DOC`, `FEATURE_DOC`, `DECISION_FILE_NAME`, `HANDOFF_FILE_NAME`), and the two SLOT
DIRECTORIES are the bare literals `'stories'` and `'bugs'`.

## Why it is not a one-file fix

`model.py` hardcodes the same two strings in **five** places of its own —
`grain_docs(fdir / 'stories')`, `slot_walk(mdir / 'bugs')`, and three more. So the honest fix is
two constants in `model` and six call sites updated, not an edit to the gate that noticed.

Six spellings of one fact is exactly the shape this package spends its comments warning about,
and it has never bitten because nobody has renamed a slot. **That is what a latent duplication
looks like from the inside**: correct everywhere, until the first rename.

## Not a correctness defect today

Nothing misreports. A tree using a different slot name is not a supported shape and would fail
`pm validate` long before it reached this. Filed so the next person to touch `slot_walk` finds
the census of spellings already taken rather than discovering it one grep at a time.
