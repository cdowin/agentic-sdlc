---
id: bg-prepare-default-is-invisible-to-the-seed-test
kind: bug
milestone: "ms-integrate-takes-the-whole-batch"
name: MINOR: the prepare default is invisible to the seed test
status: open
caused_by:
changelog:
---

# prepare-default-is-invisible-to-the-seed-test

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-prepare-default-is-invisible-to-the-seed-test` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR. `[integrate] prepare` has a stock default (absent = no targets), but `tests/test_config_seed.py::code_defaults` does not see it, so the seed's `# prepare = []` is not compared with the code (rule 5), and the seed test counts it as a declaration key.

## Root cause

`integrate.settings` defaults `prepare` with an `if key == PREPARE and key not in section: out.append(())` branch, not a `cfg.get(...)` read that `code_reads` finds by AST. Not verified by running: read from the source only.

## Fix

Read `prepare` through a form `code_reads` recognises (or register it in `VALUE_FROM_CODE`), and assert the seed holds `[integrate] prepare` at `[]`.
