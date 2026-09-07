---
id: st-order-sequences-every-container
feature: ft-the-order-is-one-mechanism
milestone: "ms-0.4.0"
name: Every container sequences its children with order, and add is the verb
status: done
owner: claude
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
| 1, 2 | unit | `test_pm_order.py` `AddBindsAndSequencesAtEveryLevel` — bind+sequence, idempotence and `remove` PARAMETERISED over `LEVELS` (root, milestone, feature), plus `set` still unbinding alone | amended — 0.3.0's module, rewritten around the verbs that replaced `pm order` |
| 1 | unit | `test_pm_order.py` `ThePlaceIsTheDecisionAndNeverAGuess` — bare append, each placement flag, a place that cannot be honoured refusing with no write, two places at once | amended |
| 3 | — | review, not a case: it is a claim about what the code does NOT do. `cmd_add` is one `set_field` + one `set_list_field`, and the rebind path PRINTS the old parent's now-dangling entry rather than reaching into it | — |
| 4 | unit | `test_pm_order.py` `ContainsDecidesWhatMayHoldWhat` — four off-mapping pairs refused naming both kinds with nothing written, a narrowed mapping refusing a bug, a mapping nothing could write at exit 2, and declared-vs-default equivalence (hard rule 5) | new |
| 5 | unit | `test_pm_order.py` `OrderIsOptionalPerContainer` — unsequenced COUNTED at exit 0, dangling REPORTED at exit 1, an entry naming no grain a WARN; and `test_pm_gate.py` `TheUnboundFamily::test_r1_names_both_directions…` for the root's half | new + amended |
| 6 | unit | `test_pm_scaffold.py::…test_a_retired_rule_is_not_a_silently_accepted_name` (V6 by name, with `order:` on the parent as its replacement); `test_pm_verbs.py` `TheOrdinalPrefixRetiredByName` (`RETIRED_KEYS`, exit 2, and the id it now mints); `test_pm_order.py::…test_the_retired_verb_names_its_replacement_at_exit_2` (`pm order`, `pm sync`) | amended |
| 6 | unit | `test_pm_verbs.py` `StatusReport::test_the_board_reads_the_milestones_own_order` — `phase:`'s grouping replaced by the parent's `order` | amended |
| 7 | unit | `test_pm_order.py` `TheRootIsAParentLikeAnyOther` and `ThePlanIsRead`; `test_pm_verbs.py` `ThePlanIsADeclaredOrder::test_a_version_change_never_touches_the_plan` | amended |

## Out of scope

Any ordering the tool COMPUTES. `depends_on` stays a dependency statement — a DAG gives a partial
order, and "what is next" wants a total one somebody decided.

done: d1a74eb — `pm add <parent> <child>` binds AND sequences, `pm remove` undoes both, and
`[pm.contains]` declares which kinds hold which, read off the two ids. One list shape at every
level including the ROOT, so `releases.md` is a container like any other and its `order` holds
milestone ids rather than versions.
`pm order`, `pm sync`, `<!-- pm:execution -->`, V6, `story_ordinal_prefix` and `phase:` all retire
BY NAME, each with its replacement where a consumer hits it. `execlist.py` is deleted.
