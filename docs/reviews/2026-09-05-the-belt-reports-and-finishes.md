# Feature review — `0.2.0/the-belt-reports-and-finishes` — HOLD

Feature-level pass (SDLC.md §0) over the commit range of `0.2.0/the-belt-reports-and-finishes`:
**`08f15d2`** (the walk always finishes), **`50cc01d`** (`--skip` goes, the machine writes the row)
and **`4a351a4`** (R1 + R2 — `findings-resolved` reads the pointers). Branch
`milestone/0.2.0-the-conveyor`, run 2026-09-05.

**Adversarial by execution.** Every criterion below was judged by running something. The conveyor
was walked against a **scratch copy of this checkout** (`git ls-files` → rsync + a copy of `.git`,
under the session scratchpad) with **`origin` removed first**, so `push-branch` and `tag` could not
reach the real remote; the CLI there is `uv run -q agentic-sdlc …`, the working tree installed on
itself. Six further probes ran through `driver.main` with an injected registry in `tempfile` trees.
Nothing in this checkout was modified except this record.

The subtraction itself is real and it works: **a red gate no longer costs a release the eleven steps
behind it.** A 21-step release over a red `gate` reached `prove-artifact` and printed a scoreboard.
The blockers are not in `_walk`. They are in the three places that still describe the OLD machine —
one of which is the document `install-sdlc` renders into every consumer's repo — and in the one
criterion that asks for work that has not been done.

## Blockers

### B1 (BLOCKER) — the shipped protocol document still publishes the postcondition R1/R2 deleted

`src/agentic_sdlc/repo/conveyor/steps.py:2616-2618` — the `STEP_DOC` entry that
`install-sdlc` renders — still reads:

> `findings-resolved` … *no document under the review directory names this milestone — every record
> resolved and deleted.*

That is verbatim the postcondition criterion 6 exists to remove, and `docs/sdlc-protocol.md:68`
carries it today:

```
$ grep -n "findings-resolved" docs/sdlc-protocol.md
68:| 14 | `findings-resolved` | JUDGEMENT | — *(operator)* | no document under the review
   directory names this milestone — every record resolved and deleted. |
```

The CODE is fixed. `check_findings_resolved` (`steps.py:1285-1317`) is one line — `ready_for(ctx,
'tag')` — and `do_findings_resolved` (`:1320-1325`) says *"The RECORD stays"*.
`tests/test_conveyor_steps.py:402` and `:428` prove both halves, including that a satisfied step
leaves `check pm` green. **The generated document was not regenerated from a fixed source, because
the source of that sentence is a second table nobody changed.**

This is worse than a stale comment. `docs/sdlc-protocol.md` is the file `install-sdlc` writes into
consumer repos, and its own header says it exists so that *"a hand-written document describing the
steps is the second home for the protocol, and a second home drifts — which is the failure this file
exists to end."* An operator who follows row 14 deletes the review record, and `check pm` D1 —
a gate in `[checks] all` — goes permanently red. That is R1/R2 shipping under a document that
claims it cannot drift.

`install-sdlc --diff` on the scratch tree reported **no** drift for this row, so nothing in the gate
set will catch it: the renderer and the tree agree, and both are wrong.

### B2 (BLOCKER) — criterion 8 is not met: the 26 stories are still parked at `reviewing`

Criterion 8: *"The 26 stories parked at `reviewing` are walked through `close story` for real, and
the ledger holds their rows."* It is I2 from
`docs/reviews/2026-09-05-the-inner-levels-are-belts-too.md`, carried forward at
`open: the 26 parked stories close through the belts in phase 5`.

```
$ uv run -q agentic-sdlc pm list --status reviewing | head -1
[pm] 26 of 31 story/ies

$ python3 -c "…count kinds in pm/roadmap/0.2.0-the-conveyor/ledger.jsonl…"
Counter({'gate': 86, 'test': 85, 'status': 47, 'decision': 10})
deviation rows: 0
```

Twenty-six stories, zero belt rows, and the feature's own directory
(`pm/roadmap/0.2.0-the-conveyor/features/the-belt-reports-and-finishes/`) holds `feature.md` and no
`stories/`. The criterion's own sentence says why it matters: *"it is the only way criterion 10 gets
tested before the release itself"* — the belts have not been run at volume against real grains.

(The record numbers a criterion 10 it does not contain; there are eight. A separate NIT, N2.)

### B3 (BLOCKER) — a `ConfigError` raised by a step's `check()` escapes as a traceback at exit 1, not exit 2

`ask()` (`driver.py:318-325`) re-raises `ConfigError` and the docstring states the intent exactly:

> *a malformed declaration is the reader failing, not a check reporting, and it belongs to exit 2
> before the walk rather than to a row on the scoreboard.*

Nothing implements the second half. `driver.py:902` calls `walk(...)` with no `except ConfigError`,
and `cli.py`'s only `ConfigError` handler is inside `_run_check` (`cli.py:266-272`). Reachable from
a shipped step and an ordinary consumer typo — `[release.version_files]` is read by
`check_version_sync` at step 6, during the walk (`steps.py:694`, `:1087`):

```
$ # scratch copy, devkit.toml: "pyproject.toml" = 42
$ uv run -q agentic-sdlc release 0.2.0 ; echo "EXIT=$?"
Traceback (most recent call last):
  File ".../src/agentic_sdlc/cli.py", line 409, in main
    return driver.main([cmd, *rest])
  File ".../repo/conveyor/driver.py", line 902, in main
    result = walk(known, names, ctx, run, record=recorder)
  File ".../repo/conveyor/driver.py", line 457, in walk
    answer = ask(step, ctx)
  ...
agentic_sdlc.core.config.ConfigError: [release.version_files] pyproject.toml must be a regex string, got 42
EXIT=1
```

Three things are wrong at once, and D8 is what makes them reachable:

1. **Exit 1, not 2.** Hard rule 6 gives 1 to findings. A consumer's CI reads a config typo as drift.
2. **The transcript is destroyed.** `walk` accumulates lines and `main` prints them only on return,
   so the five steps that were walked before the crash printed *nothing*. Not one line.
3. **Side effects survived the silence.** The crashed run appended a real `deviation` row —
   `release changelog-unreleased-nonempty not-true` — to the milestone ledger, and
   `.agentic-sdlc/run/` was never written. The tree changed; the operator was handed a stack trace.

The committed test proves only the half that is true. `test_a_ConfigError_is_re_raised_because_it_is_
the_reader_failing` (`tests/test_conveyor_driver.py:552-564`) asserts `assertRaises(ConfigError)`
around `_walk` and stops — one altitude below the claim. Its own docstring says *"it belongs to exit
2 before the walk"*, and no case asks `main` or the CLI whether that is what happens.

The same escape exists on `perform()` (`driver.py:339`), which I did not construct.

### B4 (BLOCKER) — the generated protocol document contradicts itself about halting, in the same file, 16 lines apart

`docs/sdlc-protocol.md:21-25`:

> *It walks the list below in order and **stops at the first step whose postcondition is not true**
> … Exit `0` the run completed, `1` it stopped on a step, `2` a usage or config error.*

`docs/sdlc-protocol.md:37`:

> ***No step halts the walk.** Every step is a check, every check reports, the run reaches its last
> step whatever any check said…*

Both are rendered: line 21 from `src/agentic_sdlc/repo/installables/sdlc-template.md:21,25`, line 37
from the same template's D8 paragraph. Rows 17 and 18 of the release table
(`docs/sdlc-protocol.md:71-72`, from `steps.py:2622-2626`) add *"the operator is asked and the run
refuses to advance"* for `pr-open` and `ci-green` — measured false on the scratch run, where both
answered `UNVERIFIABLE` and the walk continued through `merge`, `tag` and `prove-artifact`. The same
sentence is in `install.py:342`, in the text `install-sdlc` prints to the operator.

A consumer reading their own installed protocol cannot tell which half of it is true. Criterion 5
names "the docs" for `--skip`; this is the larger version of the same omission and it ships.

## Non-blocking findings

### M1 (MAJOR) — this repo's own release skill still documents `--skip`, which now exits 2

`.claude/skills/release/SKILL.md:49-55` carries a `## Deviating` section:

> *`--skip <step> --reason "<why>"` writes a `deviation` row to the milestone's `ledger.jsonl` and
> walks on. … If the same step is skipped every release, that step is wrong…*

and `:38` says the judgement steps *"refuse to advance rather than pass"*. Measured — the flag is
gone from all four operations:

```
$ uv run -q agentic-sdlc release 0.2.0 --skip gate --reason x        → exit 2
$ uv run -q agentic-sdlc release 0.2.0 --reason x                     → exit 2
$ uv run -q agentic-sdlc adopt 0.2.0 --skip pin-bumped --reason x     → exit 2
$ uv run -q agentic-sdlc close story 0.2.0/a/b --skip claimed --reason x   → exit 2
$ uv run -q agentic-sdlc close feature 0.2.0/a --skip stories-done --reason x → exit 2
agentic-sdlc: release: --skip was removed in 0.2.0: no step refuses to advance any more, so there
is nothing to skip. Every step that is not true is already a `deviation` row in the ledger with the
reason the step itself gave — `--status` prints them
```

The refusal is good and it names the replacement. The skill that tells the operator how to cut a
release is the one document that still teaches the removed flag.

### M2 (MAJOR) — the `close story` belt PRINTS instructions to use the removed flag

`steps.py:2260-2265`, `do_committed`, ends: *"…if some of them are another agent's work in the same
worktree, that is what `--skip --reason` records"*. This is not a comment; it is a `SAID` line on
the belt SDLC.md §0 says runs constantly. Measured on the scratch tree:

```
[story:committed] JUDGEMENT SAID — commit your own paths, by explicit pathspec — this machine never
commits for you, and it cannot know which of the paths above belong to this story; if some of them
are another agent's work in the same worktree, that is what --skip --reason records
```

An operator who follows the machine's own instruction gets exit 2. Criterion 5's replacement
sentence — the machine writes the row itself — is what belongs there.

### M3 (MAJOR) — criterion 4's named test does not exist

Criterion 4: *"**A test asserts the belt and the gate disagree** — the belt moved it, the gate
reports it, and that is correct."*

The BEHAVIOUR is right, and I measured it. On the scratch tree the release walked past a red `gate`
and a not-true `features-done`, performed `milestone-done`, and left the tree contradictory —
`check pm` then reported it, loudly:

```
[release:milestone-done] AUTOMATIC DONE — pm/roadmap/0.2.0-the-conveyor/milestone.md is 'done'
$ uv run -q agentic-sdlc check pm | tail -1
[check:pm] FAIL — 15 status-drift / integrity violation(s) across 2 milestone(s), 15 feature(s),
31 story/ies, 6 bug(s), 52 ref(s)
```

But nothing in the suite asserts it. `grep -rn "check_pm\|checks import pm" tests/test_conveyor_*.py`
returns exactly one hit — `test_a_performed_findings_resolved_leaves_check_pm_green`
(`tests/test_conveyor_steps.py:428`), which is criterion 6's, not this one. The reviewer contract
says a harness worth running once is worth committing; this is the harness, and this criterion
asked for it by name.

### M4 (MAJOR, outside this feature) — `prove-artifact`'s configured command has an unsubstituted `{version}`

Surfaced by D8, which is the point: the walk now reaches step 21. `devkit.toml:329`:

```toml
prove-artifact = "uvx --from git+https://github.com/cdowin/agentic-sdlc@v{version} agentic-sdlc --version"
```

`grep -rn "{version}" src/agentic_sdlc/repo/conveyor/` returns nothing — the conveyor never
substitutes a placeholder into a command; the only `{version}` templating in the package is in the
installables. Measured on the scratch run:

```
[release:prove-artifact] JUDGEMENT NOT-TRUE — `uvx --from git+…@v{version} agentic-sdlc --version`
exited 1 — Updating https://github.com/cdowin/agentic-sdlc (v{version}) × Failed to resolve …
```

This repo's own release will report `prove-artifact` not true forever. It belongs to
`the-release-is-a-conveyor`'s surface rather than this one, and it is raised here because this is
the pass that could reach it.

### N1 (MINOR) — `driver.py`'s "Line shapes are contract" block documents shapes the module no longer emits

`driver.py:88-100` still lists `[release:gate] GATE STOPPED — 12 failures`, `[release] STOPPED —
'gate' (GATE) at step 10/21…` and *"1 it stopped on a step"*, and lists no scoreboard line. The
CHANGELOG's `## Unreleased` records the shape change correctly; the module whose contract it is does
not. Criterion 7's two named halves ARE met — the first line reads *"a step machine that walks,
reports and finishes"* and `pm-execution.md`'s report-never-refuse rule is quoted at `:34-37` — so
this is a separate finding, not a failure of 7.

### N2 (MINOR) — a not-true step with an empty `detail` writes no ledger row, silently

`driver.py:503`: `if record is not None and answer.detail:`. Measured with two stub steps answering
`Answer.no('')` and `Answer.unverifiable('')`:

```
[release:a] JUDGEMENT NOT-TRUE
[release] step 1/2 'a' (JUDGEMENT) is not true; what would make it true:
[release:b] JUDGEMENT UNVERIFIABLE
[release] step 2/2 'b' (JUDGEMENT) is not true; what would make it true:
[release] 0/2 true · 1 not true: a · 1 unverifiable: b
LEDGER ROWS: 0
```

The scoreboard is honest; the durable half is empty. `Answer`'s own docstring names the hazard
(*"a step that answers FALSE with an empty detail has told the operator that something is wrong and
nothing about what"*) and nothing refuses it. `Answer.no()` defaults `detail` to `''`. I did **not**
prove that no shipped step can produce one — see "What I did not verify".

### N3 (MINOR) — a `deviation` row is never superseded, so `--status` reports a step that is now true

Idempotence keys on the step NAME alone (`_recorded`, `driver.py:926-933`). Two consequences,
measured:

```
P5  run1 exit 1 | rows 1     (step not true, reason "reason from run 1")
    run2 exit 1 | rows 1     idempotent — correct
    run3 exit 0 | rows 1     the step is now TRUE; PASS — 1/1 steps
    $ release 9.9.9 --status
    [release:a] NOT-TRUE — reason from run 1 (2026-09-06T02:06:42Z)
    [release:a] cached TRUE (2026-09-06T02:06:42Z) — a cache, never the authority

P6  not-true for "reason A", then not-true for "reason B — completely different"
    rows: [{"outcome": "not-true", "reason": "reason A"}]
```

Under `--skip` the row was an operator's historical act and could not go stale. Under D8 it is the
machine's account of the tree, and the tree moves. `--status` prints the two halves adjacent and
labelled, which is most of the mitigation — but the two lines contradict each other and neither says
so. Reason drift is dropped entirely.

### N4 (NIT) — a stray `unittest.main()` sits mid-file with three test classes below it

`tests/test_conveyor_driver.py:426-427`. `TheWalkAlwaysFinishes` and
`ACrashIsAnAnswerNotATraceback` — the two classes this feature added — are both below it. Harmless
under pytest, invisible under `python tests/test_conveyor_driver.py`.

### Q1 (QUESTION) — a GATE that subprocesses `agentic-sdlc` folds the callee's exit 2 into "not true", and the belt then performs

Not demonstrably a defect — it may be exactly what D8 intends — but it is the one place the ruling's
own boundary blurs, so it is raised as a question. `[verify] feature = 42` in the scratch tree:

```
[story:narrow-verified] GATE NOT-TRUE — `agentic-sdlc verify --story …` exited 2 — a CONFIG or
usage error, not a finding, so nothing was decided: [verify] feature must be a string, got 42
…
[story:story-done] AUTOMATIC DONE — …01-the-ledger-holds-what-a-gate-cost.md is 'done'
[story] 3/5 true · 2 not true: narrow-verified, committed
```

The step's own detail says *"nothing was decided"*, and the belt then decided: the story flipped to
`done` with its narrow check never run, at exit 1 rather than 2. D8 says the walk reports and the
caller decides — but the driver's docstring also says a malformed declaration is *"the reader
failing"* and belongs to exit 2 before the walk. A GATE spawning this same CLI is the seam where
those two rules meet, and the answer is a ruling, not a bug report.

## Criteria, each judged by the measurement that judged it

| # | criterion | verdict | the measurement |
|---|---|---|---|
| 1 | no step halts the walk | **met** | scratch `release 0.2.0` with `[release.commands] gate = "sh -c 'echo 12 failures; exit 1'"`: `gate` red at step 10, and the transcript carries a line for every one of the 21 steps through `[release] step 21/21 'prove-artifact'`. Every step's `check()` ran (probe P1: `after` a raising step still answered) |
| 2 | the final line is a scoreboard with counts and names | **met** | `[release] 12/21 true · 6 not true: tree-clean, features-done, gate, push-branch, merge, prove-artifact · 3 unverifiable: pr-open, ci-green, tag`. not-true and unverifiable kept apart; a fully-true run prints `[release] PASS — 1/1 steps` (P5 run3) |
| 3 | exit 0 / 1 / 2 per hard rule 6; a test asserts a red gate reaches `tag` at exit 1 | **NOT met — B3** | 0 and 1 correct (P5 run3 → 0; the red-gate run → 1). The test exists and is real (`tests/test_conveyor_driver.py:442`, asserts `tag` PERFORMED, `result.done == ('tag',)`, exit 1). **Exit 2 leaks**: a `ConfigError` from a step's `check()` is a traceback at exit 1 |
| 4 | `check pm` unchanged and still fails a contradictory tree; a test asserts belt and gate disagree | **half met — M3** | behaviour measured: belt performed `milestone-done`, `check pm` → `FAIL — 15 status-drift … violation(s)`. The named TEST does not exist anywhere in `tests/` |
| 5 | `--skip` gone from the CLI, the docs and the ledger's row vocabulary; a not-true step writes the row | **NOT met — M1, M2** | CLI: exit 2 on all four operations, message names the replacement. Ledger: `OUTCOMES = ('not-true', 'unverifiable', 'skipped')` (`ledger.py:193`) with `skipped` retained for old rows and documented as such; the scratch run wrote 9 machine-minted rows, outcomes `not-true`/`unverifiable`, one per not-true step, idempotent on re-run (P5). **Docs: `.claude/skills/release/SKILL.md:49-55` and a live `SAID` line from `steps.py:2265`** |
| 6 | R1/R2 close: `findings-resolved` reads the `reviewed:` pointers, never a substring, never absence; a completed release leaves `check pm` green | **NOT met — B1** | code correct: `check_findings_resolved` = `ready_for(ctx, 'tag')` (`steps.py:1317`), proven by `tests/test_conveyor_steps.py:402` (an `open` finding is named, the record STAYS) and `:428` (`check_pm.run()` → 0). Live run: `[release:findings-resolved] JUDGEMENT ALREADY-TRUE — RECORD … 10 finding(s), none open`. **The shipped protocol document still publishes "resolved and deleted"** |
| 7 | the driver docstring quotes `pm-execution.md` and stops saying "refuses to advance" | **met** (see N1) | `driver.py:1` reads *"a step machine that walks, reports and finishes"*; `:34-37` quotes the report-never-refuse rule verbatim. Separately, `:88-100` still documents `STOPPED` shapes |
| 8 | the 26 parked stories are walked through `close story` for real and the ledger holds their rows | **NOT met — B2** | `pm list --status reviewing` → `[pm] 26 of 31 story/ies`; the milestone ledger holds 0 `deviation` rows and no belt evidence |

## What I did not verify

- **`make milestone`, `make test` and the interpreter matrix were not run.** My slice was
  `tests/test_conveyor_{driver,deviation,close,adopt}.py` → **204 passed in 70.31 s**, my run, on
  this tree. That is 0.34 s per case for four modules; three of the four spawn, so it is expensive
  by design, but nobody has stated the number and rule 10 says a tier that got slower is a finding.
  I did not compare it against a pre-D8 baseline.
- **`tests/test_conveyor_steps.py` was read, not run.** Criterion 6's two proofs are quoted from the
  source; I confirmed the behaviour they assert independently, against the live tree, through
  `[release:findings-resolved] JUDGEMENT ALREADY-TRUE`.
- **I did not prove that no shipped step can answer FALSE with an empty `detail`** (N2). The gap is
  demonstrated with stub steps only; I read the constructions in `steps.py` and did not
  exhaustively evaluate them against a tree.
- **`perform()`'s `ConfigError` re-raise (`driver.py:339`) was not exercised.** It is the same shape
  as B3 on the other callable; I constructed only the `check()` side.
- **No release was walked to a green PASS end to end.** `push-branch`, `merge`, `tag` and
  `prove-artifact` cannot be true in a scratch clone with no remote, which is deliberate: I removed
  `origin` before the first run so nothing could reach GitHub. `tag` created a local tag in the
  scratch and answered UNVERIFIABLE because the remote could not be asked — correct behaviour, but
  the remote half of that step is unmeasured by me.
- **`close feature` was not walked.** Only its `--skip` refusal was exercised. `close story` was
  walked once, on a real story, in the scratch.
- **Duplicate step names in a list were checked and are not a finding**: `walk` would count one step
  twice (`2 not true: a, a`), but `steps_for` refuses a duplicate at config-read time
  (`steps.py:514-534`), so the path is reachable only through the test-injection seam.
- **Nothing from `docs/reviews/2026-09-05-the-release-is-a-conveyor.md` or
  `2026-09-05-0.2.0-release-review.md` was re-litigated**, including R5, the run-state cache and the
  `CORRECTED` path — though `CORRECTED` did fire correctly during my runs.
- **The `.claude/worktrees/` trees were ignored entirely**, per the brief. Every measurement is
  against `milestone/0.2.0-the-conveyor` at `f8e9e94` or a copy of it.
- **No consumer-side integration was exercised** (rule 8 puts it in the consumer's gate), so B4's
  cost to a real adopting repo is reasoned, not measured.

Reviewer's token cost: ~95k.

```
verdict: HOLD
| id | severity | disposition |
| B1 | BLOCKER | open |
| B2 | BLOCKER | open: I2 carried from the-inner-levels-are-belts-too |
| B3 | BLOCKER | open |
| B4 | BLOCKER | open |
| M1 | MAJOR | open |
| M2 | MAJOR | open |
| M3 | MAJOR | open |
| M4 | MAJOR | open: belongs to 0.2.0/the-release-is-a-conveyor |
| N1 | MINOR | open |
| N2 | MINOR | open |
| N3 | MINOR | open |
| N4 | NIT | open |
| Q1 | QUESTION | open |
```
