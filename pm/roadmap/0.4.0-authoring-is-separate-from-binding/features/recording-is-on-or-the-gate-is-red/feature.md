---
id: 0.4.0/recording-is-on-or-the-gate-is-red
milestone: "0.4.0"
name: Recording is on, or the gate is red
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# Recording is on, or the gate is red

**This feature exists because the telemetry was off for the whole of 0.3.0 and nobody could tell.**

`.claude/settings.json` wires `Stop` → `cc-ledger-session.sh` and `SubagentStop` →
`cc-ledger-subagent.sh`. Both are installed, executable, self-testing and firing. Each is a
courier: it calls `pm ledger record --from-transcript …`, and the verb writes into **the one
`in_progress` milestone's ledger**.

At the start of this session `0.1.0` was `planning`, `0.2.0` `done`, `0.3.0` `planning`, `0.4.0`
`planning`. No milestone was `in_progress`, so the verb refused every call:

    [pm] ERROR — no milestone in pm/roadmap is in progress (building, reviewing,
    accepted, packaging), so there is no ledger this report belongs to

The hook fails open by design — it must never block a stop — so it printed that to stderr and
exited 0. **Nobody reads a hook's stderr.** `pm/roadmap/` held exactly one `ledger.jsonl`, from
0.2.0, the milestone that built the ledger. And 0.3.0 is being built right now, at
`status: planning`, recording nothing, for the same reason.

## A fail-open hook needs a fail-loud gate somewhere else

That is the whole argument. Fail-open is correct for the hook: a telemetry courier that could
block a session stop is worse than one that loses a row. But fail-open with no counterpart is
indistinguishable from working, and the failure mode is silence in a durable record — the one
place this package treats silence as a cardinal sin (a census that reports `0` rather than
absence).

The tool holds both halves of the question already and asks neither:

- `check hooks` verifies the corpus under `tools/hooks/` is armed and runs. It says nothing about
  whether `.claude/settings.json` fires any of it, because settings.json is out of its scope.
- `check pm` D1–D10 asks about statuses, refs and branches. No rule asks whether the tree is
  recording.

## What changes

A `check pm` rule — the next free `D` id — that is a finding when **ledger-writing hooks are
wired and no milestone is `in_progress`**. Both halves are readable: the hooks from
`.claude/settings.json`, the categories from `[pm.states.*]` via `holds`. A tree with no ledger
hooks wired is not a finding; it opted out. A tree with them wired and nothing to write into is
losing data every session.

The rule reports; it does not refuse. That is this package's split, and this is squarely a fact
about the TREE, not about an input.

Second, the coupling gets stated where the claim happens. `pm-execution.md` step 1 is *"Claim.
`pm story building <id>` when you begin editing files for a story"*. It reads as bookkeeping. It
is also **the switch that turns recording on**, and the rule should say so in the same breath —
one clause, at the step where it becomes true.

## The question worth actually deciding

Should a `todo`-category milestone accept rows at all? The design work IS the milestone's work —
this session wrote four features and a findings document against a milestone that was `planning`
for its first twenty minutes, and none of that spend is recoverable. The counter-argument is D6:
the ledger is per-milestone and `in_progress` is what names which one, so accepting rows into a
`planning` milestone needs a different answer to "which ledger" than the one the tool has.

**Decide it in this feature, in writing, either way** — a defensible "no, and the gate is how you
find out" is a fine outcome. What is not fine is the current state, where the answer is "no" by
accident and delivered as silence.

## Ship criterion

A tree with ledger hooks wired and no `in_progress` milestone is a named `check pm` finding
pointing at the fix. `pm-execution.md`'s claim step says that the flip is what starts recording.
The `planning`-milestone question is answered in this feature file with its reasoning. No hook
changes behaviour: fail-open stays.

## Proof budget

  cases: 3-4
  tier: pyunit
  lands in: `tests/test_pm_gate.py`, which already parametrizes one case per D rule
  what already covers this: nothing — no existing case reads `.claude/settings.json` from the
    gate, so the hook-detection half is genuinely new. Cases: hooks wired + no in_progress (the
    finding), hooks wired + one in_progress (silent), no hooks wired + no in_progress (silent,
    the opt-out), and a settings.json that will not parse (unverifiable, never a failure).

## Out of scope

Changing any hook's fail-open behaviour. Attributing rows to a grain — that is
`0.4.0/every-row-names-its-grain`. Getting the hooks into a consumer at all — that is
`0.4.0/telemetry-arrives-with-the-bump`.
