---
id: ft-a-verdict-is-the-last-line
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: a verdict is the last line
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a verdict is the last line

Three issues where the output an operator reads says less, or other, than the run did: #70, #71
and #72. All three are output-shape changes (rule 6: minor).

## Decided (do not re-plan)

- **#70 — `make check` ends on its verdict.** Today `gdk_gate` prints `[CHECK] N check(s) PASS`
  and then the `[gates] extra` targets run, so the last line is whichever extra gate ran last,
  while the exit comes from an earlier one. Change the `check` recipe in
  `repo/installables/Makefile.devkit` (and `gdk_gate.sh` if the helper lives there): run the
  devkit roster and EVERY extra gate (a failing extra does not stop the next one), then print ONE
  final line and exit on it:
  `[CHECK] FAIL — <n> of <m> gate(s) failed: <name>, <name>` or `[CHECK] PASS — <m> gate(s)`,
  where `<m>` counts `check all` as one gate plus each extra. The exit is the max over all of
  them (rule 6: 2 stays 2). Re-install here with `install-gates --force`.
- **#71 — the unowned-rows footer is a count.** `pm ledger report`'s `rows this section could not
  use` section (`repo/pm/report.py` `gate_tables`) prints ONE row: rows, kinds, branches as a
  COUNT, then `(--tree lists them)`. The per-branch list moves to `--tree`, which already prints
  unowned rows by branch; nothing is lost, it moves. Name the column order in `--help` (rule 11).
- **#72 — roadmap dirt is not hygiene dirt.** Do NOT make a belt commit: a belt writes one status
  or refuses (rules 3 and 9), and a git write is neither. The refusal NullBound hit is
  `check repo-hygiene` (stock-off, in their roster), which counts `pm/roadmap/` paths; the belts'
  `tree-clean` and `committed` steps already exclude the `[pm] root` through `_uncommitted`
  (`repo/conveyor/steps.py`). Make `repo-hygiene` use the same exclusion: paths under `[pm] root`
  print as one WARN line naming the count and the commit to run
  (`git add <root> && git commit -m "pm: …"`), and do not fail the gate. Any other dirt fails as
  today. One helper, not a second copy of the exclusion (rule 10's search, `test_boundaries`).

## Ship criterion

- A scratch tree whose second of three extra gates fails: `make check` runs the third, its last
  line is `[CHECK] FAIL — 1 of 4 gate(s) failed: <name>`, and it exits non-zero.
- `ledger report` over a milestone with unowned rows ends with a one-row count; `--tree` still
  names each branch.
- `check repo-hygiene` on a tree dirty only under `pm/roadmap/` exits 0 with one WARN line; dirt
  elsewhere exits 1.

## Proof budget

  cases: 4
  tier: unit, plus ONE shell case for the real `check` recipe
  lands in: existing Makefile.devkit / report / repo_hygiene test modules
  what already covers this: search first (rule 10); amend before adding
