---
id: 0.3.0/the-release-belt-closes-a-release
milestone: "0.3.0"
name: The release belt writes the release, not somebody else's status
status: planning
reviewed:
phase:
depends_on: ["0.3.0/a-release-is-a-grain", "0.3.0/anything-can-name-its-release"]
consumed_by: []
---

# The release belt writes the release, not somebody else's status

A belt is its checks, then ONE write (D12). `close story` writes the story. `close feature` writes
the feature. **`release <version>` writes a MILESTONE** — because until now there was no release
for it to write, so the belt named after the thing reached into the nearest grain that had a
status. It is the one belt whose write is not its own subject, and it reads as an accident because
it is one.

With a release grain, the belt closes what it is named for.

**`release` with no argument means the next one.** `order` plus `version_at` already answer "which
release is current"; asking the human to retype it invites the two to disagree. A version given
explicitly is still honoured, and one that is not the current release is a refusal that names
both — shipping out of order is exactly the kind of thing a belt should stop.

**Its checks widen to what a release now knows.** Today `ready-for milestone` and `ready-for tag`
ask about one milestone. A release may carry several grains, or a feature and a hotfix bug, so the
entry condition becomes: every grain naming this release is in a `done` category, every review
record parses, no finding is open. Same three questions the existing `ready-for` family asks —
asked of the release's members instead of one milestone's children.

**What it still does not do.** Tag, push, publish. Those are git and they are the human's, and the
belt prints them as `next:` lines the way it does now. The one write is the release's status.

## Ship criterion

`release [<version>]` runs its checks over every grain naming that release and writes the
release's status to the first state of `[pm.states.release] done` — nothing else. No argument
takes the current release from `order`; a version that is not current is refused naming both. A
milestone's status is moved by the milestone's own belt, never by this one. `ready-for release
<version>` answers the entry condition as an exit code, beside `ready-for feature|milestone|tag`.

## Proof budget

  cases: 4-5
  tier: pyunit
  lands in: the release-belt test module, beside the existing check-list cases
  what already covers this: the belt's check list, its refusal shape and `--force` are covered end
    to end; the changes are what the checks ask and what the write targets, so most cases move
    rather than arrive. New: no-argument resolution, and the out-of-order refusal.

## Out of scope

`ready-for tag`, which asks a question about findings and is unchanged. And retiring
`ready-for milestone` — a milestone still has an entry condition of its own, whether or not a
release carries it.
