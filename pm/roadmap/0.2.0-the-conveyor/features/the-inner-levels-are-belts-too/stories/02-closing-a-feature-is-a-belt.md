---
id: 0.2.0/the-inner-levels-are-belts-too/02-closing-a-feature-is-a-belt
feature: 0.2.0/the-inner-levels-are-belts-too
milestone: "0.2.0"
name: A feature closes only when its stories are done and its findings are landed
status: done
owner:
depends_on: []
---

# A feature closes only when its stories are done and its findings are landed

<!-- What is observable when this ships. A story is an observation, not a task. -->

## Acceptance criteria

<!-- Filed 2026-09-05 against I4. Sourced from the title, feature.md's ship criteria 3-4 and
     risk 1, and the Close evidence below, in D8's voice: reported, never a halt. -->

1. `agentic-sdlc close feature <id>` walks six declared steps — `stories-done`,
   `feature-reviewing`, `feature-verified`, `review-recorded`, `findings-landed`,
   `feature-done` — read from config, in order.
2. `stories-done` IS `pm ready-for feature`, called as the published verb. **No step
   re-implements a predicate that already has one**, because a second implementation of
   "is this feature ready" is a second scoreboard and it will disagree.
3. A feature whose stories are not all `done` is reported with EACH open story named and its
   current state, at the step that found it, and the run finishes.
4. `review-recorded` and `findings-landed` are `verdict.parse` and inherit its ruling whole: a
   missing record, an unparseable block or a finding still at `disposition: open` comes back
   UNVERIFIABLE, which is never a pass.
5. The review-record pointer is refused BY SHAPE — a `/`, `~`, `\`, a scheme or a `..` in it is
   a malformed declaration, and refusing facts about the input is reading, not deciding.
6. Nothing claims to judge whether a review was any good (risk 1). `review-recorded` checks that
   the artifact exists and parses, and says exactly that in its `do()` text, its docstring and
   its `STEP_DOC` row — a step that pretended otherwise would be this package's cardinal sin
   wearing a protocol.

## Out of scope

- Judging whether the review was any good: `review-recorded` checks that a record exists and
  parses, and nothing more (feature.md risk 1).
- Re-implementing `pm ready-for feature` or `verdict.parse`; the steps call them.
- Closing the stories themselves: `feature-done` moves the feature, and each story closed
  through story 01's belt.

## Close

done: cc0569d — six steps, and no step re-implements a predicate that has a verb:
stories-done IS `pm ready-for feature`, review-recorded and findings-landed ARE
`verdict.parse`, inheriting its ruling that an unparseable block is UNVERIFIABLE.
