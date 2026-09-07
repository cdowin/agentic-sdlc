---
id: bg-a-composition-has-no-slot
milestone: ms-0.2.0
name: A composition target opens no gate slot, so its cost is unknowable
status: closed
caught_in: "0.2.0"
fix_milestone: 0.2.0
caused_by: ft-every-gate-reports-its-cost
kind: bug
---

# A composition target opens no gate slot, so its cost is unknowable

Filed by decision D9, from finding G3 of the `every-gate-reports-its-cost` review.

## Symptom

`agentic-sdlc verify --plan` reports the two wide rungs as `unknown` on every repo, including
this one, and the ratio the milestone's whole economics argument rests on is therefore
underivable from the ledger it built:

```
story      make gates      57 ms (FAIL)
feature    make precommit  unknown
milestone  make milestone  unknown
ratio      unknown — no `gate` rows with these targets
```

47 `gate` rows are present. None carries the name `precommit` or `milestone`.

## Root cause

`verify/main.py`'s `_cost_of` joins a rung's command to a ledger row **by make target name**,
and `gate_costs` only ever holds names passed to `gdk_gate_log`. The wide rungs are
**prerequisite-only targets** — `precommit: gates hooks-self-test test` — with no recipe of
their own, so make runs their prerequisites and never enters a recipe that could open a slot.
The join is correct; there is nothing on the other side of it.

## Fix

**The composition opens its own slot**, timing the whole target, so `gate_costs` gains a real
key. The shape that does not work is a recipe appended to the prerequisite list: make runs
prerequisites first and enters the recipe afterwards, so a recipe cannot time what preceded it.
The likely shape is a composition that invokes its members through a sub-make inside
`gdk_gate_capture`, which is a change to `Makefile.devkit`'s structure and needs its own ruling
about what `make -n` then reports.

D9 records the two alternatives already rejected — summing the members' rows (needs a Makefile
parse or a `make -p` spawn, and guesses which rows belonged to which run) and a `[gates]
precommit` config key (D1 rejected that shape for the tier roster, and the reasons carry).

**Until then `--plan` says `unknown`, which is the honest answer** and is why this is a bug
rather than a blocker: a ratio derived from an incomplete denominator would understate the wide
half, which is the direction that makes the wrong decision look right.
