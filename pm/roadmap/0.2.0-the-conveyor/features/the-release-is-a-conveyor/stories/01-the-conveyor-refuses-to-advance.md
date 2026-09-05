---
id: 0.2.0/the-release-is-a-conveyor/01-the-conveyor-refuses-to-advance
feature: 0.2.0/the-release-is-a-conveyor
milestone: "0.2.0"
name: The release runs as a step machine whose position is on disk
status: reviewing
owner:
depends_on: []
---

# The release runs as a step machine whose position is on disk

An operator runs `agentic-sdlc release 0.2.0`, gets interrupted, clears context, and runs
it again from a fresh session. The second run reports the same position as the first, skips
what is already true, and stops on the same step for the same reason. Nothing was carried in
anyone's head.

This is the machine, not the protocol: the driver, the three step kinds, the run state, and
the `release` / `adopt` routes. The 21 release steps themselves are story 03; the step list as
config is story 02; the skip is story 04; the generated doc is story 05. This story ships the
shape those four fill in, and proves it against a registry of FIXTURE steps built in the test
file — so the machine is provable before a single real step exists.

## The three kinds, and why the third is not a hack

Rule 1 is stdlib-only forever, so `pr-open`, `ci-green` and `merge` cannot be performed here.
The audit (`docs/reviews/2026-09-05-0.2.0-scope-audit.md` § G.2) rules them judgement steps
whose `check()` is a project-configured command. That ruling is only honest if the kind is a
first-class shape rather than an escape hatch bolted onto the automatic kind:

| kind | `check()` | `do()` | `verify()` |
|---|---|---|---|
| `AUTOMATIC` | is the postcondition already true? | performs it | re-asks `check()`, and the step is DONE only if it now answers yes |
| `GATE` | runs a command, exit 0 = true | none — a gate is not made true by running it again | same as `check()`; there is nothing else to prove |
| `JUDGEMENT` | reads the ARTIFACT of a judgement — a verdict block, a merge commit, a configured command's exit code | prints precisely what a human must do, and returns NOT-DONE | same as `check()` |

**A `JUDGEMENT` step with no artifact and no configured command is `UNVERIFIABLE`, which is a
refusal to advance — never a pass.** That is the whole difference between this machine and the
prose it replaces. `verdict.py` already rules this way for a record whose block does not parse
(`the-belts-refuse-to-advance` risk 2); the driver inherits the ruling rather than inventing a
softer one.

## Rule 4 lives in `verify()`, and it is the reason `verify()` exists at all

A step that reports DONE without its postcondition holding is the cardinal sin in step-machine
clothing. So **`do()` never decides its own outcome.** The driver calls `do()`, discards its
return value as advisory text only, and asks `check()` again. A step is DONE when `check()`
says so and at no other moment.

The same rule governs the state file: **it is a cache of `check()` answers, never the
authority.** On resume, a step the file records as DONE is re-`check()`ed before the driver
moves past it; a disagreement is resolved in favour of the tree, the file is corrected, and the
line says so. A run state that can assert a step is done while the tree says otherwise is the
lie this feature exists to end.

## Where the run state lives, and why there

`<repo-root>/.agentic-sdlc/run/<operation>.json` — **gitignored**, one file per operation.

1. **It is working state, not a record.** The RECORD is the ledger row in
   `pm/roadmap/<milestone>/ledger.jsonl` (story 04), which is tracked and durable. Position is
   the thing you throw away when the run finishes; a tracked position file would be a second
   scoreboard beside the ledger, and per `.claude/rules/pm-execution.md` a second scoreboard
   lies.
2. **`tree-clean` is itself a step in the list.** A TRACKED state file would be dirtied by the
   very run that checks the tree is clean — the machine making its own precondition false, which
   is the same self-defeating coupling the three release incidents were made of. Gitignoring is
   what keeps `tree-clean` answerable.
3. **Per checkout, so a worktree gets its own.** `tools/dev/agent-worktree.sh` puts parallel
   builds in sibling checkouts; a shared position would have two runs overwriting one file.
4. **One file per operation**, so an `adopt` run in progress and a `release` run cannot clobber
   each other — and so `adopt` (its own feature) needs no edit to this file's owner.
5. **Losing it costs nothing.** Every `check()` is a question about the tree, so a deleted state
   file means the next run re-derives the position by asking. That is why it can be ignored
   safely, and it is the test that proves points 1–4 were the right call.

## Refusal matrix — `release <version>` and the run-state file (SDLC.md §5)

Two input surfaces ship here. Each row is a test, each proven to refuse **without a write and
without running a step**.

**The `<version>` argument** — it is a milestone id, so it reuses the pm id grammar rather than
inventing a second one (a second grammar is a second answer):

| input | expected |
|---|---|
| no argument at all | exit 2, usage, names the argument |
| `../../etc/passwd`, `0.2.0/../0.3.0` | exit 2 — traversal, refused before any path is joined |
| `/0.2.0`, `~/0.2.0`, `C:\0.2.0` | exit 2 — absolute path, home expansion, backslash |
| `0.2.0*`, `0.2.[0-9]`, `*` | exit 2 — a glob is not an id |
| `""`, `"   "`, `.`, `..` | exit 2 — empty / whitespace-only / dot segments |
| `file:///0.2.0`, `https://x/0.2.0` | exit 2 — a scheme is not an id |
| a 4 KB version string | exit 2 — over-length, named as such |
| `0.2.0` naming no milestone directory | exit 1, refused, names the directory it looked for and does not create it |
| two versions (`release 0.2.0 0.3.0`) | exit 2 — one operation, one milestone |
| an unknown flag (`--yolo`) | exit 2 — never silently ignored (the `_run_check` precedent, `cli.py:211`) |

**The run-state file** — it is read from disk, so it is a payload parser and hostile by
default:

| input | expected |
|---|---|
| not JSON at all / truncated mid-object | refuse with the path and the reason; do NOT silently start from step 0 |
| valid JSON that is not an object (`[]`, `3`, `"x"`) | refuse, naming what it holds |
| an `operation` or `version` that is not this run's | refuse — it is another run's file, not this one's stale copy |
| a `step` name not in the configured list | refuse and name it; a renamed step must not resume into a hole |
| a duplicate step entry, or a step marked DONE that `check()` now denies | the tree wins, the file is corrected, and the correction is PRINTED |
| the file is a directory / not writable / its parent is a file | refuse with the path (`install.destination_defect` is the existing shape) |
| a `reason` string carrying U+2028 / U+2029 | round-trips as ONE record — the `ledger.LINE_BREAKERS` hazard, one layer up |

## Acceptance criteria

1. `agentic-sdlc release --help` and `agentic-sdlc adopt --help` print the verb contract and
   exit 0; `cli.py` routes both to `conveyor.main(operation, argv)`. Proven by
   `tests/test_conveyor_driver.py`.
2. `StepKind` is a closed set of exactly three members and the driver dispatches off it with no
   `if name == …` special cases. Proven by a test that asserts every registered step has a kind
   in the set, and by a fixture step of each kind exercised through one `walk()`.
3. **A `do()` that lies is caught.** A fixture `AUTOMATIC` step whose `do()` returns success
   while `check()` still answers false leaves the run STOPPED on that step, with a line naming
   the postcondition that did not hold. This test must fail at HEAD of the story's own branch
   before `verify()` exists. `tests/test_conveyor_driver.py::test_do_that_lies_does_not_advance`.
4. **A `JUDGEMENT` step with no artifact and no configured command exits non-zero and prints
   what the operator must do.** It never prints DONE and never advances.
   `tests/test_conveyor_driver.py::test_judgement_without_artifact_refuses`.
5. **Resumability.** Run a fixture list, stop it on a judgement step, delete nothing, run again:
   the earlier steps report `already true` and are not re-performed. Then DELETE the state file
   and run again: the same position is re-derived from `check()` alone, byte-identical report.
   `tests/test_conveyor_state.py`.
6. The state file lands at `.agentic-sdlc/run/<operation>.json`, and `.gitignore` (this repo's,
   and the block `agentic-sdlc init` writes) carries `.agentic-sdlc/`. Proven by a test that
   runs the driver in a scratch repo and asserts `git status --porcelain` is unchanged.
7. Every row of both refusal matrices above is a test, each asserting the exit code AND that no
   file was written and no step's `do()` ran.
8. Exit codes follow rule 6: `0` the run completed, `1` it stopped on a step (a finding), `2`
   usage or config error. A stopped run names the step, its kind, and what would make it true.

## Files this story may touch

- `src/agentic_sdlc/repo/conveyor/__init__.py` — NEW
- `src/agentic_sdlc/repo/conveyor/driver.py` — NEW (`Step`, `StepKind`, `walk`, `main`)
- `src/agentic_sdlc/repo/conveyor/state.py` — NEW
- `src/agentic_sdlc/cli.py` — the `release` and `adopt` routes, and the docstring lines for them
- `.gitignore`
- `src/agentic_sdlc/repo/init.py` — only the `.gitignore` block it writes
- `tests/test_conveyor_driver.py`, `tests/test_conveyor_state.py` — NEW

## Files this story must stay out of

`src/agentic_sdlc/repo/conveyor/config.py` (story 02), `release_steps.py` (03), `skip.py` (04),
`render.py` (05), `src/agentic_sdlc/repo/pm/ledger.py` (04),
`src/agentic_sdlc/repo/install.py` (05), `src/agentic_sdlc/core/config.py` (02), `SDLC.md` and
`.claude/skills/release/SKILL.md` (05), and everything under
`src/agentic_sdlc/repo/checks/`.

**`cli.py` is shared with `0.2.0/adopt-is-a-conveyor/01`, which `depends_on` this feature.**
That is serialization by dependency, not parallel work: this story adds BOTH routes, so the
adopt story adds none.

## Out of scope

- The real step definitions — story 03. This story's only steps are fixtures in its test file.
- Reading `[release] steps` from `devkit.toml` — story 02. `walk()` takes a registry and a
  list; who supplies them is not this story's question.
- `--skip` — story 04. The flag is parsed as unknown here and exits 2 until that story lands.
- Any change to `verdict.py`, `checks/pm.py`, or the pm state vocabulary.

## Close

done: 6e9388d — the driver, three step kinds, run state as a CACHE of check() answers and
never the authority. A lying do() cannot advance the machine — that test is the feature, and
it was watched failing with the following step having run.
