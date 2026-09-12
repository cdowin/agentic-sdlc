---
id: ft-the-gates-agree-and-a-dispatch-counts-once
kind: feature
milestone: "ms-the-tool-agrees-with-itself"
name: the version gates agree, and a dispatch counts once
status: done
reviewed: docs/reviews/2026-09-12-0.9.0-the-gates-agree-and-a-dispatch-counts-once.md
depends_on: []
consumed_by: []
changelog: none
order:
  - "st-the-version-file-is-claimed-when-a-milestone-starts"
  - "st-a-hand-record-joins-its-courier-twin"
  - "st-a-snapshot-places-a-row-only-on-a-story"
---

# the version gates agree, and a dispatch counts once

Issues: #43 #39.

These are both rule 4's first sin, seen by a consumer. In each, the tool prints a verdict or a
number as true when it is not:

- **#43.** Under `[pm] version_at = "start"`, R5 grades the version file against `current_milestone()`,
  "the first entry in `order` not yet done" (`pm/inventory.py:1082`, `graded_release` at `:1110`).
  The moment `release` writes `done`, that becomes the NEXT milestone. R5 then demands a version that
  `ci-semver-gate.yml` refuses to see before the merge. The release commit cannot be pushed without
  `--no-verify`. This happens to every `start` consumer at every release. The kit never hits it,
  because it bumps at close.
- **#39.** The courier files a grainless dispatch row. The documented remedy for that row,
  `pm ledger record --grain …` (the `RECORDING` block `dispatch.py:170` renders, and
  `pm-execution.md`), appends a second row. `report` sums both. One consumer milestone overstated
  its tool calls by 468 and its agent time by 1.9 h. Separately, `report.py:72`'s snapshot buckets
  placed those grainless rows on the one FEATURE that was building. That was the wrong feature for
  one of them: 0.4.0 D8's "finest kind" clause, working as written, gave a wrong answer.

The stories are serial: 2 and 3 both change how `pm/report.py` places and counts dispatch rows.
Story 1 is independent and goes first because it is the cheapest.

## Ship criterion

In a temp tree with `version_at = "start"`: `building` → `release` writes `done` → next milestone
`building`. R5's accepted value is this milestone's version until the next one flips, then the next
version, and R5 never names a `planning` milestone. A hand record naming the courier row's
`agent_id` leaves `pm ledger report` counting one dispatch, not two, and a counted line names how
many pairs were joined. A snapshot naming one feature and no story places nothing.

**Accepted means closed on GitHub:** #43 and #39 are each closed with a comment citing this feature
and its hash(es) (SDLC.md §2).

## Proof budget

  cases: 5–7
  tier: unit (inventory, report and record are functions over a temp tree)
  lands in: the existing R5 / `graded_release` cases and `tests/test_pm_ledger_record.py` plus the
    report's placement cases. Search before adding one (rule 10)
  what already covers this: R5 is graded under `start` and `ship` at rest. No case walks a
    `start` tree through `done` → next `building`. No case records a courier twin. D8's cases
    cover ambiguous STORY snapshots, not a feature-only one.
