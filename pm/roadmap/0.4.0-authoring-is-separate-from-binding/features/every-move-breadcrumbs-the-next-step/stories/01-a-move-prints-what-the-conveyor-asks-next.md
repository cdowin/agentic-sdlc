---
id: 0.4.0/every-move-breadcrumbs-the-next-step/01-a-move-prints-what-the-conveyor-asks-next
feature: 0.4.0/every-move-breadcrumbs-the-next-step
milestone: "0.4.0"
name: A move prints what the conveyor asks next
status: done
owner: claude
depends_on: []
---

# A move prints what the conveyor asks next
Every `pm <kind> <status> <id>` write prints, after its status line, what the conveyor asks NEXT —
the belt that closes a grain in that category and the checks that belt will run.

The moves are where 0.3.0's worst process failure happened, and nothing the tool printed at the
moment of the move said what came next. **What holds is what the tool SAYS at the moment of the
act** — prose in three documents did not stop a builder running wide gates for 21 minutes.

## The rule-9 line, and it is the whole design

A breadcrumb ships only if it is DERIVED: from `[pm.states.<kind>]` (which category the new state
is in) or from `steps.registry_for(<operation>)` (the checks the belt will actually ask). *"`close
feature` asks stories-done, feature-verified, review-recorded, findings-landed"* is the engine
reading its own registry back. *"You should run a review now"* is the engine having an opinion.
**If a sentence cannot be traced to config or to the registry, it does not ship.**

## Acceptance criteria

1. A write into an `in_progress` category names the belt that closes THAT grain and the checks it
   will run, read at runtime from `registry_for`.
2. A write into a `done` category names the parent's belt — a story's close points at
   `close feature`, a feature's at `release` — and a milestone's `done` names no belt above it.
3. **Every word of every breadcrumb is derived.** A project declaring different state words gets
   its own words back. Proven by a source-shaped case: the check names in the breadcrumb are
   `registry_for`'s keys, and the state words are the flow's.
4. `[pm] breadcrumbs = false` turns it off in one line, for a consumer parsing output strictly
   (rule 6). **Stock is ON** — a breadcrumb nobody sees teaches nobody.
5. The status line itself is unchanged, byte for byte. The breadcrumb is an additional line.

## How this is proven

| criterion | tier | the case | existing? |
|---|---|---|---|
| 1, 2, 5 | unit | `test_pm_verbs.py`'s status-move quartet already asserts what a write prints for all four kinds | amend — rows, not a new family |
| 3 | unit | the breadcrumb's check names are a subset of `registry_for`'s keys, and its state words of the flow's | new |
| 4 | unit | the key off, one line | new |

## Out of scope

Hooks — the corpus is opt-in and arming-dependent, so CLI output reaches every consumer and a hook
reaches some. Any gate, refusal or nag.

## Close

done: d0db6c4 — `_breadcrumb` reads `[pm.states.<kind>]` for the category and `registry_for` for
the checks; four call sites, one function. On STDERR, so the status line stays the one line a
consumer parses — `run_cli` grew `stdout_only=` rather than loosening the two cases that assert it.
finding: `[pm] breadcrumbs` is the second config key this milestone added; both are flags with a
stock value, which is the shape `the-config-is-the-model` says a KNOB has.
