Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-the-open-issues-close The open issues close — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-10-01 — install --force drops only a header key the packaged file never mentions

#128. The story said to keep only keys the packaged HEADER declares. That deletes values a hook body still reads when a project sets them in the header (`gdk_gate.sh` declares none, but reads `GDK_LOG_CAP_BYTES`). The rule that ships: drop a shell `NAME=` line only when the packaged file never mentions `NAME`, with its comment and continuation lines, and name each on stderr. Agent brief text blocks keep every line. Rejected: the header-only rule (it drops live settings).
