---
id: 0.4.0/every-move-breadcrumbs-the-next-step
milestone: "0.4.0"
name: every move breadcrumbs the next step, derived from the declared flow
status: building
reviewed:
phase:
depends_on: []
consumed_by: []
---

# every move breadcrumbs the next step, derived from the declared flow

**0.3.0's northstar was "the tool teaches the conveyor." It teaches at the BELTS
and nowhere else.** `close story` prints `next:` lines; `pm feature reviewing
<id>` prints `planning -> reviewing` and stops. The status moves are exactly
where 0.3.0's own worst process failure happened — nine feature reviews batched
to the end of the milestone, 93 minutes of clock on features that were already
built — and nothing in the tool's output at the moment of the move said what the
conveyor does next.

A breadcrumb at each move is the cheapest possible fix, and it is the same shape
as the two other lessons this package learned the hard way: prose in a document
did not stop a builder running wide gates, and the static `shell` mark could not
see an indirect spawn. **What holds is what the tool SAYS at the moment of the
act.**

## The rule-9 line, and it is the whole design

Hard rule 9: the tool *"never decides what a move MEANS or what should happen
next."* A breadcrumb survives that rule only if it is DERIVED:

- from the project's own `[pm.states.<kind>]` — which category the new state is
  in, and which states its `done` list opens with;
- from the belt registry — the checks `close story|feature` / `release` will
  actually ask, read from `registry_for(operation)`, never restated.

`feature 0.1/x: planning -> reviewing` followed by *"`close feature` asks
stories-done, feature-verified, review-recorded, findings-landed"* is the engine
reading its own registry back. *"You should run a review now"* is the engine
having an opinion, and it is the thing this package refuses to be. **If a
sentence cannot be traced to config or to the registry, it does not ship.**

## Ship criterion

Every `pm <kind> <status> <id>` write prints, after the status line, what the
conveyor asks NEXT for a grain in that category — the belt that closes it and
the checks that belt will run, both read at runtime. A move into a `done`
category names the parent's belt; a move into `in_progress` names its own. A
project whose flow declares different words gets its own words back, because the
line is derived, not templated.

`[pm] breadcrumbs = false` turns it off in one line, for a consumer whose output
is parsed strictly (rule 6). Stock is ON: a breadcrumb nobody sees teaches
nobody.

A test asserts every breadcrumb is reachable from `registry_for` or from
`[pm.states.*]`, so a hardcoded next-step cannot be added without failing.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_pm_verbs.py` beside the status-move quartet
  what already covers this: `StatusVerbQuartet` covers what a write PRINTS for
    all four kinds — these are rows on it, not a new family. The derived-only
    assertion is source-shaped and joins `tests/test_boundaries.py`.

## Out of scope

Hooks. The corpus is opt-in and arming-dependent, so CLI output reaches every
consumer and a hook reaches some; a `PostToolUse` breadcrumb is a later layer
over the same derived sentence, not a substitute for it.

Any gate, refusal or nag. A breadcrumb is information; the caller decides.
