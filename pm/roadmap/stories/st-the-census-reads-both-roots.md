---
id: st-the-census-reads-both-roots
kind: story
feature: ft-the-suite-is-measured-like-the-source
milestone: "ms-nothing-is-hand-rolled"
name: the census reads both roots
status: done
owner: agent
depends_on: []
changelog: none
---

# the census reads both roots

The prose census takes a ROOT and reports both of them. `src/` and `tests/` each get their prose,
their code and their ratio printed, per root, on every run — whatever the verdict — instead of the
numbers existing only inside an assertion message that fires when somebody has already lost.

Measured 2026-09-10, raw (before `0.6.0/D7`'s published-`--help` exclusion):

    src/     46 modules   14,055 code   4,709 prose (22%)   ratio 0.3350
    tests/   61 modules   20,604 code  10,830 prose (30%)   ratio 0.5256

With the exclusion applied, `src/` is at **0.3153 against a 0.3333 ceiling**.

**This story sets no ceiling for `tests/`.** It makes the number askable and reports it;
`st-the-tests-ceiling-is-declared-and-argued` sets it, after the rot is out. A root with no declared
ceiling reports and passes, and the case says so BY NAME rather than by staying quiet (rule 11).

## Gotchas

1. **`0.6.0/D7`'s exclusion is `src/`-shaped and its two failing-open guards become failing-CLOSED
   guards on a second root.** `published_docstrings()` (`test_prose_census.py:41`) derives which
   module docstrings are printed as `--help` by running every help surface; **no docstring under
   `tests/` is ever printed as `--help`**, so `published` is legitimately empty there. The two rule-4
   guards at lines 84-91 — `assert published` and `assert moved < prose` — exist because an exclusion
   that derived NOTHING would have quietly become the old measurement. Asserted over `tests/` they
   fail on a correct census. **The difference is STATED in the module, not discovered.**
2. **The census floor has to become per-root.** `assert len(PYTHON) > 10` (line 82) is one number for
   one root today; a moved `tests/` must FAIL rather than pass over nothing (rule 4, and
   `test_boundaries.py::_sources`'s `MIN_SOURCES` is the precedent).
3. **Renaming a case here breaks `tests/test_guard_corpus.py`.** Both functions in this module are on
   the `UNCOVERED` roster by name — `test_comments_and_docstrings_are_under_a_third_of_the_code` and
   `test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling` (`test_guard_corpus.py:102`,
   `:111`) — and that roster fails in BOTH directions: an entry nothing matches is a hole waiting for
   a guard to move into it. Parametrizing changes the nodeid; the roster line moves with it in the
   same commit, or the build is red for a reason that reads like something else.
4. **The census hand-rolls its own enumeration.** `PYTHON = sorted(SRC.rglob('*.py'))` (line 20),
   while `test_boundaries.py::_sources` deliberately routes through `core.walk` because *"a test that
   hand-rolled its own `rglob` to police `rglob` would be the joke that writes itself"*
   (`test_boundaries.py:102`). Widening to a second root doubles the hand-rolled walk. Route it
   through `core.walk` or write down why this census is different.
5. **`tests/` is not just `test_*.py`.** `rglob` over the root finds 61 files (57 `test_*.py`, plus
   `conftest.py` and the `tests/support` package). `tests/fixtures/` holds VENDORED trees that are
   INPUT, not content this repo maintains (`devkit.toml`'s `[grain_shape]` note makes the same point
   for the gates). Say which files are in the census and prove the narrowing discloses itself.
6. **A parametrized case is one case per row for `[tests] cases`**, which is at 1,136 of a declared
   1,140 for the unit tier. Two roots where there was one root is +1 or +2, and the ceiling has 4.

## Files this story may touch

- `tests/test_prose_census.py`.
- `tests/test_guard_corpus.py` — the two `UNCOVERED` lines, if the nodeids change.
- `devkit.toml` — `[tests] cases` only, and only if this story's rows take the unit tier over 1,140.

## Files it must stay out of

Anything under `src/`. Any test module's prose — the CUT is the next story, and a census story that
trims to make its own number look better has removed the evidence.

`tests/conftest.py`, `tests/support/**`, `tests/fixtures/**`.

## Acceptance criteria

1. The census takes a root. `prose_and_code()` and `census()` are already root-agnostic; only
   `PYTHON` is not, and a second root is a parametrize ROW rather than a second module.
2. Both roots' numbers are PRINTED on every run — prose, code, ratio, module count — not only inside
   a failure message.
3. `src/`'s verdict is unchanged: the ceiling is still `1/3`, the published-`--help` exclusion still
   applies to it alone, and a `src/` that goes over still fails.
4. **`tests/` has no ceiling in this story, and the absence is NAMED**: a root with no declared
   ceiling reports its ratio and passes, and the case says which roots are graded and which are only
   reported.
5. The two `src/`-only rule-4 guards (`assert published`, `assert moved < prose`) do not run over a
   root where `published` is legitimately empty, and the module states why the exclusion does not
   transfer.
6. The census floor is per root, and a moved or emptied root FAILS by name.
7. Which files each root's census counts is stated, and any narrowing discloses itself — a count with
   a silent filter behind it is a claim about the filter, not the tree.
8. `tests/test_guard_corpus.py` is green: any renamed nodeid moved its `UNCOVERED` line in the same
   commit, and no roster entry matches nothing.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2, 3 | unit | `test_comments_and_docstrings_are_under_a_third_of_the_code` parametrized over the roots | amend — it IS this feature for one root, which is the feature's own proof-budget note |
| 4 | unit | a case asserting the graded set and the reported set are both non-empty and that `tests/` is in exactly one of them | new; rule 11's named-absence shape, and it is what stops story 8 landing a ceiling nobody declared |
| 5 | unit | the exclusion guards move under the `src/` row of the parametrize and a case asserts they do not fire for `tests/` | amend — the guards exist, their SCOPE is what changes |
| 6 | unit | the per-root floor, proven by pointing a root at an empty temp dir and asserting the failure — `test_boundaries.py::TheCensusIsTheRealTree::test_a_moved_SRC_breaks_the_build_instead_of_passing` is exactly this case for the other census | new, patterned on an existing one |
| 7 | unit | covered by 6's census assertion plus the printed counts from 2 | covered |
| 8 | unit | `test_guard_corpus.py::test_every_ast_shaped_guard_declares_a_corpus_or_is_named` | existing — it fails in both directions already |

## Out of scope

Setting `tests/`'s ceiling, and trimming one line of prose anywhere —
`st-the-tests-ceiling-is-declared-and-argued`.

Deleting a test. The suite is 20,604 lines of test code to 14,000 of source (1.47:1) and the feature
says that is defensible.

A coverage number, a trend, or a third census. `check budget` gates cost and the corpus roster gates
probing.

Turning this census into a shipped verb — `st-every-census-this-milestone-argues-from-is-a-command`
decides that, and it decides it with a written reason as a legitimate outcome.

## Close

done: fa6fbd1 — `modules()`, `published_docstrings()`, `census()` and `report()` each take a Root;
the ceiling case is parametrized over `ROOTS`. `src/` 47 modules / 0.3159 against its 1/3 ceiling,
`tests/` 61 modules / 0.5284 REPORTED and not graded, and the absence is named by
`test_which_roots_are_graded_and_which_are_only_reported` rather than left silent.

`src/`'s verdict is unchanged and it is proven, not asserted: the pre-change `census()` read from
`git show HEAD:` returns the identical triple over the identical 47 paths. The walk moved off a
hand-rolled `rglob` onto `core.walk.descendants`, which is also what carries the scope disclosure.

**Three of this story's own claims were wrong and the code corrected them.** `test_guard_corpus`'s
`UNCOVERED` keys on the SOURCE function name, not the pytest nodeid, so parametrizing left the
roster byte-identical and gotcha 3's concurrency hazard did not exist. Only ONE of the two
`src/`-shaped rule-4 guards inverts on a second root — `assert published` fails, `assert moved <
prose` is trivially true and merely grades nothing, which is a different defect and is now written
as one. And `tests/fixtures/` holds zero `.py`, so the declared narrowing removes nothing today; it
is a walk filter precisely so it discloses on the day it bites.

**Criterion 2 is a `warnings.warn` and that is a measured choice, not a preference.** Under `make
unit`'s `-n auto`, a `print`, a `sys.stderr.write`, a `capsys.disabled()` block and the config's own
terminal writer are ALL discarded from a PASSING test — xdist ships a worker's captured streams back
only on failure. The warnings summary is the one channel pytest renders either way without reaching
into `tests/conftest.py` or the Makefile. It costs the tier summary line two words and the
Makefile's census extraction still reads the count correctly. `st-every-census-this-milestone-argues-from-is-a-command`
is where this becomes a verb and the warning goes.
