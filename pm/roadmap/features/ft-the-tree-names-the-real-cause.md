---
id: ft-the-tree-names-the-real-cause
kind: feature
milestone: "ms-the-mistake-surfaces-where-it-is-made"
name: the tree names the real cause
status: done
reviewed: docs/reviews/2026-09-29-0.17.0-real-cause.md
depends_on: []
consumed_by: []
changelog: `pm new` on a nested tree places each child under its parent directory or refuses by name and never writes a pool; `check pm` names a tree holding both layouts; R5 names a versioned milestone on no plan with its `pm add roadmap` fix; and `release` asks its gate with the milestone at `done` (restored after, and named on the gate line), so a check only a closed milestone trips fails before the write — a gate that asserts a clean working tree now fails during `release`, and a `make milestone` green recorded at `building` is not reused by `release`.
---

# the tree names the real cause

Issues: #84, #87, #88.

Three places where the tree let a mistake through and a later step blamed the wrong thing.
`pm new feature` on a nested tree wrote a flat `features/` dir and every read then found no
milestone. R5 blamed the version when the real cause was a milestone on no plan. `release` wrote
`done` and the next `make check` failed a cap on the same tree.

## Decided (do not re-plan)

- **#84 — a nested tree never gets a pool.** In `repo/pm/inventory.py::mint_dir`, the nested
  branch never falls back to `pool_dir`: when the parent does not resolve to a grain directory,
  `pm new` refuses at exit 2 and writes nothing, naming the layout (`this tree is nested; …`)
  and the parent it could not place under. `pm new milestone` on a nested tree mints the
  directory in the siblings' shape or refuses by name; the developer picks whichever the nested
  reader already reads, and a round trip (`new milestone` → `new feature` → `pm status`) proves
  it. A `check pm` finding (FAIL) names a tree holding both a pool and milestone directories.
  Fixture: a scratch copy of a nested fixture under `tests/fixtures/`, never written in place.
- **#88 — R5 names the plan.** When the version file matches a milestone that is on no plan,
  R5's line names that milestone, its status and the fix: `version '0.16.0' is claimed by ms-…
  (building), which is on no plan — pm add roadmap ms-…`. The drift is still a finding. And
  `pm new milestone … --version <v>` prints `next: pm add roadmap <id>` when the milestone is
  not in `order:` (it does not sequence it: authoring and scheduling stay separate acts).
- **#87 — reproduce first.** `release` ran its `gate` check (`make milestone`) and passed, and
  the next `make check` failed on the same tree. Find which: (a) the gate reused a verdict
  recorded before the tree moved, (b) the belt's own write moved the tree past what the gate saw,
  or (c) the consumer's `make milestone` does not include `make check`. Fix (a) or (b) in the belt.
  For (c), the tool cannot know (rule 8/9): `release`'s `next:` list names `make check` before
  the push, and the issue closes with that finding. Record which one with `pm decide`.

## Ship criterion

- The #84 replay on a nested fixture copy exits 2 at `new feature` and `pm status` still reads
  every milestone.
- The #88 replay prints the named-milestone R5 line.
- #87's cause is recorded, and a replay of it no longer writes `done` over a failing tree (or
  prints the `next:` line, for cause c).

## Proof budget

  cases: 2 for #84 (refusal, mixed-layout finding), 1 for R5 wording, 1 for the next: line, #87 per its cause
  tier: temp tree (pm writes) — integration only where the belt spawns
  lands in: tests for pm/inventory.py, checks/pm.py, conveyor
  what already covers this: nested read cases and the R5 drift case; none write into a nested tree.
