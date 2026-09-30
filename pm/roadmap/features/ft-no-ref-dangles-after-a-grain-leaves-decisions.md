Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ft-no-ref-dangles-after-a-grain-leaves no ref dangles after a grain leaves — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-30 — re-binding moves the order entry; unbinding removes it (supersedes 0.4.0's unbind-alone rule)

0.4.0 (`ft-the-order-is-one-mechanism`, review criterion 2) had `pm set <id> <field> ""` unbind
alone and leave the `order:` entry dangling, so `check pm` reported it. #102 measured the cost: a
consumer re-bound features and every one failed DANGLING until a hand `pm remove`. Chosen: a
binding change moves the order entry (`pm set` and `pm add` both), and an unbind removes it.
Rejected: keep the dangling entry as a visible reminder, since nothing reads that reminder but a
gate that then fails.
