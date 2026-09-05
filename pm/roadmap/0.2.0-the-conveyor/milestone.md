---
id: "0.2.0"
name: the conveyor
status: building
depends_on: []
branch: milestone/0.2.0-the-conveyor
reviewed: docs/reviews/2026-09-05-0.2.0-release-review.md
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

## What this changed about work already done

Phases 1-5 shipped, reviewed, and carry **36 open findings** across nine feature records. Some are
defects in code whose premise is sound and they land. **Others are defects in REFUSAL** — R1's
deadlock between `findings-resolved` and `review-landed` is two contradictory postconditions in a
machine that halts, and it dissolves when nothing halts. Each is dispositioned against the
rebuild rather than fixed twice.

## ▶ The SDLC, and who provides each piece

Written 2026-09-04 when the package split in two. **The line: a thing belongs to the KIT
whose artifact it scans, drives or installs.** Three providers, and the third is not a
mistake — a project's own rules are its own.

| phase | the piece | provider |
|---|---|---|
| **Plan** | grain schema, the state vocabulary, `pm` verbs, `check pm`, templates | **agentic-sdlc** |
| | the milestones, features, stories and bugs themselves | **the project** |
| **Claim** | agent definitions (stock roster) | **agentic-sdlc** |
| | forked/configured agents, project-specific roles | **the project** |
| **Build** | commit-pathspec, write-confine, stop-gate guards; worktree tooling | **agentic-sdlc** |
| | language runners — parse, lint, unit, integration, scenario, capture | **godot-devkit** |
| **Verify** | the gate FRAMEWORK — `gdk_gate`, `Makefile.devkit`, `[checks]`, `[gates] extra` | **agentic-sdlc** |
| | checks over SDLC artifacts — grain prose, hooks, runners, sandbox | **agentic-sdlc** |
| | checks over Godot artifacts — uid, tres, props, defaults, rng, test-shape, unit-disk | **godot-devkit** |
| | the project's own architecture scans | **the project** |
| **Review** | the review record, N-pass verdict parsing, reviewer agents | **agentic-sdlc** |
| **Release** | the protocol, version sync, changelog discipline, tag | **agentic-sdlc** |
| **Telemetry** | the ledger, the two couriers, `pm ledger report` | **agentic-sdlc** |
| **Adopt** | `install-*` verbs and their installables | **each kit, for its own** |

### The consumer's shape, in one line

> A project pins **agentic-sdlc** for how it works, pins **godot-devkit** for what it builds
> with, and owns its own rules about its own code.

`godot-devkit` is itself a consumer of `agentic-sdlc` — that is dogfooding, and it is a
CONSUMER PIN, never a library import. A scene parser must not drag in a PM tree.

### What the split has NOT yet resolved — measured 2026-09-04

`src/` split at **zero cross-imports** (repo/ 9,334 lines, godot/ 6,844, core/ 981 shared and
deliberately duplicated). **The installables did not.** Of 44:

- **6 are pure SDLC** — `cc-commit-pathspec.sh`, `cc-stop-gate.sh`, `cc-write-confine.sh`,
  `pre-push`, `prepare-commit-msg`, `setup-hooks.sh`.
- **~13 are pure Godot** — `parse.sh`, `lint.sh`, `unit.sh`, `integration.sh`, `scenario.sh`,
  `warnings.sh`, `capture.sh`, `import_cache.sh`, `compile_sweep.gd`, `hermetic_run_scan.sh`,
  `cc-godot-sandbox.sh`, `gdk_runners.sh`, `ci-uid-guard.yml`.
- **The rest are SDLC FRAMEWORK carrying a Godot ROSTER** — `Makefile.devkit` (23 Godot
  references), `ci-verify.yml` (23), `doctor.sh` (38), `project-devkit.toml`,
  `project-CLAUDE.md`, and the agent files. The structure is generic; the content names
  Godot targets.

**That middle tier is the real work of the split, and it is not a file move.** `Makefile.devkit`
must offer the gate framework while the Godot targets come from somewhere else — probably the
same `[gates] extra` mechanism a project already uses for its own. Until that is designed,
`godot-devkit` cannot cleanly shed the agentic half.

## Ship criterion

Restated 2026-09-05 so that each one can fail. The previous fifth criterion read "resolved, **or**
the milestone says why it is not", which no tree can be measured against.

1. A `git init` repo with no `devkit.toml` runs `agentic-sdlc check all` and exits **0 or 1,
   never 2** — and a test asserts the declared roster equals the set that actually dispatches.
2. **`Makefile.devkit` names no Godot target**, `precommit`/`milestone` compose from
   `GDK_*_TIERS`, and the rule-8 gate asserts it. No "or".
3. `release` and `adopt` both run as step lists that refuse to advance, and a skip is a ledger
   row with a reason rather than a silence.
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
   not been tested. A conveyor whose first release is
   performed by hand has not been tested, and every step that had to be skipped is in the ledger
   with its reason.

## Risks

1. **Over-encoding.** A step earns its place by having a checkable postcondition; anything else
   is guidance and belongs in the generated doc.
2. **A gate landing in the default roster reds every consumer at once.** Ships reporting-only or
   config-ceilinged, the posture the 0.24.0 deprecation window took.
3. **A conveyor that is always skipped is worse than none**, because it looks like control. If
   the skip ledger shows one step skipped every release, that step is wrong.
4. **Nine grains in one milestone is the scope risk.** The phase order is the mitigation: phases
   1 and 2 deliver a kit that works and a split that finishes — value that stands alone if
   phases 3 and 4 slip. Phase 4 is the only phase whose absence would leave a criterion unmet
   rather than a milestone smaller.
5. **The middle tier may still not decompose cleanly.** If it does not, the honest outcome is a
   stated blocker — but it is now a *finding against a criterion*, not a criterion that
   accommodates it.
