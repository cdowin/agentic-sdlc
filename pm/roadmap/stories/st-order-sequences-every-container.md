---
id: st-order-sequences-every-container
feature: ft-the-order-is-one-mechanism
milestone: "ms-0.4.0"
name: Every container sequences its children with order, and add is the verb
status: planning
owner:
depends_on: ["st-rename-sweeps-every-inbound-ref"]
kind: story
---

# Every container sequences its children with order, and add is the verb
Every container sequences its children with `order` — block-style frontmatter on the parent,
written by the same list-aware writer 0.3.0 built for `releases.md` — and membership stays the
child's field. One list shape at every level: root → milestones, milestone → features and bugs,
feature → stories.

**It is not a child list.** `order` carries SEQUENCE ONLY. A child bound but not listed is
UNSEQUENCED; an entry naming an unbound child is DANGLING. R1's symmetric pair, one level down,
reported by the same family.

## Acceptance criteria

1. `pm add <parent-id> <child-id> [--position N | --before <id> | --after <id>]` binds AND
   sequences; bare `add` appends. **Neither argument names a kind** — an id carries its own as a
   prefix, so both are derivable.
2. `pm remove <parent-id> <child-id>` unbinds and unsequences together. `pm set <id> <rel> ""`
   remains the way to unbind alone.
3. **`add` is exactly `set` plus a list insert.** Nothing else. D4 says to catch it in review the
   day it grows behaviour neither primitive has; the close names the reviewer who checked.
4. `[pm.contains]` declares which kinds may hold which, and `add` refuses off the mapping, naming
   both kinds — from the ids, not from a check written per level.
5. `order` is OPTIONAL per container. An unsequenced child is a census line, never a finding.
6. **`<!-- pm:execution -->`, V6 and `story_ordinal_prefix` retire by name**, each with its
   replacement in the CHANGELOG. V6's whole job was keeping a hand-maintained story roster in
   agreement with the tree — the identical defect as V2 and the path, one level down. `phase:`
   retires with them where it was used to group features.
7. **`order` lists child IDs at every level**, including the root, so renaming a version never
   touches the plan. `pm order --append` retires into `pm add` against the root, which
   `releases.md` names with its own `id:` like any other parent. Reading the plan stays
   `pm roadmap`.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 5, 7 | unit | `test_pm_order.py` (0.3.0's), parameterised over levels | amend — this is the same code over a declared mapping |
| 3 | — | review, not a case: it is a claim about what the code does NOT do | — |
| 4 | unit | the `[pm.contains]` refusal, both directions | new |
| 6 | unit | `test_pm_gate.py`'s retired roster, and `RETIRED_KEYS` | amend |

## Out of scope

Any ordering the tool COMPUTES. `depends_on` stays a dependency statement — a DAG gives a partial
order, and "what is next" wants a total one somebody decided.
