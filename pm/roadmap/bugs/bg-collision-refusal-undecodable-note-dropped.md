---
id: bg-collision-refusal-undecodable-note-dropped
kind: bug
milestone: "ms-the-backlog-is-empty"
name: NIT collision_refusal never names undecodable files when several collide; ruff deleted the unused note
status: open
caused_by:
changelog:
---

# collision-refusal-undecodable-note-dropped

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-collision-refusal-undecodable-note-dropped` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

NIT. `install.collision_refusal` names an undecodable file only when ONE destination collides. When several collide, the head lists them as "exist and differ" and does not say which could not be decoded. The comment above (Review I5) says "the reader is told". The ruff cleanup deleted the unused `note` variable and kept the comment.

## Root cause

The `note` string for the plural case was computed but never added to `head`, so ruff flagged it as unused (F841). The cleanup removed the dead code. It did not remove the gap.

## Fix

Add the undecodable names with UNDECODABLE_NOTE to the plural `head`, or delete the I5 claim from the comment. Add a test with two collisions, one of them undecodable.
