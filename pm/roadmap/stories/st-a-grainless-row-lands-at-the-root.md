---
id: st-a-grainless-row-lands-at-the-root
feature: ft-one-rule-routes-a-row
milestone: "ms-0.4.0"
name: A row naming no grain lands in the root ledger
status: done
owner: claude
depends_on: ["st-routing-asks-the-grain-not-the-tree"]
kind: story
---

# A row naming no grain lands in the root ledger

<!-- What is observable when this ships. A story is an observation, not a task. -->

`pm/roadmap/ledger.jsonl` exists and holds every row that names no grain — a `gate` row, a session
nobody could attribute, a hand entry with no `--grain`. `pm ledger report` reads it and shows those
rows in the `rows naming no grain` bucket it already prints.

Story 01 made every *attributed* row route by its grain. This one gives the rest a home instead of
a refusal, so that after these two stories **no telemetry write is ever refused for want of a
place to put it** (D3).

## Why a root file and not a per-feature one

Recorded because it will be re-proposed. A row already names its feature in `grain:`; a per-feature
ledger adds a "which file" question without adding information, multiplies the walk `ledger report`
performs, and answers with storage what `pm ledger show <feature-id>` already answers with a query.
D3 carries the full argument. **If the reader of this story wants per-feature spend, the verb for
it exists.**

## The trap: `merge=union` does not cover the root file

`skills.py:56` builds the gitattributes pattern:

```python
return f'{cfg.roadmap_dir}/*/{ledger.LEDGER_FILE_NAME}'      # pm/roadmap/*/ledger.jsonl
```

`pm/roadmap/ledger.jsonl` is **one directory level short of that glob** and will not match. Without
a second pattern the root ledger conflicts on every parallel branch that appends to it — which is
every branch, since this is where unattributed rows go. It fails quietly, as a merge conflict
nobody connects to this change, on somebody else's branch, later.

`skills.py` is also what WRITES `.gitattributes` into a consumer, so the fix has to travel: a
consumer that bumps gets the root-ledger pattern, or it gets the conflicts.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/ledger.py` — a root-ledger path helper beside `ledger_path`. It takes
  the roadmap dir where `ledger_path` takes a milestone dir; **if it ends up a one-line
  re-spelling of `ledger_path`, use `ledger_path` and pass the roadmap dir** — a second name for
  one fact is what this milestone deletes.
- `src/agentic_sdlc/repo/pm/cli.py` — the grain-less branch of the three call sites; `ledger show`
  and `ledger report` read the root file.
- `src/agentic_sdlc/repo/pm/skills.py` — the gitattributes pattern(s), and the header comment that
  explains why the ledger is `merge=union`.
- `src/agentic_sdlc/repo/pm/report.py` — the `rows naming no grain` section reads the root file.
- `tests/test_pm_ledger_record.py`, `tests/test_pm_ledger_report_sections.py`,
  `tests/test_pm_scaffold.py` (whichever asserts the gitattributes write).

## Files it must stay out of

`tools/hooks/**` and everything in `every-row-names-its-grain`. `model.py` — nothing here needs a
new resolver.

## Acceptance criteria

1. `pm ledger record --grain` omitted, with a valid row otherwise, appends to
   `pm/roadmap/ledger.jsonl` and exits 0. The file is created on first write, like a milestone
   ledger is.
2. A `--gate` row lands at the root. `gate_row` carries no `grain` key by design, so this is its
   permanent home, and story 01 deliberately left it parked — this is where it arrives.
3. **`.gitattributes` carries a `merge=union` pattern that matches `pm/roadmap/ledger.jsonl`**, and
   the existing per-milestone pattern still matches `pm/roadmap/<id>/ledger.jsonl`. Proven by a
   case asserting BOTH paths match, not by asserting the pattern string — a string assertion
   passes on a pattern that matches nothing.
4. `pm ledger report` shows root-ledger rows in `rows naming no grain`, and a milestone report
   does not silently absorb them into a grain line.
5. **`ledger report` with no argument does something stated in `--help`.** Its default came from
   the lookup story 01 deleted. Pick one and say which in the close: report every milestone
   holding a ledger, or require an explicit id. A report that defaults to the whole tree is a
   different verb from one that defaults to the live milestone — do not let the difference be
   accidental.
6. `retire` still removes a milestone's ledger with its directory, and leaves the root ledger
   alone. The `check pm` D6 rule is unchanged by this story and a case should say so.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_pm_ledger_record.py::…a_row_naming_no_grain_lands_in_the_trees_own_ledger` — the file does not exist before the call | new |
| 2 | unit | `…a_gate_row_asks_the_tree_nothing_and_lands_at_the_root`, three tree shapes | inverts 0.3.0's release-routing pair |
| 3 | integration | `test_pm_ledger_report_git.py::…the_merge_attribute_reaches_both_ledger_homes` — `git check-attr` over a real repo, both paths plus three negatives and the depth | new; a string assertion passes on a pattern matching nothing, which was the bug |
| 4 | unit | `test_pm_ledger_report_sections.py::…the_trees_own_rows_are_counted_and_never_folded_into_a_grain`, and `…a_stated_grain_outranks_the_snapshot_and_bills_nobody_else` | new |
| 5 | unit | `test_pm_ledger_report.py::…a_bare_report_asks_the_plan…` and `…two_milestones_in_progress_is_answered_from_the_plan` | amend |
| 6 | unit | `…retire_takes_the_milestones_ledger_and_leaves_the_trees` | new |

## Out of scope

Any change to what a row CONTAINS. Attribution — the other feature. Making the root ledger the
primary store: it is the residue, not the destination.

## Close

done: 8a6cf3d — `<roadmap>/ledger.jsonl` is the grainless home; `ledger_path(cfg.roadmap)` is the
join, so no second path helper exists. `.gitattributes` is `**`, proven by `git check-attr` over
both paths and a negative.
AC5 answered: `ledger report` with no id reports the CURRENT RELEASE's milestone, from `order` plus
`version_at`. Stated in `--help`. It is a missing ARGUMENT answered from the plan, not a route —
no row is placed by it, and the rows themselves never consult it.
finding: 0.3.0's `release_ledger_dir` routed the gate row. D7 records the reconciliation — it
stops routing writes and keeps only the report's subject.
review M1: `pm ledger show` read only the milestone's ledger, so it and `ledger report`
disagreed about a root row that names a grain through its `tree` snapshot — `report` billed the
story, `show` said `no rows`. Both files now, sorted by `ts`, since two files are one timeline.
review M2: the `gate cost` section was tree-wide under a milestone heading. It says so on its
heading line now; D7 is amended with the reader it missed and the rejected windowing.
review W2: the grainless address was spelled five times. `ledger.grainless_dir`/`grainless_path`
name it once; the writers take the dir because `append_row` does.
review S2: the Proof budget said `cases: 5-6`; this feature landed ~12 new functions across two
stories and deleted three (the exclusivity refusal, the two release-routing cases). Over budget,
and three of the twelve are the review's — M1, M2 and the exemption scope. Named rather than
excused.
finding: a FOURTH writer, `tests/conftest.py:278`, filed slow-test rows through
`in_progress_milestones`. Three routers, not two; all four now read the row.
