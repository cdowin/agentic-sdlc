---
id: 0.3.0/the-plan-and-the-tree-agree
milestone: "0.3.0"
name: The plan and the tree are cross-checked, and ROADMAP.md retires
status: done
reviewed: docs/reviews/0.3.0-the-plan-and-the-tree-agree.md
phase:
depends_on: ["0.3.0/a-milestone-declares-its-version", "0.3.0/the-order-is-declared-and-appended"]
consumed_by: []
---

# The plan and the tree are cross-checked, and ROADMAP.md retires

A plan nothing checks is a document. `pm order --append` deliberately does not interrogate the
tree, so everything it could have refused arrives here instead — which is the package's own split
between what a verb refuses and what a gate reports.

The `R` family asks of the plan what the `V` family asks of the tree:

- **R1 — the pair.** An entry in `order` that no milestone's `version:` claims is DANGLING. A
  milestone with a `version:` that `order` does not carry is UNSCHEDULED. Symmetric, and both name
  the two places that disagree. An entry whose milestone directory was retired is UNVERIFIABLE,
  never a failure — the concept the tree already has for a ref into a retired milestone.
- **R2 — the unbound census.** A milestone with no `version:` is backlog: a named, counted line,
  never a finding. A healthy tree has many, and a gate that reddens on planning is a gate people
  switch off.

**R1 and R2 are written as THE UNBOUND FAMILY, whose first member is the milestone-to-release
edge** — not as two milestone-specific rules. Every level of the tree has the same pair: a binding
that names nothing, and a grain that names no binding. 0.4.0 makes authoring separate from binding
everywhere, at which point a feature with no milestone and a story with no feature join this
census as further rows rather than as new rules. Naming the family now costs a sentence; naming it
later costs a rename in every consumer's output that greps these lines.
- **R3** `version:` values are unique across milestones.
- **R4 — history is a prefix.** No shipped milestone appears after an unshipped one in `order`.
  This is the invariant that makes "next = the first unshipped entry" *correct* rather than merely
  usual, and it is what lets `version_at = "start"` mean anything.
- **R6** a `done` milestone that never shipped, and a shipped version whose milestone is not
  `done`. **This catches `0.3.0/bugs/the-first-milestone-never-closed` on its first run** — 0.1.0's
  work is in the mainline, went out inside `v0.2.0`, and its milestone has said `planning` ever
  since, because every existing rule asks a question INSIDE the tree and nothing related a
  milestone to a release.

**`pm roadmap` prints the plan** — the order, each entry's milestone, its state and whether it
shipped. What `pm status` does for one milestone, for the sequence. It writes nothing.

**`ROADMAP.md` retires.** It is two things wearing one name: a hand-maintained index of milestones
still in the tree — a second scoreboard, which the tool forbids one grain down — and the only
surviving record of milestones `pm retire` deleted. `pm roadmap` derives the first. The second
needs no file: `order` keeps the version and R1 reports it UNVERIFIABLE once the directory is
gone, so the row survives its milestone. `pm retire` stops appending; the CHANGELOG names the file
retired and names `pm roadmap` as its replacement, so a consumer is told rather than left with an
orphan it still believes.

## Ship criterion

R1-R4 and R6 run in `check pm`, each naming the two places that disagree. Backlog milestones are a
counted line, never a finding. `pm roadmap` prints the plan and writes nothing. `pm retire` no
longer appends to `ROADMAP.md`, and the file is named as retired in the CHANGELOG with its
replacement.

## Proof budget

  cases: 6
  tier: pyunit
  lands in: `test_pm_gate.py` beside the V-rule cases, and `test_pm_verbs.py` for `pm roadmap`
  what already covers this: the V family is one case per rule and these follow that pattern
    exactly. R1 and R6 get two each because both are symmetric and only one direction of each is
    the bug that motivated it.

## Out of scope

Retiring `pm status`. "What is this milestone doing" and "what ships when" are different questions
and both are worth a verb.
