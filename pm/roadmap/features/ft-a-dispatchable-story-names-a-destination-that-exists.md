---
id: ft-a-dispatchable-story-names-a-destination-that-exists
kind: feature
milestone: 
name: a dispatchable story names a destination that exists
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a dispatchable story names a destination that exists

**Pool, unplanned.** Chris, 2026-09-18, on a consumer's local destination gate: *"maybe worth
adopting in sdlc?"* Filed from #62, which was closed here because the script is the consumer's.

## The shape a consumer hand-rolled

A consumer wrote a 491-line shell gate: a story a developer can be dispatched against (a story
`ready`/`building` under an open milestone) must cite a DESTINATION, and the cited file must EXIST.
What counts as a destination depends on the story's class, read from the paths its Scope names:

    class     scope names a path under…        must cite an existing…
    surface   the project's UI roots           wireframe, or a `## Destination` section of N+ lines
    art       asset roots, with an asset ext   reference asset or capture
    default   anything else                    spec section or decision D-number

A stronger citation satisfies a weaker class. `planning` and `done` stories are not graded.

## Why it may belong here

Rule 11: the need is general ("a developer needs a destination"), and a consumer had to hand-roll
it. Rule 9 holds if every class, root, extension and citation directory is DECLARED in
`devkit.toml` and the gate only checks that a declared citation resolves to a file. It must never
judge whether the destination answers the story.

## Open questions (decide at planning)

- Is it a `check` gate, a `[story] steps` entry-condition check (`ready-for story`), or both?
- Config shape: `[story.destination.<class>]` with `roots`, `extensions`, `cites` (dirs or
  patterns), `min_lines` for an authored section. A WORKFLOW key (no stock default, refused by
  name when absent) or off-by-default?
- Is "a stronger citation satisfies a weaker class" an ordering in the declaration, or a rule?
- Citation spellings (a markdown link, a bare path, `wireframe <NN>`): only the first two are
  generic. A numbered alias is project vocabulary.

## Ship criterion

<!-- At planning. -->

## Proof budget

  cases:
  tier:
  lands in:
  what already covers this:
