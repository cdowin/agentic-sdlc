---
id: ft-the-report-is-the-stamp-table
kind: feature
milestone: "ms-the-ledger-is-a-stamp"
name: the report is the stamp table
status: reviewing
reviewed: docs/reviews/2026-09-12-0.10.0-features.md
depends_on: ["ft-a-milestone-reports-only-its-own-rows", "ft-work-is-stamped-with-its-issue-and-agent"]
consumed_by: []
changelog: `pm ledger report <milestone>` prints the units table (unit grain issue agent start stop duration tokens outcome), `by agent`, `time per state` and named count lines; the spend, yield, rework, escapes, overhead, time-per-actor, no-grain and in-flight blocks are removed (their rows stay in `ledger show --json`), and gate cost moves to `--tree`.
---

# the report is the stamp table

Audit unit 6, plus the bound bug `bg-two-gate-runs-share-one-log-and-inflate-its-census` (the gate
table's census). The owner's word was "simple".

**The telemetry surface is about 4,380 shipped lines.** `report.py` alone is 2,133, and the one-id
report prints 7 headings and 17 tables. 0.8.0's run printed 203 lines, and the comparison prints 9
blocks, 4 of them contaminated. Against what the owner listed (start, stop, issue, tokens, per
milestone), most of it answers questions nobody asked. `ledger.deviation_row` has no caller.

**The report becomes the stamp:** one per-milestone table (unit, grain, issue, agent, start, stop,
duration, tokens), `time per state`, and a tree-wide gate table. Its columns are named in `--help`,
in order, and composition is the shell's job (rule 11's read side). Yield, rework, escapes and overhead
leave the telemetry verb or are cut, and each block cut is named in the close with where its question
is answered now, if anywhere.

**Removing blocks is a line-shape change** (rule 6), so it is a minor bump, and it is written in the
changelog block by block.

## Ship criterion

`pm ledger report <milestone>` prints the stamp table, `time per state` and nothing else
milestone-scoped, and `--help` lists the columns in order. `pm ledger report --tree` (or whatever the
first feature names it) prints the gate table, whose census counts one run per run. `report.py` is
measurably smaller, and the number is in the close.

## Proof budget

  cases: net NEGATIVE. The block cases for cut blocks go with them; the stamp table gets one case per
  column family
  tier: unit
  lands in: tests/test_pm_ledger_report_sections.py
  what already covers this: every current block has a case. The work is deleting most of them, not
  adding.
