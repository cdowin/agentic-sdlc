---
id: bg-a-bare-filename-is-not-checked-as-a-path
kind: bug
milestone: 
name:
status: open
caused_by:
changelog: none
---

# a bare filename in a backtick span is never checked as a path

**Found at 0.6.0's close, by grep, after `check doc` had been green all day.** Three always-loaded
surfaces carried a reference to `CHANGELOG.md` — a file deleted earlier in the same milestone — and
the gate whose job is *"a dead path in a backtick span is a finding"* said nothing about any of them.

## Symptom

`src/agentic_sdlc/repo/checks/doc.py::check_backtick_paths`:

    span = match.group(1)
    if '/' not in span or any(ch in span for ch in PLACEHOLDER_CHARS):
        continue

**A span with no `/` is skipped.** So `` `CHANGELOG.md` `` is not a path claim to this gate, while
`` `docs/CHANGELOG.md` `` is. The three that survived:

  * `SDLC.md` — *"README / CHANGELOG wording is returned as PROPOSED text"*
  * `README.md` — *"bump `DEVKIT_VERSION` in your Makefile, read the CHANGELOG"*
  * `.claude/skills/release/SKILL.md` — *"retitle the changelog's `## Unreleased`"* (twice)

All three named a step an operator would try to perform and could not.

## Root cause

The `/` test is a cheapness heuristic standing in for *"does this look like a path"*, and it is the
wrong one. `PATH_CANDIDATE` — the regex immediately below it — **already** decides that properly: it
requires a known extension (`.gd|.tscn|.tres|.py|.sh|.md`). The `/` guard is redundant with it in one
direction and wrong in the other: it excludes exactly the repo-root files that are most likely to be
cited in always-loaded prose, which is `[doc] scope`'s whole population.

## Fix

Drop the `'/' not in span` clause and let `PATH_CANDIDATE` decide. The placeholder guard stays.

Expect a first run to find more than three — `CLAUDE.md`, `README.md`, `Makefile.tiers` and friends
are cited constantly and have never been graded. Each is either real, or a finding this gate should
have been making all along.

**One risk to check before landing, not after:** a backtick span that ends in a listed extension but
is not a path — a wildcard like `*.md` (already excluded by `PLACEHOLDER_CHARS`), or prose quoting a
filename that deliberately does not exist. `<!-- doc-scan:allow -->` is the escape and it exists; the
question is only how many legitimate citations need it, and that number is the argument for or
against this change.

## Verification

The three sentences above, replanted, and asserted to FAIL. `tests/test_check_doc.py` landed in
0.6.0 and is the home — the module exists now, which it did not when this gap was created.
