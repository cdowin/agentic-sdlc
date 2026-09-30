---
id: "ms-a-green-run-costs-under-two-minutes"
kind: milestone
name: a green run costs under two minutes
status: building
depends_on: []
branch: milestone/0.18.0-a-green-run-costs-under-two-minutes
mode: parallel
version: 1.0.0
changelog:
order:
  - "ft-ci-runs-each-suite-once"
  - "ft-the-suite-proves-each-thing-once"
  - "ft-every-rung-reuses-a-green-run"
  - "ft-the-static-gate-takes-seconds"
  - "ft-the-tree-is-walked-once"
  - "ft-the-kit-ships-as-a-locked-wheel"
  - "ft-no-ref-dangles-after-a-grain-leaves"
---

# ms-a-green-run-costs-under-two-minutes — a green run costs under two minutes

Issues #98 (added 2026-09-30) and the 0.17.0 timing. Measured at 0.17.0 (2026-09-29). CI `verify` took 4.5 minutes for a stdlib package: `check` 91s
(of which `check hooks` 82-85s; 4s on a laptop), `test` 84s, then `matrix` 76s re-ran the suite,
the floor interpreter in full a second time. The test tier is 866 test-seconds, and 64% of it is
three spawn-heavy modules. The process re-bought green runs: `close feature` x6 on one commit ran
`make test` six times (12 min), and `release` cannot reuse a green `make milestone` because the
gate is asked at `done` (0.17.0 review C2). Consumers pin this kit and pay the same shapes.

## Ship criterion

- CI `verify` on this repo: under 2 minutes wall, measured on the PR.
- `make milestone` on an idle laptop: under 90s. `make unit`: under 10s. No test case over 5s.
- After a green `make milestone`, `release <version>` on the same commit reuses it (seconds).
  `close feature` on N features of one commit runs the feature rung once.
- `make check` on an unchanged tree: under 2s here, under 10s for a consumer; each gate reused
  by its input hash across every caller (#98).
- `pm validate` walks each pool once per process: a 2,000-grain tree under its budget (#100).
- The kit ships as a wheel on a public static index, built once per tag; a consumer locks it with
  uv and calls `.venv/bin/agentic-sdlc`; the Makefile git pin is gone, so this is 1.0.0 (#101).
- `check hooks` names each hook's self-test time; no hook costs over 2s in CI.
- A consumer takes all of it through the pin bump: stock `ci-verify.yml`, `Makefile.devkit`,
  the rung reuse. Nothing here names a consumer.
- `make milestone` green on this tree, with `[tests]` budgets LOWERED to the new costs.

## Risks

- Reuse is rule 4's first sin if it is wrong. Every exclusion from a digest gets a planted-drift
  probe that must re-run.
- Moving a real-repo test to a fixture can drop what it proved. Each move names the case that
  still proves it against the real thing, once.
