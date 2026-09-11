Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ft-every-printed-command-runs-in-a-stock-consumer every command the kit prints runs in a stock consumer — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-11 — a stock consumer reaches every verb through one make sdlc passthrough

`Makefile.devkit` gains one target, `sdlc`, over the `$(DEVKIT)` it already defines:
`make sdlc ARGS="dispatch --grain <id>"`. Every command the kit prints or installs for a person or an
agent to run is spelled through it. `make pm ARGS="…"` stays; it is contract (rule 6), and the
narrower passthroughs keep working.

- The name collides with no target in `Makefile.devkit` today (`help`, `pm`, `check`, `precommit`,
  `milestone`, and the `gdk-*` internals).
- It adds no file. `$(DEVKIT)` already pins the version, so the vehicle cannot drift from the pin.

**Rejected: an installed `tools/dev/agentic-sdlc` shim.** It makes the ~109 bare citations true as
written, which is tempting. But it is a sixth installer output to hold byte-current, a script on
consumer machines resolving its own pin (a second reader of `DEVKIT_VERSION`), and it teaches a
spelling that only works in trees that installed it.

**Rejected: a declared vehicle key that the CLI renders.** It is config over forks (rule 5), but no
existing consumer declares it, so every rendered line stays wrong until each one edits `devkit.toml`.
Nothing fixes itself, and the missing key needs its own absence line.

**Rejected outright: detecting `include Makefile.devkit` and rendering to match.** That is the tool
deciding what the project is (rule 9).

A consumer with its own vehicle gets it right by re-spelling the Project config block of its
agents, which it already does today.

Chris, 2026-09-11: go with the recommendation.
