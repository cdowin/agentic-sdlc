---
id: ft-the-inner-levels-are-belts-too
milestone: ms-0.2.0
name: Closing a story and closing a feature are step lists, not prose
status: done
reviewed: docs/reviews/2026-09-05-the-inner-levels-are-belts-too.md
phase: 5
depends_on: ["ft-the-release-is-a-conveyor", "ft-the-belts-refuse-to-advance", "ft-the-story-belt-knows-what-verifies-this-edit", "ft-the-belt-reports-and-finishes"]
consumed_by: []
risk: medium
size: m
labels: ["belts", "conveyor", "sdlc"]
kind: feature
order:
  - "st-closing-a-story-is-a-belt"
  - "st-closing-a-feature-is-a-belt"
  - "st-the-belt-above-refuses-to-start"
---

# Closing a story and closing a feature are step lists, not prose

> **Built 2026-09-05, under D8.** This record was written before the report-never-refuse ruling
> (`decisions.md` D8; `0.2.0/the-belt-reports-and-finishes`), and the plan audit (Q3) held it
> unbuilt until that feature landed. It has: `close story` and `close feature` are two more rows
> in `driver.OPERATIONS`, and like every belt they REPORT — each step is a check, a check that is
> not true is named with what would make it true, and the walk finishes with a scoreboard and
> exit 1. Nothing halts. **The ORDER is still the whole deliverable**; what changed is who acts on
> a step that is not true: the caller, never the engine (hard rule 9).

**Chris, 2026-09-05, on being shown the three levels written up as doctrine:**

> *"I wanna make sure I'm not too loose there. If we can encode some of this in the conveyor
> belt, we absolutely should."*

He is right, and the omission is backwards in the most expensive direction. 0.2.0 shipped
conveyors for `release` and `adopt` — the two OUTER operations, run weekly and on a pin bump —
and left the two INNER levels as prose. **The story close runs dozens of times a day.** The
level that runs most often is the one that got a paragraph.

## What the omission cost, measured on this milestone

The orchestrator building this feature parked **28 finished stories at `reviewing`** and then
reviewed the whole milestone in one pass, skipping the feature level entirely — in the milestone
that builds the levels. `pm ready-for milestone` had been answering NOT READY with all eight
features named for hours, and prose is what it takes to notice a verb telling you that.

That is not a mistake a step machine lets pass unnamed. `close story` reports a red or
unverifiable `narrow-verified` in its scoreboard; `close feature` names every story that
`stories-done` finds open.

## Two more operations on the driver that already exists

```toml
[story]
steps = ["claimed", "narrow-verified", "committed", "evidence-written", "story-done"]

[feature]
steps = ["stories-done", "feature-reviewing", "feature-verified",
         "review-recorded", "findings-landed", "feature-done"]
```

`driver.OPERATIONS` grows from two to four. Nothing else about the machine changes: the same
three step kinds, the same `do()`-never-decides rule, the same run-state cache under
`.agentic-sdlc/run/<operation>.json`, the same `--skip <step> --reason` deviation row.

**The belts wire to each other through the verbs that already exist.** `close feature`'s
`stories-done` step IS `pm ready-for feature`; `release`'s `features-done` step IS
`pm ready-for milestone`. No step re-implements a predicate that has a verb.

## Where the line is, and it is Chris's line

> *"We can't really enforce all of this perfectly through code, nor really should we, but we
> should express it when the code pops back."*

So: **the entry conditions are checked and reported, the judgement is expressed.** `stories-done`
is a fact about the tree and it is named, story by story. `review-recorded` can only check that a record EXISTS and parses —
whether the review was any good is not a thing to encode, and a step that pretended to check it
would be this package's cardinal sin wearing a protocol. Each JUDGEMENT step says, in its
`do()`, what a human must do and why the machine is not doing it.

## Ship criterion

1. `agentic-sdlc close story <id>` and `close feature <id>` walk their lists, report every step
   that is not true, finish, and are resumable — the same driver, proven by the same tests.
2. **`close story` reports a red narrow check by name and exits 1**, scanning the story's own
   commit range rather than the moment's diff; the narrow command comes from `[verify]` rather
   than being named in the step.
3. **`close feature` names every story that is not `done` and exits 1** — by calling
   `pm ready-for feature`, never by re-implementing it.
4. `close feature` reports an absent or unparseable review record, or a finding at
   `disposition: open`, as UNVERIFIABLE — never as a pass.
5. `install-sdlc` renders all FOUR lists, so the generated protocol is the whole SDLC and not
   just its outer half.
6. **0.2.0's own 28 stories and 9 features close through these verbs.** Same bar as ship
   criterion 9: a belt whose first run is performed by hand has not been tested.

## Risks

1. **Over-encoding, and this feature is where it would happen.** A step earns its place by
   having a checkable postcondition. "The reviewer was thorough" does not have one and must not
   become a step; it belongs in the `do()` text a human reads.
2. **A story-close conveyor that is slower than closing by hand will be skipped**, and a skipped
   conveyor is worse than none because it looks like control. The story list is five steps and
   four of them are already-computed facts; if it is not under a second, it is wrong.
