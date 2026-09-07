Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# 0.3.0/a-milestone-declares-its-version A milestone declares the version it ships as, and its id goes back to being a name — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-06 — D9 and D10 stay as they are; only D8 was welded to the version

The ship criterion says *"D8/D9/D10 either read `version:` or are retired BY NAME"*, offering two
outcomes. The right answer for D9/D10 is a third: **neither, because they never touched a version.**

D9 (an in-progress milestone declares `branch:`) and D10 (that branch is not the mainline) read
`branch:` and the `in_progress` category. Neither reads a version, an id-as-version, or anything
`version:` separates. **D8 was the only rule that welded the version to the id**, and it is the only
one that had to move.

Rejected: retiring D9/D10 alongside D8 for symmetry. They encode branch discipline, which this
package still runs and D3 (0.16.0) exists because it caught this tree working on main. Retiring a
live rule to make a sentence scan is the tool losing a gate to tidiness.

Rejected: making them read `version:`. There is nothing for them to read it FOR — a branch is not
a release, and coupling them would rebuild the weld R5 just removed.

Raised as review finding F11 (`docs/reviews/0.3.0-a-milestone-declares-its-version.md`): the reading
was correct and unrecorded, and an unrecorded deviation is the finding.
