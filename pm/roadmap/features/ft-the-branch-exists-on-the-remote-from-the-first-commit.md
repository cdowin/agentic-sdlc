---
id: ft-the-branch-exists-on-the-remote-from-the-first-commit
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: the branch exists on the remote from the first commit
status: done
reviewed: docs/reviews/2026-09-07-0.6.0-the-branch-exists-on-the-remote.md
depends_on: []
consumed_by: []
---

# the branch exists on the remote from the first commit

**0.5.0 ran for five hours and thirty-four commits with nothing on the remote.** Every belt run, every
review record, every decision, the whole arrival mechanism — one disk. Nobody noticed, because nothing
in the conveyor looks.

The release ceremony's `next:` lines say `git push -u origin <branch> — never the mainline`. That is
the ONLY place a push is named, and it fires at the END, after the work that would be lost.

## Why nothing caught it

Every surface that could have is pointed elsewhere:

- `release`'s `on-milestone-branch` reads `branch:` from the milestone document and checks HEAD is on
  it. It never asks whether that branch exists anywhere but here.
- `check repo-hygiene` fetches — the one gate that touches the network — and is deliberately held to
  milestone close, because it is slow.
- The pressure line counts open grains. It does not count unpushed commits.
- `pm status`, `pm roadmap`, `check pm` are all tree-local by design.

So the tree could describe five hours of finished work with total accuracy and no copy of it existed.
That is not a gap in git discipline; it is a fact about the work that the conveyor does not carry.

## The shape

**A milestone moving into an `in_progress` category is the moment the branch should exist remotely** —
that is the arrival (D3) where the work starts being worth something. `[pm.arrive.milestone.building]`
already declares what arriving there ASKS; this is a `have:`-shaped fact and a `next:`-shaped action at
the same arrival.

**The tool does not push.** Hard rule 2: it boots nothing, and a package that runs `git push` on a
status flip is a package that can publish work an operator did not mean to publish. It REPORTS — the
count, and the command:

    milestone ms-x: planning -> building
    next: `agentic-sdlc release <version>` asks tree-clean, on-milestone-branch, …
    remote: this branch is on no remote — 0 of 34 commits are anywhere else
            `git push -u origin milestone/0.5.0-a-move-is-an-event`

**And it stays visible.** One line on the pressure surface, derived like the rest: unpushed commit
count, and the age of the oldest. Silent at zero. This is the same posture as the open-work census —
absence is a NAMED line, never silence (rule 11), and the caller decides (rule 9).

## Why it belongs in this milestone

The northstar is that a document which cannot be checked against the tree is not a record. This is its
mirror: **a tree that cannot be checked against anywhere else is not backed up.** The conveyor tracks
the work's STATE in exquisite detail and does not track whether the work still exists.

## Ship criterion

A milestone arriving at an `in_progress` state reports whether its `branch:` exists on a remote, and
prints the push command when it does not. Never performs it.

The pressure line carries unpushed commits — count and the oldest one's age — when the number is
non-zero, and nothing when it is zero.

`release`'s `on-milestone-branch` additionally reports whether the branch is published and how far
ahead it is. It does NOT begin refusing on that: the release belt already prints the push as a
`next:` step, and a refusal would change a shipped exit code for a condition that has always been
tolerated (rule 6).

A tree with no remote configured is quiet, not broken — the same posture `[emit]` and the couriers take.

## Proof budget

  cases: 3
  tier: pyunit + shell
  lands in: `tests/test_pm_verbs.py` for the arrival report; the remote-reading case needs a real git
    tree and joins the `shell` tier beside `check_committed`'s
  what already covers this: the arrival report cases from `ft-the-conveyor-pushes-back` are the
    harness — this is another derived line on the same surface, not a new family.

## Out of scope

Pushing. Configuring a remote. Choosing a remote name. Any of those is the tool acting on a
consumer's behalf against a service it knows nothing about, and rule 8 says it knows nothing about
consumers at all.
