---
id: 0.2.0/the-code-knows-entry-and-exit/06-the-review-findings-land
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: Every finding in the 0.2.0 review records lands
status: done
owner:
depends_on: []
---

# Every finding in the 0.2.0 review records lands

## Acceptance criteria

- `docs/reviews/2026-09-05-the-belt-reports-and-finishes.md`: every finding lands or is `rejected: superseded by D12` where D12 removed the thing it was against.
- `docs/reviews/2026-09-05-the-project-declares-its-flow.md`: F1 lands with phase 7; F2/F3 (`pm init` appends the flow to a config it did not write, byte-preserving, and the refusal names that command); F4 the CHANGELOG.
- `docs/reviews/2026-09-05-the-suite-is-cheap-or-it-declares-itself.md`: S1–S4 in `check budget` — a failed run is not graded ok, newest row wins by timestamp, the summary names only tiers it measured, the case ceiling reads both directions.
- `docs/reviews/2026-09-05-the-inner-levels-are-belts-too.md`: I2 lands with story 07.
- No shipped surface says the walk "stops at the first step" or documents `--skip`; the release skill source says D12.
- `devkit.toml`'s `prove-artifact` command has its `{version}` substituted.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | exit 2 from a callee → UNVERIFIABLE, walk finishes | tests/test_conveyor_steps.py |
| 2 | unit | ConfigError from a check() is exit 2 at the CLI | amend tests/test_conveyor_driver.py |
| 3 | unit | `check budget` grades a FAIL row as FAIL; picks the newest by timestamp; names measured tiers only; reads a shrink | amend tests/test_check_budget.py |
| 4 | unit | `pm init` appends the flow to a config it did not write, byte-preserving | amend tests/test_init_verb.py |
| 5 | unit | `{version}` substituted in a configured command | amend tests/test_conveyor_steps.py |
| 6 | integration | no shipped surface says the walk stops | amend tests/test_install_sdlc.py |

## Out of scope

Re-litigating a finding the record already rejected.

## Close

done: 524d3ff fe680e6 9a8b226 ecf4c0b b23bf9d 7d38251 — every finding in the belt-reports, project-declares-flow, suite-is-cheap, categories and ledger-rows records dispositioned; D11 recorded
