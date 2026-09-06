---
id: 0.4.0/bugs/a-second-gate-in-one-checkout-loses-a-cost-row
milestone: "0.4.0"
name: A second gate run in one checkout loses a cost row
status: fixed
caught_in: "0.4.0"
fix_milestone:
caused_by:
---

# a-second-gate-in-one-checkout-loses-a-cost-row

<!-- A bug lives in the milestone that will FIX it; `caught_in:` keeps where it
     was found. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

A gate runs, passes, prints its verdict line — and files no `gate` row. Silent:
the verdict is on screen and `verify --plan` says `unknown` for that rung.

Caught by the `0.4.0/one-rule-routes-a-row` feature reviewer, whose first
`make test` in the worktree failed at
`test_makefile_gates.py::test_a_real_composition_run_files_one_row_per_slot_and_one_of_its_own@the-real-repo`
with the `check` cost row missing while `check` itself passed. Reproducible
whenever anything else runs a gate in the same checkout at the same time —
which is every session where an agent and a reviewer share one tree.

## Root cause

`_gdk_ledger_sidecar` named the start-time file from the LOG PATH alone
(`.gate-reports/.check.log.gdkms`), and every concurrent run of one gate in a
checkout shares that path. So the second run's `_gdk_ledger_open` overwrote the
first's start time, and the first run's `_gdk_ledger_close` unlinked the file —
leaving the second with no sidecar and therefore no row.

Every path through the ledger code returns 0 by design (a row that cannot be
written must never fail a gate), which is why it was silent.

## Fix

`tools/dev/gdk_gate.sh` (source: `installables/gdk_gate.sh`) — the sidecar is
keyed by `$$` as well as by log path. `open` and `close` are both called from
the sourcing shell (`gdk_gate_log`, `gdk_gate_verdict`), so the pair always
agree, and two concurrent runs no longer share a file.

**What is NOT fixed, stated rather than left to be rediscovered:** the report
directory is cleared per run and the transcript files collide the same way, so
a run that clears `.gate-reports/` while another holds a sidecar there still
costs that one its row. Both want a per-run directory. That is a bigger change
than one lost row justifies today, and it is the shape to reach for if this
recurs.
