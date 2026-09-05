# Feature review — `0.2.0/adopt-is-a-conveyor` — HOLD

Feature-level pass (SDLC.md §0) over the whole commit range of `0.2.0/adopt-is-a-conveyor`:
**`4de8f9e`** — the commit both its stories name in their `## Close` blocks. Branch
`milestone/0.2.0-the-conveyor`, run 2026-09-05, adversarial by execution, in `tempfile` scratch
repos and against this tree through `PYTHONPATH=src python3 -m agentic_sdlc.cli`. No repo-wide git
command was run.

The milestone review (`docs/reviews/2026-09-05-0.2.0-release-review.md`) is landed and none of its
ten findings is re-filed here.

This is the smallest of the three features and the subtraction it exists for holds: **`checks-pass`
runs this package's `check all` and never the consumer's `make check`**, and the whole eight-step
list answers in **2.82 s** on this tree. The one blocker is in the step whose entire job is the
question a pin bump asks.

## Blocker

### A1 — `config-updated` reports TRUE over a `devkit.toml` that makes three shipped gates exit 2, and names the broken section in its own pass line

`STEP_DOC['config-updated']` (`src/agentic_sdlc/repo/conveyor/steps.py:2199-2203`) promises:
*"every devkit.toml section this version still READS accepts what this repo declares."*

`_config_readers()` (`:1549-1569`) asks **six**: `[gates] extra`, `[pm]`, and the four
`[<operation>] steps / commands` tables. `check_config_updated` then builds its report line from a
**second, hand-written list of ten** section names (`:1589-1592`): `checks gates pm release adopt
story feature grain_shape repo_hygiene verify`. Four of those ten — `checks`, `grain_shape`,
`repo_hygiene`, `verify` — are named in the census and never asked.

Three scratch repos, one broken section each, measured:

| `devkit.toml` | the gate that reads it | `config-updated` |
|---|---|---|
| `[checks] all = ["doc", "wombat"]` | `check all` → **exit 2**, `[checks] all names unknown gate(s) wombat` | `TRUE — 6 reader(s) accept this repo's devkit.toml; declared here: checks` |
| `[verify] milestone = 42` + `[[verify.narrow]] paths = ["a"], run = 7` | `verify --check` → **exit 2**, `paths must be a string` / `run must be a string` | `TRUE — … declared here: verify` |
| `[grain_shape] caps = "nonsense"` | `check grain-shape` → **exit 2**, `caps must be a table` | `TRUE — … declared here: grain_shape` |

The detail line is what turns a gap into a lie: it names the very section that is broken, under the
word "accept". An operator reading `declared here: verify` after a bump has been told the `[verify]`
table survived the version change. It did not — and `checks-pass`, two steps later, would have
caught the `[checks]` case at exit 2 if `config-updated` had not already reported the config sound
and let the run advance.

This is rule 4, read side, in the step that is the whole reason `adopt` exists as a distinct list:
a pin bump's *only* real hazard is a config key this version no longer accepts, and that is the
half the step does not ask about. It is also the second-list defect CLAUDE.md names by hand —
*"there is no second list to update"* — with the two lists at `:1562-1569` and `:1589-1592`, in one
function, eleven lines apart.

The fix is one list: derive the census from `_config_readers()` and give the four unasked sections
a reader (`cli.all_roster`, `verify.rules`'s declaration reader, `grain_shape`'s caps reader,
`repo_hygiene`'s), so the number in the line is the number that was asked.

## Non-blocking findings

### A2 (MINOR) — `installable-decisions-recorded` accepts a decision by path SUBSTRING

`steps.py:1531-1533`:

```python
undecided = [rel for rel in drift
             if not any(rel in line and line.split(rel, 1)[1].strip(' :')
                        for line in decisions.split('\n'))]
```

A line satisfies a drifted path when it merely *contains* the path with any non-`:`/-space text
after it. Two consequences: a decision written for `tools/hooks/pre-push-extra` would satisfy
`tools/hooks/pre-push`, and any prose under `## decisions` that quotes a path with a trailing word
counts as a decision for it. Checked against the shipped inventory — `install.PLANS` holds 28
paths and **zero** substring pairs — so this is latent today and becomes live the first time a
verb ships `a/b` beside `a/b.md`. Anchoring the match to the start of the line, or splitting on the
documented `<path>: <verdict> — why` shape, closes it.

### A3 (NIT) — `_configured` re-reads and re-validates the whole operation config on every gate step

`steps.py:740-741` — `commands_for(ctx.operation)` with no `names` argument, which re-enters
`steps_for` → `registry_for` → `_section`. Called by `check_gate`, `check_hooks_self_test`,
`check_runner_targets_resolve`, `check_checks_pass`, `check_pm_validates`,
`check_narrow_verified`, `check_feature_verified` and the three `_judged_by_command` steps. Correct,
but it means a `[adopt] steps` list with a duplicate name re-prints the *"collapsed in declaration
order"* notice once per such step rather than once per run. `validate_config` already computed the
answer before the first step; passing it through would be cheaper and quieter.

## The four numbered ship criteria, judged

| # | criterion | verdict |
|---|---|---|
| 1 | `adopt` walks `[adopt] steps`, resumable, with the same `--skip <step> --reason` contract as `release`, into the same ledger | **met** — one driver, one `main`, one ledger writer. Verified on the shared machine: `--skip` of a name outside the list is exit 2 with no row; a skip writes exactly one `{"kind":"deviation","operation":…,"step":…,"outcome":"skipped","reason":…}` row and a re-run writes no second; a skipped step is recorded in the run state **not at all**, never as satisfied; a hand-corrupted run state claiming every step done produced `CORRECTED …` and the tree won |
| 2 | `checks-pass` runs `check all` and **not** `make check`, asserted by a test | **met** — `steps.py:1666-1679` goes through `_own_verdict(ctx, 'check', 'all')`, and `_own_cli` returns the argv it ran so a test can assert what ran rather than what the transcript says. Both tests exist and are named for this criterion: `tests/test_conveyor_adopt.py::test_checks_pass_never_runs_make` (:155, recorded argv) and `::test_checks_pass_leaves_the_consumers_own_gates_unrun` (:185, sentinel file plus a positive assertion that the step actually ran) |
| 3 | a step this package cannot perform states what the operator must do, refuses to advance until its `check()` is true, and never edits a file outside its checkout | **met** — `pin-bumped` (`:1328-1364`) reads the `DEVKIT_VERSION` line, compares it to `__version__` (the package that is RUNNING, so no network and no second checkout), names the exact one-line edit, and writes nothing; `do_pin_bumped` says so in as many words. Every `subprocess.run` in `conveyor/` (`:368`, `:388`, `:422`, `:722`) passes `cwd=str(ctx.root)`; the only write in the adopt list is `.agentic-sdlc/run/adopt-installables.md`, inside the checkout, through `core.apply` |
| 4 | `install-sdlc` renders the adopt list beside the release list, from the same source | **met** — `docs/sdlc-protocol.md` carries four `## \`<operation>\` — the ordered list` sections with 21 / 8 / 5 / 6 rows, and the row counts equal `DEFAULT_STEPS` exactly. `install-sdlc --diff` → `already current`, exit 0 |

**Risk 1 — hard rule 8 is the live hazard.** Clean. Confirmed by reading every one of the eight
`check()`s: `pin-bumped` reads `[adopt] pin_file` inside the tree; `installables-diffed` compares
`install.PLANS` bodies against files under `ctx.root`; `installable-decisions-recorded` and
`config-updated` read files under `ctx.root` and this process's own config; `hooks-self-test`,
`runner-targets-resolve`, `checks-pass` and `pm-validates` each run a command with
`cwd=str(ctx.root)`. **No step reads a second repo.** `[pm] roadmap_dir`, `review_dir` and
`template_dir` all go through `core.config.relpath`, which refuses absolute and `..` values.

**Risk 2 — a conveyor that is always skipped.** Not materialised: `pm/roadmap/0.2.0-the-conveyor/`
`ledger.jsonl` holds **zero** `deviation` rows across the whole milestone.

**The subtraction, measured.** All eight `check()`s on this tree, in one process:

```
  0.01s  pin-bumped                       UNVERIFIABLE — Makefile carries no DEVKIT_VERSION line
  0.00s  installables-diffed              FALSE — the report has not been produced
  0.02s  installable-decisions-recorded   TRUE — no installed file differs from what 0.1.0 ships
  0.00s  config-updated                   TRUE — 6 reader(s) accept …            <-- A1
  1.10s  hooks-self-test                  TRUE — check hooks exited 0
  0.00s  runner-targets-resolve           FALSE — Makefile.devkit is not in this checkout
  1.67s  checks-pass                      TRUE — check all exited 0
  0.02s  pm-validates                     TRUE — [pm] VALID — 44 grain(s), 41 ref(s)
  2.82s  TOTAL (8 checks)
```

Two answer FALSE/UNVERIFIABLE only because this repo is the producer, not a consumer — it carries
no `DEVKIT_VERSION` pin and no installed `Makefile.devkit`. The `~3 s` in story 01's `## Close`
is confirmed.

## `## Close` claims, checked

| story | claim | verdict |
|---|---|---|
| 01 | eight steps on the release driver, whole list answering in ~3 s | **true** — 2.82 s measured above; `ADOPT_STEPS` is 8 and `registry_for` keeps the two registries separate, so `[adopt] steps = ["tag"]` is exit 2 rather than a borrowed release step |
| 01 | `runner-targets-resolve` asks make rather than the filesystem, so `-include`'s silence is unreachable as a pass | **true** — `steps.py:1651` runs `make -n <targets>`; a named tier with no file is make's own `$(error)` and a non-zero exit, and an empty tier list is reported as empty rather than as a plain pass |
| 01 | finding: `installables-diffed` found real self-hosting drift on its first run | **not checkable now** — the drift it found was landed in the same range; `installable-decisions-recorded` today answers *"no installed file differs from what 0.1.0 ships"*, which is consistent with the claim having been true and acted on |
| 02 | `checks-pass` runs `check all`, never `make check`; two tests hold the line, one on the recorded argv and one on the consumer's sentinels **and** that the step actually ran | **true** — both tests found by name, and the second does carry the positive assertion |

Nothing in either `## Close` block is untrue.

## Cross-story questions

- **Did the two stories solve the same thing twice?** No. Story 01 is the list and the driver
  wiring; story 02 is one line of it (`checks-pass`) plus the tests that pin it. No overlap.
- **Did the later story weaken the earlier one's guard?** No.
- **Is any step's `check()` satisfied by its own `do()`?** No, and `installables-diffed` is the one
  that comes closest: its `check()` reads the report its `do()` wrote, but re-derives the census
  from the tree with a per-file `sha256[:12]`, so a file edited after the diff makes the report
  stale and the step answers no. Four of the eight steps have no `do()` at all — they are GATEs,
  which the driver refuses to let carry one.
- **The feature is entry-ready.** `pm ready-for feature 0.2.0/adopt-is-a-conveyor` → `READY — 2
  story/ies, all done`, exit 0. It is the **only** one of the milestone's nine features that is,
  and its two stories are the only two of the milestone's stories the ledger shows going
  `reviewing → done` through the belt (`18:00:37Z`, `18:00:39Z`), followed by the feature's own
  `building → reviewing` at `18:02:00Z`.

## What was NOT verified

- **No `adopt` run was walked to completion.** This repo cannot satisfy `pin-bumped` or
  `runner-targets-resolve` (it is the producer), so the eight `check()`s were timed and inspected
  individually rather than through `agentic-sdlc adopt <version>` end to end. The milestone review
  did run `adopt 1.4.0` on a scratch consumer and reached step 1; nothing here re-ran that.
- **`do_installables_diffed` was not run**, so `install.print_diff` over a genuinely drifted tree,
  the `## decisions` byte-preservation promise, and the directory-creation path in its
  `apply.Plan()` are unexercised by me.
- **A2 is latent, not reproduced.** I proved there is no substring pair in `install.PLANS` today; I
  did not construct one and watch the false pass.
- **The `header-only` and `unrenderable` verdicts in `_installable_drift`** were not exercised —
  no file in this tree carries a project-config header that differs, and nothing failed to render.
- **`[adopt] command_timeout`, `pin_file` and `runner_targets` refusals** were read, not run; the
  milestone review covered the `[release]` half of that matrix.
- **`make milestone` and the interpreter matrix were not run.** The slice was:
  `tests/test_conveyor_{steps,driver,state,skip,adopt,close}.py tests/test_install_sdlc.py` →
  **275 passed in 17.83 s** on 3.11.

Reviewer's token cost: ~148k (shared across all three feature records).

```
verdict: HOLD
| id | severity | disposition |
| A1 | BLOCKER | open: config-updated passes over four sections it names and never asks |
| A2 | MINOR | open: a decision line matches a drifted path by substring |
| A3 | NIT | open: _configured re-validates the whole operation config per step |
```
