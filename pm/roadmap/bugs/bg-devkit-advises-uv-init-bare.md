---
id: bg-devkit-advises-uv-init-bare
kind: bug
milestone: ms-the-backlog-is-empty
name: devkit advises uv init bare
status: closed
caused_by:
changelog: Makefile.devkit's missing-lock error points to agentic-sdlc init, not uv init --bare.
---

# devkit advises uv init bare

## Symptom

NIT. `installables/Makefile.devkit (the uv.lock error)`: it advises `uv init --bare`, which writes `version = "0.1.0"`. Source: 1.0.0-wheel/F6 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Point to the `init` seed instead.
