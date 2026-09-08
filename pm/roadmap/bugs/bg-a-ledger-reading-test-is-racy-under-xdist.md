---
id: bg-a-ledger-reading-test-is-racy-under-xdist
milestone: 
name: a ledger-reading test is racy under xdist
status: open
severity: low
kind: bug
---

# a ledger-reading test is racy under xdist

`tests/test_makefile_gates.py::test_a_real_composition_run_files_one_row_per_slot_and_one_of_its_own@the-real-repo`
failed once during 0.3.0's close and passed on the immediate re-run, with no
change between them.

It spawns a real `make` composition against THIS repo and then reads the rows it
filed. Under `-n auto`, other cases are appending to the same ledger at the same
time, so "one row per slot" is asserted over a file another worker is writing.
`--dist loadgroup` serialises the cases that spawn `make` against each other; it
does not serialise them against every case that files a row.

**A flaky test is a finding**, and this one is in the worst family for it: the
gate that would catch a real regression here is the one whose failure a reader
learns to re-run.

## Fix

Either give the case its own scratch tree rather than the real repo, or give the
ledger row it asserts on a marker only this case writes so a neighbour's row
cannot be mistaken for it. The first is likely right — a case that reads the
real repo's ledger has a shared mutable dependency by construction.

## Verified when

The case is repeated N times under `make test` and passes every time, or it no
longer reads a ledger another worker can write.
