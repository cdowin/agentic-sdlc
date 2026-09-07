---
id: ft-the-vocabulary-is-constants-not-literals
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: the vocabulary is constants, not literals
status: planning
reviewed:
depends_on: []
consumed_by: []
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
