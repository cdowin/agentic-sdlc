---
id: ft-the-unbound-census
milestone: ms-0.4.0
name: Every relationship reports both ways it can be unbound
status: done
reviewed: docs/reviews/2026-09-06-0.4.0-the-config-and-the-census.md
phase:
depends_on: ["ft-binding-is-a-field"]
consumed_by: []
kind: feature
order:
  - "st-every-edge-reports-both-ways-it-is-unbound"
---

# Every relationship reports both ways it can be unbound

0.3.0's R1 named the pair for one edge: an `order` entry no milestone claims, and a milestone
version nobody scheduled. **Every edge has that pair**, and once binding is a field the family is
uniform:

```
unbound      3 feature(s) name no milestone
unbound      1 story names no feature
unbound      5 milestone(s) declare no version
unscheduled  2 milestone(s) declare a version `order` does not carry
dangling     1 order entry no milestone's version claims
broken       1 story names feature ft-nope, which is not in the tree
```

**Unbound is a CENSUS LINE, never a finding.** A tree mid-planning legitimately has many, and it is
the default state of a newly written fact — that is the whole point of separating authoring from
binding. A gate that reddens on planning is a gate people switch off, which is the same reasoning
that moved D2/D3/D5/D6 to warnings in 0.2.0.

**Broken IS a finding.** A binding that names a grain not in the tree is a fact about the file, not
a decision someone has not made yet, and it is what V4 already reports for refs.

The distinction is the whole rule: *nothing said* is a plan in progress; *something wrong said* is
drift.

## The verb

`pm list --unbound [--kind <k>]` — "what have I written and not scheduled", per kind or across all
of them. It reads and writes nothing, and it is the question that makes writing things down cheap:
you can author freely because one command tells you what is still floating.

## Ship criterion

`check pm` reports the unbound family as counted lines per edge, never failing on them, and reports
a binding naming a missing grain as a finding. `pm list --unbound` answers per kind and across all.
The line shapes are the ones 0.3.0 established, extended by rows rather than renamed — consumers
grep these.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `test_pm_gate.py` beside R1/R2, and `test_pm_verbs.py`
  what already covers this: R1/R2 land in 0.3.0 written as the family's first members, so their
    cases are the pattern and these are further rows through the same code. New: the
    unbound-vs-broken split, and the verb's filter.

## Out of scope

Failing on anything unbound, under any config. If a project wants unscheduled work to be an error
it can ask for that later, with a reason — shipping the knob now would be a knob nobody has needed.
