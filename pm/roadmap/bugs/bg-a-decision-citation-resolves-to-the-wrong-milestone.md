---
id: bg-a-decision-citation-resolves-to-the-wrong-milestone
kind: bug
milestone: "ms-nothing-is-hand-rolled"
name: a decision citation resolves to the wrong milestone
status: open
caused_by: ft-a-surface-reaches-its-reader-or-it-is-decoration
changelog: `check doc` reports a bare `D<n>` decision citation outside the decisions file that owns it, naming the milestone it would resolve to — D-numbers restart per milestone, so the short form silently points at a real, different ruling.
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

## Out of scope

Renumbering anything. The numbers are stable per milestone and that is the point; the defect is the
missing qualifier, not the numbering.
