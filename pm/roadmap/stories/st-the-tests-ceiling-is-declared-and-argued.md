---
id: st-the-tests-ceiling-is-declared-and-argued
kind: story
feature: ft-the-suite-is-measured-like-the-source
milestone: "ms-nothing-is-hand-rolled"
name: the tests ceiling is declared and argued
status: done
owner:
depends_on: []
changelog: `tests/` gets its own declared prose ceiling — `TESTS_CEILING = 0.55`, the measured ratio after the cut rounded up to the next twentieth — with a dated per-module argument and the reason `src/`'s third does not transfer: 0.6.0/D7 moves 223 printed-`--help` docstring lines into `src/`'s code and `tests/` gets none of that.
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

## Close

THE NUMBER: `TESTS_CEILING = 0.55` in `tests/test_prose_census.py`, a module constant beside
`PYTHON_CEILING` with a dated argument block above it in the shape `devkit.toml`'s `[tests] cases`
uses. **The derivation is a rule anybody can re-run, not a number somebody picked**: the measured
ratio after the cut, rounded UP to the next twentieth — 0.5267 -> 0.55, which is 4.4% of relative
headroom and 499 prose lines of room at today's code size, against the 4.0% `src/` carries over its
own measurement. Rejected: a `[prose]` section in `devkit.toml` — hard rule 5 makes a GATE key ship a
stock default and this module is this repo's own test rather than a shipped gate, so the key would
stand behind nothing in every consumer's tree.

THE CUT, PER MODULE, and it came first (prose lines, then prose words):

| module | before | after | cut | words | what left |
|---|---|---|---|---|---|
| `test_consumer_independence.py` | 301 | 262 | **-39** | -403 | a 28-line block documenting a migration-document exemption the code no longer has (no `MIGRATION_DOC`, no `==`, no marker check — `names_a_consumer` applies `TOMBSTONES` alone); 12 lines introducing cases that were deleted; three retellings of the 0.24.0 census holes the module docstring already states |
| `test_fuzz_inputs.py` | 154 | 120 | **-34** | -304 | the v0.16.0 incident narrative and the 2026-08-30 run transcript — the blocker's shape is already in `test_the_corpus_separates_the_pre_fix_resolver`'s own docstring and the commit is already at `_pre_fix_bug_resolver`; the retired scene-plane paragraphs; an incantation CLAUDE.md now forbids (`pytest tests/<module>.py`) |
| `test_init_verb.py` | 220 | 197 | **-23** | -194 | four tombstone enumerations of files, sections and paths that left at 0.2.0, each compressed to its claim plus the decision record that holds it (`0.2.0/D1`, `D2`, `R3`) |
| `test_fresh_project.py` | 169 | 147 | **-22** | -271 | the same, one root over: "28 targets through 0.1.0", "22 of the 23 that left", the hook-census literal's story, and "THE SURFACE MOVED" |
| `test_gate_library.py` | 159 | 149 | **-10** | -116 | 9 lines on the module's own rename from `test_runners_installable.py` (a file that does not exist, so the cross-reference was dead), and the departed-artefact list inside the language-neutral clause |
| `test_pm_verbs.py` | 618 | 610 | **-8** | -112 | the 0.3.0 batched-review measurement, which lives in `ft-every-move-breadcrumbs-the-next-step` and is cited on the line above it; the three-hole enumeration from `bg-a-proof-row-names-a-case-that-proves-half`, which is cited too; two "amended from the case that…" paragraphs reduced to the claim the case makes now. The file reads 626 now — a sibling story added a case to it after this measurement |
| `test_install.py` | 627 | 621 | **-6** | -60 | a `CHANGELOG.md` scoping rule and its own retirement notice (the file left the list at 0.6.0), and `install-runners`' 0.1.0 roster |
| `test_pm_ledger_record.py` | 375 | 370 | **-5** | -66 | the all-seven-seed paragraph, which was **the same 8 lines in four modules**: kept whole in `test_pm_ledger.py` and pointed at from the other three |
| `test_pm_ledger_report.py` | 312 | 307 | **-5** | -66 | the same |
| `test_pm_ledger_report_sections.py` | 207 | 202 | **-5** | -66 | the same |
| `test_wheel_payload.py` | 51 | 48 | **-3** | -39 | a cross-reference to the `MIGRATION_DOC` entry deleted above, and the removed-entry-count story |
| `test_verdict.py` | 206 | 205 | **-1** | -6 | a repo-local reviewer definition that left in 0.2.0 |
| `test_pm_gate.py` | 1011 | 1011 | 0 | -3 | `execlist.py` — a module that does not exist — named as a reader of `owner:`; rewritten in place, not removed |
| **cut total** | | | **-161** | **-1,703** | 12 modules net, a 13th rewritten in place |
| `test_prose_census.py` | 119 | 187 | **+68** | +662 | the ceiling, its derivation, its three measurements and its rejected alternative |

Net **-93** prose lines. Every removal is prose the reader does not need (a dead reference, a deleted
mechanism, the same paragraph a fourth time) or an incident whose grain or decision record is NAMED on
the line that replaced it — nothing moved to a placement that did not already hold it, because this
story writes no new grain.

WHAT WAS MEASURED AND KEPT: `test_boundaries.py` (717 prose lines, the largest in the suite) and
`test_gate_roster.py`, read in full and cut by nothing — their comments ARE the rules the AST guards
enforce. `test_install.py` gave up 6 of 627 for the same reason. `test_shell_mark.py` was read and
left alone: a sibling story was editing it in this worktree.

**SO THE FEATURE'S PREMISE IS HALF RIGHT, AND THIS IS THE HONEST FINDING.** 30% of `tests/` is
English, and it is not mostly rot: 47% of the suite's prose was read line by line and 1.5% came out.
What was removable was dead cross-references (four paths named in prose that are not in the tree,
found by sweeping every backticked path), blocks describing deleted mechanisms, and one paragraph
pasted into four modules — a suite-wide sweep for repeated sentences found nothing else non-trivial.
The ratio is what the style costs, not what neglect left behind.

STILL OVER `src/`, STATED RATHER THAN SATISFIED (criterion 9): 0.5267 against `src/`'s 0.3206, and
the like-for-like comparison is against 0.3415 because `0.6.0/D7` moves 223 `src/` docstring lines
into `code` and `tests/` gets none of that — nothing under `tests/` is ever printed as `--help`, so
the exclusion is legitimately EMPTY here where for `src/` an empty one means the derivation went
blind. That difference is declared on the `Root` and asserted by
`test_which_roots_are_graded_and_which_are_only_reported`, not assumed. At 1/3 the suite would be 58%
over on day one and the only way green is deleting 4,130 lines of English nobody reviewed.

THE CASE THE CODE TOLD ME TO DELETE, AMENDED INSTEAD.
`test_which_roots_are_graded_and_which_are_only_reported` asserted `'tests' in ungraded` and its own
message said to *"delete it in the commit that lands `tests/`'s ceiling"* — against criterion 8 and
gotcha 3. Deleting it leaves the hole rule 11 is about: nothing would notice a third root arriving at
`ceiling=None`, reporting `NO CEILING` on a green transcript and passing over any amount of prose. So
it keeps its name and both directions with the tree's new answer — every root graded, the roster not
shrunk to make that true, and the two ceilings DIFFERENT, which is the "inherited rather than argued"
failure the previous story refused by name.

PROBE, on a scratch copy of `tests/`, five directions (BEFORE -> AFTER):

    BEFORE  11,188 prose / 21,313 code = 0.5249 vs ceiling 0.5500  PASS
    AFTER   12,388 prose / 21,313 code = 0.5812 vs ceiling 0.5500  FAIL  (1,200 comment
                                                                         lines planted)
    roster: a third root at ceiling=None  FAIL · the roster cut to one root  FAIL ·
    tests/ with publishes_help=True  FAIL · tests/ graded at PYTHON_CEILING  FAIL, but
    only after a fix: the first spelling compared the two CONSTANTS, passed the probe,
    and is now asked of the ROSTER — the half-guard
    `bg-a-proof-row-names-a-case-that-proves-half` names, caught before it shipped.
    headroom: tests/ at a ceiling under its own measurement  FAIL

CRITERIA: 1, 2, 3, 5, 7, 9 met. 6 met for both roots, watched failing. 4 met *by this story* — no
file under `src/` was touched, which `git diff --name-only` shows; the absolute `src/` ratio DID move,
0.3155 -> 0.3206, because a sibling story is editing `src/` in this worktree, reported rather than
claimed away. 8 met — the 14 modules I edited carry a byte-identical set of test callables, proven by
AST before and after; the two that gained one (`test_pm_verbs.py`, `test_cli_surface.py`) gained it
from that sibling story, which is also why `[tests] cases` is no longer at 1575 (1,595 collected).

NOT VERIFIED: that the 53% of prose I did not read line by line is free of rot. It was swept
mechanically — every backticked path checked for existence, every sentence over 45 characters checked
for a repeat elsewhere, narrative density measured per module — and the unread remainder is 8-26%
narrative by that measure. A second pass is a second story.

done: f7a8114, b89a80c — `TESTS_CEILING = 0.55`, the measured post-cut ratio rounded up to the next
twentieth, with the per-module cut table above. `b89a80c` then fixed the census that produced the
measurement and re-derived every number here; 0.5106 rounds to 0.55 too, so the ceiling held.
