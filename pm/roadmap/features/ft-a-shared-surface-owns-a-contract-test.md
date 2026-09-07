---
id: ft-a-shared-surface-owns-a-contract-test
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: a shared surface owns a contract test
status: reviewing
reviewed: docs/reviews/2026-09-07-0.6.0-a-shared-surface-owns-a-contract-test.md
depends_on: []
consumed_by: []
changelog: A `tests/test_contracts.py` registry names every shared vocabulary in the package — `ledger.ROW_KEYS`, `EVENT_KEYS`, `changelog.COLUMNS`, `cli.LIST_COLUMNS`, `model.BINDS_TO` — and round-trips each from its writer to its reader, so a key one side adds and the other never learns fails at the boundary instead of in a table somebody reads next month. A surface with no case is named.
---

# a shared surface owns a contract test

**Four of 0.5.0's blocking findings were one shape: a new WRITER met an old READER, both halves
individually correct, and no test of either could fail.** `developer.md` gained a checklist item
asking builders to enumerate readers. A checklist is a reminder; the suite is the enforcement.

## The shape, from the one that got furthest

`lessons.FIELDS` spelled its timestamp `'at'`. Every reader keyed `'ts'`. Neither spelling is wrong
to a string, so:

- the writer's own tests passed — it wrote what it declared
- the reader's own tests passed — it read what it declared
- **every lesson row sorted to the beginning of time**, and nothing said so

It survived until a reviewer read both files side by side. What closed it was
`test_the_help_names_its_columns_in_order_and_the_reader_agrees` — a test that binds the DECLARATION
to the READER rather than testing either alone. That case is the shape this feature generalises.

## What a shared surface is

A constant declaring a vocabulary that one module WRITES and another READS: `ledger.ROW_KEYS`,
`report`'s column tuples, `changelog.COLUMNS`, `cli.LIST_COLUMNS`, `verdict`'s disposition grammar,
`model.BINDS_TO`. Each is a contract between two files, and today each is held by whichever test its
author happened to write.

**A round-trip is the cheapest thing that can fail here**: write through the writer, read through the
reader, assert the value survives with its key intact. It costs a function call, and it is the exact
assertion neither half's own tests make.

## The relationship to `ft-a-guard-declares-its-violation-corpus`

Sibling, not duplicate. That feature asks *"can this guard still catch the thing it exists for"* —
about SOURCE-SHAPED guards. This asks *"do these two modules still agree about a key"* — about DATA
crossing a boundary. **They must not grow two registries.** Whichever lands first owns the mechanism
for declaring a checked thing, and the second declares into it.

## Ship criterion

Every shared surface in this package is named in one place, and each has a round-trip case binding
its writer to its reader — planted a disagreeing key, the case FAILS.

A surface named with no case is a NAMED line, never silence (rule 11); a case naming no surface is a
finding, because that is the registry going stale in the direction nobody looks.

The `at`/`ts` defect is the regression case, replanted: change the writer's spelling and the
round-trip goes red.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_contracts.py` (new) — the surfaces span `pm/`, `conveyor/` and `checks/`, so
    landing per-module would recreate the scatter this feature exists to end
  what already covers this: `test_cli_surface.py::test_the_help_names_its_columns_in_order_and_the_
    reader_agrees` is ALREADY this feature for one surface. Generalising that one case rather than
    inventing a family is the whole feature, and its existence is the argument that the shape works.

## Out of scope

Inventing new shared surfaces, or consolidating existing ones — that is
`ft-a-read-verb-is-a-declaration`'s work. This one only holds what already exists to itself.
