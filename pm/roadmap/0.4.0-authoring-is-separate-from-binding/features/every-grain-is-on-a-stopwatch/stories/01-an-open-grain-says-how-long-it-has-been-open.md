---
id: 0.4.0/every-grain-is-on-a-stopwatch/01-an-open-grain-says-how-long-it-has-been-open
feature: 0.4.0/every-grain-is-on-a-stopwatch
milestone: "0.4.0"
name: An open grain says how long it has been open
status: done
owner: claude
depends_on: []
---

# An open grain says how long it has been open
`pm status` says, for every grain not yet in a `done` category, how long it has been open — read
from its first `status` row in the ledger. `pm ledger report` says the same as a distribution:
median and worst per kind.

The number that creates pressure is the one about the grains still OPEN.
`ledger.total_seconds` already computes first-row-to-terminal and deliberately
returns None while a grain is in flight, which is exactly the case nothing measured.

## Acceptance criteria

1. `ledger.open_seconds(rows, now)` — first `status` row to NOW, for a grain whose last status is
   not in a `done` category. `None` when the grain has no status row: **a grain nobody has moved
   is UNMEASURED, never zero** (rule 4).
2. `pm status` prints it per open grain, in a form a human reads at a glance (`3d 4h`, `12m`), and
   `-` where it is `None`. Column order and the existing cells do not move: consumers cut on them.
3. `pm ledger report` gains median and worst open-duration per kind, beside the spend table.
4. **Nothing is gated on the number.** No exit code changes, no ceiling, no config key that could
   grow one. The tool expresses and the caller decides (rule 9); a ceiling on how long a feature
   may stay open is this package having an opinion about somebody's week.

## How this is proven

| criterion | tier | the case | existing? |
|---|---|---|---|
| 1 | unit | `test_pm_ledger.py`'s `total_seconds` cases — the open case is the one they assert returns None | amend |
| 1 | unit | no status row at all -> None, distinct from zero | new, one row |
| 2, 3 | unit | one case over a fixture with an aged open grain and a closed one | new |
| 4 | unit | the exit code over a tree with a very old open grain | new, one line |

## Out of scope

Any gate, ceiling or refusal on the duration. Wall-clock anywhere but a report.

## Close

done: d0db6c4 — `ledger.open_seconds` + `human_duration`; `pm status` prints the age per open
grain and `ledger report` the count/median/worst per kind.
finding: the report key is `in_flight`, not `open` — `open` is a declared bug STATE and
`test_pm_flow`'s no-state-literal gate caught it on the first run. Exactly the gate working.
