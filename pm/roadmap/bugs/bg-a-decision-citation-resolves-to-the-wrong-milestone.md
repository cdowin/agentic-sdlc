---
id: bg-a-decision-citation-resolves-to-the-wrong-milestone
kind: bug
milestone: "ms-nothing-is-hand-rolled"
name: a decision citation resolves to the wrong milestone
status: closed
caused_by: ft-a-surface-reaches-its-reader-or-it-is-decoration
changelog: `check doc` resolves a qualified `<version>/D<n>` decision citation against the decisions file that owns it, in `[doc] scope` and in every grain — a citation naming a ruling the milestone does not record is a finding that names what it does record. The BARE form is deliberately not read: `check pm`'s own rule ids share the D<n> namespace (0.7.0/D1).
---

# a decision citation resolves to the wrong milestone

Found reading `orca-sdlc-kit` against this tree — an adversarial pass checking my claims caught it
in a grain **I wrote during 0.6.0's own close.**

## Symptom

`bg-a-dispatch-nobody-records-leaves-the-spend-surface-empty` cited bare ``D1 (`emit`, never
execute)`` twice. `D1` of `ms-the-rule-reaches-the-work` is *a parent does not close over unresolved
children*. Emit-never-execute is `ms-a-move-is-an-event`'s D1 — a different milestone.

A reader following the citation lands on a real decision that says something else entirely. The
wrong answer is available, plausible and silent: the milestone's own defect class, committed inside
the milestone that named it.

## Root cause

**D-numbers restart per milestone, so a bare `D<n>` is only meaningful inside its own decisions
file.** The tree already knows this and has a convention — `<version>/D<n>`, used 47+ times across
`src/`, `pm/` and `docs/` (`0.5.0/D6`, `0.4.0/D5`, `0.6.0/D6`). Nothing enforces it, and prose
written in a hurry reaches for the short form.

`check doc` grades a `pm <kind> <status>` invocation against the declared flow and a `make <target>`
against the Makefile. A decision reference is the same kind of claim about the tree, and nothing
reads it — which is `ft-prose-that-restates-a-verb-is-rendered-or-gone`'s gap, one noun over.

## Fix

Corrected in place to `0.5.0/D1` (this branch, before the milestone was scaffolded).

The rule the correction implies: a `D<n>` citation in any file under `[doc] scope` or in a grain
resolves against the decisions file that owns it, and a bare one outside its own document is a
finding naming the milestone whose D<n> it would hit. Bare inside its own `-decisions.md` stays
legal — that is where it is unambiguous.

## What landed, and what did not

**Landed.** `check doc` builds a decision index — `{version: (milestone id, the
D-numbers its decisions file records)}`, read through the grain layer's own
`shared_doc` so a pooled tree and a nested one are read the same way (it was
`model.shared_doc` when this landed; `st-the-work-provider-leaves-the-config-module`
retired that module and the call is `inventory.shared_doc` now) — and resolves every
qualified `<version>/D<n>` in `[doc] scope` AND in every grain. A citation
naming a version no milestone declares, or a decision its milestone does not
record, is a finding that names what the milestone DOES record. 21 citations
graded over 225 grains and 6 decisions files; the count is on the verdict line,
so a census that silently narrowed to nothing is visible (rule 4).

**Did NOT land: the bare form.** The Fix above asked for it and the
measurement overruled it — `check pm`'s own rule ids occupy the same `D<n>`
namespace, and 32 of the 33 bare citations in `[doc] scope` are gate rule ids
where bare is correct. Recorded with both rejected alternatives at
`0.7.0/D1`.

**So the exact defect that filed this bug is still not mechanically caught** —
a bare `D1` resolving to a real ruling that says something else. What is caught
is every citation that resolves to NOTHING. Closing the rest needs
`<version>/D<n>` to become mandatory in grains, which is a 273-site migration
and its own decision.

## Out of scope

Renumbering anything. The numbers are stable per milestone and that is the point; the defect is the
missing qualifier, not the numbering.
