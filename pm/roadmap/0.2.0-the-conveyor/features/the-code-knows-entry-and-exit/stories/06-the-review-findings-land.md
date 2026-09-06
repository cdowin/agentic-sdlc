---
id: 0.2.0/the-code-knows-entry-and-exit/06-the-review-findings-land
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: Every finding in the 0.2.0 review records lands, and D11 is recorded
status: building
owner:
depends_on: []
---

# Every finding in the 0.2.0 review records lands, and D11 is recorded

## Acceptance criteria

- `docs/reviews/2026-09-05-the-belt-reports-and-finishes.md`: B1–B4 and M1–M4 land; Q1 is answered by D11 — a callee's exit 2 is UNVERIFIABLE, not NOT-TRUE, and the walk still finishes.
- `docs/reviews/2026-09-05-the-project-declares-its-flow.md`: F1–F4 land (F1 is phase 7's census; F2/F3 are the `init` append path and the refusal naming the command that fixes it; F4 the CHANGELOG).
- `docs/reviews/2026-09-05-the-inner-levels-are-belts-too.md`: I2 lands with story 07.
- Every "stops at the first step" / `--skip` sentence is gone from the shipped template, `install.py`, `SDLC.md` and the release skill source.
- `devkit.toml`'s `prove-artifact` command has its `{version}` substituted by the conveyor.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | exit 2 from a callee → UNVERIFIABLE, walk finishes | tests/test_conveyor_steps.py (`_own_verdict` lives in steps; no case asked it about exit 2) |
| 2 | unit | ConfigError from a check() is exit 2 at the CLI | amend tests/test_conveyor_driver.py |
| 3 | unit | `pm init` appends the flow to a config it did not write, byte-preserving | amend tests/test_init_verb.py |
| 4 | unit | `{version}` substituted in a configured command | amend tests/test_conveyor_steps.py |
| 5 | integration | no shipped surface says the walk stops | amend tests/test_install_sdlc.py |

## Out of scope

Re-litigating a finding the record already rejected.
