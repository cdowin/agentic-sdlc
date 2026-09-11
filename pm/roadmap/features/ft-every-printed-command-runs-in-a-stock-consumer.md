---
id: ft-every-printed-command-runs-in-a-stock-consumer
kind: feature
milestone: "ms-a-consumer-can-take-the-bump"
name: every command the kit prints runs in a stock consumer
status: planning
reviewed:
depends_on: ["ft-the-shipped-words-match-the-shipped-tool"]
consumed_by: []
changelog:
order:
  - "st-the-stock-wiring-has-one-vehicle-and-the-cli-prints-it"
  - "st-every-shipped-citation-resolves-through-the-stock-wiring"
---

# every command the kit prints runs in a stock consumer

Issues: #22 #36 (#36 is the sharpest case of #22: a line headed "run by you" that cannot be run).

The stock wiring never puts `agentic-sdlc` on PATH. `Makefile.devkit` defines
`DEVKIT := uvx --from "git+…@$(DEVKIT_VERSION)" agentic-sdlc` and passes through only `pm`,
`check all` and `gates-extra`. The kit still tells people to run it bare:

- about 109 backticked `agentic-sdlc <verb>` citations across 23 files under `installables/` and
  `pm/guidance/`, measured on origin/main;
- about 63 more in strings the CLI renders: the D11/D12 hints in `checks/pm.py` (D12 alone printed
  157 times on one consumer tree), `next:` lines, and `dispatch.py:167`'s RECORDING line;
- `pm-operator.md:16`, whose first instruction is a bare `agentic-sdlc dispatch`, so the agent's first
  tool call is `command not found`.

`dispatch`, `changelog`, `close`, `release`, `adopt`, `verify`, `lesson` and `cite` have no
passthrough at all. The dispatch preamble's STATIC GATES line also lists `[checks] all` and not
`[gates] extra`, so an agent that trusts it runs 4 of one consumer's 25 static gates.

## The decision this feature opens with

**How does a stock consumer reach every verb?** It must be decided before the stories are dispatched,
with `pm decide` on this feature:

1. **A generic passthrough in `Makefile.devkit`**, e.g. `make sdlc ARGS="dispatch --grain x"`. This
   is the cheapest: one target over the `$(DEVKIT)` that already exists, and no new file. (recommended)
2. An installed shim, `tools/dev/agentic-sdlc`, that reads the pin. It makes the bare citations true
   as written, but it is another installable to keep byte-current.
3. A declared vehicle key that the CLI renders. It is config over forks (rule 5), but every consumer
   has to declare it before any line is right.

**Detecting "this Makefile includes Makefile.devkit" and rendering to match is out.** That is the
tool deciding what the project is (rule 9).

Changing rendered lines is a line-shape change (rule 6), so this is a minor bump at least.

## Ship criterion

In a scratch consumer wired exactly as the README says, with nothing else on PATH, every pasteable
line the CLI renders runs as printed. A test resolves every shipped `agentic-sdlc <verb>` citation
through the stock wiring and fails by file and line on one that would not run. The dispatch preamble
names the whole static gate set the project's `make check` runs.

**Accepted means closed on GitHub:** #22 and #36 are each closed with a comment citing this feature
and its commit hash(es) (SDLC.md §2).

## Proof budget

  cases: 2–3
  tier: unit. The citation census is a text scan, and resolving a verb against the router is a table
    lookup, the way 0.6.0 resolves role-verb citations
  lands in: the module that already holds the 0.6.0 role-verb citation test. Amend it, don't add a new one
  what already covers this: 0.6.0 checks that each cited verb EXISTS in the router, not that the stock
    wiring can REACH it. That gap is exactly this issue.
