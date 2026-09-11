---
id: st-a-source-shaped-guard-names-what-it-protects
kind: story
feature: ft-the-suite-is-measured-like-the-source
milestone: "ms-nothing-is-hand-rolled"
name: a source-shaped guard names what it protects
status: done
owner:
depends_on: []
changelog: none
---

# a source-shaped guard names what it protects

The source-shaped guards are a set the code can be ASKED for, each naming the property it protects,
and each judged in writing: load-bearing, or a second scoreboard for something a behaviour test
already covers. Today the only way to ask is a grep, which is how every number in the feature brief
was produced.

Measured 2026-09-10 from `tests/test_guard_corpus.py`'s own roster reader: **57 test modules, 789
guards, 34 AST-shaped, 18 covered, 16 uncovered** — and `UNCOVERED` holds exactly those 16. Twelve
modules reach `ast.parse`/`ast.walk`, **7,781 lines, 22% of the 35,434 in `test_*.py`**. Five modules
declare a corpus: `test_boundaries.py`, `test_cli_surface.py`, `test_contracts.py`,
`test_guard_corpus.py`, `test_pm_flow.py`.

## The half that already exists, and what it is missing

`test_guard_corpus.py` derives the roster from source and never imports a module that declares
nothing (`_roster()`, line 216). It knows which guards are AST-shaped, which declare a `CORPUS`, and
which declare a `catches()`. **What it cannot say is what any of them PROTECTS.** That is the gap:
the population is derivable, the purpose is not, so "is this guard load-bearing or a second
scoreboard" is a question nobody can ask the tree.

Its own precedent is the argument for closing it: `test_guard_corpus.py` found four hollow gates
during 0.6.0's close — a router read by AST, `semver-gate.yml`'s success path, an `assertIn(x, X)`
tautology, and `check doc`'s rule wired by one unguarded line. That is the best money in the
repository. Some of the other 7,781 lines is the tool checking its own homework at a price nobody has
ever named, and nobody knows which is which.

## The finding this story starts from

**`test_guard_corpus.py:76-80` says, in the comment beside its own floors, "56 modules, 30 AST-shaped
guards, 155 replayed cases at the time of writing". The reader directly below it now returns 57 and
34.** A hand-written number quoted beside the census that would have corrected it is exactly
`bg-the-brief-undercounts-the-coupling-it-argues-from`, one file over. It is corrected here from the
reader's output, and the floors themselves (`MIN_MODULES 30`, `MIN_GUARDS 20`, `MIN_CASES 40`) stay
where they are — they exist to catch a broken root, not to track a count.

## Gotchas

1. **A third declared name is a decision, not a convenience.** `CORPUS` and `catches` are required
   today and their absence is a named finding. Adding "what this protects" as a THIRD required
   attribute widens the contract every guard must satisfy — including the 16 on `UNCOVERED`, which
   are absences with names on them, not exemptions. The alternative is the class docstring's first
   line, which every guard already has and which cannot be read as a field. **State which and why.**
2. **`UNCOVERED` fails in BOTH directions** (`test_guard_corpus.py:397`): an entry that matches
   nothing is a hole waiting for a guard to move into it. This story must not grow it, and any
   rename moves its line in the same commit.
3. **The census's limits are already stated and must not be quietly widened.** A guard that greps a
   shipped file without parsing it is outside this population, and so is a guard reaching a reader in
   ANOTHER module, "the honest limit of a single-module AST walk"
   (`test_guard_corpus.py`, module docstring). If this story widens either, it says so and prices it.
4. **`_roster()` is `functools.cache`d because reading 33k lines four times cost the inner loop four
   seconds**, and a tier that got slower is a finding (rule 10). A per-guard attribute read must not
   re-parse.
5. **Judging is not deleting.** The feature says the suite is defensible and out of scope for
   deletion. A guard judged "a second scoreboard" is RECORDED as one; removing it is a separate
   decision with its own argument.
6. **`[tests] cases` unit is at 1,136 of a declared 1,140.** A per-guard attribute is not a case, but
   any new case here spends the last of the headroom.

## Files this story may touch

- `tests/test_guard_corpus.py` — the roster reader, its floors' comment, and whatever the third
  declaration turns out to be.
- the 12 AST-shaped modules, to declare the property each guard protects: `test_boundaries.py`,
  `test_pm_flow.py`, `test_conveyor_lessons.py`, `test_cli_surface.py`, `test_init_verb.py`,
  `test_grain_shape.py`, `test_guard_corpus.py`, `test_config_seed.py`, `test_shell_mark.py`,
  `test_contracts.py`, `test_verify_rules.py`, `test_prose_census.py`.

## Files it must stay out of

Anything under `src/`. Any guard's assertions, its `CORPUS` rows or its `catches()` — this story adds
a declaration and reads the roster; it does not change what any gate catches.

`tests/conftest.py`. `tests/fixtures/**`.

## Acceptance criteria

1. The roster is ASKABLE: one call returns every AST-shaped guard with the property it protects, and
   the answer is derived from source rather than hand-listed.
2. Each of the 34 AST-shaped guards declares that property, and a guard that declares none is named —
   an absence with a name on it, never silence (rule 11).
3. The mechanism is decided in writing: a third declared attribute beside `CORPUS`/`catches`, or the
   class docstring's first line, with the argument for the one chosen and against the other.
4. Each of the 34 carries a written judgement: load-bearing — and against which of rule 4's two sins
   — or a second scoreboard for a behaviour test that is named.
5. `UNCOVERED` is not grown, and no entry in it matches nothing.
6. **The stale count beside `MIN_MODULES`/`MIN_GUARDS`/`MIN_CASES` is corrected from the reader's own
   output, and the floors do not move.** A floor raised to match a census stops being a floor.
7. The per-module AST-shaped line mass (12 modules, 7,781 lines) is reported from a command, not a
   grep — the command is `st-every-census-this-milestone-argues-from-is-a-command`'s.
8. The census's stated limits are unchanged, or the widening is named and priced.
9. `make unit` does not get slower: the roster is read once per session, as it is today.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 5 | unit | `test_guard_corpus.py::test_every_ast_shaped_guard_declares_a_corpus_or_is_named` — the same roster reader, one more declaration in the `Guard` tuple | amend; the feature's own proof budget names this case as the roster half already |
| 3, 4 | — | the written judgement in the close, graded by the feature review | not a test — "is this guard load-bearing" is judgement, and asserting it would be the second scoreboard this story exists to find |
| 6 | unit | the comment is not gated; `test_the_census_is_the_real_suite` (line 411) asserts the floors and is what proves the floors did not move | existing — the comment is read at review |
| 7 | unit | the census verb's own case, in `st-every-census-this-milestone-argues-from-is-a-command` | deferred by design |
| 8 | unit | `EveryGuardDeclaresWhatItMustCatch.CORPUS`'s nine planted modules, which pin the population's edges — a bare function, a helper class, a docstring naming `parse` | existing — a widened census reclassifies one of them and goes red |
| 9 | unit | `check budget`'s `unit` duration, at 6.7s of a 20s ceiling | existing |

## Out of scope

Deleting a guard, or deleting a test of any kind.

Sorting the whole suite into self-policing and behaviour. The population is the AST-SHAPED guards,
and that narrowing is `test_guard_corpus.py`'s own and deliberate.

The prose ceiling — `st-the-tests-ceiling-is-declared-and-argued`. A coverage number.

Probe rows. ~330 lifetime probe rows against 1,253 static cases is a real finding in the research and
it belongs to a milestone that plans it, not to a roster story.

## Close

THE MECHANISM: a third declared attribute, `PROTECTS = (the property, the judgement)`, read off the
class body by the same `_assigned` scan that finds `CORPUS` — no import, no second parse. **Against
the class docstring's first line:** every guard already has one, so that rule would have had an empty
offender list on the day it was written and would keep having one as new guards arrive with ordinary
prose — a gate nobody can fail, inside the module that exists because an empty offender list is also
what a reader that stopped reading produces. One of the thirteen does not even have a docstring
(`test_prose_census.py::test_comments_and_docstrings_are_under_a_third_of_the_code`). A name is a
decision; and a string assignment is CODE to the prose census, where 22 paragraphs of docstring would
not have been. The argument is in `tests/test_guard_corpus.py`'s module docstring, where the next
author stands. Its cost, per gotcha 1: the contract is three names wide now, and a bare FUNCTION can
satisfy none of them — not a new exemption but the finding `_guards` already records about `CORPUS`,
and all 13 are already named on `UNCOVERED`.

THE ASK: `shaped_roster()` — one call, 35 AST-shaped guards with `.protects`, derived from source.

THE JUDGEMENT, all 35 in the tree rather than here: 22 classes carry it in `PROTECTS`; the 13 bare
functions carry it in a comment beside their `UNCOVERED` line, because that is the only place a bare
function has. Verdict: **35 load-bearing, 0 wholly second scoreboards** — 28 against sin 1 (a gate
that misses drift and prints PASS), 6 against sin 2 (a write that looks legitimate and is not), 1
load-bearing inverted (the ceiling-is-not-a-growth-gate case). 17/5 of the 22 classes, 11/1/1 of the
13 functions. The honest finding is one level down:
**two CASES are second scoreboards now**, both named in their own `PROTECTS` —
`test_boundaries.py::TheOpenModeIsReadFromTheRightArgument::test_every_spelling_of_open_is_classified_by_its_real_mode`
and `TheToolEmitsAndNeverExecutes::test_the_emit_path_resolves_no_string_to_a_callable` each loop the
guard's own `CORPUS` through the guard's own `catches`, which is exactly what
`test_every_declared_corpus_is_replayed_case_by_case` does over the same table. They are the only two
whose `CORPUS` is a named constant, so the search was total. Recorded, not deleted (gotcha 5).

THE STALE COUNT: "56 modules, 30 AST-shaped guards, 155 replayed cases" → the reader says **59, 35,
202**. Corrected, dated, and declared unmaintained: the refresh is not the fix, because the quote had
gone stale by 3 modules and 5 guards in four days. Floors unmoved at 30/20/40.

NOT MET / DEFERRED: criterion 7 is the census story's verb, as planned — the reader's own numbers,
for that story to single-source, are 12 AST-shaped modules / **8,302 lines / 22.9% of 36,265 in 59
`test_*.py`** at the commit before this one (the brief's 7,781 / 35,434 / 22% / 57 was a 2026-09-10
reading; `test_*.py`, not all 62 `.py`, is the population `_modules()` globs). Criterion 8: the
population's limits are unchanged — the nine planted edges still classify as before; what widened is
the CONTRACT, which is criterion 3. Criterion 9: unit 9.7s of 20s, `_roster()` still read once per
session, and the declaration is read in the same walk. Zero new collected cases (131 before, 131
after across the seven modules): `[tests] cases` is at 1575 of 1575 and `devkit.toml` belongs to
another story this session, so the third declaration had to fit inside the existing case — it does,
as three assertions over one roster read.

done: 13bd43c — `PROTECTS = (the property, the judgement)` on 22 guard classes, a comment beside each
of the 13 bare functions, and `shaped_roster()` answering the whole set in one call. 35 guards judged:
28 against rule 4's first sin, 6 against its second, 1 inverted, 0 wholly second scoreboards — but TWO
CASES are, named inside their own guard's `PROTECTS` rather than deleted. The stale floors comment is
corrected AND declared unmaintained, because a hand-written number beside the census that answers it
is what this milestone is named against.
