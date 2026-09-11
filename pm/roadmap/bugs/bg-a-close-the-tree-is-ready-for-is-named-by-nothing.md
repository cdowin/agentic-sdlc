---
id: bg-a-close-the-tree-is-ready-for-is-named-by-nothing
kind: bug
milestone: "ms-a-consumer-can-take-the-bump"
name: a close the tree is ready for is named by nothing
status: closed
caused_by:
changelog: `check pm` names the close a tree is ready for and never ran — a story carrying `done:` evidence that is not done, a feature whose stories are all done with no review record, a feature whose record is fully dispositioned but not closed — each on a counted `CLOSE` WARN line with the one next command, and `pm status` marks the same grains.
---

# a close the tree is ready for is named by nothing

Found building 0.8.0 on 2026-09-11. After 1h8m, 15 stories carried a `done: <hash> — …` evidence
line and committed code, and 0 were `done`. Four features had every story finished, and review
records were landing, while every feature still read `building`. `check pm` passed quietly the whole
time. The belts are pull-only by design (rule 9): a belt's `next:` lines print only after the belt
runs, so a belt that is NEVER run tells nobody anything. **Rule 11: absence is a named line.**

## What the tree already holds, and nothing reads

Each of these is a fact in the files, not a judgement:

1. a story whose document carries a `done:` evidence line (the story belt's `evidence-written`
   input) while its status is not in the `done` category;
2. a feature in an `in_progress` state whose every story is in the `done` category, with no
   `reviewed:` record; its next act is the review;
3. a feature whose `reviewed:` record exists and parses, where no finding sits at
   `disposition: open`, while the feature is not `done`; its next act is `close feature`.

## Fix

One counted line per case in `check pm`'s WARN family (never the exit code), each naming the grains
and the ONE command that is the next act (`close story <id>` / `pm feature reviewing <id>` +
dispatch a review / `close feature <id>`), the same shape as the handoff WARN. It reads what the
belts read, through their own functions (`evidence-written`, `stories-done`, `review-recorded`,
`findings-landed`), never a second grammar. `pm status` marks the same grains inline, the way it marks
`<WARN: …>` today.
