---
id: bg-a-belt-merges-stderr-into-stdout
kind: bug
milestone: ms-the-backlog-is-empty
name: driver._writer merges stdout and stderr, so a stderr-only message is invisible
status: closed
caused_by:
changelog: none
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

## Disposition

OBE at 2.4.0: the close belts and arrival breadcrumbs it named were cut in 2.0.0. The one surviving merge, `belts.py::_write`, carries only release's single labelled `[release] write:` line.
