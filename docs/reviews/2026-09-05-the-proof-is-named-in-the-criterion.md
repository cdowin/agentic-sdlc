# Feature review — `0.2.0/the-proof-is-named-in-the-criterion` — HOLD

Feature-level pass over `6aeb51e` (phase C), `3afa141` (phases A and B), `97dbd6c`, `33a6f40`,
`182fa72`, `9d60fe8` (the probe pass and the reductions) and the later cuts in `549475f` (the D12
conveyor rewrite), branch `milestone/0.2.0-the-conveyor`, run 2026-09-05/06. Every number below
was produced by running something: the three tier targets five times between them, a
`--collect-only` partition census, an `ast` statement count re-derived at the pre-feature
baseline and at HEAD, twelve deliberately-broken probes in a scratch copy of the source, the two
that stayed green re-run against the whole reduced suite AND against the 1,855-case
pre-reduction suite, and `check budget` against a lowered and then a malformed `[tests] cases`
ceiling. No source, test, config or PM file in this tree was edited; the one file written is
this record.

**HOLD is not "something is broken".** Nothing found here ships a defect, and the four
deliverables that were supposed to survive attack — the probe safety net, the two templates,
`check budget`'s case ceiling, `SDLC.md` §6 — all held under everything tried. HOLD is because
**four of the six ship criteria are not met as written**, three of them by wide margins, and the
feature cannot honestly be flipped to `done` against its own contract until Chris restates them.
The feature's own text says *"the number is a direction, not the goal"* — so the decision is
his, and each finding below carries the one-line restatement I would recommend.

**The measurements moved under me and that is load-bearing for the version numbers.** The branch
was at `2cccde2` when the tiers were run and reached `f712048` by the end, through `218888c` and
two merges, with another session holding uncommitted edits to `tests/test_verdict.py`,
`tests/test_verify_main.py`, `devkit.toml` and two source files throughout. The suite census
moved 1,097 → 1,095 across that window. Every number below is tagged with the revision it was
taken at; none of the drift changes any verdict.

**The machine was not quiet.** Load average ran 5.6 to 33 on 8 cores across the session; sibling
agents were running their own suites and appending to the committed `ledger.jsonl`. Every wall
clock below is an upper bound and each is reported with the load it was taken at, and the
cheap tier was measured five times so the spread is visible rather than asserted.

**The supplied baselines reproduce, exactly.** Re-derived at `0243691` (the parent of phase C):
1,855 collected, 1,478 test functions, 691 subtests, and a tests:src statement ratio of **1.784**
against the feature's claimed 1.80. `3afa141`'s own claims — 1,478 → 1,016 functions, ratio 1.80
→ 1.49 — reproduce at 1,016 and 1.486. Nothing was quietly accommodated.

---

## The blockers

### P1 — criterion 1 is not met, and the unit tier is the half that did not move

**Under 5 s and under 30 s. Measured: 7.68–9.20 s and 37.26–46.17 s.**

| run | revision | load | verdict line |
|---|---|---|---|
| `make unit` | `2cccde2` | 5.6 | `706 passed, 2 skipped, 389 deselected, 505 subtests passed in 7.98s` (real 8.33) |
| `make unit` ×3 | `2cccde2` | 9.7 | `8.29s` · `7.68s` · `8.01s`, identical census each time |
| `make unit` | `f712048` | 8.9 | `703 passed, 2 skipped, 390 deselected, 505 subtests passed in 9.20s` |
| `make integration` | `2cccde2` | 5.6 | `389 passed, 52 subtests passed in 41.51s` (real 41.83) |
| `make integration` | `2cccde2` | 9.0 | `389 passed, 52 subtests passed in 37.26s` |
| `make integration` | `f712048` | 8.9 | `390 passed, 52 subtests passed in 46.17s` |
| `make test` | `2cccde2` | 5.6 | `1095 passed, 2 skipped, 557 subtests passed in 42.52s` (real 42.83) |
| `make check` | `f712048` | 12.9 | `[CHECK] 5 check(s) PASS`, ~2 s, exit 0 |

**The direction was travelled on integration and NOT on unit.** `devkit.toml`'s own pre-feature
note records integration at ~64 s; it is now 37–46 s at 730 → 390 cases. That half is a genuine
40% cut and it is under the old ceiling with room.

The unit tier is the finding. `3afa141` recorded it at **7.1 s for 736 cases**; it is now
**7.68–9.20 s for 705**. The tier lost 37% of its cases against the 1,123 it started at and its
wall clock did not move — because `33a6f40` deliberately moved `test_install.py` **into** it
(96 cases → 51, and 96 processes deleted). That was the right trade and it is well argued in
that commit, but it means the 5 s number was never approached and the tier that absorbed the
move is now further from it than when the number was written. The slowest twelve cases are
0.17–0.59 s and sum to about 3.4 s of the 8, so there is no single offender to cut: reaching
5 s means deleting something that bites.

Recommended restatement: **drop the unit-tier wall clock from the criteria and keep the case
ceiling instead** — a tier holds its clock while doubling in size, which is `check budget`'s own
argument for the census, and integration ≤ 50 s is the number that has actually held.

### P2 — criterion 2 is not met: 1,097 collected against 700, ratio 1.473 against 1.2

Collected, by `--collect-only`, at `2cccde2`:

```
1097 tests collected
708/1097 collected (389 deselected)   -m "not shell"
389/1097 collected (708 deselected)   -m "shell"
in BOTH slices 0 · in NEITHER 0
```

and at `f712048`, after the branch moved: `all=1095 notshell=705 shell=390`, same clean
partition, and stable across three consecutive collections.

Statements, by `ast` over `src/` and `tests/` counting every `ast.stmt` — the method that
reproduces the feature's own 1.80 and 1,478:

| | baseline `0243691` | `3afa141` | HEAD |
|---|---|---|---|
| src statements | 7,798 | 7,837 | 7,495 |
| tests statements | 13,909 | 11,644 | 11,043 |
| **ratio** | **1.784** | **1.486** | **1.473** |
| test functions | 1,478 | 1,016 | 853 |

(A stricter count that excludes `def`/`class`/`import` lines gives 1.654 → 1.389; neither
spelling reaches 1.2.)

**The direction was travelled, and by more than the collected count alone shows.** Subtests are
the number a `--collect-only` census cannot see, and I measured both ends rather than assuming:
the baseline suite ran **691** subtests, HEAD runs **557**. So effective cases went
**2,546 → 1,652, a 35% cut**, against a 41% cut in the collected number. The consolidation used
`subTest` in places precisely because it reduces the collected count — the worry that the
headline number was bought by re-labelling is the one thing I most expected to find here, and it
is not what happened: the hidden half went down too.

What remains is still 57% over the target, and the unit tier alone (705–708) is over it.

Recommended restatement: **"under 1,100 collected and a ratio under 1.5"** as the number this
feature actually reached, with 700 / 1.2 carried forward as the next milestone's target rather
than deleted — the gap is real and naming it as achieved would be the lie the feature exists to
stop.

### P3 — criterion 3 is not met for 776 of the 828 test functions this feature removed

*"No assertion is deleted without a reason recorded. Every removal names either the case that
subsumes it or the reason it proved nothing, in the commit. A diff that only shrinks a number is
not reviewable."*

Counted off the diffs — test functions removed and not re-added under the same name, against
whether the commit body names them:

| commit | removed | named in the body |
|---|---|---|
| `97dbd6c` | 1 | 1 (100%) |
| `33a6f40` | 22 | 22 (100%) |
| `9d60fe8` | 3 | 3 (100%) |
| `182fa72` | 26 | 3 by name, **all 26 by family** — see below |
| **`3afa141`** (phases A and B) | **597** | **0** |
| **`549475f`** (the D12 rewrite) | **179** | **0** |

`182fa72` is compliant in substance and my name-match under-counts it: its body enumerates every
matrix it folded and the single case each became (`TheVersionRefusalMatrix … 12 cases … ->
test_every_row_is_exit_2_runs_no_step_and_writes_nothing`), and it opens with *"No assertion
deleted; every row of every matrix still runs."*

`3afa141` and `549475f` are not. Both bodies are exactly what the criterion names — a diff that
shrinks numbers. `3afa141` reports `verify family 153 -> 68 functions`, `pm gate + verbs 260 ->
136 collected`, `ledger family 239 -> 124` and no subsumer for any individual case. A random
sample of five from each, none named anywhere in its commit:

```
3afa141:  test_a_feature_of_ANY_status_resolves
          test_a_status_outside_the_vocabulary_writes_no_row
          test_a_refused_decision_mints_nothing
          test_d3_done_milestone_with_a_live_feature
          test_off_by_default
549475f:  test_a_row_without_a_reason_cannot_be_minted_at_all
          test_no_adopt_step_names_a_repository
          test_an_empty_step_list_is_a_config_error_not_a_pass
          test_a_step_whose_check_raises_answers_unverifiable_and_names_the_crash
          test_runner_targets_resolve_refuses_a_repo_with_no_framework
```

**The five deletions I traced end to end all check out**, which is what makes this a process
finding rather than a damage finding. Each named subsumer exists and the deleted case is gone:

| deleted | subsumer named | present at HEAD |
|---|---|---|
| `test_the_installed_hooks_run_and_block_what_they_exist_to_block` | `test_pathspec_a_pathless_commit_still_blocks` | yes, at `33a6f40`; itself later folded into `test_pathspec_allows_every_path_naming_spelling_and_blocks_the_pathless` by `9d60fe8` |
| `test_a_destination_that_is_a_directory_is_a_refusal_not_a_traceback` | `test_a_defect_refuses_the_whole_command_and_writes_no_addition` | `tests/test_install.py` |
| `test_help_lists_the_standard_set_on_a_project_that_added_nothing` | `test_help_lists_the_standard_set_and_the_projects_own` | `tests/test_makefile_include.py` |
| `test_the_workflow_runs_the_projects_full_gate_and_says_so` | `test_every_make_target_a_workflow_runs_is_one_the_include_defines` | `tests/test_ci_workflows.py` |
| `test_pathspec_from_file_names_paths_and_is_allowed` | `test_pathspec_allows_every_path_naming_spelling_and_blocks_the_pathless` | `tests/test_hooks_payloads.py` |

I also chased the one chain that looked broken: `182fa72` folded the conveyor version-refusal
matrix into `test_every_row_is_exit_2_runs_no_step_and_writes_nothing`, and that case is **GONE**
at HEAD — deleted by `549475f`, which also deleted `tests/test_conveyor_state.py` whole. It is
not a loss: `549475f` deleted the module the state tests covered (`state.py` and every `do()`),
and the version grammar is re-proven at HEAD by
`test_conveyor_driver.py::test_the_version_refusal_matrix_is_exit_2`, 12 parametrized hostile
values. But nothing in the commit says so, and I had to run three greps across three revisions
to establish it — which is the cost the criterion was written to prevent.

**And the compensating record is thin.** `549475f` claims *"each kept case's docstring says what
it bites"*; measured over all 854 test functions at HEAD, **420 (49%) carry a docstring at all
and 50 (5%) say what they bite**, concentrated in the conveyor modules that rewrite touched. So
for 776 removals there is neither a per-case reason in the commit nor a per-case claim on the
survivor.

Recommended ruling: **accept `3afa141` and `549475f` as-is** — the 32 probes in `3afa141` and the
12 in this review are the evidence that the cuts were safe, which is what criterion 4 was for —
**and hold every future cut to the per-removal form `33a6f40` already demonstrates.** The
alternative, a retro-record reconstructed from a squashed history, would be prose nobody can
check.

---

## The criteria that ARE met, and what proves them

### Criterion 4 — a deliberately-broken probe still reddens. **MET**, 10 of 12, and the 2 misses are pre-existing

Twelve defects, each the one its target's tests exist to catch, injected one at a time into a
`git archive` copy of HEAD under the scratchpad — the reviewed tree was never touched, and every
patch was restored and byte-compared before the next. Three `check` gates and three `pm` write
verbs, two probes each, run against the module set that owns each surface.

| probe | broken | result | run |
|---|---|---|---|
| doc-1 | a dead link stops being reported (`if not resolve_path(…)` → `if False`) | **RED** | `5 failed, 69 passed, 137 subtests` |
| doc-2 | `scope_files()` returns `[]` — a zero-file census printing PASS | **RED** | `1 failed, 35 passed, 82 subtests` |
| pm-1 | findings no longer FAIL the gate | **RED** | `1 failed, 7 passed, 2 subtests` |
| pm-2 | the drift walk visits no milestone | **RED** | `1 failed, 3 passed` |
| hooks-1 | an installed hook that stops NOTHING passes | **RED** | `1 failed, 4 passed` |
| hooks-2 | a hook that does not even parse passes | **RED** | `1 failed, 5 passed` |
| story-1 | `pm story <state>` writes an undeclared state instead of refusing | **RED** | `2 failed, 33 passed, 8 subtests` |
| story-2 | the status write eats the file's CRLF terminators | **RED** | `1 failed, 49 passed, 44 subtests` |
| new-1 | `pm new story` stamps the ordering prefix into `id:` | **RED** | `1 failed, 13 passed` |
| new-2 | `pm new story` overwrites an existing story instead of refusing | **GREEN — MISSED** | `27 passed, 25 subtests` |
| set-1 | `pm set` writes nothing and prints success | **RED** | `1 failed, 15 passed, 43 subtests` |
| set-2 | `pm set` writes a multi-line value into the frontmatter | **GREEN — MISSED** | `68 passed, 1 skipped, 80 subtests` |

Both cardinal sins are covered from both sides: doc-2 / pm-2 are the read-side census-of-zero,
set-1 / story-2 / new-1 are the write-side diff that looks legitimate and is not.

**The two misses are not damage this feature did**, and that is measured rather than argued — see
P4. Widened to the whole 1,095-case reduced suite both stayed green, and re-run against the
**1,855-case pre-reduction suite at `0243691`** both stayed green there too. Nothing was deleted
that used to catch them; nothing ever caught them.

Scope stated: I probed 3 of the 8 `check` gates and 3 `pm` write verbs, per brief.
`grain-shape`, `shell`, `repo-hygiene` and `budget`'s time half were not probed, nor were
`pm retire`, `move`, `decide`, `close`, `ready`, `sync` or `bug` — `97dbd6c` probed the first
three with 20 defects and its own record stands.

### Criterion 5 — the templates ask, and `check budget` fails an over-ceiling tier. **MET**

`templates/story.md:19` carries `## How this is proven`, one row per criterion with the tier,
the case, and the `existing?` column; `templates/feature.md:20` carries `## Proof budget`. Both
read as intended.

The gate half, measured in the scratch copy with `cases.unit` lowered from 1250 to 700 against a
732-case ledger row:

```
  OVER COUNT  unit — 732 case(s) against a 700 ceiling (+32). A tier can hold its wall clock while doubling in size.
[check:budget] FAIL — 1 tier(s) over budget: unit (cases); …
EXIT=1
```

and a ceiling of the wrong shape refuses rather than narrowing:

```
$ # cases = "lots"
agentic-sdlc: [tests] cases must be a table, got 'lots'
EXIT=2
```

Rule 4's census, pointed at the suite's own size, and it bites. See P5 and P6 for what is
non-blocking about the way it is currently configured and adopted.

### Criterion 6 — `SDLC.md` §6 asks it. **MET for this repo, partially for a consumer**

`SDLC.md:226`, *"A new test says why the old ones were not enough"*, carries the search rule
verbatim and the measured 7,241 / 13,023 / one-per-4.9. The two shared blocks
(`cheapest-proof-review`, `new-test-justification`) are in
`installables/reviewer.md`, `installables/simplifier.md` and
`installables/verification-reviewer.md`, and the installed copies under `.claude/agents/` are
**byte-identical** to their sources (`cmp` on all three: `verification-builder.md` same,
`verification-reviewer.md` same; `code-reviewer.md` has no source and is staged for deletion by
the other session). So a consumer running `install-agents` inherits the question. See P7 for the
half that does not reach them.

---

## Non-blocking findings

### P4 — MINOR — two `pm` write-verb refusals are unproven, and were unproven before the cut too

`pm new story` refusing to overwrite an existing story
(`cli.py`, `if _exists(sf): raise Refused(f'story {fid}/{slug!r} already exists')`) and `pm set`
refusing a multi-line frontmatter scalar
(`if '\n' in value or '\r' in value: raise Refused('a frontmatter scalar is one line')`) are
both write-side rule-3 guards with no case behind them. Removing either leaves the whole suite
green:

```
HEAD reduced suite, whole:   8 failed, 1087 passed, 2 skipped, 557 subtests   (8 pre-existing)
  new-2 removed             8 failed … new failures: none
  set-2 removed             8 failed … new failures: none
pre-reduction 0243691:      10 failed, 1843 passed, 2 skipped, 691 subtests
  set-2 removed             10 failed … new failures: none
  new-2 removed             11 failed … new: test_wheel_payload::test_no_file_ships_without_a_reader_or_a_reason
```

That single new failure is a flake, and I proved it rather than assuming: the module passes
alone (`4 passed in 0.02s`) and two further clean baseline runs produced 11 and 10 failures with
`test_wheel_payload` and `test_conveyor_close` appearing once each. So the pre-reduction suite
misses both probes as well. `grep "already exists"` over `tests/` returns nothing at either
revision.

These are gaps the reduction did not create and did not close. Worth two `parametrize` rows in
`test_pm_scaffold.py` and `test_pm_verbs.py` — both are pure refusals, function-call tier.

### P5 — MINOR — the case ceilings are still the pre-reduction ones, 1250/800 against 705/390

`devkit.toml` sets `cases = { unit = 1250, integration = 800 }`, written at 1,123/730 and
explicitly holding the line *"until it lands"*. It landed. The tiers now measure 705 and 390,
so the ceiling that exists to make growth a decision is **77% and 105% above** what it grades:
the suite can nearly double back to where this feature found it before the gate says a word.

The other session updated the section's prose during this review and now discloses the choice —
*"Today's counts sit well under them; lowering the ceilings toward today's is a decision to take
on purpose, not a drift to correct in passing."* That is the right posture and it is why this is
MINOR rather than a blocker: it is a declared open decision, not a silent one. It is still a
decision nobody has taken.

### P6 — MINOR — phase C's templates are not self-hosted, and nothing gates them

Phase C is *"the actual deliverable"* and the feature's own risk 4 says it is the part most
likely to be dropped once the numbers look good. Measured over this tree:

```
features carrying '## Proof budget':        1 of 16
stories carrying '## How this is proven':   8 of 39
the feature under review carries either:    0
grain_shape.py / checks/pm.py ask for them: neither, no reference at all
```

Grandfathering explains the old grains. It does not explain the feature that introduced the
sections carrying neither, and there is no gate — `check grain-shape` never names either
heading — so the sections are template prose a builder can delete without anything noticing.
That is precisely the shape the feature diagnoses in its own opening table: *"`templates/feature.md`
— nothing. Not one word about tests."* The word is now there and nothing asks whether it was
answered.

### P7 — MINOR — the consumer-facing SDLC render never asks the question

`install-sdlc` renders `docs/sdlc-protocol.md` from `installables/sdlc-template.md`. That
template is two headings long (`# The protocol, as the machine runs it`, `## Changing this
document`) and contains no occurrence of `cheapest`, `bites`, `How this is proven`, `Proof
budget` or `already covers`. Criterion 6 reads *"`SDLC.md`'s review step asks it, and
`install-sdlc` re-renders"* — the first half is true of THIS repo's root `SDLC.md`, which is not
an installable and never reaches a consumer. What reaches a consumer is the agent roster, and
that does carry it (see criterion 6 above). So the criterion is satisfied in effect by a
different mechanism than the one it names; worth correcting in the wording rather than in code.

### P8 — NIT — the pre-reduction suite was flaky under `-n auto`; the current one was not

Three clean full runs of the 1,855-case baseline produced 10, 11 and 10 failures — 10 stable
self-hosting cases that cannot pass in an archive copy, plus `test_wheel_payload` and
`test_conveyor_close` appearing once each. Three full runs of the reduced suite produced 8
failures every time with an identical id set. Not a finding against this change; recorded
because it is the shared-mutable-state shape the reviewer contract names, and because it is the
reason P4's baseline probe needed three runs to read correctly.

### P9 — QUESTION — the feature is being reviewed at `status: planning` with zero stories

`pm status 0.2.0` reports `feature the-proof-is-named-in-the-criterion [planning] stories 0/0
done`, and the directory's `stories/` is empty. `SDLC.md` §0's entry condition — *"a feature
flips to `reviewing` when every story under it is `done`"* — is vacuously true of a feature with
no stories, so `pm ready-for feature` cannot have been the thing that authorised this review.
Eight of the milestone's sixteen features are in the same shape. Not raised as a defect in this
feature; raised because a feature whose whole subject is *"a criterion names the one case that
proves it"* shipped 828 deletions with no story-level `## How this is proven` table anywhere in
its own grain, which is the same gap as P6 seen from the tree side.

---

## Measured numbers, my runs

| what | value | where |
|---|---|---|
| `make unit` | 7.68 / 7.98 / 8.01 / 8.29 / 9.20 s · 706+2 cases, 505 subtests | 5 runs, load 5.6–9.7 |
| `make integration` | 37.26 / 41.51 / 46.17 s · 389–390 cases, 52 subtests | 3 runs, load 5.6–8.9 |
| `make test` | 42.52 s · 1095 passed, 2 skipped, 557 subtests | load 5.6 |
| `make check` | ~2 s · 5 checks PASS, exit 0 | load 12.9 |
| collected | **1097** at `2cccde2`, **1095** at `f712048` · 708/389 then 705/390, 0 in both, 0 in neither | `--collect-only` |
| tests:src statements | **11,043 : 7,495 = 1.473** (baseline 13,909 : 7,798 = 1.784) | `ast` over both trees |
| test functions | **853** (baseline 1,478) | `ast` |
| effective cases | **1,652** (baseline 2,546) — collected plus subtests, both ends measured | tier runs |
| probes | **10 of 12 RED**; 2 misses green on the pre-reduction suite too | scratch copy of HEAD |
| `check budget` case ceiling | FAIL + exit 1 at a lowered ceiling; exit 2 on a malformed one | scratch copy |
| deletions naming a subsumer | **52 of 828** by name, +26 by family in `182fa72` | commit bodies |
| survivors declaring what they bite | **50 of 854** (5%); 420 (49%) carry any docstring | `ast` |

## What was NOT verified

- **`make milestone`, `make matrix`, `make precommit` and `make fuzz` were never run**, per
  brief. Every number here is 3.11 on macOS; nothing ran on 3.12, 3.13 or 3.14.
- **Five of the eight `check` gates were not probed** — `grain-shape`, `shell`, `repo-hygiene`,
  and both `budget`'s duration half and its NOT-GRADED path. Criterion 4 asks for all eight; I
  covered the three named in my brief and say so rather than implying coverage.
- **Nine `pm` write verbs were not probed** — `retire`, `move`, `decide`, `close`, `ready`,
  `sync`, `bug`, `feature`, `milestone`. `97dbd6c` probed the first three with 20 injected
  defects and I did not re-run its twenty; I take that commit's record at its word.
- **The 8 pre-existing failures in the scratch copy were not individually diagnosed.** They are
  stable across every run and concentrated in `test_makefile_gates.py` and `test_verify_main.py`
  — self-hosting cases that read a real git history an archive copy does not have. I confirmed
  the set is identical clean and under every probe, and used only the DELTA; I did not establish
  that all eight are artifacts.
- **The remaining 823 deletions were not traced.** Five were followed end to end and one chain
  (the conveyor refusal matrices) was followed through two commits; the other 823 rest on
  `3afa141`'s 32-probe claim and my 12, not on inspection.
- **`3afa141`'s 32 probes were not re-run.** I built 12 of my own instead, deliberately aimed at
  surfaces its four agents did not report probing (`check doc`, `check hooks`, `pm new`,
  `pm set`).
- **No consumer install was performed.** `install-agents` and `install-sdlc` were not run into a
  temp repo; criterion 6 rests on the installable sources plus the byte-comparison of the three
  copies installed here.
- **`git log -S` was not used as evidence**, because `3afa141` established it does not work in
  this repo — the history is squashed and `a76b7c0 Seed the agentic half` is the sole hit for
  nearly every assertion string. That correction is already in the feature record and I
  confirmed nothing in my sampling depended on it.
- **The branch moved three times during the review** — `2cccde2` → `218888c` → `f712048` — with
  another session holding uncommitted edits to `tests/test_verdict.py`,
  `tests/test_verify_main.py`, `devkit.toml`, `src/…/conveyor/steps.py` and
  `src/…/verify/main.py` throughout. The tier numbers are at `2cccde2` and `f712048` as tagged;
  nothing between them touched the six commits under review, and the census delta across the
  whole window is 2 cases.
- **The ledger rows my runs filed were not separated from the sibling sessions'.** `check budget`
  in the scratch copy graded rows from the committed ledger, not from my runs; the tier numbers
  above are read off the pytest summary lines directly.

Reviewer's token cost: ~180k.

```text
verdict: HOLD
| id | severity | disposition |
| P1 | MAJOR | rejected: close enough and directionally right — the number was a direction, not the goal (Chris, 2026-09-06)|
| P2 | MAJOR | rejected: close enough and directionally right — the number was a direction, not the goal (Chris, 2026-09-06)|
| P3 | MAJOR | rejected: close enough and directionally right — the number was a direction, not the goal (Chris, 2026-09-06)|
| P4 | MINOR | rejected: pre-existing against the 1,855-case baseline; the write verbs that changed (retire, move, decide) were probed in 97dbd6c |
| P5 | MINOR | landed f712048|
| P6 | MINOR | rejected: the templates are prose; length is what the caps enforce, and the caps landed in 859d25b|
| P7 | MINOR | rejected: the reviewer roster is the consumer mechanism; the question lives in verification-reviewer.md|
| P8 | NIT | rejected: suite flakiness under load is the machine, not this feature; the timing case was made single-process in 6b67cd6 |
| P9 | QUESTION | rejected: a story-less feature carries its criteria as its proof table (Chris, 2026-09-06: close enough and directionally right) |
```
