---
id: 0.2.0/the-inner-levels-are-belts-too/01-closing-a-story-is-a-belt
feature: 0.2.0/the-inner-levels-are-belts-too
milestone: "0.2.0"
name: A story closes through a step list that refuses to advance
status: planning
owner:
depends_on: []
---

# A story closes through a step list that refuses to advance

<!-- What is observable when this ships. A story is an observation, not a task. -->

## Acceptance criteria

<!-- Filed 2026-09-05 against I4 (docs/reviews/2026-09-05-the-inner-levels-are-belts-too.md):
     this section shipped EMPTY, so nothing in the tree said what the story was FOR — which is
     the thing a feature review reads a `## Close` block against. Sourced from the title, from
     feature.md's ship criteria 1-2 and risk 2, and from the Close evidence below.
     WRITTEN IN THE RE-SCOPED VOICE. feature.md's banner rules that every "refuses" in that
     record now reads "warns, names what is open, and finishes" — the report-never-refuse
     ruling, hard rule 9. Criteria in the old voice would specify the halt this feature is
     being rebuilt to delete. -->

1. `agentic-sdlc close story <id>` walks the five declared steps in order — `claimed`,
   `narrow-verified`, `committed`, `evidence-written`, `story-done` — and the list is a
   declaration read from config, not a sequence spelled in the code.
2. A step whose postcondition is not met is NAMED with what is missing, and the run finishes
   and reports rather than halting the caller: the belt says where the story is, the caller
   decides what that means.
3. `narrow-verified` names no command of its own. It reads `[story.commands] narrow-verified`
   where the project declares one and otherwise asks `verify --story`, so the narrow command
   comes from `[verify]` — one ladder, not a second set of commands (D3).
4. The JUDGEMENT steps act on nothing. `committed` and `evidence-written` say what a human must
   do and why the machine is not doing it; the belt never commits and never writes the author's
   `done:` sentence.
5. Resumable, and the run state is never the authority: a state under
   `.agentic-sdlc/run/story.json` that contradicts the tree is corrected or discarded, and the
   correction is PRINTED rather than applied silently.
6. It is the SAME driver — `driver.OPERATIONS` grows by a row and nothing about the machine
   changes. A second step engine for the inner level would be a second scoreboard.
7. **Under a second**, measured across consecutive runs (feature.md risk 2): a story close
   slower than closing by hand is a conveyor people skip, and a skipped conveyor looks like
   control while being none.

## Out of scope

<!-- Left empty deliberately: nothing in this story's body or in feature.md draws a boundary
     here that could be written without inventing one, and a guessed exclusion is worse than an
     absent section. The rebuild fills it. -->


## Close

done: cc0569d — five steps, 0.21 s across three runs. The number is the feature: a story
close slower than closing by hand is a conveyor people skip, and a skipped conveyor is worse
than none because it looks like control. 55 of 56 tests watched failing at HEAD.
