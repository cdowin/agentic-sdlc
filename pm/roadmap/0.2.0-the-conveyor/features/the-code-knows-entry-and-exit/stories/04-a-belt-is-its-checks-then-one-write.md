---
id: 0.2.0/the-code-knows-entry-and-exit/04-a-belt-is-its-checks-then-one-write
feature: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: A belt is its checks, then one write or a clean error (D12)
status: done
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
| 1 | integration | each belt: one false check → error line, exit 1, file byte-identical | `test_conveyor_close.py::test_a_false_check_is_named_exit_1_and_nothing_is_written`, `::test_close_feature_names_the_story_not_in_done_and_writes_nothing`; the machine itself at unit tier in `test_conveyor_driver.py::test_every_check_runs_and_prints_one_line_and_a_false_one_stops_the_write` |
| 2 | integration | all true → exactly one write, the first done state | `test_conveyor_close.py::test_all_true_writes_exactly_the_first_done_state_and_nothing_else`, `::test_the_written_state_is_the_configs_word_not_the_literal_done`, `::test_close_feature_all_true_writes_the_feature_status_once` |
| 3 | unit | --force writes and the ledger row names the false checks | `test_conveyor_deviation.py::test_force_writes_the_status_and_one_row_naming_the_false_checks` (+ `test_conveyor_driver.py::test_force_writes_over_false_checks_and_hands_them_to_the_recorder`) |
| 4 | unit | release prints the caller list and writes nothing but the status | `test_conveyor_driver.py::test_release_prints_the_callers_list_and_writes_nothing_but_the_status`; `adopt` writes nothing at all: `test_conveyor_adopt.py::test_the_whole_belt_writes_nothing_and_touches_no_repo_but_this_one` |
| 5 | unit | the rendered protocol carries every check and the after-list | `test_install_sdlc.py::test_the_rendered_protocol_carries_every_check_the_write_and_the_after_list`, `::test_this_repos_own_protocol_document_is_byte_current_and_describes_d12` |

The conveyor shrank from 4,318 to 2,347 source lines and its tests from 3,739 to 1,508;
`state.py`, `test_conveyor_state.py` and every `do()` are gone.

## Out of scope

Any automatic step. Any belt writing a file it was not asked about.

done: 549475f — every belt is its checks then one write; `state.py` and every `do()` deleted; the protocol renders from the four lists and the after-lists.
