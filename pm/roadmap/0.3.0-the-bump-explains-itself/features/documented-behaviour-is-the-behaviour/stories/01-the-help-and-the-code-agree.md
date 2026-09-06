---
id: 0.3.0/documented-behaviour-is-the-behaviour/01-the-help-and-the-code-agree
feature: 0.3.0/documented-behaviour-is-the-behaviour
milestone: "0.3.0"
name: every documented exit code is the one that runs
status: done
owner:
depends_on: []
---

# every documented exit code is the one that runs

Three findings of the shape "the surface says one thing and the code does
another". A consumer should not have to run the binary to learn its contract.

## Acceptance criteria

1. No `--help` in the package documents an exit code the code does not return,
   held by a test that reads the help text and the exit code TOGETHER.
2. `pm --help` names the belt beside the status-write path that bypasses it.
3. The no-ledger condition is reported once per run, as information.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_the_documented_exit_code_is_the_one_the_code_returns` over 21 enumerated surfaces; `test_no_help_names_an_exit_code_outside_the_contract`; `test_a_help_that_files_a_condition_under_the_wrong_code_is_caught` (the deliberately-broken probe) | new; help text was asserted for PRESENCE of verbs, never for AGREEMENT with behaviour. Reuses `test_check_budget`'s fixtures rather than a second set (rule 10) |
| 1 | unit | `test_the_exit_contract_census_is_not_zero` | rule 4: a claim graded against nothing is a named failure |
| 2 | unit | `TestTheHelpNamesTheBeltBesideThePathThatBypassesIt` | new; it was written to `xfail` until the USAGE text landed, and disarmed itself when it did |
| 3 | — | fixed upstream by `the-ledger-binds-to-the-current-release` | confirmed gone: the recorder now resolves through `release_ledger_dir`, and the two remaining `is in progress` refusals are `ledger record` (dispatch/session rows) and `ledger report`, neither of which runs per gate |

## The finding-1 ruling: the HELP changed, not the code

`git log -S'both are findings, never a pass'` returns one commit, a docs-only
compression that fused two true sentences into one false one. The exit-code line
in the same docstring never listed unmeasured, and an existing test already
asserted exit 0 with its reasoning. Flipping the code would redden any tree
declaring a ceiling for a tier not yet run — a breaking change wearing a minor
version.

**What did change:** ceilings declared with not one `gate` row in the whole
ledger is now a FAIL. That is rule 4's zero census — a verdict over nothing —
and it is a different condition from one tier not having run. Verified not to
redden this repo, which has rows.

## Out of scope

`.claude/rules/pm-execution.md` step 4 describes the bypassing path without
naming the belt. Flagged by the builder; a doc-hygiene pass, not this story.

## Close

done: 6273959 — 21 help surfaces held to the exit codes they claim, the belt
named beside the path that skips it, and the zero census made a failure.
