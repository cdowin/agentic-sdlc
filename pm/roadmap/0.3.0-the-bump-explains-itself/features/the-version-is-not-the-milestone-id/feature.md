---
id: 0.3.0/the-version-is-not-the-milestone-id
milestone: "0.3.0"
name: The version is a release's, not a milestone's
status: planning
reviewed:
phase:
depends_on: ["0.3.0/a-release-is-a-grain", "0.3.0/anything-can-name-its-release"]
consumed_by: []
---

# The version is a release's, not a milestone's

D8 says the project's version file must equal an in-progress milestone's ID. That makes the
milestone id and the shipped version **the same string**, and the cost shows up in any tree that
subdivides work. NullBound's milestones are `0.90.3.2`, `0.90.4.1`, `0.90.4.2` — four-component
versions not because four patches shipped, but because the WORK subdivided and the id had to
absorb it. The version number is carrying plan structure.

Once a release is a grain and grains name it, the coupling has nothing left to do. D8 becomes:

**R5 — the version file equals the CURRENT release's version.** Which release is current is a
declared position, not a parse:

```toml
[pm]
version_at = "start"   # the first release in `order` that has not shipped
# version_at = "ship"  # the last release that has
```

`start` is the default and what `pm init` seeds, because bump-at-start is what the tree that
motivated this work does and a default that matches nobody is friction on day one.

**The tool never parses a version string.** Not to compare two, not to sort, not to suggest the
next one. That is what makes the scheme the project's — semver, a counter, a date, a codename. The
question D8 and CI actually ask is *did the version increase*, and once `order` exists that is
answered by **position in the list**: no parser, no version-compare, and no `0.90.10`-sorts-before-
`0.90.4`. The scheme-agnosticism is not a shrug; it is a consequence of getting the ordering from
the right place.

A milestone id goes back to being a name. `0.90.4.2-stationary-enemies-spawn` can become
`stationary-enemies-spawn` and the version it ships in is a `release:` line — one string, in one
place, that says what it means.

## Ship criterion

`[pm] version_at` selects the current release from `order`, defaulting to `start` and seeded that
way. R5 grades the version file against that release, naming both when they disagree. D8/D9/D10
either read the release grain or are retired by name, with the CHANGELOG saying which — a consumer
whose config still names D8 is told where it went, never silently ungated. No code path parses,
compares or increments a version string, and a test asserts that.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: the gate-rules module beside the existing D8 cases
  what already covers this: D8 has cases for match, mismatch and an unreadable version file — all
    extend to R5 by changing what the expected value is read FROM. Genuinely new: `version_at`
    both ways, and the no-parser assertion, which is a grep-shaped test over the source.

## Out of scope

Changing any project's version scheme. This removes the tool's opinion; adopting a counter is a
consumer's decision and a separate day's work in that consumer's tree.
