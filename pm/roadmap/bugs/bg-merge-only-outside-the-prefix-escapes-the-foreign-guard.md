---
id: bg-merge-only-outside-the-prefix-escapes-the-foreign-guard
kind: bug
milestone: "ms-integrate-takes-the-whole-batch"
name: MAJOR: a merge-only branch outside the agent prefix lands silently when a rerun drops it
status: open
caused_by:
changelog:
---

# merge-only-outside-the-prefix-escapes-the-foreign-guard

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-merge-only-outside-the-prefix-escapes-the-foreign-guard` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MAJOR. Run `integrate a b --merge-only art/x --batch one` red, then rerun `integrate a b --batch one`: the rerun is exit 0 and art/x lands in the base, though the command no longer names it. A dropped `--merge-only feat/x` is refused; a dropped `art/x` is not. Probe: scratch test over `tests/test_integrate.py` helpers, RUN2 exit 0, art.txt in the base.

## Root cause

`_refuse_foreign` (src/agentic_sdlc/repo/integrate.py) matches only `integrate <batch>: merge <prefix><slug>` subjects. A merge-only branch outside the prefix is merged with subject `merge art/x`, so the guard never sees it.

## Fix

Match every `integrate <batch>: merge <ref>` subject, and compare against the prefixed slugs plus the merge-only names. Add the rerun case to the merge-only test.
