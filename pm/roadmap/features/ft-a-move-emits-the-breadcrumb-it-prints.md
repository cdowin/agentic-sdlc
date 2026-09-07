---
id: ft-a-move-emits-the-breadcrumb-it-prints
kind: feature
milestone: "ms-a-move-is-an-event"
name: a move emits the breadcrumb it prints
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# a move emits the breadcrumb it prints

0.4.0 made every `pm <kind> <status> <id>` write print what the conveyor asks next, derived from
`[pm.states.*]` and `registry_for(operation)`. **This gives that same sentence a second carrier and
changes nothing about the first.** The breadcrumb feature's own Out of scope section is the brief:

> a `PostToolUse` breadcrumb is a later layer over the same derived sentence, not a substitute for it.

## One derivation, two renderers

The failure to avoid is two code paths computing "what comes next" and drifting — the defect V2 and
path-as-schema were both killed for. So the derivation stays where it is and gains a second consumer:

    derive_next(grain, from, to)  ->  {next_rung, next_checks, next_actions}
                                          |                  |
                                        prose               row

The prose renderer is untouched. A test asserts both read the same structure, so a change reaching
one and not the other fails.

## Ship criterion

Every status move and every belt write emits `rung.leave` carrying the same next-step facts the
printed breadcrumb states, from one derivation. The printed line stays byte-identical to 0.4.0's for
every case its tests cover — rule 6 makes that prose contract, and this feature is additive or it is
a breaking change nobody asked for.

`[pm] breadcrumbs = false` continues to silence the PROSE only: a consumer whose output is parsed
strictly still emits, because the row is not on the stream they parse.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_pm_verbs.py`, on the `StatusVerbQuartet` the breadcrumb already extended
  what already covers this: the quartet covers what a write PRINTS for all four kinds; these are rows
    on it. The one-derivation assertion joins the breadcrumb's case in `tests/test_boundaries.py`.

## Out of scope

New next-step content. If the emitted row wants a fact the printed line lacks, that fact is missing
from the DERIVATION and belongs there — where both renderers get it.
