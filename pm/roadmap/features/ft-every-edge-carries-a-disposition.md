---
id: ft-every-edge-carries-a-disposition
kind: feature
milestone: "ms-a-move-is-an-event"
name: every edge carries a disposition, and the disposition is the telemetry
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# every edge carries a disposition, and the disposition is the telemetry

**The states were always a state machine. Only the NODES were ever modelled.** A status flip writes
one word and a timestamp; what the move MEANT — who is doing the work, with what, or why nothing is —
was never a field, so it lives in a human's head and dies there.

Model the EDGE. Every transition asks one question, the answer is recorded, and **no action is not an
option — though "nothing, and here is why" is a perfectly good answer.**

## The edges, and what each asks

    -> building    what is building this?
                     --by me
                     --by agent <type> [--ref <dispatch-id>]

    -> reviewing   what happens to it?
                     --review agent <type>
                     --skip review "<why>"

    -> done        the belt already asks its check list; a skip is a disposition
                     (ft-the-close-is-cheap-and-a-check-is-dispositionable)

    -> obe         why is this abandoned?
                     --why "<reason>"

The question is DERIVED — the target state's category, and what the belt for that category will ask
from `registry_for`. A project declaring different states gets its own edges. Rule 9: nothing here is
the tool deciding what a move means; it is the tool asking, and writing down what it was told.

## A move with no disposition is allowed, and VISIBLE

This is the line between asking and refusing. A bare `pm feature building ft-x` still works and still
writes the status — refusing would make the conveyor something people route around. But the move mints
its row with `disposition: none`, and that grain appears on the pressure line
(`ft-the-conveyor-pushes-back`) until somebody answers.

**So "no action" is not blocked; it is just never invisible.** Rule 11: absence is a finding, never
silence. Rule 9: reported, and the caller decides.

## And THIS is where the telemetry comes from

Today telemetry depends on a harness hook reading a transcript. When the hook is not loaded — the
exact failure this milestone hit, nine dispatches and zero rows — there is no telemetry at all, and
`--tokens-in`/`--tokens-out` cannot even express the one number a hand-recording operator has.

A disposition row does not need a hook. **The move writes it, so the tree records itself:**

    {kind: "disposition", grain, from, to, actor, ref, why, at}

which gives, with no harness involvement whatsoever:

    time per state      the gap between two edge rows on one grain
    who did the work    actor, per grain, per milestone
    what was skipped    every skip with its reason, sweepable at the milestone review
    what was abandoned  every obe with its why

Hook-written rows stay and they ENRICH — tokens, tool calls, wall clock, joined on `ref`. But their
absence stops meaning "this milestone has no telemetry" and starts meaning "no token counts", which is
a far smaller hole. **The tree stops depending on something outside itself to know what it did.**

## Ship criterion

Every `pm <kind> <status> <id>` accepts the disposition flags its target edge declares, prints the
fork with both answers typed when none is given, and mints one `disposition` row carrying the edge and
the answer. A bare move still writes the status and records `none`.

`pm ledger report` reports time per state and spend per actor from disposition rows ALONE, on a tree
where no harness hook has ever fired. That is the test that matters, and it is exactly this
milestone's own condition.

`check pm` names grains whose current state was entered with no disposition — a WARN in the U family,
never a refusal.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: `tests/test_pm_verbs.py` on the StatusVerbQuartet, and `tests/test_pm_ledger_report.py`
  what already covers this: the quartet covers what a write PRINTS and what it MINTS for all four
    kinds; these are rows on it. The hook-free report case is the one genuinely new shape, and it is
    the one that proves the claim.

## How the other grains sit under this

This is the organising model; three grains already filed are its parts, not rivals:

    the-conveyor-pushes-back                prints the fork, and the census of unanswered edges
    the-close-is-cheap-and-a-check-is-...   the disposition on the -> done edge
    time-is-measured-per-state-and-rolls-up reads the rows this mints

If the milestone sheds weight it sheds elsewhere: without this, the other three each invent half of it.

## Out of scope

Verifying a disposition is TRUE. `--by agent developer` records a claim; the tool does not go looking
for that agent. A claim in the record is a fact about what was said, and the ledger is an append-only
log of what was said — rule 9, and the same posture as `--review-record` naming a file that only has
to exist.
