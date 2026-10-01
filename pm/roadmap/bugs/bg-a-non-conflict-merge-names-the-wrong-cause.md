---
id: bg-a-non-conflict-merge-names-the-wrong-cause
kind: bug
milestone: "ms-integrate-takes-the-whole-batch"
name: MINOR: a non-conflict merge failure names git's last line, not its cause
status: open
caused_by:
changelog:
---

# a-non-conflict-merge-names-the-wrong-cause

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-a-non-conflict-merge-names-the-wrong-cause` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR. When a lane adds a path that a prepare target wrote as an untracked file, the stop line says `git said: Merge with strategy ort failed..` — git's last stderr line, not its cause ("untracked working tree files would be overwritten"). The double period is in the output too. Probe: prepare target `gen` writes gen.txt; lane a adds gen.txt.

## Root cause

`_merge` takes `splitlines()[-1]` of stderr. For this failure, git prints the cause first and a generic line last.

## Fix

Prefer the first `error:`/`fatal:` line of stderr, else the last line; strip a trailing period before the format adds one.
