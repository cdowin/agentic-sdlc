---
id: bg-two-names-for-one-shared-doc-location
kind: bug
milestone: 
name: slot_paths and shared_doc both answer where a shared doc lives
status: open
caught_in: "ms-0.4.0"
fix_milestone:
caused_by:
---

# two-names-for-one-shared-doc-location

<!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it
     was found. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

## Root cause

## Fix

`templates.slot_paths` and `model.shared_doc` both answer "where does this
grain's decisions/handoff/review doc live". They agree today and
`test_pm_scaffold` fails the day they do not, so this is a duplication to
collapse rather than a wrong answer — deferred from
`a-document-points-at-what-it-cannot-hold` M2.

The collapse is one function; the care is that `slot_paths` returns a MAP of
slot to path and `shared_doc` answers for one slot, so the caller shapes
differ.
