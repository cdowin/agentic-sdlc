---
id: st-the-tests-ceiling-is-declared-and-argued
kind: story
feature: ft-the-suite-is-measured-like-the-source
milestone: "ms-nothing-is-hand-rolled"
name: the tests ceiling is declared and argued
status: planning
owner:
depends_on: []
changelog:
---

# the tests ceiling is declared and argued

`tests/` carries its own declared prose ceiling with the argument for that number written beside it,
in the shape `devkit.toml`'s `[tests] cases` comment already uses — a dated block naming what moved,
by how much, and why. The number is set from the suite AFTER the rot is out, and the cut is reported
PER MODULE rather than as one total.

Measured 2026-09-10: `tests/` is 10,830 prose lines against 20,604 of code — **ratio 0.5256**, 19%
docstring and 11% comment, against `src/`'s 0.3153 with `0.6.0/D7`'s exclusion applied.

## Why a number somebody has to ARGUE, and not a number somebody hits

0.6.0 spent **eight rounds** on the `src/` census, and its brief had to say *"no comment trimming to
buy census margin"* out loud because the gate kept demanding it. That fight produced `0.6.0/D7`,
which fixed what the census COUNTS rather than what it allows. **A ceiling copied from `src/` would
repeat the fight with the economics reversed** — a test docstring and a source docstring are not the
same artefact and the ratio should not be assumed equal.

## Where prose GOES rather than dies

The three placements 0.6.0 established, unchanged, and they are not trimming:

    help text                 -> a `USAGE` constant; a string assignment is CODE
    a rejected alternative    -> `pm decide`
    the story of a defect     -> the grain that fixed it

**A test docstring says what this case pins and why it can fail. It does not retell the incident.**
The incident belongs in the story, and the story is already written.

## Gotchas

1. **The ceiling is a MODULE CONSTANT, not a config key.** Hard rule 5 splits on this: a GATE key
   ships a stock default so a repo with no `devkit.toml` behaves byte-identically to one declaring
   it, and `tests/test_config_seed.py` compares the seed key by key. `test_prose_census.py` is this
   repo's own test module, not a shipped gate, so a `[prose]` section would be a key with nothing
   behind it in every consumer's tree. `PYTHON_CEILING` (line 21) is the precedent; the new constant
   sits beside it with its argument as a comment. **State the rejected alternative.**
2. **`bg-the-prose-ceiling-has-no-headroom` already ruled on what a ceiling must not become.**
   `test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling` (line 100) measures at the
   repo's OWN average so it cannot be satisfied by picking a flattering module: *"a feature that adds
   a well-documented module must go green without any comment in any OTHER file changing."* That
   clause generalises to `tests/` unchanged, and a ceiling with no room to write a new test module is
   a growth gate wearing a quality gate's clothes.
3. **Do not rename or delete a case.** A rename breaks `UNCOVERED` in `test_guard_corpus.py`, which
   fails in both directions. A deletion moves `[tests] cases`, which is at **1,136 of a declared
   1,140** for the unit tier. Trimming prose changes neither number, and that is the point: this
   story removes English, not behaviour.
4. **Nothing in `src/` is trimmed to pay for this.** `src/` is a different root after
   `st-the-census-reads-both-roots` and its ratio must not move. Report it before and after as the
   proof that it did not.
5. **Being over `src/`'s ratio after the whole cut is a legitimate outcome to STATE.** The milestone
   brief and this feature both say so, and it is the same ruling 0.6.0 made about `CLAUDE.md`. The
   deliverable is a declared, argued number — not a flattering one.
6. `test_prose_census.py` counts a docstring as `count('\n') + 1` and a comment as one TOKEN, so a
   reflowed paragraph moves the number without removing a word. Report words as well as lines if the
   two disagree.

## Files this story may touch

- `tests/test_prose_census.py` — the second ceiling and its argument.
- every module under `tests/` — DOCSTRINGS AND COMMENTS ONLY.
- `devkit.toml` — only if a placement moves help text into a `USAGE` constant that changes a count.

## Files it must stay out of

Anything under `src/`. `tests/fixtures/**` — vendored input, versioned with the code that reads it.
`tests/conftest.py`'s derivation and runtime guard, whose comments are the record of the 170x.
`tools/hooks/**`. Any assertion, any case name, any test body.

## Acceptance criteria

1. The rot comes out FIRST and the ceiling is set from the suite that remains — not the other way
   round, and not at `src/`'s number.
2. **The cut is reported per module**, not as one total: module, prose before, prose after, and what
   left. A single number hides where the essay was.
3. Every removal is one of: prose the reader does not need, or prose that MOVED to one of the three
   placements above. A line that moved says where it went.
4. `src/`'s census ratio is unchanged, reported before and after.
5. The declared `tests/` ceiling carries a written argument in the shape `[tests] cases` uses — dated,
   naming what moved and by how much, and naming the alternative that was rejected.
6. **The headroom clause holds for `tests/` too**: a new test module the size of the median one,
   documented at the suite's own rate, fits under the ceiling.
7. The ceiling lives as a module constant beside `PYTHON_CEILING`, with the argument for not making
   it a config key written down.
8. **No case is deleted, renamed, added or altered.** `[tests] cases` reports the same unit and
   integration counts before and after, and `test_guard_corpus.py`'s `UNCOVERED` roster is untouched.
9. If the suite is still over `src/`'s ratio when the cut is finished, that is STATED with the reason
   — not closed by trimming further.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 5, 7 | unit | `test_comments_and_docstrings_are_under_a_third_of_the_code`, parametrized by `st-the-census-reads-both-roots`, with `tests/` moving from reported to GRADED | amend — the previous story built the row; this one gives it a number |
| 2, 3, 9 | — | the per-module table in the close, graded by the feature review | not a test — where a line went is judgement, and a test asserting a per-module number is the growth gate this feature forbids |
| 4 | unit | the same parametrized case, `src/` row | existing |
| 6 | unit | `test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling` parametrized over both roots | amend — `bg-the-prose-ceiling-has-no-headroom`'s own verification clause, one root wider |
| 8 | unit | `check budget`'s case count, run before and after; `test_guard_corpus.py::test_every_ast_shaped_guard_declares_a_corpus_or_is_named` fails on a renamed nodeid | existing — both gates already answer this and neither needs a new case |

## Out of scope

Deleting a test. The suite is 1.47:1 and defensible; this is about the English.

A line-count target for `tests/`, or a coverage number. `check budget` gates cost, the corpus roster
gates probing, and a third number would be cargo.

Sorting the self-policing from the behaviour tests — `st-a-source-shaped-guard-names-what-it-protects`.

Trimming `src/`, `CLAUDE.md`, or any grain document.
