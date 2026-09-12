---
id: st-the-version-file-is-claimed-when-a-milestone-starts
kind: story
feature: ft-the-gates-agree-and-a-dispatch-counts-once
milestone: "ms-the-tool-agrees-with-itself"
name: under version_at start, the version file belongs to the milestone that started
status: planning
owner:
depends_on: []
changelog:
---

# under version_at start, the version file belongs to the milestone that started

Issue: #43.

Under `version_at = "start"` a milestone claims the version file when it STARTS (the bump-at-start
commit), not when its predecessor finishes. Today `graded_release` (`pm/inventory.py:1110`) grades
against `current_milestone()`, the first entry in `order` not yet done. So the instant `release`
writes `done`, R5 wants the next milestone's version, and the shipped `ci-semver-gate.yml` refuses a
PR carrying it: *"the bump-at-start of the NEXT milestone waits until the previous close has
merged."* No value satisfies both, and `check pm` runs in the pre-push `make check`.

**The fix, as the issue proposes it:** under `start`, grade against the LAST entry in `order` whose
status is in the `in_progress` or `done` category. A `planning` (todo) milestone never claims the
file. Ask the question of the category, never of a state word (rule 9).

**Do not re-point `current_milestone()`.** `current_release()` and `release_milestone()` read it too,
and `release_milestone` decides which ledger a cost row files into (see its docstring). The change
belongs to `graded_release`'s `start` branch alone. `graded_release_accepts` then stays a one-value
answer for `start`.

## Acceptance criteria

1. With `version_at = "start"`, and milestones A (`done`) then B (`planning`) in `order`, R5 accepts
   A's version and refuses B's.
2. When B moves to an `in_progress` state, R5 accepts B's version and refuses A's.
3. With A `building` and B `planning`, R5 accepts A's version (unchanged behaviour).
4. With no entry in `in_progress` or `done`, R5 says why it has no answer, on a line. It never prints
   PASS.
5. `version_at = "ship"` is byte-identical before and after. Its existing cases pass unamended.
6. The R5 DRIFT line still names the milestone and its version, and its reason text no longer says
   "the first unshipped entry" under `start`.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1–3 | unit | parametrised walk of one `start` tree through the three states | amend the existing R5 `start` case |
| 4 | unit | all-`planning` tree | search for one first |
| 5 | unit | the existing `ship` cases, untouched | existing |
| 6 | unit | assert the DRIFT line's text in case 1 | amend |

**Deliberately-broken probe (CLAUDE.md, the ladder):** plant `done` on A with the file at B's version
in a scratch copy of a fixture, and confirm R5 FAILS.

## Semver

Minor. The R5 DRIFT line is an output shape consumers grep, and its reason text changes.

## Out of scope

The semver gate itself. It is right, and R5 moves to agree with it.
