---
id: 0.2.0/the-transitions-table-is-published-vocabulary
milestone: "0.2.0"
name: The step registry is this package's vocabulary, read at a pin bump
status: planning
reviewed:
phase: 6
depends_on: []
consumed_by: []
risk: medium
size: s
---

# The step registry is this package's vocabulary, read at a pin bump

Filed by the 0.3.0 plan review, which landed on the transitions table as **"legitimate, but
unearned as written"**. The argument against it is real and the design did not answer it:

> A `[pm.transitions.<kind>]` table keyed by STEP NAME means the engine still knows every grain
> has a "review started" and a "finished". The lattice moved from words to steps; it did not go
> away.

The answer is that `[release] steps` is **already** project-configurable — a project draws its
belt from a registry — so the registry is a MENU, not a lattice. **But the plan never said so**,
and a project cannot invent a step, so unsaid it reads as opinion with a config file in front.

## What makes it declaration rather than opinion

The step registry is this package's **published vocabulary**, exactly like `[pm] checks`'s D-ids:
a closed set the package ships, that a project selects from, that `pm vocabulary` prints, and
that a consumer re-reads on a pin bump because a release may add to it.

`pm vocabulary`'s docstring today says *"There are no TRANSITIONS to print."* That stops being
true, and it is the surface where this is either declared or invisible.

## Ship criterion

1. `pm vocabulary` prints the step registry per operation and the transition each step writes.
2. A transition naming a step not in the registry is exit 2, naming both.
3. The README's adoption section names `pm vocabulary` as a read the pin bump owes — beside the
   CHANGELOG and `install-* --diff`, which it already names.
