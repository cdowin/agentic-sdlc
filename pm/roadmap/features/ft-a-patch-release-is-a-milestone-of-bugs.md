---
id: ft-a-patch-release-is-a-milestone-of-bugs
kind: feature
milestone: "ms-the-leader-finishes-the-job"
name: a patch release is a milestone of bugs
status: reviewing
reviewed: docs/reviews/2026-09-12-0.12.0-features.md
depends_on: []
consumed_by: []
changelog: `ready-for milestone` and `release` accept a bug-only milestone (no features, at least one bound bug, all done) without `--force`, and `release`'s last `next:` line syncs the mainline.
---

# a patch release is a milestone of bugs

0.11.1 shipped one bug and had to `release --force` over `features-done`: `pm ready-for milestone`
refuses a milestone with no features ("an empty feature set does not satisfy this belt; a mis-typed id
looks exactly like this"). That refusal is right for an EMPTY milestone. It is wrong for one that
holds bugs and no features, which is what a patch release is.

**Decided:** `ready-for milestone` (and so `release`'s `features-done`) is READY when the milestone
has zero features, at least one bug bound to it, and every such bug in the `done` category. It names
the shape in its ok line (`0 feature(s), N bug(s) — a bug-only milestone`). No features and no bugs
still BLOCKS with today's text (rule 4: a census of 0 fails). Features present behave exactly as
today.

Also in this lane: `release`'s printed `next:` lines gain one final line to sync the mainline after
the tag: `git switch <mainline> && git pull --ff-only`. The guard feature makes that allowed.

## Ship criterion

A milestone with 1 closed bug and 0 features passes `ready-for milestone` and `release` without
`--force`. A milestone with 0 features and 0 bugs still refuses with the same text. A bug-only
milestone with an open bug refuses, naming the bug. `release` prints the mainline sync as its last
`next:` line.

## Proof budget

  cases: 3 (parametrize rows on the existing ready-for milestone cases) + 1 amended next-lines case
  tier: unit
  lands in: the existing ready-for / release belt tests (grep `features-done`)
  what already covers this: the empty-set refusal; nothing covers a bug-only milestone.
