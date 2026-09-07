---
id: {id}
kind: {kind}
milestone: "{milestone}"
name:
status: open
caused_by:
---

# {slug}

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> {id}` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

## Root cause

## Fix
