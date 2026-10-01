Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-integrate-takes-the-whole-batch integrate takes the whole batch — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-10-01 — The proof receipt is keyed on the batch's content, not its HEAD

`integrate` writes new merge commits on every rerun, so a key on HEAD never matches and the reuse story could not hold. The batch state is history-independent (`_batch_state`). Accepted risk: a proof target that reads git history could have a PASS reused across a different history with the same files. Rejected: keying on HEAD (no rerun would ever reuse). `--no-cache` forces a fresh proof, and the reuse line names it.
