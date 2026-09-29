Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ft-the-tree-names-the-real-cause the tree names the real cause — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-29 — release asks its gate of the tree it leaves (#87)

Cause (b) of three. The belt's own `done` write moved the tree past what the gate saw. A
scratch consumer with a check that fails only on a CLOSED milestone (a stand-in for a
decisions-log cap) passed `release`'s gate at `building`, wrote `done`, then failed the next
`make check`. The gate ran live, so no verdict was reused (not a). The consumer's
`make milestone` included `make check` (not c).

Chosen: `check_gate` asks the gate with the milestone's `status:` at the state the belt will
write, and restores every byte after. Rejected: a `next:` line only — it names the trap and
still writes `done` over a tree that fails its own check.

While the gate runs, another lane reading the tree sees the transient `done`. Accepted: the
window is the gate's length, and the belt restores every byte, on SIGTERM and SIGHUP too.
