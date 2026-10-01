---
id: bg-required-fill-before-render
kind: bug
milestone: ms-the-backlog-is-empty
name: required fill before render
status: closed
caused_by:
changelog: none
---

# required fill before render

## Symptom

NIT. `repo/pm/templates/__init__.py::load`: `required.fill` runs before `render`, so a prefix containing `{id}` gets substituted. Source: 0.17.0-pm-lanes/F4 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Fill after render.
