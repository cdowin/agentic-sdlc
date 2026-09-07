---
id: ft-a-read-verb-is-a-declaration
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: a read verb is a declaration
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# a read verb is a declaration

**The belts are already the model. The read verbs never got there.**

A belt is a declaration: `[<belt>] steps` names its checks, `[<belt>] commands` says what each runs,
`[<belt>] skippable` says which may be dispositioned, and the belt writes ONE key. Adding a check is a
config line and a predicate. That half of the engine is exactly what this package says it is — key,
value, derivation.

A read verb is a module. `pm list`, `pm status`, `pm roadmap`, `pm next`, `pm ledger report`,
`lesson show` and the proposed `changelog` all do the same three things — walk a grain set, pull a
key, render columns — and each one hand-rolls all three.

## Measured, not asserted

    column declarations   9 sites across 3 modules; every read verb spells its own
    pointer resolvers     3 — cli._resolve_record, lessons._source_file, steps._record_of
                          and model._pointer_escapes is used by two of them, not the third
    ledger enumeration    3 spellings this morning, 2 after a consolidation mid-milestone

**0.5.0's findings are instances of this, not coincidences beside it:**

- `F1 MAJOR` — `lesson --source` accepts a path outside the checkout, landing verbatim in an
  append-only row. Cause: it uses the pointer resolver that lacks the escape check, while its sibling
  three files away has one.
- `T3 MINOR` — `CLOCK_COLUMNS` is dead and `--help` never names the columns, which the criterion
  explicitly requires. Cause: nothing binds a verb's columns to its help; each verb is asked to
  remember, and rule 11's read side is a convention rather than a mechanism.
- `M3 / m1 MINOR` — the same ledger walk written three times, found twice in one milestone.

Rule 11 says *if you cannot pipe it, the missing thing is a COLUMN, never a verb.* That is the right
rule, and today it is enforced nine times by hand.

## The shape

One collect-and-render primitive, and a read verb declares against it:

    over      which grains — a pool, a parent's `order:`, a ledger, a rev range
    key       the field or row kind being pulled
    columns   named once, in order

**`--help` and the renderer read the SAME declaration**, so a column that exists and is unnamed
becomes impossible rather than discouraged. `--json` falls out of the same list. A new read verb
becomes a declaration plus whatever derivation it genuinely needs, instead of a module that
re-implements the walk.

One pointer resolver, with the escape check inside it, so `--source`, `--review-record` and every
future pointer are refused the same way for the same reason.

## What this is NOT

**Not verbs declared in `devkit.toml`.** A consumer declaring their own read verbs is a plugin system,
and D1 rejected that for this package: the tool would have to resolve a declaration to a callable, and
hard rule 2 says it boots nothing. The declaration is INTERNAL — how this package spells its own
verbs, so they cannot disagree.

**Not a rewrite.** The three consolidations above are each independently landable and each has a 0.5.0
finding as its test case. If only the pointer resolver lands, F1's class is closed and the milestone
still profited. A grand unification attempted in one pass is how a framework acquires a second
scoreboard with better branding.

## Ship criterion

One pointer resolver in the package; `_source_file` and `_record_of` are gone and every caller refuses
an escaping pointer identically. A test plants `../outside.md` and an absolute path against every verb
that takes a pointer.

A read verb's columns are declared once, and `--help` renders from that declaration — a test asserts
every read verb's help names its columns in the order it prints them, by reading the declaration
rather than a copy.

At least `pm list`, `pm roadmap` and `changelog` collect through one primitive, and adding a column to
any of them is one edit.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: `tests/test_cli_surface.py` (the columns-vs-help binding already has a case shape there
    from T3's fix) and `tests/test_pm_verbs.py`
  what already covers this: `test_cli_surface.py` already reads `report.CLOCK_COLUMNS` out of the
    source to check the help — that assertion generalises to every verb rather than being written per
    verb, which is the feature in one sentence.

## Out of scope

The belts, which are already declarative, and `verify`, which shells out to a make target — the one
place this package deliberately boots something, and the one verb that is not a collect.
