---
id: 0.2.0/the-code-knows-entry-and-exit/05-the-three-bugs-are-fixed
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: The three bugs open against 0.2.0 are fixed and closed
status: planning
owner:
depends_on: []
---

# The three bugs open against 0.2.0 are fixed and closed

## Acceptance criteria

- `0.2.0/bugs/a-composition-has-no-slot`: `precommit` and `milestone` in `Makefile.devkit` open their own gate slot, so `verify --plan` reports a cost for the wide rungs; `make -n` still runs nothing.
- `0.2.0/bugs/a-collapsed-milestone-has-no-verb`: `pm retire` retires a milestone in any `done` state (`obe` included) and the ROADMAP row says which.
- `0.2.0/bugs/the-slot-names-are-spelled-in-six-places`: one spelling, in the config reader.
- All three at `closed`.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | integration | a composition run leaves a `gate` row named for it | amend tests/test_makefile_gates.py |
| 2 | unit | retire of an obe milestone | amend tests/test_pm_verbs.py |
| 3 | unit | the slot names have one source | amend tests/test_grain_shape.py |

## Out of scope

New bugs. If fixing one finds another, it is filed against 0.2.0 and fixed here too.
