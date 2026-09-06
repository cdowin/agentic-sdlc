---
id: 0.2.0/the-story-belt-knows-what-verifies-this-edit/04-verify-answers-what-proves-this-edit
feature: 0.2.0/the-story-belt-knows-what-verifies-this-edit
milestone: "0.2.0"
name: verify --changed, --plan and --check answer from the tree
status: done
owner:
depends_on: ["0.2.0/the-story-belt-knows-what-verifies-this-edit/02-one-capture-runs-one-command", "0.2.0/the-story-belt-knows-what-verifies-this-edit/03-a-test-declares-what-it-covers"]
---

# verify --changed, --plan and --check answer from the tree

<!-- What is observable when this ships. A story is an observation, not a task. -->

`agentic-sdlc verify` becomes a top-level verb an orchestrator can ask instead of guessing:

```
agentic-sdlc verify --changed [--ref <git-ref>]   # what proves the diff — and run it
agentic-sdlc verify --plan    [--ref <git-ref>]   # print the commands, run nothing
agentic-sdlc verify --check                       # validate [verify] against the tree
```

`--plan` is why the verb beats a make target: **a dispatch author asks the repo what the
narrow command is, and the answer stays true as the tree grows.**

## Files this story may touch

- `src/agentic_sdlc/repo/verify/main.py` — new: git, the flags, the fallback, the exit codes,
  the ratio.
- `src/agentic_sdlc/repo/verify/__init__.py` — the `main(argv)` export only; story 01 wrote
  the module and its docstring.
- `src/agentic_sdlc/cli.py` — one route beside `gates-extra`, and the `--help` block.
  **Serial after `0.2.0/the-extraction-finishes` (phase 1), which prunes `KNOWN_GATES` and
  ships the `roster == dispatchable` census; do not reopen what it decided.** `verify` is a
  top-level verb, not a check, so it does not enter `KNOWN_GATES`.
- `devkit.toml` — this repo's own `[verify]` section (self-hosting is a gate here, not a
  demo).
- `tests/test_verify_verb.py` — new.
- `tests/fixtures/` — scratch repos with and without `[verify]`.

## Files it must stay out of

`rules.py` / `select.py` / `declares.py` / `core/config.py` — stories 01-03. README,
CHANGELOG and `SDLC.md`: propose the wording in the report, the orchestrator applies it
(SDLC.md §2). `pm/roadmap/`.

## Acceptance criteria

1. **The dangerous case, first.** A changed path matching no rule prints that path, on its
   own line, and runs `wide`. The exit code is the WIDE command's. A run where every path
   missed must never exit 0 having run nothing. Proven by `tests/test_verify_verb.py` against
   a fixture repo whose rules deliberately miss — asserting the named path in the output AND
   that the wide command actually ran (a sentinel the fake wide command writes), not merely
   that the exit code was 0.
2. **A repo with no `[verify]` section exits 2 for all three flags**, naming the section —
   config error, not findings, and never a silent zero-command pass. Feature criterion 4
   states this for `--changed`; it is ruled here for `--plan` and `--check` too, because a
   `--plan` that prints nothing and exits 0 is the same lie one step earlier. Proven by three
   cases. `wide` absent is the same exit 2 (story 01 refuses it; prove it reaches the verb).
3. `--plan` runs **nothing**. Proven by patching the spawn surface and asserting zero calls,
   against a rule set whose `run` would create a sentinel file — then asserting the file is
   absent. The docstring's promise gets hostile input, not a re-run of the intended path.
4. `--changed` on a diff touching N files under one captured directory runs the slice
   **once** (feature criterion 1). Proven end-to-end through the verb, not only through
   story 02's selector.
5. **`--check` fails a rule whose glob matches zero tracked files, and a rule whose `run`
   names a target that does not exist, each naming the rule's own index** (feature criterion
   3). Exit 1 — these are findings about the tree, not config errors. A `--check` on a valid
   rule set exits 0 and **prints its census** (`N rules, M matched files scanned`); a check
   that reports "OK" over a rule set it did not actually resolve is this package's cardinal
   sin. Proven by three cases.
6. `--ref <git-ref>` selects the diff base; the rev is the caller's and is never searched
   for. An absent value (`--ref` at the end of argv), a rev that does not resolve, and
   `--ref` given twice are each exit 2 — `cmd_ledger_report`'s `--from` handling in
   `pm/cli.py` is the shape to copy, including its "WHETHER and WHAT are two questions"
   comment, which is a defect this package has already shipped once.
7. **Git absent, or not a git repo:** exit 2 naming it, like `report.GIT_MISSING` already
   does. Never "no changes, nothing to verify". Proven by a case.
8. **The ratio, or an honest silence.** `--plan` prints narrow-vs-wide with real numbers when
   the ledger has the durations `0.2.0/every-gate-reports-its-cost` records, and otherwise
   prints the commands and says the ratio is **unknown**. Never a guess, never an assumed
   1.0. Proven by two cases — one with a vendored ledger fixture, one with none.
9. Exit codes are contract (hard rule 6): 0 pass, 1 findings/verification failure, 2 usage or
   config. Proven by a case per code.
10. `tests/test_fuzz_inputs.py` passes with `verify` in the CLI — the standing
    refuse-or-contained-write floor now covers the new verb.
11. Slice command for the loop: `python3 -m pytest tests/test_verify_verb.py -q`. Wide:
    `make precommit`.

## Refusal matrix — the verb's argv is a new input surface

| input | expected |
|---|---|
| `verify` with no flag | exit 2 with usage — **not** a default to `--changed`, which would run commands somebody did not ask for |
| `--changed --plan`, `--changed --check`, all three | exit 2: which one it should have been is not a thing this verb may pick |
| `--ref` with no value, `--ref` twice, `--ref ''` | exit 2 (criterion 6) |
| `--ref '--plan'` | the next flag is not adopted as a rev |
| `--ref '../../../etc'`, `--ref '/etc/passwd'`, `--ref 'a b'`, `--ref $'a\nb'`, `--ref '$(id)'`, `` --ref '`id`' `` | passed to git as ONE argv element, never through a shell; a rev that does not resolve is exit 2 |
| `--ref` naming a rev in another repository, or an absolute path outside the checkout | refused — hard rule 8 |
| an unknown flag, `-x`, `--changed=1` | exit 2 naming it, never silently ignored (`_run_check` in `cli.py` is the precedent: *"a consumer that thinks it asked for a repair and got a read-only run has been lied to"*) |
| a positional argument | exit 2 — this verb takes no positionals |
| `--help` | prints the module docstring, exit 0, runs nothing |

**Adversarial cases against the docstring.** The verb will claim `--plan` runs nothing, that a
miss always falls back to wide, that it never reads outside the checkout, and that it never
writes. Generate against each: `--plan` over a rule set whose `run` writes; a diff where
every path misses; a `--ref` and a rule set that between them name `../`; and a run in a
read-only checkout, which must not attempt a write anywhere.

## Out of scope

- Parallelising the selected commands. One after another, in declaration order, stopping at
  the first non-zero — a runner that hides which command failed is worse than a slow one.
- Caching results between runs.
- A `make verify` target. `Makefile.devkit` belongs to `0.2.0/the-middle-tier-splits`; if a
  target is wanted, propose it in the report.
- Wiring `verify` into `precommit` or `check`. That changes every consumer's gate and is a
  separate decision with its own argument.
- Editing the stock agent definitions to name the verb — that is
  `0.2.0/every-gate-reports-its-cost/04-a-dispatch-names-both-commands`.

## Close

done: 6e9388d — verify --story/--feature/--milestone/--plan/--check. --plan prints measured
cost from the ledger and the word `unknown` where none exists, never an estimate: a
fabricated ratio is worse than none because it gets quoted.
