---
id: st-a-snapshot-places-a-row-only-on-a-story
kind: story
feature: ft-the-gates-agree-and-a-dispatch-counts-once
milestone: "ms-the-tool-agrees-with-itself"
name: a snapshot places a grainless row only on a story, never on a feature by elimination
status: planning
owner:
depends_on: ["st-a-hand-record-joins-its-courier-twin"]
changelog:
---

# a snapshot places a grainless row only on a story, never on a feature by elimination

Issue: #39 (the comment).

0.4.0 D8 says a grainless row *"is placed by its snapshot ONLY when the snapshot names one candidate
at its finest kind"*. `report.py:72` (`CATEGORY_BUCKETS`) and `_named_through` (`:801`) implement
exactly that. With no story `building` and one feature `building`, the finest kind named is the
feature, so every grainless dispatch lands on that feature. In the consumer's tree, one of those
dispatches was a PO for a story in a DIFFERENT feature, and another was for a bug. A bug is never in
the snapshot, and neither is milestone-level work. **"Unambiguous among what the snapshot can
name" is not "unambiguous".** D8 itself rejected the same move one level down: *"a guess wearing a
coarser grain"*.

**The fix:** a snapshot places a row only when it names exactly one STORY in progress. A feature in
the snapshot is a roll-up of its placed story, never a candidate in its own right. Everything else is
counted on `rows naming no grain`, not placed.

**This amends a recorded decision.** Write it with `pm decide` on this milestone, superseding D8's
"finest kind" clause and citing it by milestone and number. Do not change the behaviour silently.
0.4.0's decisions file keeps its text.

## Acceptance criteria

1. A grainless row whose snapshot names one feature and no story is placed on NO grain, and is
   counted on `rows naming no grain`.
2. A grainless row whose snapshot names exactly one story is placed on that story and rolled up to
   its feature (unchanged behaviour).
3. A snapshot naming two or more stories places nothing (unchanged behaviour, D8).
4. A row that STATES a grain is attributed by that grain and nothing else (unchanged behaviour, D8).
5. The legacy buckets (`LEGACY_BUCKETS`) follow the same rule, or the builder records why old-shape
   rows are left as written.
6. A `pm decide` entry in `ms-the-tool-agrees-with-itself-decisions.md` supersedes D8's clause.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | a feature-only snapshot row | new, unless D8's placement cases take a parameter |
| 2–4 | unit | D8's existing placement cases | existing |
| 5 | unit | a legacy-shape twin of case 1 | amend 1 |

## Semver

Minor. The report's numbers move for trees with a feature `building` and no story `building`.

## Out of scope

Placing a grainless row on its real grain. Only a stamp can do that (0.10.0,
`ft-a-concurrent-dispatch-attributes-itself`).
