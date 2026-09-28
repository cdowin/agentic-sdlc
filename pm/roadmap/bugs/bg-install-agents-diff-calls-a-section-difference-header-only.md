---
id: bg-install-agents-diff-calls-a-section-difference-header-only
kind: bug
milestone: 
name: install-agents --diff calls a section difference header-only
status: open
caused_by: ft-an-agent-keeps-its-project-half
changelog:
---

# install-agents-diff-calls-a-section-difference-header-only

## Symptom

For an agent whose `## Project` section differs (alone, or with its config header), `install-agents
--diff` prints `HEADER_ONLY_DIFFERS` ("differs ONLY inside its project-config header — the rest of
the file is byte-current") plus `KEPT_SECTION`. The header may be identical. Found by the 0.15.0
checkup fix pass, 2026-09-27.

## Root cause

The `--diff` branch in `repo/install.py` (the `header_only_difference` call beside `SECTION_BROKEN`)
was not moved to the three-way wording the write path got in 0.15.0 (`SECTION_ONLY_KEPT`,
`HEADER_AND_SECTION_KEPT`).

## Fix

Use the write path's choice of line in `--diff` too: section only, header and section, or header
only. Amend the existing `--diff` case with a section-only row.
