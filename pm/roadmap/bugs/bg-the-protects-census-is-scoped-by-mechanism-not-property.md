---
id: bg-the-protects-census-is-scoped-by-mechanism-not-property
kind: bug
milestone:
name: a source-shaped guard that greps instead of parsing declares no PROTECTS and nothing notices
status: open
caused_by: ft-the-suite-is-measured-like-the-source
---

# the PROTECTS census is scoped by mechanism, not by property

Found by the 0.7.0 milestone review (R5), shown failing both ways. `caused_by:` names the feature
that built the census — it met its own ship criterion for the mechanism and not for the property.

## Symptom

`tests/test_guard_corpus.py:96` defines a source-shaped guard as one that **calls `ast.parse`**. A
guard that grades the same class of fact by string containment declares nothing and nothing notices:

    a planted class using ast.parse        →  FAILS: "ProbeGuardWithNoProtects: declares no PROTECTS"
    the SAME class using assertIn(…, text) →  PASSES

Two live examples sit in the canonical guard module, both unmistakably source-shaped and neither
priced:

    tests/test_boundaries.py:1390  TheResolversCollapsed
                                   asserts twelve names are absent from the grain layer's source
    tests/test_boundaries.py:1445  OneRuleRoutesALedgerRow
                                   asserts `_building_ledger_dir` is in no source file, with its
                                   own MIN_SOURCES floor

## Root cause

**The census asks HOW a guard reads, not WHAT it grades.** `ast.parse` was the cheapest derivable
proxy for "this guard polices our own source" and it is a good one — 39 guards answer to it — but a
proxy is not the property, and the two that escape are the two that read source as text.

The feature's ship criterion says *"the source-shaped guards are a named set that says what each
protects"*. The set is named, derived from source, and empty-offender-list gated for what it
covers. What it covers is the mechanism.

Not a blocker and no behaviour: both escapees are real guards doing real work, one with its own
zero-census floor. The finding is that the roster cannot see them, so nobody has judged whether
either is load-bearing or a second scoreboard — the question the whole census exists to ask.

## Fix

Widen the classifier from "calls `ast.parse`" to "reads another module's source", which is what
both escapees do: a guard that opens a `.py` path, or reads one through `_sources()`/`walk`, and
asserts about its text. The two named above then arrive on the roster as undeclared and get their
`PROTECTS` written, which is the same shape the original 39 went through.

**The widening is a finding, not a silent change** — `st-a-source-shaped-guard-names-what-it-protects`
gotcha 3 says the census's limits are stated and must not be quietly widened, so this lands with
the new count and the argument beside it.

## How to see it fail

The probe above IS the case: a planted class that greps source and declares no `PROTECTS` must
fail. It passes today.

## Out of scope

Judging the two escapees. That is the work the widening unblocks, and it belongs to whoever writes
their `PROTECTS` — a judgement in writing, never a test.

A guard that greps a SHIPPED file rather than a module's source (`test_install.py`'s family). That
is outside the population by the census's own stated limit and the limit is deliberate.
