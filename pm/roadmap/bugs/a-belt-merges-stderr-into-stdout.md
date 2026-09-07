---
id: ms-0.4.0/bugs/a-belt-merges-stderr-into-stdout
kind: bug
milestone: "ms-0.4.0"
name:
status: open
caught_in: "ms-0.4.0"
fix_milestone:
caused_by:
---

# a-belt-merges-stderr-into-stdout

<!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it
     was found. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

## Root cause

## Fix

`driver._writer` runs `pm_cli.main` with stdout and stderr merged into one
buffer and reprints it as `[<op>] write: <said>`, so `close story` and
`close feature` emit the breadcrumb INLINE on stdout — a few lines above the
belt's own `next:` list, giving one command two next-step statements.

Deferred from `every-move-breadcrumbs-the-next-step` M3. It predates 0.4.0 and
changes an output shape consumers grep (rule 6), so it is a minor bump of its
own rather than a line in a close. The CHANGELOG's claim that "STDOUT is
byte-identical" is true of `pm` and false of the belts.
