---
id: bg-the-ready-breadcrumb-says-ready-where-the-edge-does-not
kind: bug
milestone: "ms-a-consumer-can-take-the-bump"
name: the arrival ready line says READY where ready-for says NOT READY
status: open
caused_by:
changelog:
---

# the arrival's ready line says READY where ready-for says NOT READY

From the shipped-words review, S12 (`docs/reviews/2026-09-11-0.8.0-the-shipped-words-match-the-shipped-tool.md`).

## Symptom

With `bg-bone` open under `ms-alpha`, `pm feature done ft-fone --review-record …` printed
`ready: agentic-sdlc release 0.1.0 — this write made ms-alpha READY (every feature is in done: 1 of 1)`.
At the same time, `pm ready-for milestone ms-alpha` said NOT READY (exit 1), and `release` refused at
`features-done`.

## Root cause

`pm/arrive.py:359-385`, present since `9d3165b` (0.5.0). `crossing` reads same-kind siblings only,
so an open BUG under the milestone is invisible to it. **This is rule 4's first sin in a breadcrumb:**
a READY printed while the edge says NOT READY.

## Fix

The `ready:` line asks the parent's own `ready-for` predicate, the one the belt's entry edge uses,
and prints only when that says READY. Never a second, narrower reading.
