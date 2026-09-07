---
id: ft-adopt-is-a-conveyor
milestone: ms-0.2.0
name: A pin bump is a step list scoped to the adoption, not the project
status: done
reviewed: docs/reviews/2026-09-05-adopt-is-a-conveyor.md
risk: low
size: s
phase: 4
depends_on: ["ft-the-release-is-a-conveyor"]
consumed_by: []
labels: ["adopt", "conveyor", "subtraction"]
kind: feature
order:
  - "st-adopt-walks-the-adoption"
  - "st-adoption-verifies-the-adoption-not-the-game"
---

# A pin bump is a step list scoped to the adoption, not the project

**Split out of `the-release-is-a-conveyor` on 2026-09-05.** It shares that feature's driver and
nothing else — a different operation, different postconditions — so it is a second step list,
not a second machine.

## Why — the subtraction, which is the actual point

Chris, 2026-09-04:

> *"Pinning 24 should be simple. Upgrade the pin, inspect what new install verbs came in, decide
> what to take, update/check configs, lint (to make sure the pm tree is still good against the
> new version) and go. What am I missing?"*

**Almost nothing. What is missing is that nothing scopes verification to the operation.**
Measured on the live consumers: this package's entire `check all` is **2.6 s** and `check pm`
is **0.3 s**, while a consumer's `make check` also runs its own twenty gates — and that is
where the minutes go.

Those gates verify the CONSUMER'S code against the CONSUMER'S rules. **A version bump here
cannot change their verdict.** Running them during adoption re-verifies the game, not the
adoption.

`make check` is one gate answering one question — *is everything fine?* — for every operation,
so adoption, a one-line edit and a release all pay the price of the most expensive thing anyone
might need. Same shape as the release-ordering incidents: one blunt instrument standing in for
several scoped ones.

## The step list

```toml
[adopt]
steps = ["pin-bumped", "installables-diffed", "installable-decisions-recorded",
         "config-updated", "hooks-self-test", "runner-targets-resolve",
         "checks-pass", "pm-validates"]
```

Two of those are steps a human list keeps forgetting, and both have bitten:

- **`hooks-self-test`** — `install-hooks` rewrites guard scripts, and a guard that fails OPEN is
  not there. This package has already shipped a hook that was installed, executable, and
  stopping nothing; a config diff cannot show that.
- **`runner-targets-resolve`** — `install-runners --force` rewrites `Makefile.devkit`, which
  defines the targets every later gate runs through. Broken there, every subsequent gate fails
  for the wrong reason and the operator debugs the wrong thing. **0.2.0 makes this sharper, not
  softer**: `the-middle-tier-splits` moves the composition into `Makefile.tiers`, so this is the
  release where a resolve check earns its place.

**`checks-pass` means THIS package's checks, not the consumer's whole gate set.** That is the
subtraction. On the numbers above the scoped set is seconds rather than minutes, and the
consumer's own gates run when the consumer changes its own code, which is what they are for.

## Ship criterion

1. `agentic-sdlc adopt` walks `[adopt] steps`, resumable, with the same `--skip <step>
   --reason` contract as `release`, into the same ledger.
2. `checks-pass` runs `check all` and **not** `make check` — asserted by a test, because this
   is the one line of the feature that is easy to write correctly and easy to regress.
3. A step this package cannot perform (`pin-bumped` edits the consumer's Makefile) states
   precisely what the operator must do and refuses to advance until its `check()` is true — it
   never edits a file outside the checkout it runs in.
4. `install-sdlc` renders the adopt list beside the release list, from the same source.

## Risks

1. **Rule 8 is the live hazard here.** `adopt` runs IN a consumer, on the consumer's own tree —
   that is fine. What it must never do is read a second repo, or gate on one. The steps are all
   local-tree questions and must stay that way.
2. **A conveyor that is always skipped is worse than none.** If the ledger shows the same adopt
   step skipped on every bump, that step is wrong and this feature has to say so.
