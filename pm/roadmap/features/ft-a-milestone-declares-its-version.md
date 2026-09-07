---
id: ft-a-milestone-declares-its-version
milestone: ms-0.3.0
name: A milestone declares the version it ships as, and its id goes back to being a name
status: done
reviewed: docs/reviews/0.3.0-a-milestone-declares-its-version.md
phase:
depends_on: []
consumed_by: []
kind: feature
order:
  - "st-a-milestone-declares-a-version"
  - "st-r5-grades-the-current-release"
  - "st-no-code-path-parses-a-version"
---

# A milestone declares the version it ships as, and its id goes back to being a name

**The milestone already IS the release.** `accepted` and `packaging` are milestone-only states —
words that mean nothing for "a coherent body of work" and everything for a release. It carries
`branch:`. `release <version>` writes its status. D8 welds the project version to its id. A first
draft of this work proposed a separate release grain; that was a second name for a fact the tree
already holds, and the nearest existing construct serves.

What it lacks is **one field**:

```yaml
id: stationary-enemies-spawn
version: "0.91.0"
```

**The id becomes a slug and the version becomes a fact.** Today they are the same string, and the
cost is visible in any tree that subdivides work: NullBound has `0.90.3.2`, `0.90.4.1` and
`0.90.4.2` — four-component versions not because four patches shipped, but because inserting work
between two planned milestones had no mechanism except contorting the number. `0.90.3.2` is not
valid semver, so no comparator the engine could ship would sort this repo's own tree.

**The string does not matter, and the engine proves it by never reading one.** Not to compare two,
not to sort, not to suggest the next. `"1.1.1"` and `"cow"` are equally valid. Ordering comes from
the declared list (`the-order-is-declared-and-appended`), so "did the version increase" is a
position, and scheme-agnosticism is a consequence of that rather than a promise.

**D8 becomes R5.** The version file equals the CURRENT milestone's `version:` — current being a
declared position, not a parse:

```toml
[pm]
version_at = "start"   # the first milestone in `order` that has not shipped
# version_at = "ship"  # the last one that has
```

`start` is the default and what `pm init` seeds, because bump-at-start is what the tree that
motivated this work does and a default matching nobody is friction on day one.

**A milestone with no `version:` is backlog** — it has not been proposed as a release at all. That
is the parking lot: no state, no directory, no declaration. Its counterpart, a milestone that
named a version nobody scheduled, is a finding and belongs to `the-plan-and-the-tree-agree`.

## Ship criterion

`version:` is read on a milestone, optional, and any non-empty string. R5 grades the version file
against the current milestone's `version:` and names both when they disagree; `[pm] version_at`
selects it and defaults to `start`. D8/D9/D10 either read `version:` or are retired BY NAME with
the CHANGELOG saying which — a consumer whose config still lists D8 is told where it went, never
silently ungated. No code path parses, compares or increments a version string, and a test asserts
that over the source.

## Proof budget

  cases: 4 declared; 17 shipped — the review's F1/F2 semantics each needed a case, and the
    source-shaped no-parser gate is a class the budget did not anticipate (finding F9, accepted)
  tier: pyunit
  lands in: the gate-rules module, beside the existing D8 cases
  what already covers this: D8 has match / mismatch / unreadable-file cases, all of which extend
    to R5 by changing where the expected value is read FROM. New: `version_at` both ways, and the
    no-parser assertion, which is a grep-shaped test over the source.

## Out of scope

Renaming any milestone directory, here or in a consumer. `version:` makes an id free to be a slug;
becoming one is each project's own day of work.
