---
id: bg-a-bug-is-a-grain-nested-in-a-parent
kind: bug
milestone: ms-the-rule-reaches-the-work
name: a bug carries a private binding vocabulary instead of being nested like every other grain
status: closed
caused_by:
changelog: BREAKING: a bug binds to its parent through `milestone:` alone — `fix_milestone:` and `caught_in:` retire, and `check pm` D11 replaces D3 by refusing to let any parent close over an unresolved child. The release gate had filtered on a field nothing wrote, so it could not refuse on an open bug for four releases.
---

# a bug is a grain nested in a parent

**A bug is a feature with a different word on it.** A story is nested in a feature, a feature is
nested in a milestone, a milestone is nested in the roadmap — one relationship, one field, one walk,
at every level. A bug is nested in a milestone and is the only kind that says so three times:
`milestone:`, `caught_in:` and `fix_milestone:`.

Three fields for one relationship, and the three defects below are all the same defect: **nothing
keeps them in agreement, because there is nothing to agree with — there is only ever one true
answer, and it is "which parent is this under".** Found while scheduling two bugs into 0.6.0
immediately after 0.5.0 shipped.

## Symptom 1 — the release gate has been vacuous for four releases

`ready_for_milestone` decides whether a bug blocks a release by reading one field and no other:

    src/agentic_sdlc/repo/pm/ready_for.py:448
    if model.unquote(model.field_of(bfile, 'fix_milestone')) != mid:
        continue

`fix_milestone:` is empty on **every bug in this tree since 0.2.0** — 18 of 24, including all six
0.5.0 closed. The six that carry it are all `ms-0.2.0`, all closed.

So the census line 0.5.0's belt printed — `0 bug(s) naming fix_milestone ms-a-move-is-an-event of 24
read` — does not mean the bugs were done. It means **nothing sets the field**, so the filter matched
nothing and the check could not fail. 0.5.0's own record claims the opposite in plain words:
*"`release` refuses while any open bug names this milestone, so 0.5.0 cannot ship until all five
close."* It would never have refused; those six closed because an operator closed them. **Rule 4's
first cardinal sin — a gate that stopped checking and printed PASS over zero things — running green
through four releases.**

## Symptom 2 — the scaffold conflates the binding with where the bug was found

`pm new bug <milestone> <slug>` writes its argument to `milestone:` AND to `caught_in:`, and the
comment it mints says which one it thinks it means:

    <!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it was found. -->

The argument is a parent. It is not a provenance claim, and a verb that writes one value into two
fields with different meanings guarantees one of them is wrong the moment they differ. It leaves
`fix_milestone:` — the only field the gate reads — empty.

`pm new feature <milestone> <slug>` writes the binding and nothing else. That is the shape.

## Symptom 3 — `pm add` warns about an order it did not read

Reproduced while authoring this grain. Rebinding a bug off 0.5.0 printed `noticed:
ms-a-move-is-an-event still lists <bug> in its order — that entry is now DANGLING`, naming `pm remove
ms-a-move-is-an-event <bug>` as the fix. **0.5.0's `order:` has never contained that id** — the notice
inferred order-membership from the child's old binding instead of reading the parent's list. The
named remedy then refused (`<bug> names ms-the-rule-reaches-the-work as its milestone`), because `pm
remove` verifies membership by the binding the rebind had just changed: **the command the tool
printed could not succeed at the moment it printed it.** A warning that fires on a false condition
and names an impossible fix is the mirror of a gate that cannot fail;
`ft-a-warning-is-actionable-where-it-fires` is in this milestone for the general case.

## Root cause

Bug was modelled as a special kind rather than as a nesting. Every symptom above is a place where
code had to choose among three fields that mean one thing, and chose differently: the gate reads
`fix_milestone:`, the scaffold writes `milestone:` and `caught_in:`, and `pm add`'s notice reads the
binding where it meant to read the parent's `order:`. This is the shape V6 was retired for in 0.4.0
— two copies of one fact with no way to disagree out loud — surviving in the one kind that was never
folded in.

## Fix

**`milestone:` is the parent binding, and it is the only one.** `fix_milestone:` and `caught_in:`
retire. A bug becomes what it already was: a grain nested in a parent.

  * **`ready_for_milestone` reads the binding**, so the bug walk is the feature walk.
    `_bugs_against`'s bespoke scan across every milestone collapses into the `_children_paths` walk
    every other kind already uses. The check starts being able to fail on the day it lands, on this
    tree, with no backfill.
  * **`pm new bug <milestone> <slug>` is `pm new feature <milestone> <slug>`'s shape** — the
    argument is the parent, the verb writes the binding, nothing else is stamped from it. The bug
    template (shipped, so `install`-side) loses both fields and the comment that taught every author
    the conflation: *"A bug lives in the milestone that will FIX it; `caught_in:` keeps where it was
    found."*
  * **`pm add`'s DANGLING notice reads the parent's `order:`**, not the child's binding; and
    `pm remove <parent> <child>` verifies membership against that same list, so a printed remedy is
    one that runs.
  * **`check pm` names `fix_milestone:` and `caught_in:` at exit 2** where they survive in a
    consumer tree, the way every retired key in this package is named rather than silently ignored.

**Nesting IS the promise, and there is no opt-out.** A grain under a parent must reach `done` before
that parent closes — every kind, every level. No field exempts a child from the parent holding it,
because a field saying "under this milestone but not its problem" is the second scoreboard again,
wearing a smaller word.

**The escape is the binding itself.** A bug you are not committing to now declares no milestone and
sits in the `bugs` pool, where it gates nothing and is counted. `pm remove <milestone> <bug>` already
writes exactly that — it clears `milestone:` to empty — so the opt-out is an act with a verb, visible
in the diff, rather than a field somebody has to remember to read.

  * **`pm` reports the pool count**, because absence is a NAMED line (rule 11): `N bug(s) attached to
    no milestone` on the read surface, silent at zero. An unattached bug that nobody can see is how
    a backlog becomes a place things go to be forgotten, and that is the failure this ruling exists
    to prevent — not the gating.

**So when a milestone is done, everything under it is done.** What the record says it did is what is
written, committed and durable; anything else found along the way is somewhere else, named and
counted. There is no third state where a grain is nominally under a shipped milestone and nobody
owes anything for it.

## Migration

**Seven bugs were unresolved under `ms-0.3.0` and `ms-0.4.0`, both shipped** — the third state this
ruling forbids, and no gate could say so, because `ready_for_milestone` reads `fix_milestone:` and it
was empty on all seven.

The list is derivable and is not copied here: it is the grains outside their kind's `done` category
whose parent is in one. **Naming that query is part of the fix** — a grain under a closed parent is a
`check pm` finding with a rule id, and the pool gets its counted sibling, `N bug(s) attached to no
milestone`, silent at zero.

**The evidence that it must be a verb is how this section got written.** No surface answers "what is
unresolved under a closed parent", so the agent doing this cleanup hand-rolled the walk three times
in Python. Two of the three used a frontmatter regex whose `\s*` after the colon crossed the
newline, read the FOLLOWING field as the binding, and so reported a clean tree while four bugs sat
unbound — **an ad-hoc check that printed zero and could not fail, written to look for a real check
that printed zero and could not fail.** It was caught by a `grep -c` that disagreed, not by the
script. That is rule 11's test answered out loud: someone hand-rolled a thing this package already
half-knows, nothing stopped them, and the wrong answer was the confident one.

All seven now have an answer — one closed, two into this milestone, four unbound to the pool — and
four retired compound ids were renamed in the same pass.

## Verification

The regression case is the one that would have caught it: a milestone holding an open bug, asserted
to BLOCK `ready-for milestone`; the same bug bound to no parent, asserted not to. Today the first
case passes green, which is the whole defect. `tests/test_pm_gate.py` already holds the `ready-for`
family.

A second pins the census line, because `0 bug(s) … of 24 read` is the sentence that made this
invisible for four releases: zero-because-none-are-nested has to read differently from
zero-because-none-matched. A third pins symptom 3 — rebind a bug whose parent's `order:` does not
list it, and assert the notice stays silent.

**Until this lands, `fix_milestone:` is stamped by hand** on the five bugs under this milestone, so
0.6.0 gates on them under the code that ships today. Landing the grain deletes those five stamps
**and the gating gets stronger, not weaker**: the binding gates unconditionally, so the five are
still held — by `milestone:`, which none of them can be under without being owed.

## Out of scope

`caused_by:`. It names the feature whose change produced the bug, which is a real relation between
two grains — the same kind of thing as `depends_on:`, not a second copy of the binding. It stays.
