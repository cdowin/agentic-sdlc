---
id: st-adopt-walks-the-adoption
feature: ft-adopt-is-a-conveyor
milestone: "ms-0.2.0"
name: A pin bump walks its own step list and refuses to advance
status: done
owner:
depends_on: ["st-the-conveyor-refuses-to-advance", "st-the-step-list-is-the-projects"]
kind: story
---

# A pin bump walks its own step list and refuses to advance

An operator in a consuming repo bumps `DEVKIT_VERSION`, runs `agentic-sdlc adopt`, and walks a
list scoped to the adoption. It refuses to advance past a step whose postcondition does not
hold, it resumes after an interruption from the same position, and a step it cannot perform
says exactly what the operator must do rather than pretending.

Same machine as `release`, different list. That is the whole design: story 01 and 02 of
`the-release-is-a-conveyor` ship the driver, the kinds, the run state and an
operation-generic config reader, so this story supplies a registry and a route and **adds no
second machine**. If it finds itself writing one, that is a finding against the driver.

## Rule 8 is the live hazard, and it is a property of every step here

`adopt` runs **in** a consumer, on the consumer's own tree. That is fine and it is the point.
What it must never do is read a second repo, gate on one, or write outside the checkout it was
run in. Every step below is a question about the local tree, and the story ships that as an
assertion rather than an intention: a test runs the whole list inside a scratch repo with a
sibling directory planted beside it and asserts **no path outside the repo root was opened**.

`pin-bumped` is the step that tempts otherwise — it is about a version that lives somewhere
else. It stays local: it reads the consumer's own `DEVKIT_VERSION` and compares it to the
version of the package that is running. That comparison needs no network and no second
checkout, and it is the only honest form of the question.

## The shipped list

```toml
[adopt]
steps = ["pin-bumped", "installables-diffed", "installable-decisions-recorded",
         "config-updated", "hooks-self-test", "runner-targets-resolve",
         "checks-pass", "pm-validates"]
```

Eight steps. `pin-bumped` and `installable-decisions-recorded` are judgement steps — this
package will not edit a consumer's Makefile and cannot decide which installables that consumer
wants. `installables-diffed`, `hooks-self-test`, `runner-targets-resolve`, `checks-pass` and
`pm-validates` are covered by story 02, which owns their implementations.

## Refusal matrix — `adopt` and `[adopt] steps` (SDLC.md §5)

The `<version>` grammar and the run-state hostile cases are story 01 of the release feature and
are **not re-litigated here**; what is new is that `adopt` takes no version argument and lives
in a repo that may be missing everything.

| input | expected |
|---|---|
| `adopt` with any positional argument | exit 2 — the operation is about THIS checkout; there is no id to name |
| an unknown flag | exit 2 with usage; never silently ignored |
| run outside a git repository | exit 2 naming that no repo root was found — the existing `repo_root()` refusal |
| a repo with no `devkit.toml` | the stock list runs, byte-identically to declaring it (rule 5) |
| `[adopt] steps` as a bare string / empty list / unknown name / duplicate | exit 2, per story 02's reader — one implementation, asserted through the `adopt` path too |
| `[adopt] steps` naming a **release** step (`tag`, `merge`) | exit 2 — the operations have separate registries and a step from the wrong one is a typo, not a feature |
| `[adopt.commands]` naming a step not in the adopt list | exit 2 |
| a repo with no `Makefile` at all | `pin-bumped` refuses naming the file it looked for; it does not create one |
| a repo with no PM tree | `pm-validates` refuses naming what is absent — never "vacuously fine" |
| a `.agentic-sdlc/run/release.json` present from an unrelated release run | untouched; `adopt` reads and writes only `adopt.json` |
| a symlinked repo root, or a `..` in a configured command | the command is the project's own; the refusal is on the SHAPE (story 02), not a sanitizer |
| `--skip <step> --reason "…"` | the release feature's story 04 contract, unchanged, writing into the same ledger |

## Acceptance criteria

1. `agentic-sdlc adopt [--skip <step> --reason "…"]` runs the eight-step list, resumable, with
   the same exit contract as `release` (`0` completed, `1` stopped on a step, `2` usage/config).
   `tests/test_adopt_driver.py`.
2. **No second machine.** A source-level test asserts `conveyor/adopt.py` imports `walk`,
   `Step`, `StepKind`, the state module and the skip module from the release feature's files and
   defines no `walk`-shaped loop of its own.
3. **Rule 8, asserted.** The whole list runs in a scratch repo with a decoy sibling repo beside
   it; a path-open recorder asserts nothing outside the repo root was read or written, and no
   module under `src/agentic_sdlc/repo/conveyor/` contains a repository name or URL.
4. `pin-bumped` refuses on a consumer whose `DEVKIT_VERSION` still names the old version, prints
   the exact line the operator must edit and the file it is in, and **writes nothing**.
   It passes once the line names the running version.
5. Run state lands at `.agentic-sdlc/run/adopt.json` and does not disturb a concurrent
   `release.json`. Deleting it and re-running re-derives the same position from `check()` alone.
6. Every row of the refusal matrix is a test asserting the exit code and that nothing was
   written.
7. `agentic-sdlc adopt --plan` prints the resolved list with kinds, the same shape story 02
   ships for `release`.

## Files this story may touch

- `src/agentic_sdlc/repo/conveyor/adopt.py` — NEW (the verb entry and the registry wiring)
- `src/agentic_sdlc/cli.py` — the `adopt` route **only if** the release feature's story 01 did
  not already add it. It was asked to add both; if it did, touch nothing here and say so.
- `devkit.toml` and `src/agentic_sdlc/repo/installables/project-devkit.toml` — the `[adopt]`
  section
- `tests/test_adopt_driver.py` — NEW

## Files this story must stay out of

`src/agentic_sdlc/repo/conveyor/adopt_steps.py` (story 02 of this feature),
`conveyor/driver.py`, `conveyor/state.py`, `conveyor/config.py`, `conveyor/release_steps.py`,
`conveyor/skip.py`, `conveyor/render.py`, `src/agentic_sdlc/core/config.py`,
`src/agentic_sdlc/repo/install.py`, `src/agentic_sdlc/repo/pm/ledger.py` — all owned by
`the-release-is-a-conveyor`, which this feature `depends_on`. A defect in one of them is a
finding filed against that feature, not a patch made here.

## Out of scope

- What the five automatic/gate steps DO — story 02.
- Any change to the driver, the kinds, the state file format, or the skip contract.
- The generated document's adopt section — `the-release-is-a-conveyor/05` renders it from
  `[adopt] steps`; this story only makes that list exist.

## Close

done: 4de8f9e — eight steps on the release driver, whole list answering in ~3 s.
runner-targets-resolve asks make rather than the filesystem, so -include's silence is
unreachable as a pass.
finding: installables-diffed found real self-hosting drift on its first run.
