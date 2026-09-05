# Feature review — `0.2.0/the-release-is-a-conveyor` — HOLD

Feature-level pass (SDLC.md §0) over the whole commit range of
`0.2.0/the-release-is-a-conveyor`: **`6e9388d`, `8c1ba41`, `cc0569d`** — the commits its five
stories name in their `## Close` blocks. Branch `milestone/0.2.0-the-conveyor`, run 2026-09-05,
adversarial by execution: every claim below was produced by running the shipped code, in
`tempfile` scratch repos and against this tree, through
`PYTHONPATH=src python3 -m agentic_sdlc.cli`. No repo-wide git command was run.

The milestone review (`docs/reviews/2026-09-05-0.2.0-release-review.md`) is already landed and
none of its ten findings is re-filed here.

**The machine itself is sound and I could not make it lie about a step.** The run state is
genuinely a cache — a state file hand-edited to claim all five story steps `true` produced
`CORRECTED — the run state said 'narrow-verified' was done; the tree says: …` and the run
stopped; a state file pointed at another operation was discarded and the discard printed. `--skip`
of a step not in the list is exit 2 with no ledger row; a skipped step is written to the run state
**not at all**, never as satisfied; a skip writes one `deviation` row and a re-run with the same
flags writes no second one. Every `check()` in the 21-step list is a question about the tree, and
none reads a flag its own `do()` set.

What is wrong is at the level only this review can see: **three of the twenty-one steps contradict
each other across the stories that added them**, and the machine's own working file falsifies its
own first precondition in any consumer.

## Blockers

### R1 — steps 5 and 14 are mutually unsatisfiable, so a release cannot be resumed past step 14

`findings-resolved` (`src/agentic_sdlc/repo/conveyor/steps.py:1166-1192`) requires every review
record for the milestone to be **deleted**. `review-landed` (`:946-947`) and `features-done`
(`:1090-1091`) call `pm ready-for tag|milestone`, which read each feature's `reviewed:` pointer and
BLOCK when it names no file. The driver re-asks every step on every run
(`driver.py:349-366` — *"Every step is asked, every time"*), so the two cannot both hold.

Scratch repo, one feature `done` with `reviewed: docs/reviews/2026-01-01-f1.md`, record clean:

| state | `review-landed` | `features-done` | `findings-resolved` | `check pm` |
|---|---|---|---|---|
| record present | TRUE | TRUE | TRUE *(see R2)* | PASS |
| record deleted, as step 14 demands | **FALSE** — `reviewed: names no file` | **FALSE** | TRUE | **FAIL — exit 1**, `DRIFT feature 1.0.0/f1: reviewed: … resolves to nothing` |

Walked with the real 21-step list and a run state cached as though step 14 had just been
performed:

```
[release] CORRECTED — the run state said 'review-landed' was done; the tree says: BLOCKED …
[release] STOPPED — 'review-landed' (JUDGEMENT) at step 5/21; what would make it true: …
```

The seven steps after `findings-resolved` — `milestone-done`, `push-branch`, `pr-open`,
`ci-green`, `merge`, `tag`, `prove-artifact` — are the ones a release most needs to resume into,
because `pr-open` → `ci-green` → `merge` spans a PR review and a CI wait. They are unreachable on
any resumed run. The only escape is `--skip review-landed --reason …` and
`--skip features-done --reason …` on every subsequent run, which is risk 3 of this feature's own
document arriving by construction: *"a conveyor that is always skipped is worse than none, because
it looks like control."*

Performing step 14 additionally leaves `check pm` permanently RED (D1), and `check pm` is a gate
in `[checks] all`.

Step 14 was added by story 03 (*"The list is 21, not the planned 20: SDLC.md's resolve-the-findings
step had none"*), reconciled from prose written before `pm ready-for` existed. The prose and the
verb were never reconciled with each other.

### R2 — `findings-resolved` decides by version SUBSTRING, and reports the postcondition true over a record still on disk

`steps.py:1187` — `if ctx.version in path.name or ctx.version in text:`. The census is over
records whose **filename or body happens to spell the version string**, not over the `reviewed:`
pointers that actually name this milestone's records.

Measured, same scratch repo, `docs/reviews/2026-01-01-f1.md` present and pointed at by the
feature's `reviewed:` field:

```
findings-resolved: TRUE - no record under docs/reviews/ names 1.0.0
```

The step's own docstring says *"every `docs/reviews/` record for this milestone RESOLVED AND
DELETED"*. The record was neither.

This repo passes only because its records are conventionally named `2026-09-05-0.2.0-*.md`. For any
project using `[pm] review_slug_fallback` — a shipped, documented option whose whole purpose is
records named after the feature slug — the step is **structurally always TRUE**. Rule 4, read
side: a gate that misses real drift and prints PASS.

### R3 — the conveyor's own run state is not ignored in any consumer, so `release` falsifies `tree-clean` from its second run onward

`state.py:11-13` names gitignoring as the mitigation that keeps `tree-clean` answerable: *"A
TRACKED state file would be dirtied by the very run that checks the tree is clean — the machine
making its own precondition false. Gitignoring is what keeps `tree-clean` answerable."*

`agentic-sdlc init` **does** write a `.gitignore` block for exactly this purpose —
`src/agentic_sdlc/repo/init.py:89` `GITIGNORE_HEADER = '# agentic-sdlc run artifacts (agentic-sdlc
init)'` — and `IGNORED` at `:98-100` holds one entry, `.gate-reports/`. `.agentic-sdlc/` is not in
it. Nothing else this package installs writes the line either (zero hits for `agentic-sdlc/` under
`installables/`). This repo has it at `.gitignore:17`, hand-written.

Fresh consumer, `init`-shaped tree, nothing but the belt's own writes present:

```
[release:tree-clean] JUDGEMENT STOPPED — 4 modified path(s): …, .agentic-sdlc/, pm/roadmap/1.0.0-m/ledger.jsonl
[release] STOPPED — 'tree-clean' (JUDGEMENT) at step 1/21
```

Run 1 can pass `tree-clean` because the file does not exist yet; `run_state.save` then writes it,
and run 2 stops at step 1 naming it. **Resumability — the property this feature exists to deliver
— does not survive its own artifact in a stock consumer**, and the operator is told to "commit or
stash your own paths" about a file the machine wrote. One line in `init.IGNORED` closes it.

## Non-blocking findings

### R4 (MAJOR) — `_status_at_or_past` tracebacks where its later twin answers UNVERIFIABLE

`steps.py:824` — `if states.index(status) >= states.index(wanted):` with no guard that `wanted` is
in the project's `[pm] milestone_states`. `_grain_status_at_or_past`, added one grain down by
`the-inner-levels-are-belts-too` (`steps.py:1735-1739`), **has** that guard and answers
`UNVERIFIABLE` naming the config key. The later story added the guard to the copy and did not
backport it to the twin it was copied from:

```
grain has the guard : True
milestone has it    : False
```

`[pm] milestone_states = ["planning","building","reviewing","done"]` — a legal per-project value
under rule 5 — and `milestone-packaging`'s check raises:

```
File ".../steps.py", line 824, in _status_at_or_past
    if states.index(status) >= states.index(wanted):
ValueError: tuple.index(x): x not in tuple
```

It surfaces at step 11 or 13, **after** `version-sync`, `readme-pins` and `changelog-retitle` have
rewritten files and after `gate` has run, and `run_state.save` never executes so the position is
lost. That is exactly the failure `validate_config` (`:596-615`) promises to prevent — *"a config
error that surfaces halfway through a release — after `version-sync` has written two files"* — for
every `[<operation>]` key, but not for the `[pm]` keys these four steps read. Rule 6: it is a
config error and must be exit 2.

### R5 (MINOR) — the "a skip cannot un-do a postcondition that holds" guard is enforced by a cache the docs say costs nothing to delete

`driver.py:784-790` asks `run.answer_for(name) == TRUE`, i.e. the gitignored run state, and
`state.py:18-22` says losing that file costs nothing. Measured:

```
$ close story … --skip claimed --reason "…"        # cache present
agentic-sdlc: close story: --skip names claimed (completed …); a skip cannot un-do a postcondition that holds   → exit 2
$ rm -rf .agentic-sdlc
$ close story … --skip claimed --reason "…"        # same command, cache gone
[story:claimed] AUTOMATIC SKIPPED — probe: cache deleted                                                        → walks on
```

Skipping a true step breaks nothing, but it writes a `deviation` row for a step that was satisfied,
and the deviation record is the one thing risk 3 depends on being honest. Asking `check()` instead
of the cache costs one call.

### R6 (MINOR) — the reasoning that keeps the driver's rows out of the tracked ledger does not cover the rows `gate` causes

Story 04's `## Close`: *"Skips ONLY: the ledger is tracked, so a row per completed step would
dirty the tree and falsify `tree-clean` — the machine making its own precondition false."* Correct,
and the driver honours it. But step 10 `gate` runs `make milestone`, and the installed
`gdk_gate.sh` recorder writes `{"kind":"gate",…}` rows into that same tracked
`pm/roadmap/<milestone>/ledger.jsonl` — 30-odd such rows are in this repo's ledger, interleaved
with the status rows. So the step list dirties the tree mid-run anyway, and a run resumed after
`gate` stops at `tree-clean`. Unlike R1 this is satisfiable (commit the ledger rows and re-run),
which is why it is not a blocker — but it is the same shape, and the story's stated reason for the
design does not actually hold in the shipped list.

### R7 (NIT) — `main-merged` reads a remote-tracking ref it never refreshes

`steps.py:875-887` prefers `origin/<mainline>` and never fetches, while its own `do()` says
`git fetch origin && git merge origin/<mainline>`. On a checkout whose `origin/main` is stale the
step answers TRUE for *"the mainline is an ancestor of HEAD"* when the real mainline has moved on.
Fetching would be right here and costs no rule: `tag` already calls `git ls-remote`.

## The feature's own scope and rulings, judged

`feature.md` states no numbered ship criteria; it states a scope table, two settled rulings and
three risks. Judged against those:

| thing | verdict |
|---|---|
| a `release` verb + step registry | **met** — 21 steps, `registry == default list` for all four operations, `STEP_DOC` covers every registered step, `review-landed` at index 4 precedes `gate` at index 9 |
| `devkit.toml [release]` with a shipped default | **met** — a repo with no `devkit.toml` walks the same 21 names; a misspelled step is `ConfigError` → exit 2 before any step runs; `[release.commands]` naming an AUTOMATIC step, an unlisted step or an empty string are each exit 2 |
| run state, resumable and inspectable | **caveat — R1, R3.** The mechanism is right and proven hostile-safe; what it cannot survive is step 14 and its own untracked file |
| `install-sdlc` renders the doc from the step list | **met** — `install-sdlc --diff` → `already current` at HEAD; `tests/test_install_sdlc.py::test_this_repos_own_protocol_document_is_byte_current` holds this repo's copy to `sdlc_doc.render()`; four tables with exactly 21 / 8 / 5 / 6 rows, matching the four registries; a step name carrying `\|`, `#`, backticks or `-` is refused at exit 2 and the document is never written (`test_a_step_name_cannot_smuggle_markdown_through_the_config`) |
| `.claude/skills/release/SKILL.md` shrinks | **met** — a test asserts it names no step outside `NO_DEFAULT_COMMAND` |
| `SDLC.md` § Close protocol GENERATED | **met** — `SDLC.md:211` is now *"Close protocol — GENERATED, not written here"* and enumerates no steps, only the four judgements |
| Ruling: steps are skippable and a skip is RECORDED | **met** — verified end to end; see R5 for the one soft edge |
| Ruling: the docs are generated and shipped like the other install verbs | **met** |
| Risk 1 — over-encoding | **met** — six items sit in `GUIDANCE` with no postcondition rather than as steps |
| Risk 2 — a second home for the protocol | **met** — one renderer, no per-step prose in `sdlc_doc.py`, gated by a test |
| Risk 3 — a conveyor that is always skipped | **caveat** — zero `deviation` rows exist in this milestone's ledger today, so the risk has not materialised; R1 makes two skips *mandatory* on every resumed release, which is the risk arriving by construction rather than by habit |

**Hard rule 1 — no network in `pr-open` / `ci-green` / `merge` / `prove-artifact`.** Clean, by
reading and by grep. Three of the four are `_judged_by_command` (`:744-756`): a configured command
or `UNVERIFIABLE`, and `NO_DEFAULT_COMMAND = ('pr-open','ci-green','prove-artifact')` ships none.
`check_merge` (`:1254-1266`) is `git rev-parse --verify` plus `git merge-base --is-ancestor` against
the LOCAL `origin/<mainline>` ref — no fetch, no URL, no `gh`. The only remote reaches in the file
are `git ls-remote` and `git push` inside `tag`/`push-branch`, which are outside the four named and
are what those steps are for.

**Hard rule 8.** All four `subprocess.run` call sites in `conveyor/` (`:368`, `:388`, `:422`,
`:722`) pass `cwd=str(ctx.root)`. No second repo is read.

## `## Close` claims, checked

| story | claim | verdict |
|---|---|---|
| 01 | run state as a CACHE, never the authority; a lying `do()` cannot advance the machine | **true** — reproduced by hand-editing the state file to claim every step done |
| 02 | `[release] steps` / `[release.commands]` as config, 23 refusal rows | **true in substance** — the refusal matrix over a hostile tree is a 24-row block at `tests/test_conveyor_steps.py:310-443`; the count is off by one or counts a different table, which is not worth a finding |
| 03 | `review-landed` precedes `gate` in the shipped list; the list is 21, not 20 | **true** — indices 4 and 9, length 21 |
| 04 | `--skip` writes a `deviation` row; skips ONLY, because the ledger is tracked | **true** for the driver — see R6 for what the reason does not cover |
| 05 | `install-sdlc` renders from the step lists; `SDLC.md`'s Close protocol is gone; all four lists render since `cc0569d` | **true** — the heading survives as a pointer that enumerates nothing, which is what the claim means |

Nothing in the five `## Close` blocks is untrue.

## Cross-story questions

- **Did two stories solve the same thing twice?** Yes, once, and it cost a guard: `_flip` /
  `_status_at_or_past` (this feature, `6e9388d`) and `_grain_flip` /
  `_grain_status_at_or_past` (`the-inner-levels-are-belts-too`, `cc0569d`) are the same closure at
  two grains. See R4.
- **Did a later story weaken an earlier one's guard?** No. `cc0569d` only added — `_load_run`'s
  stale-file path is scoped to `CLOSE_OPERATIONS` and leaves `release`/`adopt` on the strict
  refusal, which is the right split.
- **Is any step's `check()` satisfied by its own `do()`?** No. Audited all 21. The status flips
  read the milestone file the pm CLI wrote (a tree fact); `installables-diffed` re-derives its
  census from the tree with per-file digests; `gate` and the three command judgements run a
  command; `push-branch` reads `rev-parse @{u}`.

## What was NOT verified

- **No release was walked to completion.** The conveyor stops at `tree-clean` on this tree and at
  step 4/5 in scratch repos, so `push-branch`, `pr-open`, `ci-green`, `merge`, `tag` and
  `prove-artifact` were read and reasoned about but never reached. R1's proof drives `driver.walk`
  directly with a pre-seeded run state rather than by performing steps 1-14.
- **`make milestone` and the interpreter matrix were not run.** The conveyor + install slice was:
  `tests/test_conveyor_{steps,driver,state,skip,adopt,close}.py tests/test_install_sdlc.py` →
  **275 passed in 17.83 s** on 3.11.
- **R6 was inferred for consumers from this repo's ledger contents**, not reproduced in a fresh
  consumer with an armed gate recorder.
- **`do_version_sync` / `do_readme_pins` / `do_changelog_retitle` were not run.** They write, and
  writing to this tree is outside a reviewer's remit; their `check()`s were exercised, their
  `do()`s only read.
- **One unreproducible crash.** A single invocation raised
  `ConfigError: [pm] dropped_states is empty` out of `model.load()` from `check_on_milestone_branch`
  in a scratch repo that had not declared the key; the identical command in the identical directory
  then loaded cleanly four times running. `model.load:280` does read `tup('dropped_states', ())`
  with an empty fallback and `tup` raises on an empty result, which is a real-looking shape — but I
  could not reproduce it and will not file what I cannot show.
- **The `--status` output was not exercised against a run with recorded deviations** on this tree
  (the milestone's ledger holds none).

Reviewer's token cost: ~148k.

```
verdict: HOLD
| id | severity | disposition |
| R1 | BLOCKER | landed 08f15d2 + this commit: the deadlock dissolved with the halt (D8); the false postcondition is fixed with R2 — one finding read from two ends |
| R2 | BLOCKER | landed: findings-resolved asks `pm ready-for tag` — the reviewed: pointers' dispositions, never a version substring, never a record's absence |
| R3 | BLOCKER | landed 274e18c (plus .agent-scope and .claude/worktrees/, found by the sweep) |
| R4 | MAJOR | open: `_status_at_or_past` IS `at_or_past`; owned by phase 7, which deletes the line |
| R5 | MINOR | rejected: superseded by D8 — the guard lived entirely inside `if skips:` and went with `--skip` in 50cc01d |
| R6 | MINOR | landed 274e18c: the write stays (those rows are what `pm ledger report` reads); the false attribution is what was fixed |
| R7 | NIT | landed 274e18c: refreshes first, and refuses rather than answering off a ref it could not refresh |
```
