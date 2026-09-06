---
id: 0.3.0/a-config-error-is-complete/01-every-defect-is-reported-and-the-flow-first
feature: 0.3.0/a-config-error-is-complete
milestone: "0.3.0"
name: a config read reports every defect at once with the flow named first
status: building
owner:
depends_on: []
---

# a config read reports every defect at once with the flow named first

Every config refusal in this package was excellent and arrived one at a time, in
an order nothing ranked. A real adoption had two defects at once and was told
the cosmetic one.

## Acceptance criteria

1. A `devkit.toml` read reports EVERY defect it found, one line each.
2. Where several are present the FLOW is named first — a tree with no flow has
   no working verbs and everything else is cosmetic beside it.
3. Exit 2 once, not once per defect.
4. `check all` does not let a roster error hide a gate's own config error: an
   unknown gate name is reported WITH what the correctly-named gates would have
   said about their own sections.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | `test_two_defects_are_both_reported_and_the_flow_comes_first` | new — every refusal was covered SINGLY, which is the gap |
| 3 | unit | `test_it_is_exit_2_once_not_once_per_defect` | new |
| 4 | unit | `test_a_roster_error_carries_what_the_named_gates_would_have_said` | new — `gates-extra`/roster paths were covered by NAME, never for what they hide |

Measured: a tree with a retired key and no flow now reports both, flow first;
a roster naming `uid, tres` reports the unknown gates AND the missing flow that
routing at the roster used to conceal.

## Out of scope

Changing any individual message. Each is already better than most tools manage;
this is about how many a consumer gets, and in what order.

## Close

done: 40fa9c2 — `all_config_defects` collects rather than raises at the first,
flow first, and a roster error now carries what fixing the roster alone would
never have shown you.
