---
id: 0.2.0/the-inner-levels-are-belts-too/03-the-belt-above-refuses-to-start
feature: 0.2.0/the-inner-levels-are-belts-too
milestone: "0.2.0"
name: Each belt refuses to start until the belt below it has finished
status: planning
owner:
depends_on: []
---

# Each belt refuses to start until the belt below it has finished

<!-- What is observable when this ships. A story is an observation, not a task. -->

## Acceptance criteria

<!-- Filed 2026-09-05 against I4. Sourced from the title, from feature.md's "the belts wire to
     each other through the verbs that already exist" and its ship criteria 5-6, and from the
     Close evidence below.
     THE TITLE IS THE PART THE RE-SCOPE CHANGED. feature.md's banner rules the halt out: a belt
     no longer refuses to start, it names what the belt below left open and finishes. The ORDER
     is still the whole deliverable — what changed is who acts on it. -->

1. Each belt asks the belt below it through the verb that already answers: `close feature`'s
   `stories-done` IS `pm ready-for feature`, `release`'s `features-done` IS
   `pm ready-for milestone`. The wiring is a call, never a re-derivation.
2. A belt started over unfinished work below it NAMES what is open — each grain and its state,
   at the step that found it — and finishes. It reports the fact; whether that fact is a
   descope, a hotfix or a mistake is a question this package cannot ask (hard rule 9).
3. The report is loud enough to be acted on without reading the tree: the 28 stories parked at
   `reviewing` while `pm ready-for milestone` answered NOT READY for hours are the measured
   cost of this being prose, and prose is what it takes to not notice a verb telling you.
4. `install-sdlc` renders ALL FOUR step lists — `release`, `adopt`, `story`, `feature` — so the
   generated protocol is the whole SDLC and not just its outer half, and every registered step
   carries a postcondition sentence rather than the placeholder.
5. The generated protocol is byte-current in this repo, held there by a test: a contract that
   drifts from the machine it describes is worse than none.
6. **The belts' own first run is not performed by hand** (ship criterion 6): 0.2.0's own stories
   and features close through these verbs, because a belt whose first run was hand-driven has
   not been tested.

## Out of scope

<!-- Left empty deliberately — see story 01. -->


## Close

done: cc0569d — proven live on this milestone: `close feature` stopped at step 1/6 naming
three stories at `reviewing`, and `close story` stopped at evidence-written refusing to
write the author's sentence.
finding: the run state CORRECTED itself against the tree mid-run and said so — the cache-is-
never-the-authority rule firing outside a test.
