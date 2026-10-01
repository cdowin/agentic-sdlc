---
id: bg-a-slug-also-named-merge-only-is-deleted
kind: bug
milestone: "ms-integrate-takes-the-whole-batch"
name: NIT: a branch named as a slug and as merge-only is deleted
status: closed
caused_by:
changelog: integrate refuses a branch named both as a lane and as --merge-only, at exit 2.
---

# a-slug-also-named-merge-only-is-deleted

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-a-slug-also-named-merge-only-is-deleted` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

NIT. `integrate a --merge-only feat/a` is exit 0 and deletes origin feat/a, though the usage text says a merge-only branch "is never deleted". Probe: `ls-remote origin feat/a` is empty after the run.

## Root cause

`parse` does not check whether a merge-only name equals `<prefix><slug>` for a named slug; the slug path then closes and removes the lane.

## Fix

Refuse at exit 2 when a merge-only branch is also a named slug's lane, with a sentence that names both.
