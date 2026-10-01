---
id: bg-verify-inputs-lost-update
kind: bug
milestone: "ms-the-loop-proves-itself"
name: verify-inputs sidecar lost update under parallel runs
status: closed
caused_by:
changelog: none
---

# verify-inputs-lost-update

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-verify-inputs-lost-update` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR: two `verify` runs in one checkout (e.g. `--spot` and a milestone rung, or two gates) that PASS close together can lose one entry of `verify-inputs.local.json`; the older entry for that rung stays, so the next miss prints `changed:`/`added:` lines against a stale PASS — false lines, not a missing one. Found by reading, not probed.

## Root cause

`cache._keep_inputs` is read-modify-write (`_read_inputs`, update one key, temp+rename) with no lock; the rename is atomic but the read is not tied to it.

## Fix

Re-read and merge immediately before the rename and accept the race, or keep one file per rung+target key (no shared read-modify-write). Document the residual race either way.
