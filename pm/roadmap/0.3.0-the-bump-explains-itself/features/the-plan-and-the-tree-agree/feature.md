---
id: 0.3.0/the-plan-and-the-tree-agree
milestone: "0.3.0"
name: The plan and the tree are cross-checked, and ROADMAP.md retires
status: planning
reviewed:
phase:
depends_on: ["0.3.0/a-release-is-a-grain", "0.3.0/anything-can-name-its-release"]
consumed_by: []
---

# The plan and the tree are cross-checked, and ROADMAP.md retires

A plan nothing checks is a document. The `R` family asks of the release plan what the `V` family
already asks of the tree:

- **R1** every entry in `order` names a release grain, and every release grain is in `order`.
  A release whose covered milestone directory was retired is UNVERIFIABLE, never a failure — the
  concept the tree already has for a ref into a retired milestone.
- **R2** every grain's `release:` resolves. Grains with none are unscheduled: a named, counted
  line, never a finding.
- **R3** versions are unique across release grains.
- **R4 — history is a prefix.** No shipped release appears after an unshipped one. This is the
  invariant that makes "next = the first unshipped release" *correct* rather than merely usual,
  and it is what lets `version_at = "start"` mean something.
- **R6** a release whose grains are all `done` but which never shipped, and a shipped release with
  a grain not in `done`. **This is the rule that catches
  `0.3.0/bugs/the-first-milestone-never-closed` on its first run** — 0.1.0's work is in the
  mainline, went out inside `v0.2.0`, and its milestone has said `planning` ever since, because
  every existing rule asks a question inside the tree and nothing related a milestone to a
  release.

**Two verbs read the plan.** `pm roadmap` prints the order with each release's state, name and the
grains naming it — the thing `pm status` does for one milestone, for the sequence. `pm next`
prints the first unshipped release and what is in it. Neither writes.

**`ROADMAP.md` retires.** It is two things wearing one name: a hand-maintained index of milestones
that are still in the tree — a second scoreboard, and the tool forbids those — and the only
surviving record of milestones `pm retire` deleted. `pm roadmap` derives the first. The second is
already safe, because a release grain outlives the milestone directory it covered. `pm retire`
stops appending a row; the CHANGELOG names the file as retired and says what replaces it, so a
consumer is told rather than finding an orphan.

## Ship criterion

R1-R4 and R6 run in `check pm`, each naming the two places that disagree. Unscheduled grains are a
counted line, never a finding. `pm roadmap` and `pm next` print the plan and write nothing. `pm
retire` no longer appends to `ROADMAP.md`, and the file is named as retired in the CHANGELOG with
`pm roadmap` named as its replacement.

## Proof budget

  cases: 6-7
  tier: pyunit — one per rule, plus the two verbs' output shape
  lands in: `test_pm_gate.py` beside the V-rule cases, and `test_pm_verbs.py`
  what already covers this: the V family is covered one case per rule and these follow that
    pattern exactly. R6 gets two — a done-but-unshipped release and a shipped-but-unfinished one —
    because the rule is symmetric and only one direction is the bug that motivated it.

## Out of scope

Retiring `pm status`. It answers "what is this milestone doing", which is a different question
from "what ships when", and both are worth having.
