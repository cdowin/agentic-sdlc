---
id: bg-init-diff-omits-inputs-ignore
kind: bug
milestone: "ms-the-loop-proves-itself"
name: init --diff omits the verify-inputs ignore line
status: open
caused_by:
changelog:
---

# init-diff-omits-inputs-ignore

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-init-diff-omits-inputs-ignore` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR: `init --diff` on a tree whose .gitignore has `pm/roadmap/ledger.local.jsonl` but not `pm/roadmap/verify-inputs.local.json` prints `already ignores pm/roadmap/ledger.local.jsonl` and says nothing about the second line, yet a real `init` appends it. A preview that omits a write.

## Root cause

`init._diff` (src/agentic_sdlc/repo/init.py ~line 336) still calls `skills.local_ignore_line` (one line); the writer `install_local_ignore` now uses `local_ignore_lines` (two).

## Fix

Iterate `skills.local_ignore_lines(...)` in `_diff` and print one line per entry; extend the init --diff test with a tree that has only the ledger line.
