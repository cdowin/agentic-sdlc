---
id: ft-a-rung-has-an-entry-edge
kind: feature
milestone: "ms-a-move-is-an-event"
name: a rung has an entry edge, and it is ready-for
status: planning
reviewed:
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
rungs that lack it and emits `rung.enter` from all of them.

    ready-for story <id>        the story rung's entry condition
    ready-for feature <id>      shipped
    ready-for milestone <id>    shipped
    ready-for tag <id>          shipped
    ready-for adopt <version>   the pin bump's entry condition

What `ready-for story` must be true of is a DECLARATION, not a guess — the story belt's own check
list read from `registry_for("story")`, minus the ones that can only be answered after the work
(`evidence-written` cannot be true before the story is built). The entry condition is the subset that
is decidable up front, and which those are comes from the registry, never from a list in this file.

## Why the blockers matter more than the boolean

Exit 1 already names every blocker. Structured, that list is the agent's work queue:

    {rung: "feature", grain: "ft-x", ready: false,
     blockers: [{check: "stories-done", why: "st-a, st-b not in done"}]}

The loop closes with the exit edge: `rung.leave` names `next_rung`, the agent asks `ready-for` on it,
gets blockers, works, runs the belt. **An agent driving this never has to hold the SDLC — it asks at
each edge and is told.** That is hard rule 11 at the surface an operator is actually standing in.

## Ship criterion

`pm ready-for` answers for every rung a belt exists for, each condition read from that belt's
registry entry, each blocker named. `ready-for story` exists and the story belt is no longer the only
rung an agent must guess at.

A full story-to-close loop is drivable from `ready-for` plus `rung.leave` alone, with no line of
human prose parsed. That is the feature's real test and it belongs in the suite as one.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_pm_ready_for.py`
  what already covers this: the three shipped conditions have cases there already; the new rungs are
    rows on the same harness. The drive-the-loop assertion is one integration case and is the only
    new shape.

## Out of scope

Any refusal. `ready-for` reports and the caller decides — a rung that says "not ready" never stops a
belt, because `--force` is the deviation and the ledger records it.
