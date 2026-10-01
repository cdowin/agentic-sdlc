---
id: bg-builder-check-line-close-nudge
kind: bug
milestone: ms-the-backlog-is-empty
name: builder check line close nudge
status: closed
caused_by:
changelog: The [CHECK] lines no longer tell a builder to close its story; the integrator closes.
---

# builder check line close nudge

## Symptom

NIT. `installables/Makefile.devkit::check`: a builder's `[CHECK]` line nudges it to run `pm story done`, the integrator's job. Source: 1.0.0-close-now/F3 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Drop the clause in builder context.
