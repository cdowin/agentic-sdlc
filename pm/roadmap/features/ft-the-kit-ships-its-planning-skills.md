---
id: ft-the-kit-ships-its-planning-skills
kind: feature
milestone: 
name: the kit ships its planning and execution skills
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the kit ships its planning and execution skills

Issue: #42. Pool: a feature request, a new installable, kept out of 0.9.0's bug-and-debt scope.

The kit ships the loop (`pm-execution.md`, `dispatch`, the agent briefs). It does not ship the two
skills that decide how much planning happens and when a builder stops, and in one consumer those two
decided most of a milestone's cost. The consumer's own versions open with two rules that are not
stack-specific:

- **writing-plans: plan only when needed.** If a story brief, an audit or a bug's Fix already
  outlines the work, build it. Write at most a one-page decision sheet of the open decisions, each
  with a recommendation. Sibling stories get their sheets in one pass.
- **executing-plans: file and continue.** File an out-of-scope defect and keep building. Move a claim
  blocked by broken production onto that bug. Adapt a stale detail inside the contract and record
  the deviation. Stop only when a contract cannot hold, the decision is not the builder's, or a
  verification fails twice with no diagnosis.

It also asks that the same two rules go into the shipped `architect`, `po` and `milestone-reviewer`
briefs: an architect "Phase 0: end state first", and a reviewer "lens zero: is there a simpler end
state?".

**Open questions for whoever schedules it:**

- **Rule 8.** The evidence is one consumer's. Ship the two rules and none of their stack material.
  The project section of the skill is the consumer's.
- **Carriage (#15).** A skill body never reaches a dispatched agent, only its description does. A
  rule that has to bind a BUILDER belongs in the role brief or the `dispatch` preamble. A skill
  reaches only the session that invokes it.
- **Overlap.** `ft-the-flow-is-boring-by-construction` (0.10.0) rewrites the architect's dispatch
  loop, so "Phase 0" should land with it or after it.

## Ship criterion

<!-- Written when it is scheduled. -->

## Proof budget

  cases:
  tier:
  lands in: `tests/test_install.py`, where every installable is proven byte-current
  what already covers this: `pm install-skills` and its currency check, for the skills it ships now.
