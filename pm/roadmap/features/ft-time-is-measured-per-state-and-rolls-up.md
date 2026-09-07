---
id: ft-time-is-measured-per-state-and-rolls-up
kind: feature
milestone: "ms-a-move-is-an-event"
name: time is measured per state, and it rolls up at any level
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# time is measured per state, and it rolls up at any level

**`pm ledger report` sums seconds per CATEGORY. `building` and `reviewing` are both `in_progress`.
So the tool collapses exactly the distinction anyone actually asks about.**

The questions this milestone exists to answer are:

    total building time for this milestone
    total review time for this feature
    how long did this story sit in reviewing

None is answerable today. The rows are there — every `pm <kind> <status> <id>` write mints a `status`
row with a timestamp — but the report aggregates by the category a state sits in, and the two states
worth comparing sit in the same one.

## What changes

Time is attributed to the STATE held between one status row and the next, per grain. A category total
stays available and becomes a sum of its states rather than the only number.

    ms-a-move-is-an-event      building 4h12m   reviewing 1h48m   planning 22m
      ft-the-tool-emits…       building   24m   reviewing    9m
        st-…                   building    6m

Roll-up is the feature, not a view: a milestone's building time is the sum of its features', which is
the sum of its stories'. Membership already gives the tree that shape (`milestone:`/`feature:` are
fields, 0.4.0), so the sum is a walk, not a join.

**Nothing is inferred.** A state a grain never held contributes no key rather than a zero. A grain
still in a state at read time reports its elapsed time as OPEN and says so — never folded silently
into a total, because a running clock and a finished one are different facts (this is `verify --plan`'s
`unknown` posture, applied to duration).

## Ship criterion

`pm ledger report [<grain-id>]` reports seconds per STATE, per grain, at whatever level the id names —
milestone, feature or story — with each level's total being the sum of the level below plus its own.
`--json` emits the same keyed by state name.

A grain currently IN a state has that state's elapsed time reported as open, distinctly from closed
time. Category totals remain, derived from the state totals.

The columns are named in order in `--help`, so the shell is the filter (rule 11's read side): "total
review time for this milestone" is a documented pipe, never a new flag.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_pm_ledger_report.py`
  what already covers this: the per-category aggregation cases exist and become rows on the state
    aggregation; the roll-up assertion is the one genuinely new shape.

## Out of scope

Estimating. The tool reports what the rows hold; a state nobody moved through has no time, not a
guess, and no projection is offered.
