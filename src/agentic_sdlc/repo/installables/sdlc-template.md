# The protocol, as the machine runs it

<!-- Written by `agentic-sdlc install-sdlc`. Do not hand-edit: the ordered
     lists below are RENDERED from `[story]`, `[feature]`, `[release]` and
     `[adopt]` steps in this repo's devkit.toml and from the step registry
     that walks them, so
     the only way to change them is to change the config or the code and
     re-run the verb. A hand-written document describing the steps is the
     second home for the protocol, and a second home drifts — which is the
     failure this file exists to end. -->

Run it — one verb per level, and none of them is "run the biggest thing":

```
agentic-sdlc close story   <story-id>      the inner loop, seconds
agentic-sdlc close feature <feature-id>    once its stories are done
agentic-sdlc release       <version>       once its features are done
agentic-sdlc adopt         <version>       a devkit pin bump, scoped to the adoption
```

It walks the list below in order **to the end**, and for every step whose
postcondition is not true it says so by name and says what would make it
true. It is resumable: the position is a cache under `.agentic-sdlc/run/`,
every step is re-checked against the tree on every run, and deleting that
file costs nothing. Exit `0` every postcondition holds, `1` one or more do not
(the walk still finished), `2` a usage or config error — the declaration
could not be read, before the walk or at the step whose reader met it.

Three kinds of step, and the third one is the honest limit:

- **AUTOMATIC** — code performs it, then re-asks the postcondition. `do()`'s
  own report is never what marks it done.
- **GATE** — a command; exit 0 is true. It has no `do()`, because a gate is not
  made true by running it again.
- **JUDGEMENT** — code cannot perform it. It reads the ARTIFACT of a judgement,
  or a command the project configures. With neither, it answers UNVERIFIABLE,
  which is never a pass and is counted apart from a plain no.

**No step halts the walk.** Every step is a check, every check reports, the run
reaches its last step whatever any check said, and the final line is a
scoreboard: `19/21 true · 1 not true: gate`. Whether a not-true step should
stop you is YOUR question — the engine cannot know whether it is wrong
(descoped? a hotfix? deliberate?), and a machine that blocks on a question it
cannot ask is asserting an answer. `agentic-sdlc check <gate>` is the thing
that FAILS a tree, in CI and pre-push, with an exit-code contract for exactly
that.

Every step that is not true is written to the milestone's `ledger.jsonl` as a
`deviation` row carrying the reason the step itself gave. Deviation stays
possible; invisible deviation does not. `--status` prints what has been
recorded.

<!-- STEPS -->

<!-- GUIDANCE -->

## Changing this document

Edit `[release] steps` (or `[release.commands]`) in `devkit.toml` and re-run
`agentic-sdlc install-sdlc --force`. There is nothing to edit here: every line
of the lists above is derived from the config and the registry that runs it.
