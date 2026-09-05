---
id: 0.2.0/the-middle-tier-splits
milestone: "0.2.0"
name: The gate framework ships without a Godot roster in it
status: building
reviewed:
risk: medium
size: m
phase: 2
depends_on: ["0.2.0/the-extraction-finishes"]
consumed_by: ["0.2.0/the-kit-owns-the-gates-that-scan-its-own-artifacts", "0.2.0/the-story-belt-knows-what-verifies-this-edit"]
labels: ["extraction", "installables", "framework", "unblocks-godot-devkit"]
---

# The gate framework ships without a Godot roster in it

**Promoted out of ship criterion 5 on 2026-09-05.** The criterion read *"the middle tier is
resolved, **or** the milestone says in writing why it is not"* — an unfailable criterion over
the one deliverable another repo is blocked on. `HANDOFF.md`: `godot-devkit` 0.25.0 *"cannot
green until `agentic-sdlc` is pinnable"*, and `Makefile.devkit` — carrying the gate framework
and the Godot target roster in one file — is *"the entire middle tier and the only design
problem left in the split."*

So it is work, and it has an owner.

## The seam, measured

`Makefile.devkit` is 314 lines and reads in three parts:

| lines | what | whose |
|---|---|---|
| 1–146 | header, `DEVKIT_VERSION`/`DEVKIT`, `VERBOSE`, `GDK_SUM_*`, the `gdk_gate` define, `help` | framework |
| 147–277 | `parse` `lint` `warnings` `unit` `integration*` `scenario` `smoke` `capture` `import-cache` `uid-scan` `hermetic-scan` `hooks-self-test` `doctor` + the five scene aliases | Godot roster |
| 278–315 | `check` `precommit` `milestone` | framework — but the compositions name Godot targets |

**The only real coupling is two prerequisite lists:**

```make
precommit: check parse lint unit integration-diff
milestone: check parse lint warnings unit integration-all
```

## The mechanism — `-include`, not a third config key

```make
GDK_TIERS_MK        ?= Makefile.tiers
GDK_PRECOMMIT_TIERS ?=
GDK_MILESTONE_TIERS ?=
-include $(GDK_TIERS_MK)

precommit: check $(GDK_PRECOMMIT_TIERS)
milestone: check $(GDK_MILESTONE_TIERS)
```

A language kit's `install-runners` writes `Makefile.tiers`: it **defines** its targets and
**declares** which compositions they join. Three reasons this beats `[gates] precommit` in
devkit.toml, and each is a failure the config route would have:

1. **Make cannot get target definitions out of TOML.** The tier file has to exist either way, so
   a file that defines the targets and says where they run is ONE source; a TOML key beside it
   is a second one that can disagree — a target listed in config and absent from the file is a
   `check`-time crash naming the wrong thing.
2. **No sub-make, no runtime cost, no `-n` hazard.** `-include` resolves at parse time and
   prerequisites stay prerequisites. `check`'s sub-make dance exists because `[gates] extra` is
   genuinely per-project *data*; tiers are not.
3. **`[gates] extra` keeps meaning one thing** — the project's own gates. Three authorities
   writing into one list is how a roster stops having an owner.

`[gates] extra` is untouched. A project's own gates still arrive exactly as they do today.

## The rule this settles, and it settles four files at once

> **An installable belongs to the kit whose ARTIFACT it acts on — not to the kit whose
> STRUCTURE it borrows.**

Both `milestone.md` and `the-extraction-finishes` deferred this question. One answer:

| installable | acts on | verdict |
|---|---|---|
| `Makefile.devkit` | the gate framework | **stays**, roster removed |
| `cc-godot-sandbox.sh` | Godot engine boots | **leaves** — and `hooks-self-test` with it |
| `doctor.sh` | the Godot toolchain (38 Godot references) | **leaves**; a framework `doctor` shim stays |
| `ci-verify.yml` | the workflow shape (23) | **stays**, engine/linter steps become tier-provided |
| `model.py` D8 `version_file` | defaults to `project.godot` | **default changes to `pyproject.toml`** — configurable, so this is a default fix; a non-Godot consumer currently gets D8 pointed at a file it does not have |

## Ship criterion

1. `Makefile.devkit` names **no Godot target**, and `tests/test_consumer_independence.py` grows
   the assertion — the same gate that already holds rule 8, extended one word.
2. `precommit` and `milestone` compose from `GDK_*_TIERS`, and a tier name that resolves to no
   target is a **loud** failure, not a silently-shorter gate. That is rule 4 applied to a
   composition: a gate list that quietly gets shorter is the cardinal sin with a Makefile in
   front of it.
3. With no `Makefile.tiers` present, `make precommit` runs `check` alone and **says so** — a
   pure-SDLC consumer is a supported shape, not a degraded one.
4. `tests/test_makefile_include.py` proves both shapes: tiers absent, and tiers present
   contributing two targets to each composition.

## Risks

1. **`-include` of a missing file is silent by design** — that is what makes shape 3 work, and
   it is also how a *typo'd* `GDK_TIERS_MK` becomes a gate that runs half of what it claims.
   The mitigation is criterion 2: an empty tier list is fine, a NAMED tier that does not resolve
   is not.
2. **`--warn-undefined-variables` is on.** `GDK_*_TIERS` must be defined before use in every
   path, including the one where the include does not happen.
3. **This file is `--force`-overwritten by `install-runners`.** A consumer that hand-edited it
   loses the edit — which is already true and already documented in its header, but this release
   is the one that makes them re-install, so the CHANGELOG line matters more than usual.
