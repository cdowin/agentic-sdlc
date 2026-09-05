---
id: 0.2.0/the-release-is-a-conveyor/04-every-deviation-is-a-ledger-row
feature: 0.2.0/the-release-is-a-conveyor
milestone: "0.2.0"
name: A skipped step is a ledger row with a reason, never a silence
status: reviewing
owner:
depends_on: ["0.2.0/the-release-is-a-conveyor/01-the-conveyor-refuses-to-advance", "0.2.0/the-release-is-a-conveyor/03-the-gate-cannot-run-before-the-review-landed"]
---

# A skipped step is a ledger row with a reason, never a silence

After 0.2.0 ships, `pm/roadmap/0.2.0-the-conveyor/ledger.jsonl` holds one row per step of the
release that produced it — what ran, when, and for anything that did not run, **who said so and
why**. Reading the ledger tells you how the release actually went, not how the protocol says
releases go.

Chris's ruling, 2026-09-04: *steps are skippable, and a skip is RECORDED.* A protocol nobody
can deviate from gets worked around, and a worked-around protocol teaches nothing. Deviation
stays possible; **invisible** deviation does not.

## The run record is the durable half; the state file is not

Story 01's `.agentic-sdlc/run/<operation>.json` is gitignored working state — a cache of
`check()` answers, thrown away when the run ends. **The ledger row is the record**, tracked,
appended, and living in the milestone directory that owns it, so `pm retire` removes it with the
directory and git is the archive (`ledger.py:35`).

That split is what makes ship criterion 8 answerable at all: the evidence that 0.2.0 was
released *through* the conveyor is a set of committed rows, not a claim in a report.

## Row shape — minted in `ledger.py`, beside `status_row` and `decision_row`

A new `KIND_STEP` constant and a `step_row()` function go where the other two live. Row minting
is `ledger.py`'s job (it owns `dumps`, `TS_FORMAT`, `LINE_BREAKERS` and `ROW_KEYS`); a second
module writing JSONL by hand would be a second serialisation contract, which
`dumps`'s docstring exists to prevent.

Fields: `ts`, `kind: "step"`, `grain` (the milestone id), `operation` (`release` / `adopt`),
`step`, `outcome` (`done` | `skipped` | `stopped`), and `reason` — **present only on `skipped`,
and never empty**. `COPY WHAT THE RUN DID, OMIT WHAT IT LACKS, INVENT NOTHING`, the rule
`ledger.py:124` already states for the usage rows: no sentinel reason on a `done` row, no
"unknown" standing in for a field that was absent.

**A row is appended when the outcome is decided, never before.** A `done` row is written after
`verify()` answered yes — writing it beside `do()` would be exactly the report-without-the-
postcondition that rule 4 calls the cardinal sin.

## Refusal matrix — `--skip <step> --reason "…"` (SDLC.md §5)

A new flag pair is a new input surface, and this one writes to a durable log.

| input | expected |
|---|---|
| `--skip` naming a step not in the configured list | exit 2, names it and the list; **no row written** |
| `--skip` with no `--reason` | exit 2 — a skip without a reason is the silence this story exists to end |
| `--reason` with no `--skip` | exit 2 — a reason for nothing |
| `--reason ""` / `"   "` / only punctuation | exit 2 — empty is not a reason; the minimum is stated in the message |
| `--reason` longer than the cap (1 KB) | exit 2, names the length — a durable log is not a paste buffer |
| `--reason` containing U+2028 / U+2029 | **accepted**, and the row reads back as ONE record — `ledger.LINE_BREAKERS` already escapes them; a test proves it through this path |
| `--reason` containing a newline or a raw `\x00` | exit 2 — one row is one line |
| `--skip` the same step twice in one invocation | exit 2 — one decision per step |
| `--skip` a step already recorded `done` in this run | exit 2, names when it completed; a skip cannot un-do a postcondition that holds |
| `--skip` used with an unresolvable `<version>` | exit 1 before any row — the milestone directory is where the row goes, so it must resolve first |
| the ledger file is a directory, or not writable | refuse with the path; the step is NOT marked skipped, because the record is the point |
| `--skip` naming every step in the list | runs, writes every row — and prints a warning naming the count, because a fully-skipped conveyor is risk 3 arriving |

## The self-hosting proof, and the trap in it

Ship criterion 8 is *0.2.0 is released through `agentic-sdlc release 0.2.0`*. The rows above are
the evidence. **Do not write a pytest asserting this repo's 0.2.0 ledger holds a completed
release run** — it would be red for the entire milestone and green only after the tag, so
`make milestone` (which runs BEFORE the tag, as step 10 of the list) could never pass. A gate
that cannot be green at the moment it must run is a gate that gets deleted.

What ships instead:

- a **well-formedness** test over any ledger, on a fixture: every `step` row names a step in
  that operation's list, every `skipped` row carries a non-empty reason, no step carries two
  outcome rows, and every row round-trips through `read_rows`;
- `agentic-sdlc release <version> --status`, which prints the recorded run for that milestone —
  so the close report quotes the machine rather than the operator's memory;
- a **live-tree** assertion in the same test module, guarded to the case where the version in
  `__init__.py` matches a milestone whose ledger holds `step` rows: it checks those rows are
  well-formed, and is inert before the run starts. It proves the shape, never the existence.

The existence half is the close protocol's own job, and story 05 renders it into the doc.

## Acceptance criteria

1. `ledger.KIND_STEP` and `ledger.step_row()` exist beside `status_row`/`decision_row`, and a
   test asserts a `skipped` row without a reason cannot be minted at all.
2. `agentic-sdlc release 0.2.0 --skip prove-artifact --reason "…"` appends exactly one row to
   `pm/roadmap/<milestone>/ledger.jsonl`, advances past that step, and re-running is idempotent —
   the second run reports the step already skipped and writes no second row.
   `tests/test_conveyor_skip.py`.
3. Every row of the refusal matrix is a test asserting the exit code AND that the ledger file is
   byte-identical afterwards.
4. A `done` row is written only after `verify()` returned true — proven by monkeypatching a
   fixture step's `do()` to a no-op and asserting the ledger gains a `stopped` row and no `done`
   row.
5. **`pm ledger report` does not redden on the new kind.** A ledger holding `step` rows beside
   `status`, `decision`, `dispatch` and `session` rows still reports, exit 0. A row kind the
   report does not know must be ignored, never a parse error — that is a
   forward-compatibility claim and it gets its own test.
6. The well-formedness test and `release --status` from § above, both shipped.
7. `check pm` still exits 0 on this repo with the new rows present.

## Files this story may touch

- `src/agentic_sdlc/repo/conveyor/skip.py` — NEW
- `src/agentic_sdlc/repo/pm/ledger.py` — `KIND_STEP`, `step_row`, and only what those need
- `src/agentic_sdlc/repo/pm/cli.py` — only if `pm ledger report` must be taught to ignore an
  unknown kind (criterion 5). If it already does, touch nothing and say so in the report.
- `tests/test_conveyor_skip.py` — NEW
- `tests/test_ledger.py` — the `step_row` rows

## Files this story must stay out of

`conveyor/driver.py`, `conveyor/state.py`, `src/agentic_sdlc/cli.py` (story 01),
`conveyor/config.py`, `src/agentic_sdlc/core/config.py` (02), `conveyor/release_steps.py` (03),
`conveyor/render.py`, `src/agentic_sdlc/repo/install.py`, `SDLC.md`,
`.claude/skills/release/SKILL.md` (05), `src/agentic_sdlc/repo/pm/verdict.py`,
`src/agentic_sdlc/repo/checks/pm.py`.

**`pm/cli.py` and `pm/ledger.py` are also read by `0.2.0/every-gate-reports-its-cost` (phase 3),
which lands first.** Rebase onto its shape rather than reverting it.

## Out of scope

- Actually performing the 0.2.0 release. That is the milestone's close protocol, not a story.
- A `pm ledger report` VIEW over step rows (what got slower per step). That is
  `every-gate-reports-its-cost`'s territory; this story only guarantees the rows do not break it.
- `--skip` for `adopt` — the flag is operation-generic here, so the adopt feature inherits it
  and adds nothing.
