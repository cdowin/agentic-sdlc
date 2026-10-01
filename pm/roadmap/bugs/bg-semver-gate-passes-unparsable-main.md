---
id: bg-semver-gate-passes-unparsable-main
kind: bug
milestone: "ms-the-backlog-is-empty"
name: MAJOR semver gate passes every PR when main version file exists but VERSION_PATTERN matches nothing
status: open
caused_by:
changelog:
---

# semver-gate-passes-unparsable-main

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-semver-gate-passes-unparsable-main` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MAJOR. `installables/ci-semver-gate.yml` (and `.github/workflows/semver-gate.yml`) exits 0 with a warning when main HAS the version file but VERSION_PATTERN matches no line in it (for example a dynamic version, or a changed format). Probe: the Compare step body with PR=2.4.0, MAIN='' exits 0. Pre-existing before this range; the range rewrote this gate and kept it.

## Root cause

The Extract step runs `git show origin/main:$VERSION_FILE 2>/dev/null | read_version`. A missing file and an unmatched pattern both give an empty MAIN_VERSION. The Compare step reads every empty MAIN as "first versioned merge".

## Fix

In Extract, test `git cat-file -e origin/main:$VERSION_FILE` first. Allow with the warning only when the file is absent. When the file exists and the pattern matches nothing, write an ::error:: that names the file and pattern, and exit 1. Add a case to tests/test_ci_compare_step.py that fails before the fix.
