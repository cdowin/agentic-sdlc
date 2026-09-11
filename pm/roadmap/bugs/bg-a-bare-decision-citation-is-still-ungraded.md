---
id: bg-a-bare-decision-citation-is-still-ungraded
kind: bug
milestone:
name: the defect that filed the citation bug is still not mechanically caught, and closing that bug retires its only pointer
status: open
caused_by:
changelog: none
---

# a bare decision citation is still ungraded

Filed at the 0.7.0 milestone review (§8) so the residual keeps a pointer.
`bg-a-decision-citation-resolves-to-the-wrong-milestone` says in its own body *"the exact defect
that filed this bug is still not mechanically caught"*; that bug goes to `closed` with the release,
and a `closed` grain's body is nobody's next action.

## Symptom

`check doc` grades the QUALIFIED form — `<version>/D<n>` — and says nothing about the bare `D<n>`.
The defect that filed the original bug was a bare one: ``D1 (`emit`, never execute)`` cited against
a D1 that ruled on something else entirely. That exact shape still passes.

## Root cause, and why the bare form was left alone deliberately

`0.7.0/D1` carries the measurement: **32 of 33 bare `D<n>` in `[doc] scope` are `check pm`'s own
rule ids** — D4 an undeclared status, D12 a belt is its checks, D9/D10 the branch rules — and those
are correct as bare, because the gate's rule namespace is not the decisions namespace. Reading the
bare form as a decision citation would report 32 false findings to report 1 true one.

So the rule shipped for the half it can grade, and the rejected alternative (gloss-matching the
citation against the decision's title) is recorded in D1 with its own argument.

**What makes this a grain rather than a footnote:** the class is closed by the 273-site migration
that qualifies every bare citation, and no grain names that work. A residual with no pointer is a
residual nobody will find.

## Fix

Qualify the citations, then grade the bare form as a finding. In that order — the rule cannot fire
before the migration or it reports the 32.

Price it first: 273 sites is the measured figure and it spans `[doc] scope` plus every grain, so it
is a sweep with a rewrite verb behind it rather than an afternoon. `agentic-sdlc cite` is the census
that answers how many and where.

## Out of scope

Gloss-matching. Rejected in `0.7.0/D1` with the argument, and re-litigating it is what a decision
record exists to prevent.

The qualified form's rule. It shipped, it works, and it is not this.
