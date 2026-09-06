---
id: 0.2.0/bugs/the-gate-census-column-is-always-absent
milestone: "0.2.0"
name:
status: fixed
caught_in: "0.2.0"
fix_milestone: "0.3.0"
caused_by: 0.2.0/every-gate-reports-its-cost
---

# the gate-cost census column is structurally always absent

Filed from the 0.2.0 release review as **L3**, deferred with its reason rather than fixed.

`pm ledger report`'s gate-cost section carries a `census` column, and **nothing this package
ships ever sets `GDK_GATE_CENSUS`** — so on every consumer the column is `-` for every row, and
every delta is starred as "census moved or is absent".

## Why it was deferred rather than fixed in 0.2.0

The one cheap way to fill it is the one the feature explicitly forbids: parsing the number out of
the gate's own verdict prose. A gate that walked 683 files and printed `PASS — 683 doc(s)` would
sometimes yield `683` and sometimes yield `0`, depending on the sentence — and a `0` there is the
empty census hard rule 4 calls a cardinal sin, arrived at by regex, with a number on it that
looks measured.

**The column is honest-but-empty, not wrong.** The report marks an absent census `*` and counts
the starred rows in its own heading, so nobody reads a delta as comparable when it is not. That
is the difference between a gap and a lie, and it is why this waits.

## What fixing it actually requires

A machine-readable census OUT of the gate rather than a guess AT it: the Python gates would emit
a second, parse-shaped line (`[check:doc] census=683`) that `gdk_gate_verdict` reads, or
`gdk_gate_capture` would take the census as an argument the recipe supplies. Both are output-format
changes, which hard rule 6 makes a **minor** bump at least, and both want the tier-providing kits
to agree — which is a conversation with `godot-devkit` 0.25.0, not a patch here.

## The tell that it was forgotten

`pm ledger report` prints `N delta(s) marked * for a census that moved or is absent` and the
number never falls. If it is still equal to the row count a release from now, nobody filled it.
