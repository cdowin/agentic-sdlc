---
id: bg-install-carry-drops-an-indented-line-after-a-retired-name
kind: bug
milestone: "ms-the-open-issues-close"
name: MINOR install --force drops an indented line that follows a retired name
status: open
caused_by:
changelog:
---

# install-carry-drops-an-indented-line-after-a-retired-name

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-install-carry-drops-an-indented-line-after-a-retired-name` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR. A header `OLD=1` followed by `  PROTECTED_BRANCHES="$PROTECTED_BRANCHES dev"` loses BOTH lines on `install --force` when the packaged file does not mention `OLD`: a live setting is deleted.

## Root cause

`_CONTINUES` (`^(?:[ \t]+\S|\))`) in install.py attaches ANY indented line after a declaration as its continuation, not only the items of an open `NAME=(` array.

## Fix

Treat an indented line as a continuation only while the declaration opened `(` and no `)` has closed it.
