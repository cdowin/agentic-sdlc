---
id: 0.4.0/recording-is-on-or-the-gate-is-red/01-the-gate-sees-a-courier-writing-nothing
feature: 0.4.0/recording-is-on-or-the-gate-is-red
milestone: "0.4.0"
name: A tree with hooks wired and no rows says so
status: planning
owner:
depends_on: []
---

# A tree with hooks wired and no rows says so
A tree whose `.claude/settings.json` wires the ledger couriers and whose ledgers hold no rows gets
a named `check pm` WARN. A tree that wires none is silent — it opted out, and this package does not
conscript (D5).

The feature file carries the four causes and the argument; this story is the gate and one clause in
the rule that auto-loads.

## Acceptance criteria

1. A new `check pm` rule id — the next free `D` — reports **hooks wired and no ledger row in this
   tree**, as a WARN line, never in the exit code. It is OPT-IN, like every other flow-shaped rule,
   and it is in `KNOWN_CHECKS`, the README row and the CHANGELOG.
2. The line names the four causes and how to tell them apart, and it names the ONE command that
   answers all of them.
3. Hooks wired **and** rows present: silent. Hooks wired and no rows: the WARN. **No hooks wired at
   all: silent** — the opt-out, and the case most likely to be got wrong by a rule written from the
   failure it was born in.
4. A `.claude/settings.json` that will not parse is **UNVERIFIABLE, never a failure** — the
   existing convention for a pointer the gate cannot follow. It says which file and why.
5. `pm-execution.md` step 1 no longer reads as though the status flip is what starts recording.
   One clause, at the step where it stops being true — the file is a template in the wheel, so a
   consumer gets it on the bump.
6. Nothing about any hook's fail-open behaviour changes. A courier that can block a session stop is
   worse than one that loses a row.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3 | unit | `test_pm_gate.py`, which already parametrizes one case per D rule — three rows: wired+empty, wired+rows, unwired | the roster exists; these are rows in it |
| 2 | unit | the same rows assert the causes are named, not just that a line appeared | — |
| 4 | unit | a fourth row with a truncated settings.json | the unverifiable convention is asserted for `--review-record`; this reuses the shape |
| 5 | unit | `test_pm_guidance.py` already pins the shipped rule text | amend |
| 6 | integration | `test_hooks_payloads.py` is unchanged and still green | existing, unamended — that IS the claim |

## Out of scope

Every hook's behaviour. The routing rule (`0.4.0/one-rule-routes-a-row`, depended on). Attribution
(`0.4.0/every-row-names-its-grain`). Somebody else's tree —
`0.4.0/telemetry-arrives-with-the-bump` asks the same question of a consumer.
