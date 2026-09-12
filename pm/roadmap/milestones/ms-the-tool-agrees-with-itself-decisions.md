Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-the-tool-agrees-with-itself the tool agrees with itself — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-12 — a hand record joins its courier twin in the reader, by agent_id

Join in the reader, not with an annotation row: rows are never rewritten (D7) and `report` already
reads both ledgers. A hand row is folded into the one courier row (the one carrying `messages`) with
the same `agent_id`; the hand row's grain wins, the courier's measured numbers win unless it has none.
No id, or not exactly one courier row, joins nothing. **Rejected:** matching on similar timing or
tool-call counts, as #39 proposed — a guess (rule 9). Shipped b79c5c8.

## D2 — 2026-09-12 — a snapshot places a row only on exactly one story (supersedes 0.4.0 D8 finest-kind clause)

Supersedes 0.4.0 D8's "finest kind" clause. A grainless row is placed by its snapshot only when the
snapshot names exactly one story in progress; a feature in the snapshot is that story's roll-up, never
a candidate of its own. Features and no story places nothing, counted on `rows naming no grain`. Old
shape rows follow the same rule. **Why:** bugs and milestone-level work never appear in a snapshot, so
"the only feature building" is a guess by elimination — the coarser-grain move D8 already rejected one
level down; in #39 it billed a PO dispatch to the wrong feature. D8's other clauses stand. Shipped b79c5c8.
