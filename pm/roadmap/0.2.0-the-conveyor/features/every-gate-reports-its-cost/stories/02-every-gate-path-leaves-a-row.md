---
id: 0.2.0/every-gate-reports-its-cost/02-every-gate-path-leaves-a-row
feature: 0.2.0/every-gate-reports-its-cost
milestone: "0.2.0"
name: Every path that prints a verdict also files what it cost
status: reviewing
owner:
depends_on: ["0.2.0/every-gate-reports-its-cost/01-the-ledger-holds-what-a-gate-cost"]
---

# Every path that prints a verdict also files what it cost

<!-- What is observable when this ships. A story is an observation, not a task. -->

Run any gate — through the `gdk_gate` define, through `runners-self-test`'s open-coded
calls, or through `parse` / `lint` / `warnings` / `unit`, which publish their own verdict —
and one row lands in the building milestone's `ledger.jsonl`. A ledger that cannot be
written changes nothing about the gate's exit code.

## Two corrections to the feature file, found by reading the funnel

The feature file (lines 60-68) says *"the timer opens in `gdk_gate_capture` and the row is
written in `gdk_gate_verdict`"*. Reading `gdk_runners.sh` and the four self-publishing
runners, that produces two defects:

1. **`unit.sh` never calls `gdk_gate_capture`** — it uses `gdk_gate_publish`
   (`unit.sh:343`), the capture-then-parse shape. A timer that opens in `gdk_gate_capture`
   leaves `unit` — one of the five gates the audit says the `define` misses — with no
   duration at all.
2. **`gdk_gate_verdict` is called MORE THAN ONCE per run.** `parse.sh` calls it at
   lines 175, 183, 199, 209, 222 and 226; `warnings.sh` at 277, 292, 301, 312, 320;
   `unit.sh` at 349, 375, 385, 393, 401, 407, 411. Writing a row per call files up to six
   rows for one `make parse`, and the report's "what got slower" then averages a run
   against its own early-exit branches.

**The funnel is `gdk_gate_log` → `gdk_gate_verdict`, and the slot path is the key.**
`gdk_gate_log <gate>` is called exactly once per run by every one of those paths; it mints,
clears and names the transcript slot. The timer opens there, keyed by the slot path; the row
is written by the FIRST `gdk_gate_verdict` naming that slot, and a marker keyed on the same
path makes every later call for that run a no-op. `parse`'s two capture stages then sum into
one duration instead of reporting the sweep alone.

## How the shell reaches the CLI — hidden scope the feature file does not name

`gdk_runners.sh` has no idea how this package is invoked. `DEVKIT` is a *make* variable
(`Makefile.devkit:~93`, `uvx --from git+…@$(DEVKIT_VERSION) agentic-sdlc`) and is not in a
sourced library's environment. So:

- `gdk_runners.sh` reads `GDK_LEDGER_CMD`, defaulted empty, and records **only** when it is
  set — the same override-able-default shape every other `GDK_*` in that file's project-config
  header already has.
- `Makefile.devkit` gains ONE line exporting it: `export GDK_LEDGER_CMD ?= $(DEVKIT)`.

That second file is shared with `0.2.0/the-middle-tier-splits` (phase 2), which lands first.
Rebase onto it; do not restructure anything it wrote.

## Files this story may touch

- `src/agentic_sdlc/repo/installables/gdk_runners.sh` — `gdk_gate_log`, `gdk_gate_verdict`,
  the project-config header comment for `GDK_LEDGER_CMD`, the exported-function census near
  line 851, and the `--self-test` block (~line 540) which is where the new behavior is
  proven in shell.
- `src/agentic_sdlc/repo/installables/Makefile.devkit` — the one `export` line, nothing else.
- `tests/test_runners_installable.py`.
- `tests/test_makefile_gates.py` — only if the funnel assertion there needs the new call.

## Files it must stay out of

`parse.sh`, `lint.sh`, `warnings.sh`, `unit.sh`, `capture.sh` and every other runner — the
whole argument for the funnel is that they need no edit; touching one is evidence the funnel
was placed wrong. Also: all of `src/agentic_sdlc/repo/pm/` (story 01/03), `src/agentic_sdlc/cli.py`,
and `pm/roadmap/`.

## Acceptance criteria

1. **Fail open, proven by construction.** With `GDK_LEDGER_CMD` pointed at a script that
   exits 3, prints to stderr and hangs up, a gate whose command exits 0 still exits 0 and
   still prints its verdict line first; a gate whose command exits 7 still exits 7. Proven
   in `gdk_runners.sh --self-test` (a case beside the existing `GDK_GATE_EXIT` cases) and
   asserted from `tests/test_runners_installable.py`. **This is the risk-1 test: the funnel
   is on every gate in every consumer.**
2. **`GDK_LEDGER_CMD` unset records nothing and costs nothing** — no subprocess is spawned.
   Proven by a self-test case asserting a sentinel file the recorder would have created does
   not exist, so a consumer with no PM tree pays zero.
3. **One row per run, not one per verdict line.** A scripted gate that calls
   `gdk_gate_verdict` three times against one `gdk_gate_log` slot produces exactly one
   recorder invocation, and its duration spans from `gdk_gate_log` to the FIRST verdict.
   Proven by a self-test case counting recorder invocations. Without this the report is
   wrong for `parse`, `warnings` and `unit`, which is most of the measured cost.
4. **`unit`'s path is covered.** A gate that calls `gdk_gate_log` then `gdk_gate_publish`
   then `gdk_gate_verdict` — never `gdk_gate_capture` — still records a duration. Proven by
   a self-test case shaped like `unit.sh`.
5. **The census is absent, never zero.** `gdk_gate_verdict` receives `<TAG> <message>
   <logfile>` and no census; the message is free text (`"PASS (12 files)"`,
   `"COVERAGE FAIL (0 test scripts found)"`). Do NOT parse a number out of it — a regex over
   prose is how a gate ends up filing `census: 0` for a run that scanned 683 files. The
   recorder passes `--census` only when the caller set `GDK_GATE_CENSUS` before the verdict;
   otherwise the flag is omitted and story 01's row omits the key. Proven by a self-test case
   for each of set and unset, plus a `tests/test_runners_installable.py` assertion that no
   census is inferred from the message. *If a builder finds a way to make the census
   first-class without breaking the shipped 3-argument `gdk_gate_verdict` contract, that is a
   better answer — say so in the report; it is a minor bump either way and the orchestrator
   rules.*
6. `bash src/agentic_sdlc/repo/installables/gdk_runners.sh --self-test` exits 0, and
   `make runners-self-test` is green. Slice command for the loop:
   `python3 -m pytest tests/test_runners_installable.py -q`.

## Refusal matrix — `GDK_LEDGER_CMD` is an input surface

It is a command string this library executes, read from the environment, so it ships its
matrix here. Each is a `--self-test` case asserting the gate's own exit code is preserved and
no row is claimed:

| value | expected |
|---|---|
| unset / empty | no spawn at all (criterion 2) |
| a path that does not exist | gate unaffected, one line on stderr, exit code preserved |
| a command that exits non-zero | ditto |
| a command that writes to stdout | **must not pollute the verdict line** — a consumer greps `[TAG] … full log:` (hard rule 6); the recorder's stdout goes to `/dev/null` |
| a command that hangs | bounded, so a broken recorder cannot hang every gate in a consumer's pre-push hook. Use the library's own `gdk_run_bounded` |
| a gate name containing whitespace or a metacharacter (a mis-set `GATE_TAG`) | passed as ONE argv element, never word-split; story 01's grammar then refuses it and the gate is still unaffected |

**Adversarial cases against the docstring.** `gdk_gate_capture`'s comment block claims the
errexit suspend/restore is "the only shape that keeps PIPESTATUS readable" and that `|| true`
would reset it. The recorder call is a further simple command in that neighbourhood: prove
under `set -euo pipefail` that a gate whose command exits 7 still reaches its verdict AND
still reports 7 with the recorder present — the existing self-test at ~line 572 is the
template.

## Out of scope

- The Python side of the row — story 01 owns `ledger.py` and `pm/cli.py`.
- The report — story 03.
- Any edit to a language runner, or to the `gdk_gate` define in `Makefile.devkit`.
- Naming any consuming project (hard rule 8). Fixtures stay under `tests/fixtures/`.
