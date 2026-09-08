---
id: bg-a-proof-row-names-a-case-that-proves-half
kind: bug
milestone: ms-the-rule-reaches-the-work
name: a proof row names a case that exists and proves half of what it claims
status: closed
caused_by:
changelog: Five test cases that ran green while the property they name was deleted are amended so their setup produces the state they assert against: the `done`-milestone handoff WARN, the writer half of the retired slot header, the non-empty in-flight distribution, three unpinned numbers on the arrival pressure line, and the telemetry-live vehicle output. Each carries the guard assertion that would have caught the vacuity, and each was re-run against the mutation that proved it.
---

# a-proof-row-names-a-case-that-proves-half

## Symptom

A case exists, is named in a `## How this is proven` row, runs green, and is
cited to the orchestrator as proof the property holds — while its SETUP cannot
produce the state its assertion is about. The case is not wrong; it is
unfalsifiable. Delete the behaviour the row names and it stays green.

Measured, not read: each instance was proven by planting the drift its row
claims to catch in a scratch copy of this tree and running BOTH tiers — 1063
cases at `-m "not shell"`, 1486 across both. Every probe stayed green except
where a sibling case is named.

  1. **`tests/test_pm_gate.py::ReadyIsAStampWithACheck::test_each_warning_fires_on_the_scaffold_and_is_silent_on_a_filled_grain`**
     — story 02 AC1: *an `in_progress` milestone with no handoff warns; a `done`
     one does not.* Every milestone in the module was `building`, so nothing
     held the second half. Probe: `if m_live and not handoff.is_file():` →
     `if not handoff.is_file():` in `checks/pm.py`. 1063 passed, and 227 passed
     across the four modules that name `handoff`. The dropped narrowing is one
     WARN per historical milestone on every consumer's tree.
  2. **`tests/test_grain_shape.py::test_a_doc_opening_with_a_RETIRED_header_still_passes`**
     — story 01 AC4: a doc opening with a retired header *passes and is never
     double-headed.* The case runs only the GATE, and the gate reads
     `KNOWN_SLOT_HEADERS` independently of the WRITER, so the writer half was
     held by a source-text grep for the constant's NAME. Probe:
     `templates._header_wanted` → `got in (model.KNOWN_SLOT_HEADERS -
     model.RETIRED_SLOT_HEADERS)`, constant name intact so the grep still
     passes. 1486 passed, and `pm new milestone` then stacks a second header on
     every doc written under the old words.
  3. **`tests/test_pm_ledger_report.py::test_a_dropped_ARRIVAL_row_is_disclosed_whichever_kind_carries_it`**,
     with the golden at `test_the_seeded_ledger_produces_this_exact_json_object`
     — AC3 of `every-grain-is-on-a-stopwatch` is *median and worst
     open-duration per kind*. `in_flight` was asserted only as `[]`, over a
     fixture where every grain is closed, so `report.py`'s `median_s`,
     `worst_s` and the line rendering them never executed in either tier.
     Probes: swap `median_s`/`worst_s`; separately mangle the printed sentence.
     1486 passed on each.
  4. **`tests/test_pm_verbs.py::AnArrivalIsTheOneEvent::test_every_word_and_number_is_derived`**
     — its docstring says *every number on the pressure line traces to
     `[pm.states.*]`, to the ledger's own rows or to a frontmatter field*.
     Three did not, probed independently against `arrive.Census.line`: the age
     hardcoded to `human_duration(99999)` — 1063 passed; the wip clause deleted
     — this case passed and one sibling subtest reddened
     (`test_wip_over_the_declared_limit_is_reported_and_never_a_refusal`), so
     the ROW overstated rather than the capability being unheld; the
     `no reviewed record` clause deleted — 1063 unit AND 423 shell cases
     passed, because the only assertion on it was an `assertNotIn`.
  5. **`tests/test_conveyor_adopt.py::test_telemetry_live_names_which_of_the_three_ways_a_bump_records_nothing`**
     — proof row 2: *asserting the self-test actually RAN (its output, not a
     file read)*. Modes 2 and 3 asserted `'.PHONY'` and `'[pm.states.*]'`, both
     static literals in ONE f-string in `steps.check_telemetry_live`, so each
     assertion also passes on the other mode's answer; the vehicle's own words
     reach the detail only through `{_clip(out)}`, which nothing read. Probe:
     `{_clip(out)}` → `<redacted>`. 1486 passed.

Two instances the original record named are closed, recorded so nobody goes
looking. `the-pooled-model` M3 (four rows naming cases that did not exist) is
answered by `tests/test_pm_migrate.py`, which drives `tools/dev/pm_migrate.py`.
`telemetry-arrives-with-the-bump` M4 is a MISSING case rather than a vacuous
one and stays open: no case asserts the belt's EXIT CODE with `telemetry-live`
false — every assertion on it calls `check()`, never `adopt()`.

## Root cause

**An assertion written against the fixture that was already standing.** Every
case above reached for the tree its neighbours use — `tree()` with a
`building` milestone, the seeded ledger where everything is closed, a stub
Makefile whose recipe never runs. The assertion is then true for a reason that
has nothing to do with the behaviour: there was no `done` milestone to stay
silent about, no open grain to measure, no output to read. Rule 4's census
discipline — *a gate scanning 0 files FAILS and says so* — is stated for GATES
and was never asked of a test's own INPUTS.

**A negative assertion standing in for a derivation.** `assertNotIn`,
`assertEqual(x, [])` and `assertIn('<a substring of the line>', out)` are all
green over a code path that was DELETED. Instance 4's record clause and
instance 3's `'in_flight': []` are one defect: absence asserted with no
presence case beside it, so the emptiness is reported rather than measured.

The multiplier is the proof ROW: once it names the case, the next reader —
usually an LLM with no memory of last week — finds the case, sees it green, and
reports the property as held. Rule 4's first sin, wearing a test's name.

## Fix

Each case AMENDED, never duplicated (rule 10, *prove it once*), so its setup
produces the state and a guard assertion fails first if it ever stops.

  * `tests/test_pm_gate.py` — the milestone half of the census is a two-leg
    loop over `('building', True), ('done', False)` on trees whose handoff was
    never minted, with `assertFalse(handoff.is_file())` as the guard: with the
    file present neither leg means anything.
  * `tests/test_pm_scaffold.py::Scaffolding::test_new_mints_no_shared_doc_and_repairs_the_header_of_one_present`
    — the WRITER half, which the gate case cannot reach, lands beside the
    idempotence rows already there: every RETIRED wording written into every
    slot, `pm new milestone` run, the doc asserted BYTE-IDENTICAL. Guarded by
    `assertTrue(retired)` — an empty set would make the loop ask nothing.
  * `tests/test_pm_ledger_report.py` — the discard census and the distribution
    are one answer, so the same trees carry three OPEN stories an hour apart.
    Three is the floor that tells a median from a worst: with two,
    `found[len // 2]` and `found[-1]` are the same row. The SPACING is what is
    pinned — those ages ignore the `frozen` fixture and read the real clock.
  * `tests/test_pm_verbs.py` — the oldest grain is PLANTED `3d 5h` back and the
    line must render THAT; the wip number is bound to its word (`wip of 1`, not
    a bare `1` that is on the line anyway) with
    `assertGreater(len(open_now), cfg.wip)` as the guard; the record clause is
    asserted from both sides on two trees, the second `with_record=False`, both
    counts read off the grains rather than typed in.
  * `tests/test_conveyor_adopt.py` — the inert stub prints a marker appearing
    nowhere in the check's own sentence (`INERT_SAID`), so mode 3 asserts the
    VEHICLE's words and mode 2 asserts their absence. The two modes are told
    apart by the one part of the detail that is derived.

**No gate ships with this, and that is the finding.** The general class needs
mutation testing — plant the drift, run the tier, see what reddens — and this
suite costs 13 s narrow, 3 m 30 s wide, so a campaign over ~1500 cases is
hours, not a rung. A source-shaped scan cannot decide it either: whether a
fixture can produce a state is a question about the code under test. ONE
sub-shape IS statically decidable — a `.replace(old, new)` over a module-level
constant not containing `old`, exactly the already-fixed sixth instance
`test_a_hand_edit_reaches_what_the_cli_refused_and_the_gate_still_says_PASS`.
That scan was written and run over all 56 `.replace(` call sites in `tests/`:
ZERO survivors. Shipping it would be a guard with an empty violation corpus,
gating one spelling of six known instances while reading as though the class
were closed — this bug committing this bug. The mechanism it wants is
`ft-a-guard-declares-its-violation-corpus`, in flight in this milestone, and
`tests/test_boundaries.py` is this repo's one home for AST gates
(0.5.0/`a-lesson-surfaces-where-you-stand` M2).

## Verification

`make check`, `make unit`, `make test`. Each amended case was additionally
re-run against the probe that proved it vacuous, in a scratch copy, and now
reddens:

| case | probe | after |
|---|---|---|
| `test_each_warning_fires_on_the_scaffold_and_is_silent_on_a_filled_grain` | drop `m_live and` from the handoff WARN | FAILS at `subTest(milestone='done')` |
| `test_new_mints_no_shared_doc_and_repairs_the_header_of_one_present` | `_header_wanted` stops honouring retired wordings | FAILS, `decisions.md grew a second header` |
| `test_a_dropped_ARRIVAL_row_is_disclosed_whichever_kind_carries_it` | swap `median_s`/`worst_s`; mangle the printed line | FAILS on each, separately |
| `test_every_word_and_number_is_derived` | hardcode the age; delete the wip clause; delete the record clause | FAILS on each of the three, separately |
| `test_telemetry_live_names_which_of_the_three_ways_a_bump_records_nothing` | `{_clip(out)}` → `<redacted>` | FAILS |

Looked at versus bit: 56 `.replace(` sites scanned statically (0 survivors), 20
loops over a computed iterable in a test body (all guarded or over literal
dicts), 133 `assertNotIn` and 123 `assertFalse`/empty-collection assertions
triaged against the 0.4.0 and 0.5.0 review records, 9 review findings naming a
case by file and line followed through to the current tree. Five bit.
