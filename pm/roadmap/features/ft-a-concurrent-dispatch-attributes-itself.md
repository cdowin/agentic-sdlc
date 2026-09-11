---
id: ft-a-concurrent-dispatch-attributes-itself
kind: feature
milestone: "ms-the-ledger-is-a-stamp"
name: a concurrent dispatch attributes itself, once
status: planning
reviewed:
depends_on: ["ft-work-is-stamped-with-its-issue-and-agent"]
consumed_by: []
changelog:
---

# a concurrent dispatch attributes itself, once

Defect D-B of the audit (units 3 and 4). It overlaps the pool feature `ft-the-record-is-harvested-not-pushed`,
which stays in the pool: this is the part of it 0.9.0 needs.

**Today concurrent work is unattributable, and hand records double-count it.** A courier names a
grain from `GDK_LEDGER_GRAIN` in its own environment, else from "exactly one story in progress", else
not at all. On 2026-09-11, 12 of 74 hook-recorded rows named a grain, all 12 through the one-story
fallback. `GDK_LEDGER_GRAIN` has attributed 0 of 89 such rows, ever, because an orchestrator cannot
export into a subagent's environment. So 0.8.0's per-grain spend exists only because the orchestrator
hand-recorded each dispatch. All 18 of those hand rows duplicate a hook row, and nothing links the
pair.

**The fix:**

1. **The dispatch carries its own stamp.** `agentic-sdlc dispatch --grain <id>` renders one exact
   stamp line (grain, and issue ids from the stamp feature) into the prompt. The courier, or `record
   --from-transcript`, copies that line VERBATIM from that agent's own transcript. A transcript is
   per-agent, so concurrent dispatches attribute themselves. The line is a stamp copied, never searched
   for or guessed (rule 9).
2. **One dispatch is one row.** A hand record joins its courier twin by `agent_id` (the flag exists,
   and none of the 18 rows used it) and annotates that row instead of adding a second dispatch. The
   report counts one dispatch per `agent_id`.

## Ship criterion

Three subagents dispatched concurrently with `dispatch --grain` each land one row naming their own
grain, with no environment variable exported. Hand-recording one of them afterwards adds no second
dispatch to the report's count. A transcript with no stamp line lands unattributed and is COUNTED on
a line.

## Proof budget

  cases: 3–5
  tier: unit for the stamp copy (a transcript is a file); the courier's own replay corpus for the hook
  lands in: tests/test_pm_ledger_record.py, and the courier's `--self-test` corpus
  what already covers this: the couriers replay their corpus, but no corpus row carries a stamp line,
  and no case records a twin.
