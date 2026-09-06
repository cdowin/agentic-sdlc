---
id: 0.4.0/the-unbound-census/01-every-edge-reports-both-ways-it-is-unbound
feature: 0.4.0/the-unbound-census
milestone: "0.4.0"
name: The unbound family is counted lines, and broken is a finding
status: planning
owner:
depends_on: ["0.4.0/binding-is-a-field/01-set-binds-and-unbinds-and-pm-move-dies"]
---

# The unbound family is counted lines, and broken is a finding
`check pm` counts, per edge, both ways it can be unbound; `pm list --unbound [--kind <k>]` answers
"what have I written and not scheduled". Neither ever fails on an unbound grain.

    unbound      3 feature(s) name no milestone
    unbound      1 story names no feature
    unbound      5 milestone(s) declare no version
    unscheduled  2 milestone(s) declare a version `order` does not carry
    dangling     1 order entry no milestone's version claims
    broken       1 story names feature ft-nope, which is not in the tree

## Acceptance criteria

1. Each line above is emitted by `check pm` as a **counted line, never a finding and never in the
   exit code**. A tree mid-planning legitimately has many; a gate that reddens on planning is a
   gate people switch off.
2. **Broken IS a finding.** A binding naming a grain not in the tree is a fact about the file, not
   a decision nobody has made yet — the same thing V4 already reports for refs. The unbound/broken
   split is the whole rule: *nothing said* is a plan; *something wrong said* is drift.
3. `pm list --unbound` answers per kind and across all kinds, emitting the same columns the verb
   already emits (`0.4.0/the-read-verbs-compose` — no withheld field).
4. The line shapes are 0.3.0's R1/R2, **extended by rows rather than renamed**. Consumers grep
   these.
5. No config makes an unbound grain an error. A project that wants that can ask later, with a
   reason; shipping the knob now would be a knob nobody has needed.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 4 | unit | `test_pm_gate.py`'s R1/R2 cases are the family's first members | amend — these are further rows through the same code |
| 2 | unit | the unbound-vs-broken split, one case each way | new |
| 3 | unit | `test_pm_verbs.py`'s list cases | amend |
| 5 | unit | the exit code over a tree that is entirely unbound | new — it is the claim people will doubt |

## Out of scope

Failing on anything unbound, under any config.
