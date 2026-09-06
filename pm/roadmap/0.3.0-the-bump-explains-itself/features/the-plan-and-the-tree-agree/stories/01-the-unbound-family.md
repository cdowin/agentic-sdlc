---
id: 0.3.0/the-plan-and-the-tree-agree/01-the-unbound-family
feature: 0.3.0/the-plan-and-the-tree-agree
milestone: "0.3.0"
name: R1 pairs the plan and the tree and R2 counts the backlog
status: building
owner:
depends_on: []
---

# R1 pairs the plan and the tree and R2 counts the backlog

Written as **the unbound family, whose first member is the milestone-to-release
edge** — not as two milestone-specific rules. Every level has the same pair: a
binding that names nothing, and a grain that names no binding. When 0.4.0 makes
authoring separate from binding everywhere, a feature with no milestone joins
this census as a ROW, not as a new rule.

## Acceptance criteria

1. An `order` entry no milestone claims is UNBOUND and a **WARN** — dangling if
   never written, unverifiable if its milestone was retired; the two are
   indistinguishable and neither is a failure.
2. A milestone whose `version:` the plan does not carry is UNSCHEDULED and a
   **FAIL**, naming `pm order --append`.
3. R2 counts milestones declaring no `version:` as BACKLOG — a named, counted
   line, never a finding.
4. Both are opt-in; the stock roster runs neither.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | `test_r1_names_both_directions_and_only_one_of_them_reddens` | new — the V family is one case per rule and this follows it |
| 3 | unit | `test_r2_counts_the_backlog_and_never_reddens_on_it` | new |
| 4 | unit | `test_off_unless_named` | mirrors `FlowChecks.test_off_unless_named` exactly |

## Out of scope

Feature-to-milestone and story-to-feature rows. 0.4.0 adds them to this census.

## Close

done: in-place — R1 symmetric with only the authored half reddening, R2 as a
counted line. The family is named now so 0.4.0 adds rows, not rules.
