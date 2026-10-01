---
id: bg-the-seed-census-cannot-read-a-per-kind-table
kind: bug
milestone: ms-the-backlog-is-empty
name: the seed census cannot read a per-kind table
status: closed
caused_by: ft-a-template-grows-without-a-fork
changelog: none
---

# the-seed-census-cannot-read-a-per-kind-table

## Symptom

`tests/test_config_seed.py` checks `[pm.templates.<kind>] extra_sections` through a hand-written
`PER_KIND_READS` table, not through `COERCERS`. Adding `kind_tables` to `COERCERS` fails the census
with a KeyError on `('pm', 'templates')`. Found by the 0.15.0 checkup (N2), 2026-09-27.

## Root cause

`kind_tables`' fourth argument is the kind list, not a fallback, so the census's model (one
coercer call, one default) does not fit a computed section name.

## Fix

Teach the census one shape for a per-kind table: expand the section over its kind list and ask the
code's reader for each default, then retire `PER_KIND_READS`. A planted drift in one kind must
still fail by name.
