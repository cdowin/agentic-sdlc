---
id: 0.4.0/recording-is-on-or-the-gate-is-red
milestone: "0.4.0"
name: A tree that is not recording says so
status: building
reviewed:
phase:
depends_on: ["0.4.0/one-rule-routes-a-row"]
consumed_by: []
---

# A tree that is not recording says so

**This feature exists because the telemetry was off for the whole of 0.3.0 and nobody could tell.**

`.claude/settings.json` wires `Stop` → `cc-ledger-session.sh` and `SubagentStop` →
`cc-ledger-subagent.sh`. Both are installed, executable, self-testing and firing. Each is a
courier: it calls `pm ledger record --from-transcript …`, and the verb wrote into the one
`in_progress` milestone's ledger. At the start of the session that found this, no milestone was
`in_progress`, so the verb refused every call:

    [pm] ERROR — no milestone in pm/roadmap is in progress (building, reviewing,
    accepted, packaging), so there is no ledger this row belongs to

The hook fails open by design — it must never block a stop — so it printed that to stderr and
exited 0. **Nobody reads a hook's stderr.** `pm/roadmap/` held exactly one `ledger.jsonl`, from
0.2.0, the milestone that built the ledger.

## What is left after D1, and what is not

`0.4.0/one-rule-routes-a-row` deletes the cause: a row is routed by its grain, at any status, so
"no milestone is in progress" stops being a condition that can lose data. **That closes the
specific hole and closes none of the class.**

What remains is everything else that makes a courier's output go nowhere, all of it silent, none
of it addressed by grain-first routing:

- the settings.json entries were never pasted, so nothing fires;
- the `pm` target is not `.PHONY`, so `make` exits 0 without reaching the verb (the hook detects
  this exact case and says so — on stderr);
- `[pm.states.<kind>]` is undeclared, so the CLI is inert and the courier's call refuses;
- `python3` is not on PATH, or the transcript path does not resolve.

Every one produces zero rows and zero visible complaint. The hole was one instance; the shape is
**a fail-open courier with no fail-loud counterpart anywhere**, and that is what this feature
fixes.

## The gate

A `check pm` rule — the next free `D` id — reporting the plain form of the question:

> **ledger-writing hooks are wired, and this tree has no rows.**

Both halves are already readable: the hooks from `.claude/settings.json`, the rows from the
ledgers the tree holds. A tree with no ledger hooks wired is **not** a finding — it opted out, and
this package does not conscript. A tree with them wired and nothing landing is losing data every
session.

**It WARNS. It never refuses.** That is this package's split — it refuses facts about the INPUT and
reports facts about the TREE, and this is squarely the second. It is also what was asked for: the
posture is *clearly available, and warned when absent*, not *mandatory*.

Second, the coupling gets stated where the claim happens. `pm-execution.md` step 1 reads as
bookkeeping; under D1 it is no longer the switch that turns recording on, and the rule should stop
implying that a status flip is what makes the tree honest. One clause, at the step where it
becomes true.

## Already answered, recorded here so it is not re-argued

**Should a `todo`-category milestone accept rows?** Yes — D1. Design work is the milestone's work,
and the routing rule that makes it possible is `one-rule-routes-a-row`'s, not this feature's. The
first twenty minutes of the session that found all of this are unrecoverable, and that is the last
time it should be possible.

## Ship criterion

A tree with ledger hooks wired and no ledger rows is a named `check pm` WARN pointing at the four
causes above and how to tell them apart. A tree with no hooks wired is silent. `pm-execution.md`
no longer implies the status flip is what starts recording. No hook changes behaviour: fail-open
stays, because a telemetry courier that can block a session stop is worse than one that loses a
row.

## Proof budget

  cases: 3-4
  tier: pyunit
  lands in: `tests/test_pm_gate.py`, which already parametrizes one case per D rule
  what already covers this: nothing — no existing case reads `.claude/settings.json` from the
    gate, so the hook-detection half is genuinely new. Cases: hooks wired + no rows (the WARN),
    hooks wired + rows present (silent), no hooks wired (silent, the opt-out), and a settings.json
    that will not parse (unverifiable, never a failure — the existing convention for a ref the
    gate cannot check).

## Out of scope

Changing any hook's fail-open behaviour. The routing rule — `0.4.0/one-rule-routes-a-row`, which
this depends on. Grain attribution — `0.4.0/every-row-names-its-grain`. Getting the hooks into a
consumer at all, and probing them there — `0.4.0/telemetry-arrives-with-the-bump`, which is the
same question asked of somebody else's tree.
