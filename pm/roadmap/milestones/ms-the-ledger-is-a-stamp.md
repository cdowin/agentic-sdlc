---
id: "ms-the-ledger-is-a-stamp"
kind: milestone
name: the ledger is a stamp
status: planning
depends_on: ["ms-a-consumer-can-take-the-bump"]
branch: milestone/0.9.0-the-ledger-is-a-stamp
version: 0.9.0
changelog:
---

# 0.9.0 — the ledger is a stamp

> ## Northstar, in Chris's words: **"The ledger is supposed to be granular, per milestone. It should
> be simple telemetry that someone can stamp. start times, stop times, issue_ids being worked, token
> use, etc etc."**

## Where this came from

It came out of building 0.8.0 on 2026-09-11. Asked "are we more efficient than 0.7.0?", the tree
could not answer, for two reasons found that session:

- **The comparison is contaminated.** `pm ledger report <a> <b>` puts the ROOT ledger's unattributed
  rows (gate, test, verify, session and dispatch rows naming no grain) into EVERY milestone's row.
  0.6.0 and 0.8.0 printed byte-identical "rows naming no grain" and "gate cost" blocks, and identical
  spend in/out/cache numbers. That is rule 4's first sin in a read verb: numbers printed as true of a
  milestone that are not.
- **Concurrent work is unattributable.** The couriers name a grain from `GDK_LEDGER_GRAIN` in their own
  environment, else from "exactly one story in progress", else not at all. With parallel subagents,
  every row lands unattributed. The only per-grain spend 0.8.0 has is what the orchestrator
  hand-recorded from each agent's report.

The scout's audit, `docs/reviews/2026-09-11-ledger-telemetry-audit.md`, is the evidence this
milestone is decomposed from.

**Planning only.** Features and stories are written from the audit, and none is dispatched before
0.8.0 ships.

## Ship criterion

<!-- Written from the audit. The shape Chris asked for, as a first cut:
     - a person can stamp START and STOP on a unit of work, with the grain and the external issue id(s)
       it serves, and token use when it is known, each with one verb and none inferred;
     - every row a milestone's report counts is that milestone's, and a comparison of two milestones
       shares no row between them;
     - concurrent work is attributable without an environment variable the orchestrator cannot export;
     - what the ledger cannot say, it says it cannot say (rule 11), rather than printing a shared number. -->

## Risks

- **"Simple" may mean trimming as much as adding.** The report prints 23 blocks. A stamp nobody can
  read back simply is the same failure one layer out.
- **Rule 9.** Attribution must be a STAMP someone made, never a guess the tool makes from timing or
  file paths.
