---
id: bg-a-belt-merges-stderr-into-stdout
kind: bug
milestone: 
name: driver._writer merges stdout and stderr, so a stderr-only message is invisible
status: open
caused_by:
---

# a-belt-merges-stderr-into-stdout

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
