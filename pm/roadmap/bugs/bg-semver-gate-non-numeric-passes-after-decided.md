---
id: bg-semver-gate-non-numeric-passes-after-decided
kind: bug
milestone: "ms-the-backlog-is-empty"
name: MINOR semver gate passes a non-numeric PR version such as 3.x once an earlier component decides
status: closed
caused_by:
changelog: none
---

# semver-gate-non-numeric-passes-after-decided

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-semver-gate-non-numeric-passes-after-decided` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR. The Compare step passes PR=3.x against MAIN=2.4.0 (exit 0), and PR=2.5.0rc1 against 2.4.0. The comment says "non-numeric refuses" and the error says "Versions are dotted integers only". After 3.x merges, each later PR such as 3.1 refuses on main's non-numeric component.

## Root cause

The non-numeric `case` check runs inside the compare loop. The loop breaks at the first component that differs, so later components are never checked.

## Fix

Check every component of both PR_PARTS and MAIN_PARTS for non-numeric text before the compare loop. Add 3.x vs 2.4.0 to the refusal cases in tests/test_ci_compare_step.py.
