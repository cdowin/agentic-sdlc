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

## D2 — 2026-09-11 — the vehicle bootstraps through the pinned uvx form, quotes safely, and costs the exit code

From the spec scout, C1, M1, M2 and m5 (`docs/reviews/2026-09-11-0.8.0-spec-review.md`). D1 stands.
These are the conditions that make it true.

**Bootstrap (C1).** A consumer's `Makefile.devkit` has no `sdlc` target until `install-gates --force`
has run, so a `make sdlc` line printed before that fails with `No rule to make target`. The commands
that WRITE `Makefile.devkit` (`install-gates`, `init`'s next steps, and `adopt`'s remedy for a stale
`Makefile.devkit`) are rendered in the pinned form, `uvx --from "git+…@v<__version__>" agentic-sdlc
install-gates --force`. The tool reads its own version, so nothing is inferred. `adopt` names
`install-gates` first among the installers.

**Quoting (M2), probed by the scout.** `ARGS='pm set x changelog "costs $5"'` wrote `costs ` and exited
0. That is rule 4's second sin. And `ARGS` leaks into every sub-make a belt spawns. The recipe uses
`$(value ARGS)`, `unexport ARGS`, and runs `$(DEVKIT)` with `MAKEFLAGS=`. A rendered free-text line
wraps its argument in single quotes (precedent: `pm/cli.py:2074`), and a unit case round-trips every
rendered vehicle line through `shlex`. `sdlc` joins `.PHONY` (m5).

**Exit codes (M1), a known cost, accepted.** Make turns any nonzero recipe exit into 2, so through
the vehicle a verb's 1 reads as make's 2, with the verb's own code in make's `Error N` line. Rule 6's
contract is the CLI's, and it is unchanged. The vehicle's `make help` line and the dispatch preamble's
EXIT CODES line say where the verb's code shows up. The milestone's ship criterion is reworded to "the
verb exited 0 or 1, and make never said `No rule` or `command not found`".

**Rejected: making the recipe preserve the code** (`; exit $$?` tricks, or `.IGNORE`). Make still
reports 2 to its caller. There is no portable way to pass 1 through, and a trick that works on GNU make
4 alone is a new portability surface.

Orchestrator decision under Chris's standing "go with the recommendations" for 0.8.0.
