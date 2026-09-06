---
id: 0.2.0/the-code-knows-entry-and-exit/04-a-belt-is-its-checks-then-one-write
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: A belt is its checks, then one write or a clean error (D12)
status: planning
owner:
depends_on: []
---

# A belt is its checks, then one write or a clean error (D12)

## Acceptance criteria

- `close story <id>`: checks — the story exists; `verify --story` over its commit range is green; nothing outside the roadmap directory is uncommitted; the story carries a `done:` line. Write: status → the first `done` state.
- `close feature <id>`: checks — every story is in the `done` category (each one that is not is named); `reviewed:` points at a record that parses; no finding in it is `open`. Write: status → first `done` state.
- `release <version>`: checks — tree clean; HEAD is the milestone's `branch:`; `## Unreleased` non-empty; every feature in `done`; every review finding dispositioned; no open bug names the milestone; every version site names `<version>`; `make milestone` green. Write: milestone status → first `done` state. Then PRINT the caller's list: retitle the changelog, push, open the PR, tag, prove the artifact.
- `adopt`: checks only; it writes nothing.
- Every check runs and prints; any false → `error: <check>: <what is false>` per check, exit 1, no write. `--force` writes and the ledger row lists the false checks. `--skip` stays gone.
- The driver and steps shrink to that: no `do()` on any step but the one write; the run-state file under `.agentic-sdlc/` goes, because every run re-reads the tree.
- `docs/sdlc-protocol.md` renders from the four check lists and the after-belt instructions.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | each belt: one false check → error line, exit 1, file byte-identical | replace tests/test_conveyor_close.py |
| 2 | unit | all true → exactly one write, the first done state | replace tests/test_conveyor_close.py |
| 3 | unit | --force writes and the ledger row names the false checks | replace tests/test_conveyor_deviation.py |
| 4 | unit | release prints the caller list and writes nothing but the status | replace tests/test_conveyor_driver.py |
| 5 | unit | the rendered protocol carries every check and the after-list | amend tests/test_install_sdlc.py |

## Out of scope

Any automatic step. Any belt writing a file it was not asked about.
