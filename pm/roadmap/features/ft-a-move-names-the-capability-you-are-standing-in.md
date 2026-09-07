---
id: ft-a-move-names-the-capability-you-are-standing-in
kind: feature
milestone: "ms-a-move-is-an-event"
name: a move names the capability you are standing in
status: planning
reviewed: docs/reviews/2026-09-07-0.5.0-the-capability-and-the-breadcrumb.md
depends_on: []
consumed_by: []
---

# a move names the capability you are standing in

A move into `in_progress` is the exact moment worktree isolation becomes relevant, and the exact
moment nobody remembers `tools/dev/agent-worktree.sh` exists. **`install-hooks` ships that script and
no surface ever mentions it again.**

Hard rule 11: *a capability this package HAS is named in the surface someone is standing in when they
need it.* The breadcrumb already prints at every move, derived from `[pm.states.*]` and the belt
registry. This adds one more derived line — the INSTALLED CAPABILITY that applies to this transition.

    feature ft-x: planning -> building
    next: `close feature` asks stories-done, feature-verified, review-recorded, findings-landed
    have: tools/dev/agent-worktree.sh is installed — isolation for parallel work on this grain

## Why this is not the tool having an opinion

Rule 9 forbids deciding what a move MEANS or what should happen next. This decides nothing. It reads
two facts the tree already holds: **which installed files exist**, and **which transition just
happened**. The mapping from transition to capability is a DECLARATION — a config table, so a project
that installs different tooling names its own — never a hardcoded list.

`have:` is deliberately a different word from `next:`. `next:` is the belt's own check list and is
binding. `have:` is inventory. A line that read *"you should run the worktree script"* would be an
opinion and must not ship; *"this exists, here, now"* is the census this package prints everywhere
else.

## What this build proved

Seven agents ran against one shared checkout because the orchestrator did not think of isolation. The
cost, measured: three agents could not get a verdict on their own work and rebuilt isolated trees with
`git archive HEAD` before they could test; `pm new` crashed mid-call because `cli.py` was being
rewritten underneath it; two agents independently edited `CHANGELOG.md`; `test_prose_census` went red
cumulatively, so no single agent broke it and no single agent could fix it.

The script that prevents all of it shipped in the box and was never named at the moment it mattered.

## Ship criterion

Every status move prints, after `next:`, the installed capabilities a `[capabilities]` table binds to
that transition — each named only when the file is actually present. A transition with no binding
prints nothing. A bound file that is absent is a named line, never silence (rule 11), because a
capability declared and missing is a contradiction the tree is holding.

Emitted on `rung.leave` beside `next_actions`, as `have`, so an agent and a human get it together.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_pm_verbs.py`, on the `StatusVerbQuartet` the breadcrumb already extended
  what already covers this: the quartet covers what a write PRINTS; these are rows on it. The
    derived-only assertion joins the breadcrumb's existing case in `tests/test_boundaries.py`.

## Out of scope

Running anything. This package boots nothing (rule 2, D1) — it names the script; the operator runs it.
