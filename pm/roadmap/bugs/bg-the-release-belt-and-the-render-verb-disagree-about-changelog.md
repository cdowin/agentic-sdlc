---
id: bg-the-release-belt-and-the-render-verb-disagree-about-changelog
kind: bug
milestone:
name: release blesses a release note whose first sentence is missing, because its check asks a narrower question than changelog does
status: open
caused_by:
changelog: none
---

# the release belt and the render verb disagree about changelog

Found by the 0.7.0 milestone review (R1), on this tree, in exactly this state.

## Symptom

Two readers of one field give different answers about the same tree:

    $ agentic-sdlc changelog <milestone-id>
    … 14 entry/ies of 26 grain(s); 11 declined, 1 unanswered
                                                ^^^^^^^^^^^^ the milestone itself

    $ agentic-sdlc release <version>
    ok: changelog-unreleased-nonempty — … every closed grain answered

Reproduce on a scratch consumer: give every child a `changelog:`, leave the milestone's blank, run
both. The render verb counts the milestone and the belt does not.

## Root cause

**`changelog-unreleased-nonempty` asks "every CLOSED grain answered", and the milestone is not in a
`done` state when the check runs** — `release` is the verb that will put it there. So the sentence
is literally true and the check is right about what it asked. The defect is that what it asked is
narrower than what `changelog` renders, and the grain it passes over is the MILESTONE's — the one
sentence a consumer upgrading a pin reads first.

This is rule 11's shape rather than rule 4's: the belt does not lie, it stays quiet. A release note
whose top line is blank ships with a green `ok:` beside it.

## Fix

`changelog-unreleased-nonempty` asks the question `changelog` asks: every grain the render verb
would count, the milestone included, carries a sentence or the word `none`. `none` stays a legal
answer — the field separates *decided* from *forgotten* and that is the whole point of it.

The one thing to get right: the milestone is `in_progress` at the moment the belt runs, so the check
cannot key on `done`. It keys on **the grain the release is FOR**, which `release <version>` already
resolved to get there.

## How to see it fail

The scratch consumer above, as a case: a tree whose milestone has an empty `changelog:` and whose
every child has one. `release` exits 0 today; it should name the milestone and exit 1.

## Out of scope

Whether a `none` is TRUE — that a grain declining a sentence really changed nothing a consumer sees.
That is judgement and a gate asserting it would be the second scoreboard. 0.7.0 declined 11 and each
was read at the milestone review; none was mechanically graded.
