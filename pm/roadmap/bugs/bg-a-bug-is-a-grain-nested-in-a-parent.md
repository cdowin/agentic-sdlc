---
id: bg-a-bug-is-a-grain-nested-in-a-parent
kind: bug
milestone: ms-the-rule-reaches-the-work
name: a bug carries a private binding vocabulary instead of being nested like every other grain
status: open
caught_in: "ms-a-move-is-an-event"
fix_milestone: "ms-the-rule-reaches-the-work"
caused_by:
---

# a bug is a grain nested in a parent

**A bug is a feature with a different word on it.** A story is nested in a feature, a feature is
nested in a milestone, a milestone is nested in the roadmap — one relationship, one field, one walk,
at every level. A bug is nested in a milestone and is the only kind that says so three times:
`milestone:`, `caught_in:` and `fix_milestone:`.

Three fields for one relationship, and the three defects below are all the same defect: **nothing
keeps them in agreement, because there is nothing to agree with — there is only ever one true
answer, and it is "which parent is this under".**

Found while scheduling two bugs into 0.6.0 immediately after 0.5.0 shipped.

## Symptom 1 — the release gate has been vacuous for four releases

`ready_for_milestone` decides whether a bug blocks a release by reading one field and no other:

    src/agentic_sdlc/repo/pm/ready_for.py:448
    if model.unquote(model.field_of(bfile, 'fix_milestone')) != mid:
        continue

`fix_milestone:` is empty on **every bug in this tree since 0.2.0** — 18 of 24, including all six
0.5.0 closed. The six that carry it are all `ms-0.2.0`, all closed.

So the census line the belt printed at 0.5.0's release:

    features-done — 15 feature(s), 0 bug(s) naming fix_milestone ms-a-move-is-an-event of 24 read

That `0` does not mean the bugs are done. It means **nothing sets the field**, so the filter matched
nothing, so the check could not have failed. 0.5.0's own milestone record states the opposite in
plain words:

> `release` refuses while any open bug names this milestone, so 0.5.0 cannot ship until all five
> close.

The belt would never have refused. Those six closed because an operator closed them. **This is rule
4's first cardinal sin — a gate that stopped checking and printed PASS over zero things — and it ran
green through four releases.**

## Symptom 2 — the scaffold conflates the binding with where the bug was found

`pm new bug <milestone> <slug>` writes its argument to `milestone:` AND to `caught_in:`, and the
comment it mints says which one it thinks it means:

    <!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it was found. -->

The argument is a parent. It is not a provenance claim, and a verb that writes one value into two
fields with different meanings guarantees one of them is wrong the moment they differ. It leaves
`fix_milestone:` — the only field the gate reads — empty.

`pm new feature <milestone> <slug>` writes the binding and nothing else. That is the shape.

## Symptom 3 — `pm add` warns about an order it did not read

Reproduced while authoring this grain. `pm add ms-the-rule-reaches-the-work
bg-a-hand-recorded-dispatch-cannot-carry-a-total` rebound a bug from 0.5.0 and printed:

    noticed: ms-a-move-is-an-event still lists bg-a-hand-recorded-dispatch-cannot-carry-a-total
             in its `order` — that entry is now DANGLING;
             `agentic-sdlc pm remove ms-a-move-is-an-event bg-…` takes it out

**0.5.0's `order:` has never contained that id.** The notice inferred order-membership from the
child's old binding instead of reading the parent's list. Then the remedy it named was refused:

    [pm] REFUSED — bg-… names ms-the-rule-reaches-the-work as its milestone,
         not ms-a-move-is-an-event — nothing was written

`pm remove` verifies membership by the binding the rebind just changed, so the command the tool
prints cannot succeed at the moment it prints it. A warning that fires on a false condition and
names an impossible fix is the mirror of a gate that cannot fail, and
`ft-a-warning-is-actionable-where-it-fires` is in this milestone for the general case.

## Root cause

Bug was modelled as a special kind rather than as a nesting. Every symptom above is a place where
code had to choose among three fields that mean one thing, and chose differently: the gate reads
`fix_milestone:`, the scaffold writes `milestone:` and `caught_in:`, and `pm add`'s notice reads the
binding where it meant to read the parent's `order:`.

This is the shape V6 was retired for in 0.4.0 — two copies of one fact with no way to disagree out
loud — surviving in the one kind that was never folded in.

## Fix

**`milestone:` is the parent binding, and it is the only one.** `fix_milestone:` and `caught_in:`
retire. A bug becomes what it already was: a grain nested in a parent.

  * **`ready_for_milestone` reads the binding**, so the bug walk is the feature walk.
    `_bugs_against`'s bespoke scan across every milestone collapses into the `_children_paths` walk
    every other kind already uses. The check starts being able to fail on the day it lands, on this
    tree, with no backfill.
  * **`pm new bug <milestone> <slug>` is `pm new feature <milestone> <slug>`'s shape** — the
    argument is the parent, the verb writes the binding, and nothing else is stamped from it. The
    bug template loses both fields and the comment that explains them, which is the sentence that
    taught every author the conflation in the first place:

        <!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it was found. -->

    Rendered prose describing a field that no longer exists is this milestone's own theme; the
    template is a shipped file, so it is `install`-side, not a hand edit to a consumer's tree.
  * **`pm add`'s DANGLING notice reads the parent's `order:`**, not the child's binding; and
    `pm remove <parent> <child>` verifies membership against that same list, so a printed remedy is
    one that runs.
  * **`check pm` names `fix_milestone:` and `caught_in:` at exit 2** where they survive in a
    consumer tree, the way every retired key in this package is named rather than silently ignored.

**A bug still does not have to gate a milestone.** The choice does not disappear with the field; it
moves to the act that was always expressing it. A bug you intend to fix now is nested under the
milestone. A bug you are carrying is nested under nothing, sits in the backlog, and gates nothing —
exactly as an authored-but-unscheduled feature does. Scheduling is the promise, at every level, for
every kind.

## Verification

The regression case is the one that would have caught it: a milestone holding an open bug, asserted
to BLOCK `ready-for milestone`; the same bug bound to no parent, asserted not to. Today the first
case passes green, which is the whole defect. `tests/test_pm_gate.py` already holds the `ready-for`
family.

A second case pins the census line, because `0 bug(s) … of 24 read` is the sentence that made this
invisible for four releases: zero-because-none-are-nested has to read differently from
zero-because-none-matched.

A third pins symptom 3 — rebind a bug whose parent's `order:` does not list it, and assert the
notice stays silent.

**Until this lands, `fix_milestone:` is stamped by hand.** The five bugs in 0.6.0's `order:` carry
it explicitly, so 0.6.0's own release gates on them under the code that ships today. Landing this
grain deletes those five lines along with the field.

## Out of scope

`caused_by:`. It names the feature whose change produced the bug, which is a real relation between
two grains — the same kind of thing as `depends_on:`, not a second copy of the binding. It stays.
