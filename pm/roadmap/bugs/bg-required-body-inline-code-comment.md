---
id: bg-required-body-inline-code-comment
kind: bug
milestone: 
name: required body inline code comment
status: open
caused_by:
changelog:
---

# required body inline code comment

## Symptom

MINOR. `repo/pm/required.py::_body`: a `<!--` in inline code opens a comment, so a filled line reads missing. Source: 0.17.0-pm-lanes/F2 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Skip comment markers inside backtick spans.
