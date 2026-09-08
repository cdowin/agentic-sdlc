---
id: ft-the-vocabulary-is-constants-not-literals
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: the vocabulary is constants, not literals
status: done
reviewed: docs/reviews/2026-09-08-0.6.0-the-vocabulary-is-constants.md
depends_on: []
consumed_by: []
changelog: none
---

# the vocabulary is constants, not literals

A maintainability sweep, and the targets are measured rather than felt. It runs LAST in this
milestone because it touches everything, and it must be behaviour-preserving with a MECHANICAL proof
— not a reviewer's confidence.

## What the tree actually holds

    src/                20,457 lines
    cli.py               2,978   model.py 2,783  — two modules are 28% of src
    functions              894   32 over 60 lines; largest is driver.main at 184
    'feature'               96x  as a bare string literal
    'milestone'             84x       'story' 73x   'kind' 56x   'status' 48x
    127 / 120 / 124 / 126    5x each in steps.py, unexplained
    version refs in comments 40   (21x "0.4.0", 11x "0.5.0") across 1,567 comment lines
    module constants unread   7   in src/ — some are read by TESTS, which is legitimate

## The literal problem is not style — it shipped a bug this milestone

`'feature'`, `'milestone'`, `'story'`, `'bug'` are this package's entire grain vocabulary, and they
are bare strings ~250 times. `'kind'`, `'status'`, `'grain'`, `'ts'` are its frontmatter and row
vocabulary, spelled the same way.

**That is the `at` versus `ts` defect's root.** `lessons.FIELDS` spelled its stamp `'at'` while every
reader keyed `'ts'`, so those rows sorted to the beginning of time and nothing caught it — because
neither spelling is wrong to a string. It survived until a reviewer read both files side by side. A
constant makes the disagreement a NameError at import; a literal makes it a silent sort.

Same shape, same milestone: `_ledger_paths` written three times, `KIND_ENTER` defined twice,
`READY_KEY` duplicating a field name inside `ENTER_KEYS`.

## The sweep

**Vocabulary to constants.** Grain kinds, frontmatter field names, row kinds and tap names become
named constants with one home each. This is the load-bearing half and should land first.

**Unexplained numbers get a name or a reason.** `127`/`120`/`124`/`126` in `steps.py` five times each.
Either they are one concept (name it) or they are four (say why each differs).

**Dead constants: delete or promote.** Seven are unreferenced in `src/`. **Check `tests/` before
cutting any of them** — `report.CLOCK_COLUMNS` is read by `test_cli_surface.py` precisely so the
constant stays live, which is a feature and not rot. A constant only a test reads is either the
contract that test pins, or it is dead; decide per constant, in writing.

**Archaeology, distinguished from reasoning.** Forty version references sit in comments. Most are
LOAD-BEARING — `RETIRED_CHECKS` names the version a rule went in because a consumer whose config still
lists it needs to be told where it went, and *"retired in 0.4.0 — it kept `id:` in agreement with the
path"* is a reason, not a stamp. What goes is the bare breadcrumb: a version that dates a line without
explaining anything. **The test is whether deleting the version changes what the sentence teaches.**

**Split by domain, not by line count.** `cli.py` at 2,978 lines is argument parsing, verb dispatch,
and per-verb logic in one file. The split follows those seams. `model.py` is config reading, the
document layer, and the grain index. Do not split to hit a number.

**Consolidate the genuine duplicates.** `ft-a-read-verb-is-a-declaration` owns the pointer resolvers
and the column declarations; this feature takes what is left after it lands, so the two do not fight
over the same lines.

**One shape for a refusal.** Exit-2 messages are contract (rule 6) and an operator greps them. They
should be one shape across verbs, and they are not audited.

## What this must NOT become

**No line-count gate on functions or files.** A number is a proxy, and `driver.main` at 184 lines may
be a legitimate dispatch table that reads worse split. `check budget` already gates test COST and the
prose census already gates comment ratio; a third number would be cargo.

**No comment trimming to buy census margin.** The census sits at ~0.333 with a handful of spare lines,
and a sweep that pays for itself by deleting reasoning has done the opposite of this milestone.

## Ship criterion

The grain kinds, frontmatter field names, row kinds and tap names have one constant home each, and a
test asserts no module spells one as a bare literal — so a second spelling is an import error, not a
silent sort.

Every integer in `src/` that is not 0, 1 or -1 is either named or carries a reason.

`cli.py` and `model.py` are split along stated domain seams, each split named in the commit.

**Behaviour preservation is proven mechanically, not asserted**: parse before and after, normalise
docstrings, compare `ast.dump`. The prose passes in 0.5.0 used exactly this and it is why they could
claim zero code change with a straight face.

`make test` and every gate green at each landing, not only at the end.

## What landed, and what did not — 0.6.0

Four of the six sweeps landed. Two did not, and this section is that decision rather than a silence.

**Landed — the vocabulary.** 603 bare literals of the four vocabularies became 62, and every one of
the 62 is a top-level DECLARATION named in the gate with the reason it is a different word. Grain
kinds have one home (`model.GRAIN_MILESTONE|FEATURE|STORY|BUG`, and `FLOW_KINDS` is built from them);
frontmatter field names have one (`model.FIELD_ID|KIND|STATUS|NAME|OWNER`); the durable row's own
three have one (`ledger.TS_FIELD|KIND_FIELD|GRAIN_FIELD`, and every key tuple and minter below them
is built from those). Taps were already constants. **Five parallel declarations of the kind
vocabulary collapsed**: `grain_shape.MILESTONE|FEATURE|STORY|BUG` and `report.KIND_*` became aliases,
`templates.GRAINS` became `model.FLOW_KINDS`, `ledger.GRAIN_BUG` was deleted, and `verify/main.py`
compared a row kind against a bare `'gate'` where `ledger.KIND_GATE` already existed.

**Landed — the gate, as rows on the state census.** `tests/test_pm_flow.py` now holds a `VOCABULARIES`
table of four rows; `test_no_state_literal_survives_outside_the_seed` keeps its name and is the STATE
row, and `NoVocabularyLiteralSurvivesOutsideItsHome` is the other three, with a `CORPUS` and a
`catches()` per `tests/test_guard_corpus.py`. **What it does NOT grade is stated in the class
docstring**: a frontmatter field outside a `field_of`/`field_in`/`set_field` argument, and a row field
outside a mapping key. Those are the positions where a second spelling is SILENT; the same words
elsewhere are a git subcommand, a printed column (rule 6) and an English noun, and a census that
cannot tell them apart forces a module to lie. Probed all four by planting drift in real source: each
reports `path:line 'word'`, never a count.

**Landed — the numbers.** `127`/`126`/`124` are not one concept with `120`: the first three are the
SHELL's codes for a command that never ran (`NOT_ON_PATH`, `CANNOT_RUN`, `TIMED_OUT`), and `120` is
`git`'s timeout in SECONDS (`GIT_TIMEOUT`). Naming them is what makes that visible. The `_clip`
budgets, the census caps, the porcelain prefix and `MS_PER_SECOND` are named too.

**NOT landed — exit code `2`, 88 sites.** 28 are `return 2`, ~37 are arity or index (`len(rest) != 2`,
`seek(0, 2)`), and the rest are slices. Rule 6 already documents the exit codes and
`verify/rules.EXIT_CONFIG` is a third spelling of one of them; a real fix is ONE `EXIT_*` home that
`core/` and `repo/` can both reach, which is a module-level decision, not a rename. Named here rather
than swept badly.

**NOT landed — the `cli.py` / `model.py` split.** Deferred whole. Five features landed in `cli.py`
today and splitting two modules that are 28% of `src/` at the end of a 17-grain milestone is the grand
unification `ft-a-read-verb-is-a-declaration` warns against. Sweep 6 (one shape for a refusal) is
deferred with it: it did not fall out of the constants work.

**The archaeology finding.** 89 version references, 14 removed. The spec predicted most would be
load-bearing and that is what the reading found: a version naming a decision (`0.5.0/D6`), a
retirement a consumer's config still lists, a boundary an old pin sits on, or example data all teach
something the sentence loses without them. **Removing the 14 bare ones freed ZERO prose-census lines**
— a breadcrumb is a word inside a comment, not a comment — so sweep 4 is not a census lever, and
saying so is more useful than the deletions were.

**Dead constants, decided per constant.** DELETED: `model.ROADMAP_DOC` (nothing in `src/`, `tests/` or
`docs/` read it, and its comment claimed a recognition behaviour no code implements);
`verdict.CHECK_DISPOSITIONS` (a one-element tuple nobody read — `SKIPPED`, which the conveyor does
import, is what the comment was about); `verify/main.MAKE_PROGRAM` (a second spelling of
`rules.RUNG_PROGRAM`); `ledger.GRAIN_BUG` (a second spelling of a grain kind, read only by `report`).
KEPT, each because a test pins it as the contract and hand-copying it into the test is the second
scoreboard: `init.SEEDS` (the documented project-owned file set, read by `test_init_verb` and
`test_install`), `cli.ROADMAP_COLUMNS` (the `--help` line and the row width), `ledger.DISPOSITION_KEYS`
(the disposition row's key set), `report.CLOCK_COLUMNS` (already the named precedent). The
`ROADMAP_COLUMNS` comment claimed a single-sourcing the code does not do and now says what is true.

**The mechanical proof, and its limits.** `ast.dump` cannot be compared directly, because replacing
`'feature'` with `GRAIN_FEATURE` is exactly what changed. What was compared instead: parse the HEAD
source and the working source, strip every docstring, resolve every name in a declared roster of the
new constants to its RUNTIME value in both trees, and diff the canonical `ast.unparse`. 33 of 46
modules come back character-identical; the residual is 51 lines and every one is a constant
declaration added, a constant deleted, an import line, the `ready_for` tuple split, or one hand-edited
`cli.py` expression checked by eye. **What that proves**: each edit was a value-preserving
substitution and nothing else in the parsed tree moved. **What it does not prove**: that a constant's
VALUE is the one its reader wants (a test does that), that the 59 wrapped lines read better, or
anything about `tests/`. Comments and formatting are outside an AST comparison by construction.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_boundaries.py` — this is a source-shaped assertion and that module is the
    package's existing home for them
  what already covers this: `test_pm_flow.py::test_no_state_literal_survives_outside_the_seed` is
    ALREADY this feature for one vocabulary — state words — with a `SEED_ASSIGNMENTS` exception list.
    The kind/field/row vocabularies are rows on that harness, not a new family. That case's existence
    is also the argument: somebody already decided literals of a declared vocabulary are a defect, and
    only gated one of the four.

## Out of scope

`tests/`. The sweep is over `src/`; test modules have different economics and their cost is already
gated by `check budget`.

Renaming anything a consumer greps — output line shapes are contract (rule 6). Internal names move
freely; printed ones do not.
