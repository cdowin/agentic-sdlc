Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-fast-parallel-development Deterministic parallel development — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-10-01 — CI evidence before milestone close

PR [#113](https://github.com/cdowin/agentic-sdlc/pull/113) ran at
`1eb8991133e2d9d1acb117d2d5847143c7022e7b`. The required `verify` job and
the Python 3.12, 3.13, and 3.14 matrix passed in
[run 36794612813](https://github.com/cdowin/agentic-sdlc/actions/runs/36794612813).
The first verify attempt failed when a transient Git
`.git/objects/maintenance.lock` disappeared during fixture copying; its one
targeted rerun passed the full milestone gate in 46 seconds. The version gate
was red before close because the 1.1.0 milestone was still `packaging`; it
requires the matching milestone to be `done`. This CI evidence covers the
final pre-close commit. The next commit records the PM close and will receive
its own required CI run.
