---
id: st-the-stock-wiring-has-one-vehicle-and-the-cli-prints-it
kind: story
feature: ft-every-printed-command-runs-in-a-stock-consumer
milestone: "ms-a-consumer-can-take-the-bump"
name: the stock wiring reaches every verb, and every line the CLI renders names it
status: done
owner: agent
depends_on: []
changelog: `Makefile.devkit` gains `make sdlc ARGS='<verb> …'`, which reaches every verb at your pin, and every command the CLI prints for you to run is now spelled `make pm|sdlc ARGS='…'` with free text single-quoted; `ARGS` no longer leaks into sub-makes, the dispatch preamble's STATIC GATES lists `[gates] extra` and the stock roster, and a stale `Makefile.devkit` is remedied first with the pinned `uvx … install-gates --force` — run `install-gates --force` before anything else when you take this bump.
---

# the stock wiring reaches every verb, and every line the CLI renders names it

Issues: #22 (the vehicle, the rendered hints, STATIC GATES), #36.

The vehicle is decided (feature D1): **`make sdlc ARGS="<verb> …"`**, one `Makefile.devkit` target
over the existing `$(DEVKIT)`.

The lines the CLI RENDERS, as opposed to the prose it installs (the next story):

- `dispatch.py:167`, the RECORDING line under *"rendered here, run by you"*:
  `agentic-sdlc pm ledger record --grain … --agent-type …`;
- the D11 and D12 finding hints in `checks/pm.py` (`:961`, `:1011`). The D12 hint printed 157 times on
  one consumer tree;
- `next:` lines from the belts, and the `pm/inventory.py:1109` / `conveyor/steps.py` hints;
- `dispatch.py:192-193`, STATIC GATES: `_roster()` renders `[checks] all` and never `[gates] extra`.

## Acceptance criteria

1. `Makefile.devkit` has an `sdlc` target that reaches every CLI verb through the pinned
   `$(DEVKIT)`, listed by `make help`, and `install-gates` installs it. This repo's own copy is
   re-installed byte-current.
2. Every command the CLI renders for a human to run is spelled `make sdlc ARGS="…"` (or
   `make pm ARGS="…"` for a pm verb), from one constant. Nothing is detected from the Makefile (rule 9).
3. `dispatch --grain <id>`'s RECORDING line, pasted verbatim into a scratch consumer wired as the
   README says with nothing on PATH, runs and files its row.
4. STATIC GATES lists `[checks] all` AND `[gates] extra`, or says in words that `make check` runs
   more than it lists.
5. `bash -c 'command -v agentic-sdlc'` is empty in the probe consumer. The proof must not pass
   because the builder's shell has the tool on PATH.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 2 | unit | every rendered command string resolves through the vehicle | the next story's census covers rendered strings too |
| 3, 5 | integration (it IS a process) | scratch consumer, paste the rendered line | new, the only process case in the feature |
| 4 | unit | render the preamble over a config with `[gates] extra` | amend the dispatch render case |

## Semver

Minor: a new `Makefile.devkit` target and changed rendered line shapes (rule 6).

## Amended from the spec scout (C1, M1, M2, m4, m5, M8) — feature D2

6. **Bootstrap:** every command that WRITES `Makefile.devkit` (`install-gates`, `init`'s next steps,
   and `adopt`'s remedy for a stale `Makefile.devkit`) renders in the pinned form,
   `uvx --from "git+…@v<__version__>" agentic-sdlc install-gates --force`, reading the tool's own
   version. `adopt` names `install-gates` first. Probe: a scratch consumer holding a 0.7.0
   `Makefile.devkit` (no `sdlc` target) is told the pinned command, not `make sdlc`.
7. **Quoting:** the recipe uses `$(value ARGS)`, `unexport ARGS`, and runs `$(DEVKIT)` with
   `MAKEFLAGS=`. `sdlc` is in `.PHONY`. Every rendered free-text argument is single-quoted. A unit
   case round-trips every rendered vehicle line through `shlex.split`, and a probe writes
   `pm set x changelog 'costs $5'` through the vehicle into a scratch tree and reads back `costs $5`.
8. **Exit codes:** `make help`'s `sdlc` line and the dispatch preamble's EXIT CODES line say that
   through make, a verb's code shows up in make's `Error N` line (D2).
9. **STATIC GATES with nothing declared (m4):** `_roster()` returns `()` when `[checks] all` is not
   declared (`dispatch.py:202-214`), so a stock consumer gets no line. The stock default must reach
   the renderer without `repo/` importing `cli.py`'s `KNOWN_GATES` (move the constant down, or pass it
   in).
10. **The probe runs the checkout, not the network (M8):** criteria 3 and 5 set `DEVKIT=` to this
    checkout (`Makefile.devkit:17-23` already supports that). 0.8.0 is not tagged, and `uvx --from
    git+…@<pin>` would run old code.

## Close

done: 188c831 — `make sdlc ARGS=` over the pinned $(DEVKIT) with value/unexport/MAKEFLAGS= quoting; one helper (repo/vehicle.py) spells every rendered command (73 -> 20 bare strings in src/, the rest usage/prefixes); STATIC GATES names [gates] extra and the stock roster; Makefile.devkit remedy is the pinned uvx install-gates; a pasted RECORDING line runs with nothing on PATH (tests/test_makefile_include.py). Hand-typed double-quoted ARGS still expands $ — the shell does it before the CLI sees it; the single-quote rule is documented, no guard possible.
