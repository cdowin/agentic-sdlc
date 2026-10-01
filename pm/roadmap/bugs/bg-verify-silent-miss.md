---
id: bg-verify-silent-miss
kind: bug
milestone: "ms-the-loop-proves-itself"
name: verify miss with no moved input prints nothing
status: open
caused_by:
changelog:
---

# verify-silent-miss

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-verify-silent-miss` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

NIT: a cache miss whose cause is not a file (HEAD moved with identical content, `environment`, scope, or the `moves_out` choice) prints no line at all, and a static gate (`inputs_state`) never keeps input digests, so its misses are always silent. Rule 11: absence is a finding.

## Root cause

`miss_lines` diffs only per-path digests; `State.input_digests` is filled only by `_state_of`; `inputs_state` leaves it ().

## Fix

When `miss_lines` finds no path change but a prior entry exists, print one line naming that the key moved for a non-file reason; or record the key's non-file parts beside the digests.
