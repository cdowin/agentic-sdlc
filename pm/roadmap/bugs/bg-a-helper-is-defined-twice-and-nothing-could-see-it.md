---
id: bg-a-helper-is-defined-twice-and-nothing-could-see-it
kind: bug
milestone: "ms-nothing-is-hand-rolled"
name: pm/cli.py defines _slugify twice and the first has never been reachable
status: fixed
caused_by:
changelog: none
---

# a helper is defined twice and nothing could see it

Found by the po pass that decomposed `ft-the-module-says-what-it-does`, reading
`pm/cli.py` for the helper census rather than looking for defects.

## Symptom

`src/agentic_sdlc/repo/pm/cli.py` defines `_slugify` **twice** — at line 549 and
again at line 1720 — with byte-identical bodies and differently worded
docstrings. Python binds the name twice; the second definition wins. There is
exactly one call site, `_mint_path` at line 1739, and it is below both.

**So the definition at 549 has never been reachable.** It is not a near-miss or
a shadowed edge case: it is dead from the line it was written on.

## Root cause

`pm/cli.py` is 3,136 lines carrying **75 module-level helpers across 1,129
lines** — as much helper as the 24 verb bodies they serve (1,208 lines). At that
size a reader looking for "is there already a slugifier" scrolls, does not find
it, and writes one. Nothing in the suite asks whether a module defines a name
twice, and Python does not warn.

**This is rule 11 from the source side.** A capability nobody can find is a
capability you do not have — and here the capability existed twice, in one file,
and the second author could not see the first.

## Fix

Delete the definition at 549 and keep the one beside its caller. **Behaviour is
unchanged by construction**: the deleted binding is overwritten before any call,
so no call site can observe the difference. That is what makes it safe to land
inside a move story rather than ahead of one.

The gate is the part that lasts: a case asserting no module under `src/` binds
the same top-level name twice. It fails at HEAD on this file, which is what
makes it worth writing.

## Where it lands

`st-the-pm-cli-helpers-find-a-home` carries the deletion and the gate as its
criterion 1. Filed as a bug anyway rather than absorbed into that story, because
a defect that shipped gets a record with a symptom and a root cause — a story
criterion is what we did, and a bug is what was wrong.

## Out of scope

The other 74 helpers, and where they go. That is the story, and it is a move
rather than a deletion.

## Fixed

`2198600` — `_slugify`'s dead twin deleted and the gate written
(`test_boundaries.py::NoNameIsBoundTwice`, 14 `CORPUS` cases). `inspect.getsourcelines`
confirmed the interpreter picked 1725, not 549 — the line numbers here are stale by one.

**The symptom's central claim is too narrow, and the gate is why we know.** "the only
duplicated top-level binding in the module" is true of `cli.py` and false of `src/`: the
gate failed at HEAD with THREE offenders. `inventory.py::Sequence` (20/1190) was a
dataclass shadowing `collections.abc.Sequence`, so `get_type_hints` on that module raised
`TypeError` — a live defect, not a dead twin. `inventory.py::duplicate_ids` (455/667) had
two DIFFERENT return shapes, `dict` and `list[tuple]`, and both callers unpack tuples, so
the dead one could never have served them. Both predate the `model.py` split; the root
cause above describes that file too. A 7-line dead `_known_feature_ids` went with them,
found by reading rather than by the gate — reachability is a different shape, and stays
uncovered.
