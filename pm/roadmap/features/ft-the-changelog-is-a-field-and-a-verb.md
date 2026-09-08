---
id: ft-the-changelog-is-a-field-and-a-verb
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: the changelog is a field and a verb
status: done
reviewed: docs/reviews/2026-09-07-0.6.0-the-changelog-is-a-field-and-a-verb.md
depends_on: []
consumed_by: []
changelog: BREAKING: CHANGELOG.md is retired — the changelog is a `changelog:` field on every grain and `agentic-sdlc changelog [<id>] [--json]` renders the entries beneath one, in the `order:` the parent declares. `release` now refuses when a closed grain answered neither a sentence nor `none`, naming the grain instead of counting bullets in a file.
---

# the changelog is a field and a verb

**`CHANGELOG.md` goes the way of `ROADMAP.md`, and for the same reason.** 0.3.0 retired the roadmap
file because `order:` on the tree plus `pm roadmap` said the same thing without a second copy to keep
in agreement. The changelog is the last hand-maintained scoreboard left.

    changelog:   a FIELD on any grain — feature, bug, story, milestone
    changelog    a VERB that collects them over an input set and renders

## The evidence is this milestone's own file

0.5.0's `## Unreleased` is **469 lines written by roughly twelve different agents**, two of whom
edited it concurrently and had to be told the other was there. Nobody owns it. Nothing binds an entry
to the grain it describes, so:

- an entry can survive a grain that was retired, and nothing notices
- a grain can close with no entry, and nothing notices
- the ORDER is whatever order agents appended in, not the order the work shipped in — the milestone's
  `order:` already knows the real sequence and the file cannot see it
- two agents writing at once is a merge conflict in a file that carries no code

Every one of those is the defect this package deletes everywhere else: **one fact stored twice, in a
place that cannot check itself against the other.**

## The shape

A grain's `changelog:` is the consumer-visible sentence that grain earned. Most stories have none —
they are internal. A feature usually has one. A bug has one if a consumer would notice.

`agentic-sdlc changelog [<grain-id> | <milestone-id> | --from <rev>]` collects the entries of the
grains the argument names, **in the order `order:` already declares**, and renders. Ad hoc, at any
level, exactly like `pm ledger report` and `pm roadmap` — the tree is the source and the document is
a view.

**The release check gets better, not weaker.** `changelog-unreleased-nonempty` grades a FILE for
being non-empty, which is nearly no assertion at all. It becomes: every grain closing in this
milestone either carries a `changelog:` or has said it needs none. That is per-grain, actionable at
the rung it fires on, and it names the grain rather than the file — which is
`ft-a-warning-is-actionable-where-it-fires` applied to the release belt.

## What this does NOT mean

**Not a rendered `CHANGELOG.md` committed to the repo.** That would be the same second scoreboard with
a generator attached — the file would still drift the moment somebody edited it, and `docs/sdlc-
protocol.md` only survives because a gate holds it byte-current. If a consumer wants a file, they run
the verb and redirect it; the release ceremony's `next:` lines can say so.

**Not history rewriting.** Shipped releases keep whatever `CHANGELOG.md` recorded, the way retired
milestones keep their ledger rows under their old ids. This changes what the tree does NEXT.

## Ship criterion

`changelog:` is a declared field on every grain kind, absent by default, and `check pm` names a grain
that closed without one and without saying it needed none.

`agentic-sdlc changelog <id>` renders the entries beneath that id in `order:` sequence, at any level,
`--json` included, columns named in order in `--help`.

`release`'s changelog check grades grains, not a file. `CHANGELOG.md` is retired from the installables
and from this repo's own tree, and the retirement is named in the sweep so a consumer bumping the pin
is told where it went rather than finding it missing.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_pm_verbs.py` for the field, a new render module beside `test_pm_ledger_report.py`
  what already covers this: `pm roadmap`'s render cases are the nearest shape — this is the same
    collect-and-render over a different field, so they are rows on that harness rather than a new family.

## Out of scope

Choosing a consumer's changelog FORMAT. The verb renders what the tree holds; a project that wants
Keep-a-Changelog headings declares them, the way `[pm.states.*]` declares its words. Rule 9.
