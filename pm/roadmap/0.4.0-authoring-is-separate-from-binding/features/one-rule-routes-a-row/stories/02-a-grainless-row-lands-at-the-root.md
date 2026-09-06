---
id: 0.4.0/one-rule-routes-a-row/02-a-grainless-row-lands-at-the-root
feature: 0.4.0/one-rule-routes-a-row
milestone: "0.4.0"
name: A row naming no grain lands in the root ledger
status: done
owner: claude
depends_on: ["0.4.0/one-rule-routes-a-row/01-routing-asks-the-grain-not-the-tree"]
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
finding: a FOURTH writer, `tests/conftest.py:278`, filed slow-test rows through
`in_progress_milestones`. Three routers, not two; all four now read the row.
