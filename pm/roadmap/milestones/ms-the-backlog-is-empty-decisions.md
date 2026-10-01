Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-the-backlog-is-empty The backlog is empty — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-10-01 — The denylist stops at single-command alias routes

The hook guards an agent's mistakes; it is not a sandbox against an attacker. 2.3.0 and 2.4.0 refuse every route by which one command, or an exported `GIT_CONFIG_*`, defines an alias or an include. Rejected: chasing `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG` and config files written earlier and included later. Each needs a file the agent writes on purpose first, and the hook would grow without end.
