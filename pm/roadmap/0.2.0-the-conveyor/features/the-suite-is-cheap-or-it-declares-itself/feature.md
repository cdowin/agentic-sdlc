---
id: 0.2.0/the-suite-is-cheap-or-it-declares-itself
milestone: "0.2.0"
name: A test proves it the cheapest way that can fail, and the budget is a gate
status: building
reviewed:
phase: 6
depends_on: []
consumed_by: []
risk: medium
size: l
labels: ["tests", "economics", "gates", "installables", "subtraction"]
---

# A test proves it the cheapest way that can fail, and the budget is a gate

**Chris, 2026-09-05, on being shown a 240-second suite:**

> *"This is a dead simple set of scripts. The integration suite shouldn't take more than 2-3
> minutes, ever. We're probably over-integrating. Most of those tests are probably unit tests in
> disguise. … I'm tired of waiting for tests forever."*

> *"How did we get into this mess? Don't we have a test writer? Don't reviewers watch for this
> kind of thing? Should be part of agents, skills, CLAUDE.md etc."*

**This milestone exists to end a measured 170x — a wide gate run in a loop — and its own suite is
the same defect one layer down.** That is not irony worth noting and moving past; it is the
strongest evidence available that naming the failure in a tool does not remove it from the hands
that built the tool.

## Measured, 2026-09-05, before any of this

| | |
|---|---|
| tests | 1842, plus 691 subtests |
| wall | 240 s on one interpreter; `make milestone` multiplies it by `PY_MATRIX` |
| CPU | **150 s of 240 s — 62%.** Not compute-bound. Spawn-bound. |
| modules carrying the `shell` mark | **32 of ~46** |
| scoped pytest fixtures in the whole suite | **1** |
| tree builders that are per-test `@contextlib.contextmanager`s | **18** |

## How it happened, and it was not discipline

**1. The architecture made the integration test the only option.** `core/project.py`'s
`repo_root()` shelled out to `git rev-parse --show-toplevel`, `load_config()` was keyed off it,
and both were zero-argument `lru_cache`s. So there was no way to test a config-reading function
without a real git repo on disk, and no way to point either at another tree except `os.chdir` +
`cache_clear()`. Every author hit that wall and did the only thing available: `git init`. **Nobody
chose an integration test — the design chose it for them, about 1800 times.**

**2. The doctrine only pushed one way.** *"The committed fixtures ARE the fixtures"*,
*"self-hosting is the behavior proof"*, rule 4's *"prove the file census matches intent"* — all
correct, all aimed at the read-side cardinal sin. **There was no counterweight.** Nothing said
*prove it the cheapest way that can actually fail*, so every judgement call resolved toward "more
real".

**3. CLAUDE.md mandated the widest thing per change.** *"Run `make precommit` after a change"* —
and `precommit` is `gates hooks-self-test test`, the entire suite. Twenty `[[verify.narrow]]`
rules exist for exactly this, and the doctrine sentence above them contradicted them.

**4. Nobody's job was speed.** `reviewer.md` and `verification-reviewer.md` mention neither
speed nor spawning. **Reviewers catch what the rules name, and no rule named this.**

**5. The measurement existed and was normalised.** CLAUDE.md records *"~85% of this suite's wall
clock is subprocess"* — and uses that fact to justify **skipping interpreters in the matrix**
rather than to fix the spawns. The number was known, written down, and treated as weather.

**6. The instrument could only observe.** `conftest.module_spawns` DERIVES the `shell` mark by
parsing each module for a `subprocess` import. It reports the mess; it cannot constrain it. And
G3 means `verify --plan` reads `unknown` for both wide rungs, so the one tool that would have
shown the ratio was blind.

## The budgets, and they are guidelines with teeth

Chris's numbers, argued rather than accepted:

| tier | budget | why |
|---|---|---|
| **unit** | **< 5 s**, zero subprocess, zero git | it is a code run |
| **integration** | **< 30 s total**, and COUNTED — tens, not thousands | a single case over ~2 s is testing too much or rebuilding shared setup |
| **full gate** | **< 2 min** across `PY_MATRIX` | N × the suite is legitimate *provided the thing multiplied is seconds* |

Where this pushes back on the brief: a 30-second *individual* integration test is already a bug,
not a ceiling — and the release gate may legitimately take minutes, because it is a multiple.

## The shape of the fix

**Cheap by construction, expensive by declaration.**

1. **`repo_root` walks for `.git` instead of spawning git.** One function; every config read comes
   through it. A tree only has to be MARKED to be found, so a fixture is a `mkdir` rather than
   three processes.
2. **Share the expensive TEMPLATE, copy per test.** A pristine repo built ONCE per session, and
   `shutil.copytree` per case. Chris proposed shared-state-plus-cleanup; **the copy is the robust
   version of the same idea** — isolation is total and requires no cleanup discipline, because
   nothing is shared. Cleanup by convention is the class of problem that produced this feature.
3. **Parallelism.** 56% CPU is half a machine idle on a spawn-bound suite. `pytest-xdist` is a
   TEST-time dependency, like pytest itself; hard rule 1 governs the RUNTIME, and a consumer's
   pre-push hook resolves neither.
4. **The tier is DECLARED and BUDGETED, not derived.** The mark stops being inferred from a
   `subprocess` import and becomes a declaration with a census the gate fails on — rule 4's own
   shape, pointed at this suite for the first time.
5. **The ladder is fixed.** `precommit` becomes the narrow rung; the full suite moves to
   `milestone`; CLAUDE.md stops saying otherwise.
6. **It is encoded where it will be enforced next time** — the agent roster, CLAUDE.md, and the
   ledger — because this feature's whole finding is that a rule nobody wrote is a rule nobody
   catches.

## Ship criteria

1. **Nothing in `core/` spawns to answer where the checkout is.** `repo_root` walks; `git_lines`
   still spawns, because asking git what CHANGED is genuinely git's question.
2. **The unit tier runs in under 5 seconds and spawns nothing**, and a test asserts the spawn
   count is zero rather than trusting it.
3. **The integration tier is under 30 seconds**, is counted, and every member DECLARES itself.
4. **A budget is a GATE**: `check` fails when a tier exceeds its declared ceiling or its census
   grows past its declared size, naming what grew. Rule 4 applied to cost.
5. **`make precommit` is the narrow rung**, `make milestone` is everything, and CLAUDE.md's
   verification-loop section says so.
6. **`test-writer`, `reviewer` and `verification-reviewer` carry it**, so a consumer's roster
   inherits the rule instead of each project re-learning it at 240 seconds a run.
7. **CLAUDE.md gains the tenth hard rule** — the counterweight that was missing.
8. **The ledger records what each TIER cost**, so `verify --plan` answers the question that was
   `unknown`, and the next drift is visible in telemetry rather than in somebody's patience.
9. **The full suite is green and the pass count does not drop.** A speed-up that deletes coverage
   is the write-side cardinal sin wearing a stopwatch.

## Risks

1. **A budget that fails the gate on a slow machine is a gate that gets deleted.** It has to be
   generous, measured on the ledger rather than guessed, and it must name what grew rather than
   only that something did.
2. **`copytree` hides a test that depended on shared state.** That is a feature — it will surface
   as a failure — but it will surface as a CONFUSING failure, so the conversion goes tier by tier
   with the suite green in between.
3. **Deleting an integration test because it is slow is the sin this feature is supposed to
   prevent.** The conversion is narrow→cheap, never wide→gone. Criterion 9 is the guard.
4. **xdist makes an order-dependent test flake instead of fail.** `test_boundaries`'s
   `OneApply` case was already found order-dependent once (L2 of the release review). Parallelism
   will find the rest, and each one is a real finding.

## Close

**Measured, on the floor interpreter, before and after:**

| | before | after |
|---|---|---|
| `make precommit` (per edit) | 240 s+ | **10.3 s** |
| unit tier | did not exist as a target | **7.2 s**, 1112 tests, one process |
| integration tier | — | **60 s**, 730 tests, 8 workers |
| whole suite | 240 s | **39 s** |
| CPU utilisation | 62% | **463%** |
| modules carrying `shell` | 32 of ~46 | **19 of 46** |
| tests | 1842 | **1853** |

**The pass count went UP.** 419 tests came back out of the slow tier because they had been marked
integration for a branch they never took, and eleven are the budget gate's own. Criterion 9 held:
nothing was deleted to make a number smaller.

### Where the time actually was

Four things, and only the last was a test being wrong:

1. **`repo_root` spawned `git rev-parse` on every config read** — one function, and the reason
   1800 tests ran `git init`.
2. **xdist was never used** on a suite that was 62% idle.
3. **Two mutation cases in `test_gate_library` were 47 of 96 seconds**, waiting on a corpus that
   slept 20 s against a 10000 ms ceiling. The proof is a RATIO, so it sleeps 3 s against 2000 ms
   now — every margin still wide, `--self-test` still 62 cases.
4. **A handful of tests spawn `make` against THIS repo** and collided under parallelism. They pass
   alone and fail together, which is the shape a serial suite hides. `xdist_group` is the
   declaration that fixes it, and it says out loud what they share.

### Three findings this surfaced that were not about speed

- **`test_verdict`'s shared-paragraph check built its reference and its subjects by DIFFERENT
  rules** — subjects cut at the next `## `, the reference run to end of file. They agreed only
  while `reviewer.md` happened to end with that section. The first block appended after it failed
  all five cases against a paragraph that had not changed. One extractor now.
- **`test_makefile_gates` had two `pytestmark` assignments**, and the second silently replaced the
  first: the module lost its `make`-is-missing skip the moment a second mark was added beside it.
- **A budget gate in `check all` is circular.** It grades the last recorded run, and `check all`
  runs inside a test that spawns `make gates` against this tree — nine tests went red for a timing
  number unrelated to what they assert. D10 carries the ruling.

### What is encoded, so this is caught rather than re-discovered

CLAUDE.md **hard rule 10** and its verification-loop section; `test-writer`, `developer`,
`reviewer`, `simplifier` and `verification-reviewer`, so a consumer's roster inherits it;
decision **D10**; and the telemetry — every tier files a `gate` row with its duration on every
run, and `check budget` is what reads them.

### Criterion 3, honestly: NOT met

The integration tier is 60 s against a 30 s target and 730 tests against "tens". The tier is
declared, counted and budgeted — but it is not yet SMALL. What remains is the conversion the
feature names and did not finish: a pristine template built once per session and `shutil.copytree`
per case, replacing the per-test `git init` in the modules that genuinely need a repository. The
ceiling is set at 130 s so it cannot drift further while that work waits.

done: in-place — the ladder, the budget gate, the rules and the roster. 1853 passed, 2 skipped,
691 subtests; `check all` green.
