# Feature review — `0.2.0/the-suite-is-cheap-or-it-declares-itself` — HOLD

Feature-level pass over `bdfe784`, `1efb740`, `96c9ca7`, `8aa7666`, branch
`milestone/0.2.0-the-conveyor`, run 2026-09-05. Every claim below was produced by running
something: the three tier targets, the budget gate against deliberately-lowered ceilings in a
scratch copy of the tree, a hand-applied `shell` mark on a scratch suite, a collection-level
partition census, a `PY_FLOOR` refusal, and a `sitecustomize` spawn counter wrapped around
`subprocess.Popen`, `os.posix_spawn`, `os.fork`, `os.system` and `os.popen`. No source, test,
config or PM file was edited; the one file written is this record.

**Measured at `f8e9e94`. The branch moved to `6b67cd6` during the review** (another session is
committing to it). `git log f8e9e94..HEAD` touches none of `budget.py`, `Makefile.tiers`,
`tests/conftest.py` or `devkit.toml`, so every finding below still stands at `6b67cd6`; one
finding (S9) was landed by that session while this was being written and is dispositioned as
such.

**The machine was not quiet and that is load-bearing for the numbers.** Sibling agents run their
own suites in `.claude/worktrees/`; load average moved between 26 and 72 on 8 cores across the
session, and the committed `ledger.jsonl` was being appended to by those sessions throughout.
Every wall-clock number below is an upper bound under contention, and each is reported with the
load it was taken at.

**Four findings, and they share one shape: the budget gate reports a number without reporting
what the number is a measurement OF.** The verdict of the run it grades, the age-ordering of the
row it picks, whether a declared tier was measured at all, and the direction a census moved — the
gate reads all four and prints none of them on the passing path. This is the feature's own
subject matter (rule 4 pointed at cost) applied one level short of its own gate.

The mark derivation, the tier partition, the `PY_FLOOR` refusal, the zero-spawn claim for the
unit tier and the over-ceiling failure path all held under everything tried.

---

## The blockers

### S1 — `check budget` grades a run that FAILED as `ok`, and prints PASS

`src/agentic_sdlc/repo/checks/budget.py:276-278`. The verdict is read — `_last_costs` carries it
at `:171`, `run()` unpacks it at `:267`, and the OVER BUDGET branch prints it at `:275` — and the
`ok` branch drops it.

Measured, live, on this checkout. `make unit` and `make test` both ended red (two
`test_consumer_independence` cases, and at the time a timing case, see S9). The rows they filed:

```
{"ts":"2026-09-06T02:02:20Z","kind":"gate","gate":"unit","verdict":"FAIL","duration_ms":9274,"census":734}
{"ts":"2026-09-06T02:10:24Z","kind":"gate","gate":"test","verdict":"FAIL","duration_ms":123087,"census":1406}
```

and what the gate said about them, unmodified, exit 0:

```
  ok          integration — 86.3s of 130s, measured 2m ago
  ok          test — 123.1s of 150s, measured just now
  ok          unit — 9.3s of 20s, measured 8m ago
  ok          integration — 673 of 800 case(s)
  ok          unit — 734 of 1250 case(s)
[check:budget] PASS — 3 tier(s) within their time budget, 2 within their case ceiling
```

A tier that stopped early is cheaper and smaller than a tier that finished, so a FAILED run is
the run most likely to sit comfortably under both ceilings — the gate is at its most confident
exactly where its input is least trustworthy. `unit` here is 734 cases of a tier that collects
738; the 4 it did not complete are invisible in both columns, and `9.3s` is the cost of a run
that stopped.

That this is a choice rather than an oversight is visible in the same file: the OVER BUDGET line
says `verdict FAIL` (reproduced in the probe below), and `verify --plan` renders the same row as
`96583 ms (census 1401, FAIL)`. Two readers of one row; only the one that gates drops the column.

Hard rule 4, read side, in the gate whose docstring invokes rule 4 four times. Minimum fix: a row
whose verdict is not `PASS` is not a measurement of the tier — report it as such (its own line,
beside UNMEASURED) rather than grading it.

### S2 — the gate grades the LAST row in the file and calls it the newest; on this repo's own ledger those are different rows

`src/agentic_sdlc/repo/checks/budget.py:143-173` (`_last_costs`), and identically `:98-122`
(`_counts`) and `:202-228` (`_slowest`). All three walk `ledger.read_rows` and overwrite per gate
name, so the survivor is the last row in FILE ORDER. The docstring at `:148-149` says otherwise —
*"Newest WINS rather than an average, and the reason is what this gate is for"* — and
`ledger.py:735` supplies the assumption underneath it: *"Every row in one ledger, oldest first."*

Nothing enforces that. The ledger is append-only from concurrent writers and is a COMMITTED file
that gets merged. Both routes were live in this checkout during the review:

```
newest unit row BY TIMESTAMP:
{"ts":"2026-09-06T02:17:46Z","gate":"unit","verdict":"FAIL","duration_ms":13237,"census":734}
last unit row IN FILE ORDER:
{"ts":"2026-09-06T02:09:19Z","gate":"unit","verdict":"PASS","duration_ms":62576,"census":736}
```

and the gate, unmodified:

```
  OVER BUDGET unit — 62.6s against a 20s ceiling (+42.6s), verdict PASS, measured 10m ago
  ok          unit — 736 of 1250 case(s)
  slowest    unit — 7.2s  tests/test_fuzz_markdown.py::test_fence_scanner...
[check:budget] FAIL — 1 tier(s) over budget: unit.
```

**It reported the tier at 62.6 s and failed the gate, eight minutes after that tier measured
13.2 s.** A 4.7x error, with a confident `measured 10m ago` attached to it — the age is computed
from the row it picked, so the one column that exists to stop a stale number reading as a current
one certifies the stale number instead.

The failure is symmetric and the other direction is the worse one: a ledger whose last-in-file
row is an old fast run grades a tier that has since doubled, prints `ok`, and exits 0. D10's
accepted cost was *"the budget is always one run behind"*; this is the budget being an
arbitrary number of runs behind, chosen by file layout.

`ledger.parse_ts` already exists (`ledger.py:454`) and is already used by another reader at
`:699`, so the fix is a `max` by parsed timestamp in the three walkers, with rows carrying an
unparseable `ts` reported rather than silently ordered.

### S3 — the summary line counts a tier that was never measured as being within its budget

`src/agentic_sdlc/repo/checks/budget.py:260-266` (UNMEASURED, `continue`, never appended to
`over`), `:280-284` (UNCOUNTED, same), and `:306-307`, which reports `len(budgets)` and
`len(ceilings)` regardless.

The module's docstring is explicit that this is not what it does: *"A tier with no ROW is reported
as unmeasured, which is not a pass: a gate that has not run has not told you anything."*
Probed in a scratch copy of this tree, by adding three ceilings for tiers with no rows:

```
  UNMEASURED  docs — ceiling 10s, and no `gate` row for it in this milestone's ledger; run `make docs`
  UNMEASURED  fuzz — ceiling 10s, and no `gate` row for it in this milestone's ledger; run `make fuzz`
  UNMEASURED  lint — ceiling 10s, and no `gate` row for it in this milestone's ledger; run `make lint`
[check:budget] PASS — 6 tier(s) within their time budget, 3 within their case ceiling
EXIT=0
```

**Three of the six were never measured, one of the three was never counted, and the summary line
asserts all nine.** That line is the grepped one (hard rule 6: `[check:x] PASS — …` is a
consumer-visible shape), and it is the only line a CI log tail or a `| grep PASS` will keep. The
detail lines are loud and correct; the line that survives summarising is false.

Reachability is not exotic: a consumer declares a ceiling for a tier, renames or stops running
that target, and the gate goes green forever — quieter than never having declared the ceiling at
all, because the declaration reads as coverage.

### S4 — the case ceiling only looks up, and the census in this tree has already fallen 35% under it

`src/agentic_sdlc/repo/checks/budget.py:286-292` fails only on `count > ceiling`. `devkit.toml:99`
declares `cases = { unit = 1250, integration = 800 }` against a baseline the comment above it
records: *"Measured 2026-09-05: 1,123 unit and 730 integration."*

Measured now, from collection rather than from a row:

| tier | declared baseline | today | delta |
|---|---|---|---|
| unit | 1,123 | **734** | −389 (−35%) |
| integration | 730 | **673** | −57 (−8%) |
| whole suite (feature's own Close table) | 1,853 | **1,411 collected** | −442 |

`check budget` reads `ok unit — 734 of 1250 case(s)` and has no opinion, because a census that
shrinks cannot trip a ceiling.

The shrink here is legitimate — `3afa141`, a later feature, deliberately cut 1,478 test functions
to 1,016 — and that is the point rather than a mitigation: **the gate cannot tell that case from
the one the feature's own risk 3 names**, *"deleting an integration test because it is slow is the
sin this feature is supposed to prevent."* Criterion 9 (*"the full suite is green and the pass
count does not drop"*) was the guard, and it is a human reading a table, not a gate. The gate that
exists to be rule 4 pointed at cost is one-sided on exactly the axis rule 4's write-side sin
travels.

The fix is not necessarily a floor key — reporting the DELTA against the previous run's census
(the rows are already there) would make a drop visible without anyone maintaining a second number.

---

## Non-blocking findings

- **S5 (MINOR) — the unit tier exceeds its own 20 s ceiling under the load this repo's SDLC
  itself generates.** Measured, same command (`pytest -q -m "not shell"`), same interpreter, same
  734 cases:

  | load average (8 cores) | wall |
  |---|---|
  | ~10 (ledger row, 33 m before I started) | 8.3 s |
  | 28 | 12.8 s |
  | 72 | 21.0 s / 31.2 s / 35.7 s |

  The ceiling was set at ~2x an idle-machine number; three sibling agents running suites in
  worktrees is not an idle machine, and it is the normal operating state of this branch. Feature
  risk 1 predicted precisely this — *"a budget that fails the gate on a slow machine is a gate
  that gets deleted"* — and D10 rejected `check budget` from `[checks] all` for the same reason.
  Not raised as a blocker because `budget` runs only in `make milestone`, where a human is
  present; raised because the number is one contended afternoon from teaching people to ignore it.
  Integration held up much better: 86.3 / 92.0 / 86.1 s at load 72 against a 130 s ceiling.

- **S6 (MINOR) — the `shell` derivation reads two routes to a spawn and there is a third.**
  `tests/conftest.py:139-176` marks a module when it imports `subprocess` or binds a
  `tests/support` name that reaches one. A test that reaches a spawn through the PACKAGE — and
  `src/agentic_sdlc/core/project.py:85`'s `git_lines` is one the feature's criterion 1 explicitly
  keeps — is neither. Built and run in a scratch suite under a copy of the real conftest:

  ```
  tests/test_indirect.py  (calls agentic_sdlc.core.project.git_lines, no subprocess import)
    -m "not shell"  ->  tests/test_indirect.py::test_it_asks_git      <- collected in the UNIT tier
    spawn probe     ->  Popen ['git','ls-files']  test_indirect.py:5 <- project.py:85:git_lines
  ```

  Latent, not live: the spawn counter saw **zero** spawns across the whole current unit tier
  (below), so no such module exists today. It matters because the mark's stated contract is
  *"`pytest -m shell` should be a statement about what the source does"*, and `make matrix` skips
  unmarked modules on three of four interpreters — an unmarked spawner is a silent hole in the
  matrix, which `tests/test_shell_mark.py:212`'s `NoUnreadSpawnSpelling` exists to prevent for the
  `os.system`/`os.popen` family and does not reach here.

- **S7 (MINOR) — the feature's `## Close` table no longer describes the tree, and it is the
  tree's evidence.** `1853` tests against 1,411 collected; `integration 60 s` against a recorded
  39.7 s and a measured 86–92 s; `whole suite 39 s` against 121–124 s measured. Two later
  features moved all of it. A close table is what a fresh session reads as the current cost, and
  a story-grain fix (a line saying which commit the numbers are as-of) is cheaper than the
  confusion.

- **S8 (NIT) — criterion 3 is self-declared NOT met and the disclosure is accurate.** 673
  integration cases against *"tens"*, ~40 s idle / ~90 s loaded against a 30 s target, ceiling
  parked at 130 s to stop the drift. Re-derived, not re-litigated; the honesty is the right
  posture and the record already carries it.

- **S9 (MINOR, landed during this review) — a wall-clock assertion inside the suite.**
  `tests/test_conveyor_close.py:237` asserted `elapsed < 1.0` unconditionally, and it went red in
  my `make test` run at load 72 — the third failure in `3 failed, 1406 passed`. Same shape D10
  rejected for `check budget` (*"a gate that reddens on somebody else's clock… is the kind that
  gets deleted"*), living inside the tier the ruling created. Another session landed the
  `PYTEST_XDIST_WORKER` guard in `6b67cd6` while this record was being written; recorded rather
  than dropped, because the failing run is what filed the `test` FAIL row that S1 grades as `ok`.

---

## The nine ship criteria, each with the measurement that judged it

| # | criterion | verdict | how |
|---|---|---|---|
| 1 | nothing in `core/` spawns to answer where the checkout is; `git_lines` still does | **met** | spawn counter around `repo_root()` + `load_config()`: **0 spawns**. `grep subprocess src/agentic_sdlc/core/*.py` returns `project.py` only, at `:85` inside `git_lines`. Also checked the case the walk changed: from inside a linked worktree, `repo_root()` and `git rev-parse --show-toplevel` return the same path (`.git` is a file there and `:63` uses `.exists()`) |
| 2 | the unit tier runs under 5 s and spawns nothing, asserted rather than trusted | **caveat** | **spawns: 0**, measured — `sitecustomize` wrapping `Popen`/`posix_spawn`/`fork`/`system`/`popen` over the whole `-m "not shell"` tier logged nothing; the same probe logged 105 spawns on one known-spawning module, so it was not measuring nothing. **Wall clock: never 5 s** — 8.3 s at rest, 12.8 s at load 28, 21–36 s at load 72. The declared ceiling is 20 s, four times the criterion, and S5 is the consequence |
| 3 | integration under 30 s, counted, every member declares itself | **not met, disclosed** | 673 cases, 86.1 / 86.3 / 92.0 s at load 72, 39.7 s in the last quiet row. Counted: yes, census rides on the gate row. Declared: yes, derived. The feature's own `### Criterion 3, honestly: NOT met` is correct (S8) |
| 4 | a budget is a GATE: `check` fails over a ceiling or a grown census, naming what grew | **caveat — the paths it names work; three it does not name fail open** | The named paths hold. Scratch copy of the tree, `unit` ceiling 20 → 5: `OVER BUDGET unit — 9.3s against a 5s ceiling (+4.3s), verdict FAIL, measured 9m ago`, exit 1. `cases.unit` 1250 → 700: `OVER COUNT unit — 734 case(s) against a 700 ceiling (+34)`, exit 1, both named in the summary. A ceiling of `0` exits 2 with the right sentence. The unnamed paths are S1 (a FAILED run graded), S2 (the wrong row picked), S3 (unmeasured counted as within budget) and S4 (the census only checked upward) |
| 5 | `make precommit` is the narrow rung, `make milestone` is everything, CLAUDE.md says so | **met (read, not run)** | `Makefile.tiers:13-14` sets `GDK_PRECOMMIT_TIERS := unit` and `GDK_MILESTONE_TIERS := matrix budget`; CLAUDE.md's verification-loop table names the five rungs with costs; `devkit.toml:192` sets `[verify] feature = "make test"`, which `8aa7666` moved off `make precommit` — the hour-long hole the config comment records. `make precommit` and `make milestone` were NOT run (see below) |
| 6 | `test-writer`, `reviewer` and `verification-reviewer` carry it | **met** | Five installables carry the shared blocks: `developer.md`, `reviewer.md`, `simplifier.md`, `test-writer.md`, `verification-reviewer.md`. Extracted each delimited block and hashed it — `cheapest-proof-review` and `new-test-justification` are **one distinct body each** across the three that carry them; `test-writer.md:107` and `developer.md:132` carry the build-side `cheapest-proof` variant. The one copy installed in this repo (`.claude/agents/verification-reviewer.md`) is byte-identical to its source |
| 7 | CLAUDE.md gains the tenth hard rule | **met** | Present, and it is the counterweight it claims to be — it names the four load-bearing modules, the prove-it-once rule, and *"a tier that got slower is a finding"* |
| 8 | the ledger records what each TIER cost, so `verify --plan` answers what was `unknown` | **met for the rung this feature owns** | `verify --plan` now prints `feature  make test  96583 ms (census 1401, FAIL)`. `milestone` is still `unknown` — `make milestone` is prerequisite-only and opens no slot, which is the prior review's G3, dispositioned `rejected` and filed as `0.2.0/bugs/a-composition-has-no-slot`; not re-litigated. Note the contrast with S1: `--plan` renders the FAIL, `check budget` does not |
| 9 | the full suite is green and the pass count does not drop | **cannot be judged in this checkout** | The suite is NOT green here: `2 failed` in `unit`, `3 failed` in `test`. All 30 evidence lines of the two `test_consumer_independence` failures name files under `.claude/worktrees/`, which are untracked trees belonging to other sessions and out of this review's scope; the third was S9. The pass count has since dropped 1,853 → 1,411 by way of `3afa141`, deliberately and in a different feature — which is S4's point, not this criterion's failure |

## The three mechanisms the feature is built on, each run

- **The mark is derived and a hand-applied one is refused by name.** Scratch suite under a copy of
  the real `tests/conftest.py`. A FALSE mark on a non-spawning module: exit 4, `ERROR:
  hand-applied 'shell' mark in: tests/test_innocent.py …`. A TRUE mark on a module that really
  spawns: **refused identically**, which is the docstring's stated intent and the harder half.
  Both at once: one error naming both files. Delete the marks and the derivation puts the spawner
  in `-m shell` and the innocent module in `-m "not shell"` with no further input.
  `tests/test_shell_mark.py:295`'s `HandApplicationIsRefused` already holds all three.

- **The two slices partition the suite exactly.** From `--collect-only`, as sets of node ids:

  ```
  shell 673 · not shell 738 · all 1411
  in BOTH slices     0
  in NEITHER slice   0
  in a slice but not collected  0
  modules carrying shell: 19 of 46
  ```

  673 + 738 = 1411. `19 of 46` is exactly the number the feature's Close table claims.

- **A `PY_FLOOR` outside `PY_MATRIX` is refused before anything runs.**
  `make matrix PY_FLOOR=3.99 UV=/usr/bin/false`, recorder disabled so the committed ledger was not
  written:

  ```
  EXIT=2
  [MATRIX] REFUSED: PY_FLOOR "3.99" is not in PY_MATRIX "3.11 3.12 3.13 3.14", so no
           interpreter would run the whole suite — full log: .gate-reports/matrix.log
  ```

  The log body is one line — the refusal — so no interpreter ran, and the refusal path files no
  cost row at all (`gdk-gate: gate "matrix" published no verdict this library can name`), which is
  the honest answer for a gate that did not execute.

## Measured tier numbers, my runs

| tier | wall | cases | verdict | load |
|---|---|---|---|---|
| `make unit` | 9.4 s / 13.4 s | 734 passed, 2 failed, 2 skipped, 673 deselected | FAIL (S9 / worktrees) | 72 / 28 |
| `pytest -m "not shell"` | 21.0 / 31.2 / 35.7 s | same 734 | — | 72 |
| `make integration` | 90.4 / 92.4 / 86.4 s | 673 passed, 52 subtests | PASS | 72 |
| `make test` | 123.8 s | 1406 passed, 3 failed, 2 skipped, 568 subtests | FAIL | 72 |
| `make check` | ~2 s | 5 checks | PASS | 28 |
| `uv run -q agentic-sdlc check all` | — | doc 5 · grain-shape 63 · pm 62 grains · shell 10 · hooks 7 | PASS | 28 |
| `verify --check` | — | 23 rules, 240 of 243 tracked files matched, 16 runs unvalidated | PASS | 28 |

## What was NOT verified

- **`make milestone`, `make precommit` and `make matrix` past its refusal path were never run.**
  Nothing ran on 3.12, 3.13 or 3.14; every number here is 3.11.15 on macOS.
- **`make fuzz` was not run**, and the fuzz tier's interaction with the `shell` partition was not
  examined.
- **No consumer install was performed.** `install-gates` and `install-agents` were not run into a
  temp repo; criterion 6 rests on the source installables plus the one copy installed here.
- **The two `test_consumer_independence` failures were not proven absent on a clean checkout** —
  only that all 30 of their evidence lines name `.claude/worktrees/` paths. Whether the hard-rule-8
  census should be walking untracked directories at all is a question for whoever owns that
  module, not raised here.
- **`gdk_gate.sh`'s census plumbing was not re-derived.** `GDK_GATE_CENSUS` is the milestone
  review's L3; I read the census values off the rows the tiers filed and confirmed they match the
  pytest summary line, and went no further into the shell.
- **`check budget` against a corrupt or unreadable ledger** (`LedgerError` → `_last_costs`
  returning `({}, defect)`) was not probed; nor was a `gate` row with a non-integer
  `duration_ms`.
- **A census of exactly 0 was injected, not produced.** A hand-written row with `census: 0` reads
  `ok unit — 0 of 1250 case(s)` and PASS — but I did not establish that a real tier run can file
  one, and the plausible routes (collection error, everything deselected) exit non-zero, which the
  tier reports as FAIL. Filed here as context for S1/S3 rather than as its own finding.
- **xdist behaviour was not attacked.** Whether `--dist loadgroup` actually serialises the
  `xdist_group`-marked tests that spawn `make` against this repo, and whether the worker count
  changes outcomes, were not probed — the tiers were run only at `-n auto` on 8 cores.
- **Every timing number is contended.** Load average ranged 26–72 on 8 cores throughout, and the
  committed `ledger.jsonl` was written by other sessions during the review; the rows I attribute
  to my runs are identified by timestamp above, and rows with census 736 are not mine.
- **The branch moved.** Measurements are at `f8e9e94`; HEAD is `6b67cd6`. The four files under
  review are unchanged between them, and nothing at `6b67cd6` outside them was reviewed.

Reviewer's token cost: ~165k.

```text
verdict: HOLD
| id | severity | disposition |
| S1 | CRITICAL | open |
| S2 | CRITICAL | open |
| S3 | MAJOR | open |
| S4 | MAJOR | open |
| S5 | MINOR | open: the ceiling holds at rest and is exceeded at load 72 |
| S6 | MINOR | open: latent, zero spawns in today's unit tier |
| S7 | MINOR | open |
| S8 | NIT | rejected: the record already discloses criterion 3 as not met, which is the right posture |
| S9 | MINOR | landed 6b67cd6 |
```
