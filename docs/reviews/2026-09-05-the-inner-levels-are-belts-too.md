# Feature review — `0.2.0/the-inner-levels-are-belts-too` — HOLD

Feature-level pass (SDLC.md §0) over the whole commit range of
`0.2.0/the-inner-levels-are-belts-too`: **`cc0569d`** — the commit all three of its stories name in
their `## Close` blocks. Branch `milestone/0.2.0-the-conveyor`, run 2026-09-05, adversarial by
execution, in `tempfile` scratch repos and against this tree through
`PYTHONPATH=src python3 -m agentic_sdlc.cli`. No repo-wide git command was run.

The milestone review (`docs/reviews/2026-09-05-0.2.0-release-review.md`) is landed and none of its
ten findings is re-filed here.

**The two belts arrived on the existing driver and changed nothing about the machine, exactly as
claimed** — same three kinds, same `do()`-never-decides rule, same run-state cache, same
`--skip … --reason` row. `close feature` blocks at `stories-done` naming each story; `close story`
answers in **0.20-0.24 s** re-measured, which is the number the feature was built for. Both were
attacked with a corrupted run state, a state file belonging to another operation, and a skip of a
step that was already true.

Two blockers. The first is a step that reports DONE over a check it never ran. The second is that
the feature's own three stories never went through the belts they built, which is criterion 6 and
the tree says so.

## Blockers

### I1 — `narrow-verified` is vacuous once the work is committed, and the belt's own step 4 requires it to be

`check_narrow_verified` (`src/agentic_sdlc/repo/conveyor/steps.py:1765-1782`) delegates to
`agentic-sdlc verify --story`. `verify.main._run_story` (`verify/main.py:437-442`) returns
`EXIT_OK` when the selection is empty:

```python
if not selection.matched and not selection.missed:
    print('verify --story: no changed paths against HEAD — nothing to verify')
    return EXIT_OK
```

So on a committed tree the step passes over a census of **zero**, and the driver prints
`GATE ALREADY-TRUE` and counts it in `PASS — 5/5 steps`.

Proven end to end. Scratch consumer, `[[verify.narrow]] paths = "src/**"` → `run = "make narrow"`,
with `make narrow` genuinely exiting 1:

```
# work uncommitted — the gate has teeth
[story:narrow-verified] GATE STOPPED — `agentic-sdlc verify --story` exited 1: … make narrow … Error 1
[story] STOPPED — 'narrow-verified' (GATE) at step 2/5
                                                                                  EXIT=1, status: building

# same tree, same red rung, work committed first
[story:narrow-verified] GATE ALREADY-TRUE — `agentic-sdlc verify --story` exited 0 … no changed paths against HEAD
[story:committed]       JUDGEMENT ALREADY-TRUE — no modified path outside pm/roadmap/
[story:evidence-written] JUDGEMENT ALREADY-TRUE — carries `done: abc1234 — the thing shipped.`
[story:story-done]      AUTOMATIC DONE — … is 'done'
[story] PASS — 5/5 steps
                                                                                  EXIT=0, status: done
$ make narrow
NARROW RUNNING
make: *** [narrow] Error 1
```

**The story closed `done` with its narrow check red, and the check never ran.** Ship criterion 2 —
*"`close story` refuses while the story's own narrow check is red"* — is not met.

This is not an exotic ordering. It is the ordering the belt itself requires: `evidence-written`
(step 4) demands `done: <hash>` naming a real commit, and `.claude/rules/pm-execution.md` step 2 is
*"Commit atomically."* So by the time a story can satisfy step 4, its work is committed and step 2
has nothing to scan. The single-run path — commit, write the evidence line, `close story` — is the
canonical one, and on it `narrow-verified` is structurally vacuous.

The same module answers this exact question the other way eleven hundred lines earlier:
`check_readme_pins` (`:1058-1063`) returns `Answer.unverifiable` on a census of zero with the
comment *"Rule 4: a census of zero is REPORTED, loudly, rather than passed over."* Two answers to
"what does a scan of nothing mean" in one file, and the permissive one is on the belt that runs
dozens of times a day.

Either answer closes it: make an empty `verify --story` selection `UNVERIFIABLE` here (a refusal,
which is this package's own ruling everywhere else), or select against the story's commit range
rather than against `HEAD` so the check has something to scan after the commit.

### I2 — the feature's own three stories never entered the belt, and criterion 6 is false in the tree

Ship criterion 6: *"0.2.0's own 28 stories and 9 features close through these verbs. Same bar as
ship criterion 9: a belt whose first run is performed by hand has not been tested."*

The tree, at HEAD:

```
$ pm ready-for feature 0.2.0/the-inner-levels-are-belts-too
  BLOCKED  0.2.0/the-inner-levels-are-belts-too/01-closing-a-story-is-a-belt is planning
  BLOCKED  0.2.0/the-inner-levels-are-belts-too/02-closing-a-feature-is-a-belt is planning
  BLOCKED  0.2.0/the-inner-levels-are-belts-too/03-the-belt-above-refuses-to-start is planning
[pm] NOT READY — feature 0.2.0/the-inner-levels-are-belts-too: 3 blocker(s), across 3 story/ies
```

All three carry a `## Close` block naming `done: cc0569d`, and all three sit at `status: planning`.
`pm/roadmap/0.2.0-the-conveyor/ledger.jsonl` holds **no status row of any kind** for any of them —
they were never moved off `planning` by any verb. Their evidence lines were hand-written in
`c70c0bf` ("the inner-belt stories carry their close evidence").

That combination is precisely the second scoreboard this milestone exists to end: the evidence line
says the work shipped and the status field says it was never started, and `pm ready-for feature`
reads the field. It is also unreachable through the belt — `claimed` (step 1) moves `planning →
building`, so a story the belt had touched could not still be at `planning`.

Across the whole milestone the ledger shows exactly **two** stories going `reviewing → done` and
**zero** features reaching `done`:

| grain | rows in the ledger |
|---|---|
| `0.2.0/adopt-is-a-conveyor/01-adopt-walks-the-adoption` | `reviewing → done` at `18:00:37Z` |
| `0.2.0/adopt-is-a-conveyor/02-adoption-verifies-the-adoption-not-the-game` | `reviewing → done` at `18:00:39Z` |
| `0.2.0/adopt-is-a-conveyor` (the feature) | `building → reviewing` at `18:02:00Z` — `close feature` step 2 |
| everything else | `planning → reviewing` / `planning → building`, by `pm story|feature <state>` before the belts existed |

So **2 of 28 stories and 0 of 9 features** have closed through these verbs. The feature's own
document says the bar is that they do, and names the reason: a belt whose first run is performed by
hand has not been tested. Three of the twenty-eight are this feature's own.

I am not filing this as a criterion note because it is not one. A story at `planning` carrying a
`done:` line is a state the tree should not be able to hold, and the two verbs that read it —
`pm ready-for feature` and `close feature`'s `stories-done` — both correctly refuse it. What is
open is the work: run the belts.

## Non-blocking findings

### I3 (MINOR) — the 0.21 s number survives only where a narrow rule covers the roadmap directory

`close story` writes into `pm/roadmap/` (`claimed`, `story-done`) and appends to the tracked
`ledger.jsonl`. `check_committed` (`:1785-1811`) rightly excludes `roadmap_dir` from its own
question — but `narrow-verified`, two steps earlier, does not: `verify --story` sees those writes as
changed paths, and a path matching no `[[verify.narrow]]` rule sends it to the **milestone** rung.
Measured, fresh consumer, closing a second story right after a first:

```
[story:narrow-verified] GATE ALREADY-TRUE — … 2 changed path(s) match no [[verify.narrow]] rule:
    pm/roadmap/1.0.0-m/features/f1/stories/01-s.md
    pm/roadmap/1.0.0-m/ledger.jsonl
  falling back to the milestone rung … $ make milestone
```

The belt ran the full gate inside the step advertised as *"four of its five steps are
already-computed facts."* This repo does not see it because `devkit.toml:179` declares
`paths = "pm/roadmap/**"`; a consumer without that rule pays a milestone gate on every story close
after the first, which is risk 2 arriving — *"a story-close conveyor that is slower than closing by
hand will be skipped."* Re-measured here, where the rule exists: **0.20 s, 0.21 s, 0.21 s** for
three runs of one story, and **0.24 s / 0.21 s** for two consecutive closes.

### I4 (NIT) — all three stories ship with empty acceptance-criteria sections

`01-closing-a-story-is-a-belt.md`, `02-closing-a-feature-is-a-belt.md` and
`03-the-belt-above-refuses-to-start.md` each carry `## Acceptance criteria` and `## Out of scope`
headings with nothing under them. The `## Close` block is the only prose in each file that says
what shipped, so nothing in the tree records what the story was *for* — which is the fact a feature
review is supposed to read a `## Close` block against. `check grain-shape` caps prose length and has
no opinion about an empty section, so no gate catches it.

## The six numbered ship criteria, judged

| # | criterion | verdict |
|---|---|---|
| 1 | `close story <id>` and `close feature <id>` walk their lists, refuse to advance, and are resumable — the same driver, proven by the same tests | **met** — `driver.OPERATIONS` is four rows in one table; `SUBJECT` gives each its segment count and `subject_defect` applies `version_defect`'s grammar per segment, so `close story` handed a feature id is refused by shape rather than resolving to the wrong file. Resumable and hostile-safe, all measured: a run state hand-edited to claim every step `true` produced `CORRECTED — the run state said 'narrow-verified' was done; the tree says: …` and stopped; a state file whose `operation` was rewritten to `adopt` was discarded with the discard PRINTED, then re-derived from the tree; a state file belonging to a different story was likewise discarded, which is the `CLOSE_OPERATIONS`-only relaxation `_load_run` documents. `tests/test_conveyor_close.py` is 26 test functions; the whole conveyor slice is 275 passing |
| 2 | `close story` refuses while the story's own narrow check is red, and the narrow command comes from `[verify]` rather than being named in the step | **not met — I1.** The second half is right: `check_narrow_verified` names no command, reads `[story.commands] narrow-verified` if the project sets one, and otherwise asks `verify --story`. The first half fails on a committed tree |
| 3 | `close feature` refuses while any story is not `done`, naming each — by calling `pm ready-for feature`, never re-implementing it | **met** — `check_stories_done` (`:1883-1891`) is one line of `ready_for(ctx, 'feature')`, through `pm_cli.main(['ready-for', 'feature', id])`, the published contract. Measured: `[feature:stories-done] JUDGEMENT STOPPED — BLOCKED 1.0.0/f1/01-s is building [pm] NOT READY — …` at step 1/6 |
| 4 | `close feature` refuses while its review record is absent, unparseable, or holds a finding at `disposition: open` | **met** — `check_review_recorded` (`:1958-1976`) and `check_findings_landed` (`:1989-2011`) both go through `_record_of` → `model.review_record_for` (which refuses `/`, `~`, `\`, a scheme and `..` by shape) and `_passes` → `verdict.parse`. `NoVerdict` and `MalformedVerdict` are both returned as `Answer.unverifiable`, which the driver prints as `UNVERIFIABLE` and treats as a refusal, never a pass. `verdict.OPEN` is the token; nothing is re-parsed. A blank `reviewed:` is a plain no naming the field. Measured: `close feature` on a feature with no record reached `feature-verified` and would have stopped at `review-recorded` |
| 5 | `install-sdlc` renders all FOUR lists, so the generated protocol is the whole SDLC | **met** — `docs/sdlc-protocol.md` carries `## \`release\` / \`adopt\` / \`story\` / \`feature\` — the ordered list` with 21 / 8 / 5 / 6 rows, equal to `DEFAULT_STEPS` for each. `STEP_DOC` covers every registered step in all four registries (zero gaps), so no row renders the *"ships no postcondition sentence"* placeholder. `install-sdlc --diff` → `already current`, exit 0, and `tests/test_install_sdlc.py::test_this_repos_own_protocol_document_is_byte_current` holds it there |
| 6 | 0.2.0's own 28 stories and 9 features close through these verbs | **not met — I2.** 2 of 28 stories, 0 of 9 features, and this feature's own three at `planning` |

**Risk 1 — over-encoding, and this feature is where it would happen.** Held. `review-recorded`
checks only that the artifact exists and parses, and says so in its docstring, its `STEP_DOC` row
and its `do()` text. Nothing in the two lists claims to check whether a review was good.

**Risk 2 — a story-close conveyor slower than closing by hand.** Met here, caveated for consumers
— see I3. Zero `deviation` rows exist in this milestone's ledger, so nobody has skipped anything
yet.

## `## Close` claims, checked

| story | claim | verdict |
|---|---|---|
| 01 | five steps, 0.21 s across three runs | **true** — re-measured 0.20 / 0.20 / 0.21 s on a done story, and 0.24 / 0.21 s for two consecutive closes. Caveated by I3 for a consumer with no roadmap narrow rule |
| 01 | 55 of 56 tests watched failing at HEAD | **not checkable** — `tests/test_conveyor_close.py` carries 26 test functions; 56 is plausible with subtests but I did not reconstruct the pre-`cc0569d` run |
| 02 | six steps, and no step re-implements a predicate that has a verb: `stories-done` IS `pm ready-for feature`, `review-recorded` and `findings-landed` ARE `verdict.parse` | **true** — confirmed by reading all six and by the criterion-3 and criterion-4 rows above |
| 03 | proven live on this milestone: `close feature` stopped at step 1/6 naming three stories at `reviewing` | **consistent, not confirmable** — two features carry exactly three stories at `reviewing` (`the-belts-refuse-to-advance`, `the-middle-tier-splits`), so the sentence fits the tree; `stories-done` writes nothing, so a run that stops there leaves no ledger row and the claim cannot be checked after the fact |
| 03 | `close story` stopped at `evidence-written` refusing to write the author's sentence | **consistent** — `check_evidence_written` reads and never writes, and `do_evidence_written` says so; same, no durable trace |
| 03 | finding: the run state CORRECTED itself against the tree mid-run and said so | **true** — reproduced twice by hand (a corrupted state file, and one belonging to another story) |

**No `## Close` claim in this feature is untrue.** What is untrue is what the *status fields*
imply — see I2, which is the tree contradicting the criterion rather than a story contradicting
itself.

## Cross-story questions

- **Did two stories solve the same thing twice — or duplicate an earlier feature's work?** Yes,
  across features: `_grain_status_at_or_past` / `_grain_flip` (`:1715-1758`, this feature) are a
  near-copy of `_status_at_or_past` / `_flip` (`:811-826`, `0.2.0/the-release-is-a-conveyor`). The
  copy is the better one — it guards `wanted not in states` and answers `UNVERIFIABLE` naming the
  config key, where the original raises `ValueError` out of `tuple.index`. **This feature added the
  guard and did not backport it**, which is filed against the feature that owns the original as R4
  in `docs/reviews/2026-09-05-the-release-is-a-conveyor.md` rather than duplicated here.
- **Did a later story weaken an earlier one's guard?** No. `_load_run`'s stale-state relaxation is
  scoped to `CLOSE_OPERATIONS` and leaves `release`/`adopt` on the strict refusal; the `Step`
  constructor's `_MAY_PERFORM` / `_MUST_PERFORM` tables still refuse a GATE carrying a `do()` and an
  AUTOMATIC without one, and all eleven new steps satisfy them.
- **Is any step's `check()` satisfied by its own `do()`?** No, for all eleven. The four status flips
  (`claimed`, `story-done`, `feature-reviewing`, `feature-done`) read the frontmatter the pm CLI
  wrote — a tree fact, and written through `pm story|feature <state>` so `check pm`, the drift gate,
  reads what the CLI wrote rather than a regex. `evidence-written` reads a line only a human writes.
  `committed` reads `git status --porcelain`. `stories-done`, `review-recorded` and
  `findings-landed` read the tree through other people's verbs. `narrow-verified` and
  `feature-verified` run a command — I1 is that one of them sometimes runs nothing, not that it
  reads its own flag.
- **Consequence carried in from the sibling feature.** `init.IGNORED`
  (`src/agentic_sdlc/repo/init.py:98-100`) does not ignore `.agentic-sdlc/`, so in a stock consumer
  `close story`'s own run state is untracked from its second run onward and feeds I3's fallback.
  Filed once, as R3 in the release feature's record.

## What was NOT verified

- **`close feature` was never walked to completion.** Its `feature-done` step writes to
  `pm/roadmap/`, which a reviewer must not do to this tree, and the scratch runs stopped at
  `feature-verified`. So `check_feature_done`, `do_feature_done` and the
  `pm feature done --review-record` hand-off were read, not run.
- **`close story` was never run against a story it would advance in THIS tree** — only against
  already-`done` stories, where every step answered `ALREADY-TRUE` and no `do()` fired. The
  advancing path (`claimed` and `story-done` actually flipping) was exercised only in scratch repos.
- **`[story.commands]` / `[feature.commands]` overrides were not exercised.** The configured-command
  branch of `check_narrow_verified` and `check_feature_verified` was read, not run; only the shipped
  `verify --story|--feature` path was.
- **`review_slug_fallback` was not exercised** against `_record_of`, so a `close feature` satisfied
  by a glob-resolved record nobody stamped in `reviewed:` is unmeasured.
- **`make milestone` and the interpreter matrix were not run.** The slice was:
  `tests/test_conveyor_{steps,driver,state,skip,adopt,close}.py tests/test_install_sdlc.py` →
  **275 passed in 17.83 s** on 3.11.
- **I2 reads the ledger and the status fields.** It does not prove *why* the three stories were
  never walked; only that they were not.

Reviewer's token cost: ~148k (shared across all three feature records).

```
verdict: HOLD
| id | severity | disposition |
| I1 | BLOCKER | open: narrow-verified passes over a census of zero once the work is committed |
| I2 | BLOCKER | open: criterion 6 — 2 of 28 stories closed through the belts, its own three at planning |
| I3 | MINOR | open: the belt's roadmap writes drive verify --story to the milestone rung |
| I4 | NIT | landed — all three stories now carry acceptance criteria (7, 6 and 6 lines), sourced from each story's own title and Close block plus feature.md's numbered ship criteria and risks, each concrete and checkable. Written in the RE-SCOPED voice on purpose: feature.md's own banner rules that every "refuses" in that record reads "warns, names what is open, and finishes", so criteria in the old voice would have specified the halt this feature is being rebuilt to delete. `## Out of scope` is left empty in all three and says why in a comment — nothing in the bodies or in feature.md draws a boundary that could be written without inventing one, and a guessed exclusion is worse than an absent section |
```
