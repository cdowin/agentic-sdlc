---
id: st-r5-grades-the-current-release
feature: ft-a-milestone-declares-its-version
milestone: "ms-0.3.0"
name: R5 grades the version file against the current release and D8 retires by name
status: done
owner:
depends_on: ["st-a-milestone-declares-a-version"]
kind: story
---

# R5 grades the version file against the current release and D8 retires by name

D8 welded the project version to the id of whichever milestone was in progress.
R5 grades it against a POSITION in the plan, which fits bump-at-start and
bump-at-close both, and has no opinion about what a version string looks like.

## Acceptance criteria

1. R5 grades `[pm] version_file` against the current release, naming BOTH values
   and the milestone that claims the expected one when they disagree.
2. `[pm] version_at` selects which entry — `start` (default) or `ship`.
3. A tree with no `order` WARNs and never reddens; a version file with no version
   is a finding.
4. `[pm] checks` naming `D8` is exit 2 saying it retired into R5 — never
   "unknown rule", which would silently ungate it.
5. D8's hotfix special case leaves with it: a hotfix is an entry in the plan.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_the_current_release_is_graded_and_a_mismatch_names_both` | amends D8's match/mismatch pair |
| 2 | unit | `test_version_at_ship_grades_the_last_shipped_entry_instead` | new — D8 had one flow only |
| 3 | unit | `test_no_version_in_the_file_is_a_finding`, `test_a_tree_with_no_plan_warns_and_never_reddens` | first amends D8's unreadable-file case; second new |
| 4 | unit | `test_d8_in_the_roster_is_named_as_retired_never_as_unknown` | new — no rule id had ever retired |
| 5 | unit | the deleted `test_d8_admits_a_hotfix_of_the_released_milestone_and_nothing_else` | removed with the semantics |

## Out of scope

Enabling R5 on this repo's own `devkit.toml` — it needs `releases.md`, which
`the-order-is-declared-and-appended` writes. It lands there.

## Close

done: 0ed6e38 — R5 grades the version file against the current entry in `order`;
`[pm] version_at` picks start or ship. D8 is exit 2 naming R5, and its hotfix
grammar left with it — a hotfix is now just an entry in the plan.
