---
id: "ms-the-ledger-is-a-stamp"
kind: milestone
name: the ledger is a stamp
status: done
depends_on: ["ms-the-tool-agrees-with-itself"]
branch: milestone/0.10.0-the-ledger-is-a-stamp
version: 0.10.0
changelog: `pm ledger report` is reshaped (minor, rule 6): the stamp/units table, `by agent`, `time per state`, the milestone's own gate tables and named count lines replace the old 17-table report, and `--tree` holds every row no milestone owns — scripts grepping the removed blocks must move; `pm ledger stamp` and `record --outcome` are how a unit is stamped.
order:
  - "ft-the-flow-is-boring-by-construction"
  - "ft-a-milestone-reports-only-its-own-rows"
  - "ft-work-is-stamped-with-its-issue-and-agent"
  - "ft-a-concurrent-dispatch-attributes-itself"
  - "ft-the-report-is-the-stamp-table"
  - "ft-a-dispatch-row-carries-its-outcome"
  - "bg-an-unknown-agent-type-is-recorded-as-a-dispatch"
  - "bg-two-gate-runs-share-one-log-and-inflate-its-census"
mode: parallel
reviewed: docs/reviews/2026-09-12-0.10.0-milestone-review.md
---

# 0.10.0 — the ledger is a stamp

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

**Re-versioned 0.9.0 → 0.10.0 on 2026-09-11.** `ms-the-tool-agrees-with-itself` took 0.9.0 as a lean
bug-and-debt release. It ships #39's "one dispatch is one row" half (`st-a-hand-record-joins-its-courier-twin`)
and amends 0.4.0 D8's snapshot placement (`st-a-snapshot-places-a-row-only-on-a-story`). Read both closes
before the scout. **Added at the re-version:** `ft-a-dispatch-row-carries-its-outcome` (#41, dispatch outcome and spend by
role) is bound here. It adds report blocks, so weigh it against this milestone's own "simple" risk
below. #40 (`ft-the-session-says-what-it-can-do-before-the-first-dispatch`, 0.11.0) overlaps
`ft-the-flow-is-boring-by-construction`.

**Planning only.** Features and stories are written from the audit, and none is dispatched before
0.9.0 ships.

## Ship criterion

Four features, one per work unit (the audit's six candidates, consolidated), plus two bound bugs:

    ft-a-milestone-reports-only-its-own-rows       D-A: no shared rows; rows claimed by branch:
    ft-work-is-stamped-with-its-issue-and-agent    start/stop/issue/agent/tokens as one verb
                                                   (+ bg-an-unknown-agent-type-is-recorded-as-a-dispatch)
    ft-a-concurrent-dispatch-attributes-itself     D-B: the dispatch carries its stamp; one row each
    ft-the-report-is-the-stamp-table               "simple": the report IS the stamp table
                                                   (+ bg-two-gate-runs-share-one-log-and-inflate-its-census)
    ft-a-dispatch-row-carries-its-outcome          #41, added at the re-version: outcome stamped on a
                                                   dispatch; spend by role

**Ship criterion.** Someone can stamp START and STOP on a unit of work, with its grain, the external
issue id(s) it serves, its agent and its tokens, with one verb each and nothing inferred. Every row a
milestone's report counts is that milestone's, and a comparison of two milestones shares no row.
Concurrent dispatches attribute themselves without an environment variable nobody can export, and a
dispatch counts once. `pm ledger report <milestone>` is the stamp table. What the ledger cannot place,
it counts on a named line; it never prints a shared number as one milestone's.

**Decomposition into stories happens when 0.9.0 has shipped**, by the same flow: a scout against the
code at that point, then stories.

## Risks

- **"Simple" may mean trimming as much as adding.** The report prints 23 blocks. A stamp nobody can
  read back simply is the same failure one layer out.
- **Rule 9.** Attribution must be a STAMP someone made, never a guess the tool makes from timing or
  file paths.
