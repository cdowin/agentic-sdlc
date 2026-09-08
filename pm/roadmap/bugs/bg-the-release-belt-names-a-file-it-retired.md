---
id: bg-the-release-belt-names-a-file-it-retired
kind: bug
milestone: "ms-the-rule-reaches-the-work"
name: the release belt names a file it retired
status: closed
caused_by: ft-the-changelog-is-a-field-and-a-verb
changelog: The `release` belt's first `next:` line pointed at `CHANGELOG.md`'s `## Unreleased` section, which this release retires; it now names `agentic-sdlc changelog <milestone-id>`, and `docs/sdlc-protocol.md` re-renders from the same list.
---

# the release belt names a file it retired

**Found by running the belt.** `agentic-sdlc release 0.6.0` passed every check, wrote the milestone
`done`, and then printed:

    next: retitle the changelog: `## Unreleased` becomes `## v0.6.0 — <ISO date>`,
          with a fresh empty `## Unreleased` above it
    next: commit the roadmap directory and the changelog as the release commit

There is no changelog file. `ft-the-changelog-is-a-field-and-a-verb` deleted `CHANGELOG.md` earlier
in this same milestone.

## Root cause

`steps.AFTER['release']` is a tuple of `next:` lines and nothing gated it against the retirement.
The feature that retired the file swept the README, `SDLC.md`, the release skill and three agent
definitions — and missed the belt's own output, which is the one surface an operator is standing on
at the exact moment the instruction applies.

`tests/test_conveyor_driver.py` asserted the list by keyword and one of the keywords was `retitle`,
so the test pinned the stale line in place rather than catching it.

## Why it is worth a grain rather than a quiet edit

**It is `bg-the-shipped-rules-name-retired-behaviour` on a new surface.** That bug was about two
files `pm install-skills` writes into every consumer telling an operator to maintain `ROADMAP.md`.
This is the same shape one layer in: a `next:` line is an instruction, it ships to every consumer,
and it is read at the moment it is least likely to be questioned — the belt just said `ok`, so the
lines after it carry the belt's authority.

`test_no_installable_names_a_retired_thing_except_as_a_migration_note` sweeps the INSTALLABLES for
retired names off the code's own registries. It does not sweep `steps.AFTER`, because those lines
are code rather than a shipped file. That is the gap, and it is worth naming even though this fix
does not close it: the retirement registry exists, and a second reader of it would have caught this.

## Fix

The line names `agentic-sdlc changelog <milestone-id>` and says the notes come off each grain's
field in the milestone's declared `order:`, with no file maintained. The second line drops "and the
changelog". `docs/sdlc-protocol.md` is RENDERED from this list and re-rendered with it, which is why
that document has never drifted and this line did.

The keyword assertion is amended: `retitle` becomes `changelog`, and a new assertion refuses
`Unreleased` anywhere in the belt's `next:` lines — so the retired name cannot come back through the
door it left by.

## Out of scope

Sweeping `steps.AFTER` against the retirement registries the way the installables are swept. It is
the right fix for the CLASS and it is a new reader, not a wording change; filed here as the gap
rather than built at a close.
