---
id: ft-a-rung-has-an-entry-edge
kind: feature
milestone: "ms-a-move-is-an-event"
name: a rung has an entry edge, and it is ready-for
status: reviewing
reviewed: docs/reviews/2026-09-07-0.5.0-a-rung-has-an-entry-edge.md
depends_on: []
consumed_by: []
order:
  - "st-ready-for-story-answers-the-inner-loop"
---

# a rung has an entry edge, and it is ready-for

Every belt already has an exit edge: it writes one status and prints `next:` lines. Only some have an
entry edge. `pm ready-for` takes `feature | milestone | tag` — three conditions, each an exit code
with every blocker named.

**The story rung has none.** It is the rung an agent runs dozens of times a milestone, the one the
execution loop calls the inner loop, and it is the only one with no machine-readable answer to *may I
start*. An agent's alternative is to guess, or to read prose written for a human.

## What an entry edge is

`ready-for` is already the right shape and needs no redesign: exit 0 ready, exit 1 not ready naming
every blocker and never a tally, exit 2 usage. Writes nothing. This feature extends the verb to the
rung that lacks one, and emits `rung.enter` from all of them **to the sink `[emit]` declares** — a
tree that declares no `[emit]` section emits nothing at all, which is how the verb keeps its
"writes nothing" contract.

    ready-for story <id>        the story rung's entry condition
    ready-for feature <id>      shipped
    ready-for milestone <id>    shipped
    ready-for tag <id>          shipped

There is no `ready-for adopt`, and the refusal says why rather than reading as a typo — every check
in the adopt belt is either the work the bump DOES or one that runs a command, so the derived entry
set is empty and the rung could only ever answer NOT READY. Recorded as D4; see `## Out of scope`.

What `ready-for story` must be true of is a DECLARATION, not a guess — the story belt's own check
list read from `registry_for("story")`, narrowed to the names the registry puts in
`ENTRY_CONDITIONS`. Which those are comes from the registry, never from a list in this file, and the
census states only what the derivation KNOWS about the rest: that they were not declared entry
conditions, plus the action the belt runs at the close. *"Answers after the work"* is true of
`evidence-written` and false of `committed`, which reads git and answers fine up front — it is
excluded on a ruling written at `ENTRY_CONDITIONS`, and a verb printing a reason it did not derive
is rule 4's shape one size down.

## Why the blockers matter more than the boolean

Exit 1 already names every blocker. Structured, that list is the agent's work queue:

    {rung: "feature", grain: "ft-x", ready: false,
     blockers: [{check: "stories-done", why: "st-a, st-b not in done"}]}

The loop closes with the exit edge: `rung.leave` names `next_rung`, the agent asks `ready-for` on it,
gets blockers, works, runs the belt. **An agent driving this never has to hold the SDLC — it asks at
each edge and is told.** That is hard rule 11 at the surface an operator is actually standing in.

## Ship criterion

`pm ready-for` answers for **`story`, `feature`, `milestone` and `tag`** — every rung whose belt has
a condition that is decidable before the work — each condition read from that belt's registry entry,
each blocker named. `ready-for story` exists and the story belt is no longer the rung an agent must
guess at. The fifth belt, `adopt`, is answered by the ABSENCE said out loud: the derivation returns
an empty set for it, so the verb names the rung and says why rather than reporting a typo (D4).

`rung.enter` is emitted from every rung to the sink `[emit]` declares, and emission is never
load-bearing — a malformed, escaping or unwritable sink is one line on stderr and moves neither the
exit code nor a printed byte.

The story-to-close loop drivable from `ready-for` plus `rung.leave` alone is the MILESTONE's
criterion, not this feature's (`ms-a-move-is-an-event.md`, *"an agent can drive a full story-to-close
loop from emitted events alone"*). Nothing in `src/` emits `rung.leave` yet, so the case cannot be
written here; it is deferred by name in `## Out of scope`.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: `tests/test_pm_ready_for.py`
  what already covers this: the three shipped conditions have cases there already; the new rung is
    rows on the same harness. The fifth is the emission-failure case (review E4) — the swallow was
    correct and held by nothing, while the sibling feature's identical swallow WAS tested.

## Out of scope

Any refusal. `ready-for` reports and the caller decides — a rung that says "not ready" never stops a
belt, because `--force` is the deviation and the ledger records it.

**`ready-for adopt`, and it is a ruling rather than a gap** (D4). The derived entry set for the
adopt belt is empty — `pin-bumped`, `installables-current` and `config-updated` are the work the
bump does, and the other five run commands, which `ready-for` never does — so the rung could only
ever exit 1. Writing the condition by hand instead is the rejected alternative: it would be the one
rung whose question this package DECIDED rather than read. What ships is the named refusal.

**The drive-the-loop case, deferred to `ft-one-event-shape-serves-three-readers`.** It needs
`rung.leave`, whose shape that feature declares and which `ft-a-move-emits-the-breadcrumb-it-prints`
emits; both are `status: planning`, so nothing in `src/` emits the event the loop would be driven
by. Not carried as `depends_on:` — that would hold this feature's close on two features that have
not started, for a case the MILESTONE's criterion already owns. It is deferred here by name so the
criterion stays honest, and the milestone's close is where it comes due.
