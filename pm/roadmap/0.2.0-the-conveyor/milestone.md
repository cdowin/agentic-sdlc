---
id: "0.2.0"
name: the conveyor
status: done
depends_on: []
branch: milestone/0.2.0-the-conveyor
reviewed: docs/reviews/2026-09-05-0.2.0-release-review.md
version: 0.2.0
---

# 0.2.0 — the conveyor

> ## Northstar: **a simple local Jira.**
> *Chris, 2026-09-05.* It creates the work, moves it, expresses what the states are and what the
> flow is — **and it infers nothing.** Expressing the flow is the power; deciding what it means to
> move through the flow is a separate problem and belongs to whatever is running it.

**0.3.0 was collapsed into this milestone on 2026-09-05.** It had been opened that afternoon to
rebuild the belts as reporting-not-refusing, over states declared by the project rather than
named by the engine — and shipping a conveyor built on a premise already ruled against, in order
to replace it one release later, is work nobody should do. Chris: *"The end-goal of 0.2.0 is to
ship a working conveyor belt."*

So the belts land **once, correctly**, and this milestone ships when they do.

## The two rulings the whole thing now rests on

**Hard rule 9 — express, never infer.** The engine has two verbs: `move(grain, to_state)`, which
asks whether the transition is declared, and `holds(grains, category)`, which names who is not
there. Everything else is the project's declaration. `docs/design/state-categories.md` is the
design; the inference census in §6 is nine items, one of which the plan review withdrew because I
had attributed a **gate's** job to the engine.

**It gates the SDLC; it does not run it.** A belt moves, warns and finishes — it does not refuse.
Facts about the INPUT are refused at exit 2 (a state in no category, an undeclared transition, a
malformed value: reading, not deciding). Facts about the TREE are reported and the walk continues,
because the engine cannot know whether an open child is wrong — descoped? a hotfix? — and a
machine that blocks on a question it cannot ask is asserting an answer. `check pm` is the gate.

## What this changed about work already done — audited 2026-09-05

Phases 1-4 shipped, reviewed, and carry **36 open findings** across nine feature records. The
worry was that landing them before the rebuild means touching some code twice.

**The audit dispositioned all 36 against the rebuild before choosing an order, and the worry is
aimed at the wrong object.** `docs/reviews/2026-09-05-0.2.0-plan-audit.md` carries the table:
**25 independent, 5 bookkeeping, 4 owned by the rebuild, 1 half-dissolving, 0 dissolving
outright.** Thirty of thirty-six do not care which order is picked; the order governs four. Five
of the independent 25 are BLOCKERs — G4, I1, K1, T1, R3 — every one a hard rule 4 defect, a gate
printing PASS over what it did not measure, and T1 is D1's accepted cost arriving as predicted.
**Land those now.** D4 is the ruling.

**R1 does not dissolve, and reading it properly is the test for every "dissolves" disposition.**
The deadlock goes when nothing halts; the defect does not. Step 14 requires every review record
for the milestone to be **deleted**, which leaves `check pm` permanently RED on D1 — a gate in
`[checks] all`. **Removing the halt changes what a false postcondition costs; it does not make the
postcondition true.** R1 and R2 are one finding, closing in `the-belt-reports-and-finishes`.

**The real double-touch is a feature, not a finding.** `the-inner-levels-are-belts-too` is
`planning`, 0 of 3 stories built, and specifies belts that REFUSE — written before §7. It is the
only unbuilt feature that would have to write the halt and then delete it, so
`the-belt-reports-and-finishes` moves ahead of it in the same phase via `depends_on`. That costs
nothing and closes I2 for free: the 26 stories parked at `reviewing` are parked because the belts
refuse, and walking them through the real verb is the only way criterion 10 gets tested.

## The phase order, re-cut 2026-09-05 by the plan audit

| phase | feature |
|---|---|
| **1** | `the-extraction-finishes` |
| **2** | `the-middle-tier-splits`, `the-kit-owns-the-gates-that-scan-its-own-artifacts` |
| **3** | `every-gate-reports-its-cost`, `the-belts-refuse-to-advance`, `the-story-belt-knows-what-verifies-this-edit` |
| **4** | `the-release-is-a-conveyor`, `adopt-is-a-conveyor` |
| **5** | **`the-belt-reports-and-finishes`** → then `the-inner-levels-are-belts-too` |
| **6** | `the-project-declares-its-flow` — the declaration exists. **Additive.** |
| **7** | `every-question-is-asked-of-a-category` — every question asks it. **The behaviour change.** |
| **8** | `the-ledger-rows-carry-categories` |

**The collapse brought in five features and the audit re-cut them to four.** Categories,
transitions, the `init` append path and the reader are **one config schema**: same block, same
seed, same `init`, same append path, same reader, same two refusals. P1 is the proof — no-fallback
is unshippable without the append path, and the append path has no reason to exist without
no-fallback. **Four features that cannot individually close is the shape that parked 26 stories at
`reviewing`.**

The seam that does exist is between additive and behavioural, and each half closes green — which
is the property neither four features nor five had. **If phase 7 slips, phase 6 leaves the tree
shippable rather than half-migrated.**

**And phase 7 builds the engine's two verbs, which have never existed.** §6 states the
architecture as `move` and `holds`; `grep -rn "def move(\|def holds(" src/` finds one hit and it
is `core/apply.py`'s file mover. Landed without them, phase 7 is ten private `category_of()`
lookups agreeing by convention — a second scoreboard with ten columns, and the `also_done` shim
already proves the failure is live (`ready_for.py` has it, `model.py:1155` does not, so
`pm ready-for feature` and `check pm` D2 disagree today about an `obe` story). D6 is the ruling.

## ▶ The SDLC, and who provides each piece

**The provider table moved to [`docs/design/two-kits.md`](../../../docs/design/two-kits.md) on
2026-09-05** — it is durable doctrine about the two kits, not something this milestone decides, and
a milestone is not where a permanent table lives. The line it encodes: **a thing belongs to the KIT
whose artifact it scans, drives or installs**, and a project's own rules are its own. D2 is the
ruling that settles the installables the same way.

### What the split had NOT resolved — measured 2026-09-04, answered since

`src/` split at **zero cross-imports**. The installables did not: 6 pure SDLC, ~13 pure Godot, and
a middle tier of SDLC FRAMEWORK carrying a Godot ROSTER — `Makefile.devkit` (23 Godot references),
`ci-verify.yml` (23), `doctor.sh` (38), `project-devkit.toml`, `project-CLAUDE.md`, the agent
files. Generic structure, Godot content, and it is what blocked `godot-devkit` 0.25.0.

**Both halves are now ruled rather than open** — D1 splits the tier by `-include` and two tier
variables, D2 assigns each installable to the kit whose ARTIFACT it acts on. `the-middle-tier-splits`
is the grain; criterion 2 is how it fails. T1 is D1's accepted cost arriving as predicted, and it
is open.

## Ship criterion

Restated 2026-09-05 so that each one can fail. The previous fifth criterion read "resolved, **or**
the milestone says why it is not", which no tree can be measured against.

1. A `git init` repo with no `devkit.toml` runs `agentic-sdlc check all` and exits **0 or 1,
   never 2** — and a test asserts the declared roster equals the set that actually dispatches.
2. **`Makefile.devkit` names no Godot target**, `precommit`/`milestone` compose from
   `GDK_*_TIERS`, and the rule-8 gate asserts it. No "or".
3. **Every step is a check, every check reports, and the walk always finishes** — `release` and
   `adopt` run their step lists to the end regardless of what any check said, and the final line
   is a scoreboard naming every step that is not true. **A release over a red `make gates` reaches
   `tag`**, and a test asserts it. *(Rewritten 2026-09-05 under D8. It read "refuse to advance …
   and a skip is a ledger row" — written before the ruling, asserting the premise the collapse
   rejected, which is P1's shape recurring in the document that absorbed P1's ruling. Chris:*
   "Everything is just a check. `release` should release on a red tree if I want — why stop
   someone?"*. The ORDER was always the deliverable; `check pm` is still the gate.)*
4. The SDLC document a consumer reads is GENERATED from its own step list — `install-sdlc`
   beside `install-agents` — so it cannot drift from what runs.
5. Every gate records name, duration, verdict and census through **one funnel**, failing open,
   and `pm ledger report` grows the view that answers *what got slower*.
6. The four gates that scan this kit's own artifacts ship in `[checks] all`, and the tree that
   never had a prose-cap gate gains one.
7. `verify --changed` answers *what proves this edit* from config, **names any path that matched
   nothing**, and falls back to the widest rung.
8. **Every operation has exactly one verb and one scope, and none of them is "run the biggest
   thing"** (decision D3). The ladder is three rungs — `verify --story | --feature | --milestone`
   — plus `pm ready-for` between them and `adopt` beside them, and `README.md` carries the table.
   The failure this closes: a story close reaching for `make milestone`, which is the measured
   170x this milestone exists to end.
9. **All four levels are belts, not two.** `release` and `adopt` are the OUTER operations, run
   weekly and on a pin bump; `close story` and `close feature` are the inner ones, run dozens of
   times a day. Shipping conveyors for the outer two and prose for the inner two is backwards in
   the most expensive direction, and it is what let this milestone's own orchestrator park 28
   finished stories at `reviewing` and review the whole thing in one pass.
10. **0.2.0 is released through `agentic-sdlc release 0.2.0`** — and its own stories and features
   close through `close story` / `close feature`. A belt whose first run is performed by hand has
   not been tested. **Every warning the run emitted is in the ledger with the reason it was
   accepted.** *(Rewritten 2026-09-05: the clause read "every step that had to be skipped", and
   `--skip` shrinks to a note once there is no refusal to escape. The ledger row was always the
   honest half — it becomes what a WARNING records.)*

### And four the northstar needs, added 2026-09-05

Criteria 1-10 were all written before the collapse and none of them asks whether the engine has an
opinion. **The northstar is not measurable against this list**, which is criterion 5's own failure
(*"restated so that each one can fail"*) applied to the milestone's headline.

11. **The engine has two verbs and they exist.** `move(grain, to_state)` refuses an undeclared
   transition at exit 2; `holds(grains, category|state)` answers and names who is not there. Every
   row of the inference census routes through one of them, and **a test enumerates the census** —
   no state literal survives outside the config reader.
12. **A project that renames every state word gets identical behaviour**, proven on a fixture tree
   with a fully renamed vocabulary, vendored here per hard rule 8. Without that fixture, "the
   engine has no opinion" is an assertion rather than a measurement.
13. **`init` writes the flow into `devkit.toml` and can append it to a config it did not write**,
   preserving every other byte, idempotent on the second run. The runtime reads it every run and
   **does not fall back**; a tree without it is refused by name, and the refusal prints the command
   that fixes it rather than the seed to hand-paste.
14. **The CHANGELOG names what a consumer STOPS seeing** — D2 and D5 report strictly less over
   three categories than over seven `LIFECYCLE` positions. A behaviour change, not an improvement.

## Risks

1. **Over-encoding.** A step earns its place by having a checkable postcondition; anything else
   is guidance and belongs in the generated doc.
2. **A gate landing in the default roster reds every consumer at once.** Ships reporting-only or
   config-ceilinged, the posture the 0.24.0 deprecation window took.
3. **A conveyor that is always skipped is worse than none**, because it looks like control. If
   the skip ledger shows one step skipped every release, that step is wrong.
4. **Fourteen grains in one milestone is the scope risk, and the collapse doubled it.** The phase
   order is the mitigation and it now has two independent halves: phases 1 and 2 deliver a kit
   that works and a split that finishes, and phase 6 delivers a declarable flow — each stands
   alone if what follows slips. **Phase 7 is the only phase whose absence leaves the northstar
   unmet** rather than the milestone smaller. P5 of the plan review is the warning worth carrying:
   0.2.0's own scope audit exists because a milestone's real size stayed hidden until it was being
   built, and it recurred one milestone later. **The audit's answer is seams, not smaller
   features**: phase 6 closes green with no behaviour change, so if phase 7 slips the tree is
   shippable rather than half-migrated.
6. **The additive seam is the thing that will be argued away.** Phase 6's criterion 7 — *a test
   asserts no engine question changed* — is what a builder under pressure to "just fix D2 while
   we're in here" will satisfy loosely. A behaviour change landing in phase 6 makes the seam a
   fiction and phase 7 unreviewable, and then this is one 14-feature milestone with no green
   waypoint in it.
5. **The middle tier may still not decompose cleanly.** If it does not, the honest outcome is a
   stated blocker — but it is now a *finding against a criterion*, not a criterion that
   accommodates it.
