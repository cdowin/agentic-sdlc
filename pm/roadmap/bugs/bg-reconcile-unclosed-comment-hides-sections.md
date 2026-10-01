---
id: bg-reconcile-unclosed-comment-hides-sections
kind: bug
milestone: "ms-the-backlog-is-empty"
name: MAJOR an unclosed comment in a reconcile record hides every later section from the gate
status: closed
caused_by:
changelog: none
---

# reconcile-unclosed-comment-hides-sections

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-reconcile-unclosed-comment-hides-sections` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MAJOR, regression and rule 4. `reconcile._sections` (src/agentic_sdlc/repo/pm/reconcile.py:72) now reads
comments through `core.markdown.uncommented`, which treats an unclosed `<!--` as a comment to the end
of the record. One `<!--` with no `-->` (for example `none changed <!-- see below`) hides `## Updated`
and `## Needs you`, so a dangling grain id under `## Updated` is no longer reported and the gate passes.
Probe: at ba76a2f `_sections` returned all three sections; at 321c49c it returns `Contracts` only.

## Root cause

The old reader used `<!--.*?-->` (DOTALL), so an unclosed opener stayed literal text. `uncommented`
keeps `in_comment` true to end of input and drops each line it covers. It does not report that.

## Fix

In `uncommented`, an opener with no `-->` before end of input opens nothing (keep it literal), or the
callers report the unclosed opener by name. Add a unit case to tests for `_sections` with an
unclosed `<!--` above `## Updated`.
