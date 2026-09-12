---
id: ft-a-milestone-reports-only-its-own-rows
kind: feature
milestone: "ms-the-ledger-is-a-stamp"
name: a milestone reports only its own rows
status: reviewing
reviewed: docs/reviews/2026-09-12-0.10.0-features.md
depends_on: []
consumed_by: []
changelog: `pm ledger report` and its comparison read only rows the milestone owns — its grains', or grainless rows whose `branch` is its declared `branch:` — and every other root row is reported once by the new `pm ledger report --tree`; `ledger show` attributes a row as the report places it.
---

# a milestone reports only its own rows

Defect D-A of `docs/reviews/2026-09-11-ledger-telemetry-audit.md` (audit units 1 and 2). The owner's
"granular, per milestone".

**Today every per-milestone number is contaminated.** The report adds the root ledger's rows (gate,
test, verify, session, and dispatch rows naming no grain) to EVERY milestone:
`pm/cli.py:2819-2823` for one milestone, `:2964-2974` for the comparison, and `report.py:1118-1120`
counts every dispatch row before narrowing. 0.6.0 and 0.8.0 printed byte-identical "rows naming no
grain" and "gate cost" blocks, and all of 0.8.0's in/out/cache tokens came from the root file. `ledger
show` has the same problem: 29 of the 32 rows it printed for one story were other work. The report's
own note says "the delta is real and not 0" above a delta of 0. **This is rule 4's first sin in a read
verb.**

**The fix has two halves, and neither infers anything:**

1. A milestone's totals and every comparison block read ONLY rows that milestone owns. Tree-wide rows
   get their own, separately headed tree report. `ledger show` attributes by `grain` only.
2. Every row records the branch it was filed on (HEAD read as text), and a milestone claims rows by its
   own declared `branch:`. That gives gate, verify, session and grainless dispatch rows a milestone
   home, because a milestone already declares its branch. It is a stamp the tree made, never a guess
   from timestamps.

## Ship criterion

`pm ledger report <a> <b>` shares no row between two milestones: a planted root row appears in
exactly one block, headed as tree-wide, never in either milestone's row. A gate run on a milestone's
declared branch lands in that milestone's numbers, and one on `main` lands in the tree report. A row
the tree cannot place is COUNTED on a line, never folded in (rule 11).

## Proof budget

  cases: 4–6
  tier: unit (the report reads files; the branch stamp is a text read of HEAD)
  lands in: tests/test_pm_ledger_report*.py — amend the comparison cases, which today assert the
    contaminated shape
  what already covers this: comparison cases exist, but none plants a root row and asks WHICH block
    it lands in. That is the case that must fail first.
