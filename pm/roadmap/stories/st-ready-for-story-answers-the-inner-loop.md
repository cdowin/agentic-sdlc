---
id: st-ready-for-story-answers-the-inner-loop
kind: story
feature: ft-a-rung-has-an-entry-edge
milestone: "ms-a-move-is-an-event"
name: ready-for story answers the inner loop
status: done
owner:
depends_on: []
---

# ready-for story answers the inner loop

`agentic-sdlc pm ready-for story <story-id>` answers *may I start* as an exit code: 0 ready, 1 not
ready with every blocker NAMED, 2 usage. It is the rung an agent runs dozens of times a milestone
and it was the only belt with no machine-readable entry edge — the alternative was to guess, or to
parse prose written for a human.

**What it asks is DECLARED, never spelled in this package.** The condition is derived at runtime
from three sources and nothing else: `driver.step_names('story')` for the project's own
`[story] steps`, `driver.registry_for('story')` for the check objects, and
`steps.ENTRY_CONDITIONS` for which of those the registry declares decidable before the work. A
project that narrows its `[story] steps` gets its own list answered back:

    READY — story st-…: 1 of 4 [story] check(s) decidable before the work
    (story-exists), all true; 3 at the close: story-verified (answers after the
    work, by `agentic-sdlc verify --story`), committed …, evidence-written …

The second clause is rule 11 at the surface: every check this rung did NOT ask is named with why,
because silence about a check teaches a reader the belt has one.

## Acceptance criteria

1. `pm ready-for story <id>` exists and reaches all three exit codes correctly — 0 ready, 1 not
   ready naming each blocker, 2 usage — beside the three shipped kinds.
2. **The condition is derived from those three runtime sources, never from a list in
   `ready_for.py`.** A tree that declares its own `[story] steps` is answered about ITS list.
3. Every declared check this rung did not ask is NAMED in the census with why, and a check
   excluded because it is not an entry condition is described as what the derivation actually
   knows — *not declared an entry condition* — rather than as a decidability claim the verb never
   made.
4. A tree whose whole declared list answers only after the work is exit 1 saying **nothing was
   asked**. A READY over a census of zero is rule 4's first sin, and it is refused.
5. An id that resolves to no story is the belt's OWN check at exit 1 — `story-exists`, carrying the
   sentence `close story` prints — never exit 2, because two rulings over one fact is what this
   package deletes.
6. Every rung emits `rung.enter` — `{rung, grain, ready, blockers}` — to the sink `[emit]` declares,
   and nothing at all on a tree that declares none.
7. **Emission is never load-bearing.** Neither the exit code nor one printed byte moves when the
   sink is malformed, escaping, unwritable, or names a tap this version does not emit. The finding
   goes to stderr in `emit`'s own prefix.
8. The three shipped rungs' output shapes are unchanged, and the verb still writes nothing.
9. `ready-for adopt` is not built, and the refusal SAYS SO by name rather than reading as a typo
   (D4).

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | unit | `StoryBelt::test_the_condition_comes_from_the_registry_and_the_census_names_the_rest` | new |
| 2, 4 | unit | `StoryBelt::test_a_project_that_declares_its_own_steps_gets_its_own_answer` — two trees, `1 of 2` and `0 of 2` + `nothing was asked` | new |
| 5 | unit | `StoryBelt::test_a_story_that_resolves_to_nothing_is_the_belts_own_blocker` | new |
| 6 | unit | `StoryBelt::test_rung_enter_is_emitted_by_every_rung_and_changes_neither_answer` | new |
| 7 | unit | `StoryBelt::test_a_broken_emit_is_a_finding_on_stderr_and_never_the_answer` — four failure classes, `(code, stdout)` tuple-equal against a quiet tree | new (review E4) |
| 8 | unit | `FeatureBelt`, `MilestoneBelt`, `TagBelt`, `NothingIsWritten` — they assert the TEXT, so a shape change fails them | existing, unmodified |
| 9 | unit | `ArgvRefusals::test_every_argv_shape_exits_2` and `::test_an_unknown_kind_names_the_closed_set` | amend — one row, `adopt` |

## Out of scope

- **`ready-for adopt`.** Recorded as D4 in `ms-a-move-is-an-event-decisions.md`: every one of the
  eight `DEFAULT_ADOPT_STEPS` fails the derivation, so the entry set is empty and the verb could
  only ever exit 1. The refusal names it; nothing was built.
- **The drive-the-loop case** the feature's ship criterion calls its real test. It needs
  `rung.leave`, which nothing in `src/` emits yet — `ft-one-event-shape-serves-three-readers`
  declares the shape and `ft-a-move-emits-the-breadcrumb-it-prints` emits it. Deferred by name in
  the feature's Out of scope.
- Any refusal. `ready-for` reports and the caller decides.
- A config key by which a project declares its own entry condition. `ENTRY_CONDITIONS` is one
  package ruling over a name space this package closes.

## Close

done: a4545c2 — `_entry_condition` composes `[story] steps` × `registry_for` × `ENTRY_CONDITIONS`
at every call; five configurations probed in review and no path found where a literal wins.
`ready-for adopt` declined and recorded (D4), and the unknown-kind refusal now names it with why.
finding: emission's swallow was correct and untested — the case landed against review E4.
