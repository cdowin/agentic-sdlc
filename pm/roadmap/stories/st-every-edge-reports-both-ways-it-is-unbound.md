---
id: st-every-edge-reports-both-ways-it-is-unbound
feature: ft-the-unbound-census
milestone: "ms-0.4.0"
name: The unbound family is counted lines, and broken is a finding
status: done
owner: claude
depends_on: ["st-set-binds-and-unbinds-and-pm-move-dies"]
kind: story
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
3. **Every kind is LISTABLE and each one that binds emits its binding as a column**, so
   "what have I written and not scheduled" is `pm list --kind feature | awk -F'\t' '$3 == "-"'`.
   Not a `--unbound` flag: hard rule 11 says a missing filter is a column, never a verb, and
   `pm list` knowing only story and milestone is what made a flag look necessary — see D1.
4. The line shapes are 0.3.0's R1/R2, **extended by rows rather than renamed**. Consumers grep
   these.
5. No config makes an unbound grain an error. A project that wants that can ask later, with a
   reason; shipping the knob now would be a knob nobody has needed.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 4 | unit | `test_pm_gate.py`'s R1/R2 cases are the family's first members | amend — these are further rows through the same code |
| 2 | unit | the unbound-vs-broken split, one case each way | new |
| 3 | unit | `test_pm_verbs.py::test_every_kind_is_listable_and_a_binding_is_a_COLUMN` | new, beside the list cases |
| 5 | unit | the exit code over a tree that is entirely unbound | new — it is the claim people will doubt |

## Out of scope

Failing on anything unbound, under any config.

done: d91fc69, f0a58b5 — V7 grades every binding: empty is UNBOUND (a counted line, never a
finding, never in the exit code), and naming a grain not in the tree or one of the wrong KIND is
drift. *Nothing said* is a plan; *something wrong said* is drift.
It walks the POOLS rather than descending, because a grain nothing claims is exactly what a
descent cannot see. And the READY warnings follow it there: an unbound grain is now asked every
question a bound one is, which it was not.
