---
id: 0.4.0/one-rule-routes-a-row/01-routing-asks-the-grain-not-the-tree
feature: 0.4.0/one-rule-routes-a-row
milestone: "0.4.0"
name: Routing asks the grain, and _building_ledger_dir is deleted
status: done
owner: claude
depends_on: []
---

# Routing asks the grain, and `_building_ledger_dir` is deleted

<!-- What is observable when this ships. A story is an observation, not a task. -->

`pm ledger record` writes into the milestone that owns the row's grain, at any status. The
milestone's own status is not read on any write path, and `_building_ledger_dir` is not in the
source.

**This is the story that stops the bleeding.** Today a telemetry row is refused when zero
milestones are `in_progress` and refused when two are — and 0.3.0 and 0.4.0 are both live right
now, so the second is not hypothetical. After this story neither is a refusal.

## What routes, and how

`_stamp` already does it, at `cli.py:255`:

```python
mdir = model.milestone_dir_of(cfg, path)
```

That is the whole mechanism: given the grain's file, the milestone directory that owns it. This
story gives the three telemetry call sites the same answer.

    cmd_ledger_record  --from-transcript   cli.py:1433
    cmd_ledger_record  --gate              cli.py:1525
    cmd_ledger_report                      cli.py:1706

`--grain <id>` already resolves a grain id to its file — `_ledger_id` at 1567 does it for the
hand-entry form — so the resolver exists and this story reuses it rather than writing a second.

**The gate row is the one that does not fit, and it must be decided here.** A `gate` row names no
grain: `gate_row(gate, verdict, duration_ms, census)` has no `grain` key and the feature file is
explicit that a gate run is not a grain. So `--gate` has no grain to route by, and its row belongs
to the root ledger by the rule in story 02. **Until 02 lands, `--gate` keeps writing where it
writes today** — do not leave it refusing, and do not invent a third rule for it. Say in the
commit which of the two it is on.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/cli.py` — delete `_building_ledger_dir`; route 1433, 1525 and 1706.
  Its `Usage` strings go with it, including the two long refusal messages.
- `tests/test_pm_ledger_record.py`, `tests/test_pm_ledger_report_sections.py` — the existing cases
  that assert "lands in the building milestone" INVERT here; see Acceptance 4.

## Files it must stay out of

`src/agentic_sdlc/repo/pm/ledger.py` (no row shape changes in this story),
`tools/hooks/cc-ledger-*.sh` (story 01 of `every-row-names-its-grain`), `.gitattributes` and
anything creating a root ledger (story 02), and every `pm/roadmap/**` file except this one's close
block.

**`cli.py` is shared with `every-row-names-its-grain/01`**, which edits `cmd_ledger_record`'s flag
parsing while this edits its routing. Those two are SERIAL: this one lands first.

## Acceptance criteria

1. `_building_ledger_dir` does not appear in `src/`. Proven by `tests/test_boundaries.py` or a
   grep case — whichever that suite already uses for "this symbol is gone".
2. `pm ledger record --grain <feature-id>` against a feature in a **`planning`** milestone appends
   to that milestone's `ledger.jsonl` and exits 0. Today this is exit 1 with no write. Proven in
   `tests/test_pm_ledger_record.py`.
3. **Two milestones `in_progress`, a row against a grain in one of them, lands in that one.** This
   was the "which one owns this row is the one thing this verb cannot know" refusal; the row knows,
   so it is no longer a question. Proven in `tests/test_pm_ledger_record.py`.
4. The existing cases asserting a row lands in the *building* milestone's ledger are rewritten to
   assert it lands in the *grain's* milestone's ledger, with a fixture where those two differ —
   otherwise the case passes for the old reason and proves nothing.
5. `--grain` naming an id no grain in the tree carries is still refused, exit 1, no write. Routing
   by grain must not turn an unknown id into a new place to write.
6. Nothing that used to be written is now refused. Run the full `tests/test_pm_ledger*` set and
   say so in the close.

## Out of scope

The root ledger and `merge=union` — story 02. Anything the couriers pass — the other feature.
`ledger report`'s no-argument default: **it currently comes from the in-progress lookup, so
deleting that forces the question.** Answer it in story 02 alongside the root ledger, and until
then keep `report` requiring an explicit milestone id rather than guessing.

## Close

done: d49cc6c — `_row_ledger_dir` is the one rule; `_building_ledger_dir` is gone from `src/`,
proven by a name gate in `test_boundaries.py`. A grainless row is PARKED on the gate resolver,
which story 02 replaces with the root ledger.
finding: `ledger report`'s default was the lookup's second caller and is now the current
release's milestone (D7), reconciling 0.3.0's `release_ledger_dir` — it chooses a SUBJECT, never
a route.
finding: `tests/conftest.py:278` files slow-test rows through `in_progress_milestones` — a THIRD
router nobody had listed. It belongs to story 02, with the other grainless rows.
