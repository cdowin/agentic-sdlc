---
id: bg-a-proof-row-names-a-case-that-proves-half
kind: bug
milestone: ms-the-rule-reaches-the-work
name: a proof row names a case that exists and proves half of what it claims
status: open
caught_in: "ms-0.4.0"
fix_milestone: ms-the-rule-reaches-the-work
caused_by:
---

# a-proof-row-names-a-case-that-proves-half

<!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it
     was found. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

## Root cause

## Fix

Several 0.4.0 review findings are proof rows naming a case that EXISTS and
proves HALF of what the row claims — the behaviour is right and covered, the
row overstates. Deferred from four records rather than fixed under a close,
because rewriting a proof table mid-close is how a review turns into a second
build phase.

Named by record and id:

  * `a-document-points-at-what-it-cannot-hold` M3 — story 02 AC1 says "a `done`
    milestone does not warn"; the case proving it has every milestone
    `building`, so the guard could be dropped and the case stays green.
  * `a-document-points-at-what-it-cannot-hold` M4 — story 01 AC4 says a header
    is "never double-headed"; the case never runs `pm new`, so the WRITER side
    is held only by a source-text grep.
  * `every-grain-is-on-a-stopwatch` M3 — nothing drives a NON-EMPTY
    `in_flight`, so `median_s`, `worst_s` and the printed line never execute.
    AC3 is proven to the depth of "the key exists".
  * `telemetry-arrives-with-the-bump` M4/M5 — the mode-2 and mode-3 rows named
    cases that could not be written against the old hermetic probe. The probe
    was replaced (8b81afc) and both cases now exist; the ROWS still describe
    the old shape.
  * `the-pooled-model` M3 — the migration story's four rows name cases that do
    not exist. No module drives `tools/dev/pm_migrate.py`, which is why its
    BLOCKER and CRITICAL shipped.
