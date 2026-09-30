---
id: ft-ci-runs-each-suite-once
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: ci runs each suite once
status: building
reviewed: docs/reviews/2026-09-30-0.18.0-ci.md
depends_on: []
consumed_by: []
changelog: `make milestone` runs each suite once: `matrix` runs only the interpreters past `PY_FLOOR`, in parallel, and the stock `verify.yml` runs them as a concurrent `python` job with a `matrix` aggregate that `install-ci --ruleset branch` now requires beside `verify`; `GDK_MILESTONE_SKIP` removes named tiers from `milestone`; `check hooks` prints each hook's seconds; and a VERBOSE gate streams its lines as they arrive.
---

# ci runs each suite once

Measured: CI `make milestone` = `check` 91s + `test` 84s + `matrix` 76s. `matrix` re-runs the
floor interpreter's full suite right after `test` ran it, and runs the other three serially.
`check hooks` took 82-85s on the runner in two runs and 4s on a laptop; the cause is not known.

## Decided (do not re-plan)

- **The milestone rung runs each suite once.** `matrix` never re-runs the floor interpreter:
  it runs only the NON-floor interpreters, each with the no-spawn tier (`-m "not shell"`).
  `PY_MATRIX` stays `3.11 3.12 3.13 3.14`; its runs go parallel (one process per interpreter,
  each its own log), not serial. Applies to `Makefile.tiers` here and to whatever the stock
  `Makefile.devkit` / `project-Makefile` composes for consumers.
- **CI runs the matrix as its own job, concurrently.** The stock `ci-verify.yml` gets a second
  job: `strategy.matrix` over the non-floor interpreters, running the unit tier with
  `uv run --python <v>`. The `verify` job runs `make milestone` WITHOUT the matrix (a make
  variable or target the workflow passes; the developer picks the spelling). Required check
  names stay stable: `verify` remains the one required check; the matrix job is named so the
  ruleset `install-ci --ruleset branch` prints can require it too — update that payload.
  Re-install this repo's workflows with `install-ci --force`.
- **`check hooks` prints each hook's time.** The PASS line (or a detail line above it) names
  every hook with its self-test seconds, slowest first (rule 11: the cost is visible where you
  stand). Then FIND the 82s: reproduce what differs on a runner (a fresh clone, `setup-hooks.sh`
  armed, no `~/.gitconfig`, 2 cores, `CI=true`) in a scratch clone. Fix the cause at its layer.
  If you cannot reproduce it, ship the timing line and say so; the orchestrator reads it off
  the first CI run.
- Cache: `setup-uv`'s cache stays as installed (off on PR by v10's default); do not add caching
  that a PR could poison.

## Ship criterion

- `make milestone` runs the full suite once; the matrix runs only non-floor interpreters,
  parallel, no-spawn tier.
- A fresh `install-ci` writes a verify workflow with a concurrent matrix job, and the ruleset
  payload names both checks.
- `check hooks` output names each hook's time.

## Proof budget

  cases: amend the ci-workflow shape tests and the check-hooks output case; no new module
  tier: unit (workflow text), one integration case for the timing line if it must spawn
  lands in: tests/test_ci_workflows.py, tests/test_check_hooks.py (coordinate: another lane rewrites test_check_hooks.py's fixtures — add, do not restructure)
  what already covers this: workflow shape and pin tests; nothing measures matrix duplication.
