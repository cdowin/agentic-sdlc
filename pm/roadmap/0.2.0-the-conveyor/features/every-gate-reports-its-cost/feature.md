---
id: 0.2.0/every-gate-reports-its-cost
milestone: "0.2.0"
name: Every gate records what it cost, so the gate set can be argued from data
status: done
reviewed: docs/reviews/2026-09-05-every-gate-reports-its-cost.md
risk: medium
size: m
phase: 3
depends_on: ["0.2.0/the-kit-owns-the-gates-that-scan-its-own-artifacts"]
consumed_by: ["0.2.0/the-release-is-a-conveyor"]
labels: ["telemetry", "ledger", "gates", "performance"]
---

# Every gate records what it cost, so the gate set can be argued from data

**Chris, 2026-09-04:**

> *"The gates should probably always be timed and using the ledger the sdlc now provides right? We should
> always be collecting this telemetry. Where do we do this so we can get better?"*

## Why — the measurement that prompted it took a hand-rolled loop, and that is the problem

A consumer's `make check` had grown to feel like "many minutes". Nobody knew which gate, because nothing
records it. Timing all twenty by hand, once, produced this:

| gate | s |
|---|---|
| `pm-shape-scan` | **34.8** |
| `loot-category-dispatch-scan` | **12.4** |
| `runners-self-test` | 8.0 |
| `signal-emitter-scan` | 5.8 |
| `hooks-self-test` | 3.4 |
| the other 15 together | ~5.6 |

**70 s total, and two gates are 47 s of it — 67%.** Fourteen of the twenty are under one second.

Two things fell out immediately, and neither was guessable:

- **`z-layer-scan`, the one suspected by name of being bloat, is 0.2 s** — among the cheapest in the set.
  A name is not evidence.
- **`pm-shape-scan`'s 34.8 s is an implementation defect, not work.** Its `_doc_lines` spawns four
  subprocesses per file (`wc`, `head`, `awk`, `head`) across 683 markdown files, called from several
  patterns — thousands of spawns to count lines and skip frontmatter. One `awk` pass does it in under a
  second.

**A one-off hand measurement cannot catch a gate getting slower.** It caught this one because someone
finally asked; nothing would have caught the drift that produced it.

## Where it goes — there is exactly one funnel, and it already exists

`gdk_gate` in `installables/Makefile.devkit` is the single wrapper every gate runs through: it already
owns the verdict line, the summary function and the `.gate-reports/<name>.log` transcript. **Instrument
there and every gate is covered for free, including gates that do not exist yet** — which is the whole
argument for putting it in the funnel rather than in each gate.

The ledger is already shipped (`pm ledger record`, the two courier hooks, `pm ledger report`). A gate row
is a new `kind`, not a new mechanism.

**Correction, 2026-09-05 — `gdk_gate` is the common CALLER; `gdk_gate_verdict` is the funnel.**
Traced against the file: every gate target in `Makefile.devkit` routes through the `gdk_gate`
define **except** `runners-self-test`, which open-codes the same three calls (lines 180–196),
and `parse`/`lint`/`warnings`/`unit`, which publish their own verdict from inside the runner and
are deliberately not wrapped again. Instrumenting the `define` therefore misses five gates —
including the 8-second one. **`gdk_gate_verdict` in `gdk_runners.sh` is the single line every
one of those paths reaches**, and it already receives the tag, the summary and the log path.
Duration is the one thing it does not have, so the timer opens in `gdk_gate_capture` and the row
is written in `gdk_gate_verdict`.

Record per run: gate name, wall duration, verdict, and enough tree identity to compare like with like
(a gate's cost scales with the corpus it walks, so a duration without a census is not comparable across
repos or across a year of growth).

## What it makes possible, and what it must not become

- **A gate getting slower becomes visible** instead of being discovered when someone complains.
- **The gate set becomes arguable from data** — "these fourteen cost 5.6 s together, this one costs 34.8"
  is a different conversation from "check feels slow".
- **`0.2.0/the-release-is-a-conveyor` consumes it.** Its `adopt` step list exists because adoption should
  not pay for a project's own gates; deciding what a step is allowed to cost needs the numbers.

**Not a budget that fails a build.** A gate that reds because it got 200 ms slower on somebody's laptop
is a gate people disable. This REPORTS; whether a ceiling is ever enforced is a separate decision with
its own argument.

## The second consumer of this telemetry is the DISPATCH BAR, and it is where the cost actually lands

Measured 2026-09-04, greening a suite after an extraction: **the full suite is 154 s; a single test
module is 0.9 s. 170x.** An agent asked to fix eleven failures ran the full suite after each one and
took **31 minutes**. Re-checking the same five modules afterwards took **13 seconds**.

**The dispatch was the cause, not the agent.** It said *"VERIFY: `pytest tests/ -q` — target is 0
failed"*, naming the slow command as the verification and never mentioning that a module can be run
alone. An agent given one command uses it as its inner loop, because nothing told it there was another.

So the rule this feature has to make enforceable, rather than hope for:

> **Name the narrow command for the loop and the wide one for the close.** A dispatch that names only
> the full gate teaches the full gate as the inner loop. State both, with their measured costs, and say
> which is which.

**This is exactly what the telemetry is for.** Once `gdk_gate` records duration per gate, a dispatch can
carry real numbers instead of an author's guess, and the numbers stay true as the suite grows. Without
them, "run the narrow thing first" is advice; with them it is a fact an agent can act on.

Two things fall out for scope:

- The recorded row should make the **narrow-vs-wide ratio** derivable, not just the wall time — that
  ratio is what makes the rule obvious. A 1.2x ratio does not warrant a two-command dispatch; a 170x one
  does.
- The stock agent definitions this kit installs should carry the rule, so every consumer's agents inherit
  it rather than each orchestrator re-learning it by burning half an hour.

## Risks

1. **Timing the funnel changes the funnel.** `gdk_gate` is on the path of every gate in every consumer;
   a bug here reds everything. It has to be additive and fail open — a ledger write that cannot happen is
   not a gate failure, exactly as the two couriers already rule for themselves.
2. **Duration without a census invites the wrong conclusion.** The same gate is legitimately slower on a
   bigger tree; the row needs the corpus size beside the seconds or someone will "optimise" a gate that
   is simply doing more.
3. **Telemetry nobody reads is cost with no benefit.** If `pm ledger report` does not grow a view that
   answers "what got slower", this is a write-only table and should not ship.

## Ship criterion

1. A gate run through any of the paths above appends one row carrying **name, wall duration,
   verdict and census**, through the one funnel, **failing open** — a ledger that cannot be
   written is never a gate failure.
2. `pm ledger report` grows the view that answers *what got slower*. This is a **blocker, not a
   nice-to-have**: risk 3 says telemetry nobody reads is cost with no benefit, and a feature
   whose own risk register condemns it shipping half-done should not ship half-done.
3. Every gate that **opens a slot** records name, duration, verdict and census through the one
   funnel, and `verify --plan` reports a cost it does not have as `unknown` rather than deriving
   one. *(Amended 2026-09-05 by decision D9, from finding G3. It read "the row makes the
   narrow-vs-wide ratio derivable", and it is not: `_cost_of` joins by make TARGET NAME, and the
   wide rungs are prerequisite-only targets with no recipe, so they never open a slot and the
   ratio's denominator is empty in every configuration this package ships. The code was right and
   the criterion overclaimed — `--plan` saying `unknown` rather than inventing a number is the
   behaviour this milestone's whole read side is built on. The ratio is
   `0.2.0/bugs/a-composition-has-no-slot`.)*
4. The stock agent definitions carry the name-both-commands rule, so a consumer's agents inherit
   it instead of each orchestrator re-learning it by burning half an hour.
