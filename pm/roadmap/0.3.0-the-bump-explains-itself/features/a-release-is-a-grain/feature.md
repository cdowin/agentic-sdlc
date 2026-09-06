---
id: 0.3.0/a-release-is-a-grain
milestone: "0.3.0"
name: A release is a grain, and the plan is its order
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# A release is a grain, and the plan is its order

The package has no concept of a release. It has a `release` BELT, a `[pm] version_file`, and D8
saying the project version equals an in-progress milestone's id — three facts about versions and
nothing that *is* one. So a version cannot be planned, ordered, or pointed at.

**Two artifacts, one job each.**

`pm/roadmap/releases/<version>.md` — a grain like any other. Frontmatter carries the version as
its id, a name, and a `status:`; the body carries the release's GOAL, which is forward-looking
prose about what this release wants to do. Not a changelog: a changelog is written at the end from
the grains that shipped, and `changelog-writer` already does that.

`pm/roadmap/releases.toml` — the ORDER, and nothing else:

```toml
order = ["0.1.0", "0.2.0", "0.3.0"]
```

**Why the order is not in the grains.** Filename order is string order, which is the defect this
work exists to remove — `0.90.10` sorts before `0.90.4`, and on this very tree `0.1.0` sorts first
while `0.2.0` has shipped. A `seq:` field makes insertion a renumbering. An ordered list makes
inserting a release a one-line edit whose diff shows exactly where it went.

**Why the order is not in `devkit.toml`.** Config is how a project WORKS. A release plan is
content — it changes weekly. It belongs in the tree with the work it sequences.

**Why the tool never writes `releases.toml`.** `tomllib` is stdlib and READ-ONLY, and this package
is stdlib-only at runtime (hard rule 1). A design that writes TOML hand-rolls a serialiser. This
one does not have to: the order is a human decision, hand-edited, and everything the tool writes
is frontmatter — the one format the CLI already rewrites a line of while preserving every other
byte.

**`[pm.states.release]`** joins the other three, seeded by `pm init`, with no default behind it
like the rest. The honest cost is a fourth table every consumer declares, which is real adoption
friction of exactly the kind that just cost a consumer its PM CLI — mitigated only by the seed, so
the seed had better be right.

`pm new release <version> [<name...>]` scaffolds the grain and reports that the version is not yet
in `order`. `pm release <state> <version>` moves it, through the same code path as
`pm story <state> <id>`.

## Ship criterion

A release is a grain the tree holds, with a state, a name and a goal; `releases.toml` declares the
sequence and the tool only ever reads it; `pm new release` and `pm release <state>` work like every
other kind; and `[pm.states.release]` is in the `pm init` seed with its categories argued where it
sits, the way the other three are.

## Proof budget

  cases: 5-6
  tier: pyunit
  lands in: `test_pm_scaffold.py` for the new kind, `test_pm_verbs.py` for the state write,
    `test_pm_flow.py` for the fourth states table
  what already covers this: the three existing kinds are covered end to end and the machinery is
    shared, so most of this is a fourth row through paths that already have cases. The genuinely
    new surface is `releases.toml` — one reader, and a refusal for an entry naming no grain.

## Out of scope

Anything that reads the order to answer a question — `pm roadmap`, `pm next` and the cross-checks
are `the-plan-and-the-tree-agree`. This feature lands the objects.
