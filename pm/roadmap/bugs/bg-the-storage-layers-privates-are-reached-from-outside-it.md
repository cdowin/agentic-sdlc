---
id: bg-the-storage-layers-privates-are-reached-from-outside-it
kind: bug
milestone: ms-the-tool-agrees-with-itself
name: fourteen sites reach core/frontmatter's private names, and the gate only forbids re-binding them
status: closed
caused_by: ft-the-module-says-what-it-does
changelog: none
---

# the storage layer's privates are reached from outside it

Found by the feature review of `ft-the-module-says-what-it-does` (F3), and its count corrected by
the pass that landed the review's findings. `caused_by:` names that feature for the five sites it
manufactured — see below; the other nine it inherited.

## Symptom

`ft-the-module-says-what-it-does`'s ship criterion says `tests/test_boundaries.py` *"forbids its
internals being reached from outside it"*. **What ships forbids one of the 8 names in
`FRONTMATTER_INTERNALS` being RE-BOUND** — a ban on a second implementation, which the file's own
comment says plainly. It does not forbid reaching them, and fourteen sites do:

    repo/pm/rename.py:53,76,77,96,110,111,119          _split, _fence_bounds, _LIST_ITEM,
    repo/checks/grain_shape.py:181,192                 _without_trailing_comment, _FENCE
    repo/pm/inventory.py:808,984,989,1423,1490

## Root cause, and the half that is this feature's

**Nine are inherited.** They existed at `412301c` spelled `model._split` and friends; the receiver
was renamed and nothing else changed.

**Five are new as BOUNDARY CROSSINGS, and 0.7.0 made them.** `inventory.py:808,984,989,1423,1490`
were intra-module calls inside `model.py` — `_FENCE.match` at `model.py:2128` is now
`inventory.py:808`. The call text is pre-existing; **the boundary it crosses is not.** Splitting
`model.py` into `vocabulary.py` + `inventory.py` + `core/frontmatter.py` turned five private calls
into five reaches across a seam the same feature declared. That is the honest finding, and it is
why the criterion reads "NOT as stated" in the review rather than "met".

A private name reached from outside is not a rule-3 risk here: every reach inherits the owner's
preservation rules because it goes THROUGH the owner. The risk is drift — nothing stops the owner
changing `_FENCE`'s shape, and five modules would learn about it at runtime.

## Fix

Two halves, and they are different sizes.

**The five in `inventory.py` are the cheap half**: each wants a public name on the owner. They ask
the same three questions — where does the fence sit, is this line a list item, what is this line
without its trailing comment — and the owner already answers all three internally.

**The gate is the other half.** Widening `OneStorage` from "no second implementation" to "no reach"
fails on fourteen sites the day it is written, so it lands with the migration or not at all. A
roster is the wrong answer: an exemption list naming every offender is a gate that cannot fail,
which is the defect the feature's own M1 was.

`rename.py`'s seven reaches are the subject of
`bg-the-rename-verb-carries-a-second-frontmatter-grammar` and go with that fix, not this one.

## Out of scope

`core/walk.py`, `core/apply.py` and `core/spawn.py`. Their guards hold a different property — an
allowlist of who may call, not a ban on reaching privates — and neither carries an exemption
roster at all.

## Close

Fixed in 1a55d18 (2026-09-12), by ft-frontmatter-has-one-grammar-and-one-way-in.
