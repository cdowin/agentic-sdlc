---
id: bg-adopt-absent-every-installer
kind: bug
milestone: "ms-the-loop-proves-itself"
name: adopt absent fails a consumer that skips an installer
status: closed
caused_by:
changelog: adopt prints one not taken: line for an installer a project never ran, instead of failing on each of its files.
---

# adopt-absent-every-installer

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-adopt-absent-every-installer` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR: `adopt` now exits 1 for a consumer that skips an installer on purpose (e.g. a GitLab project without `install-ci`): `[adopt] absent: .github/workflows/verify.yml` (and semver-gate.yml, auto-tag.yml). Probe confirmed on a scratch consumer after `init` with the workflows removed. Before this batch the same tree passed adopt.

## Root cause

`belts._absent` treats every destination of every plan in `_every_plan()` as required. The only escape is `[adopt] ours`, whose meaning is 'the project owns this file', not 'this project does not take this installer' — so the tool decides which installers a project must run (rule 9).

## Fix

Name absence per installer the consumer took (e.g. an installer counts as taken when any of its destinations exists, and only its missing siblings are `absent:`), or add an explicit declared opt-out instead of overloading `ours`.
