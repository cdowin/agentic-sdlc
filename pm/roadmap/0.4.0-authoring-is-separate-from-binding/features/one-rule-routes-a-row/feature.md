---
id: 0.4.0/one-rule-routes-a-row
milestone: "0.4.0"
name: One rule routes a row, and the in-progress lookup is deleted
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# One rule routes a row, and the in-progress lookup is deleted

**This is the milestone's own thesis, found inside the ledger.** Two functions in `cli.py` answer
"which ledger does this row belong to", and they answer differently:

    _stamp()                line  255   milestone_dir_of(cfg, path) — the milestone that owns
                                        the GRAIN'S FILE. No status check at all.
    _building_ledger_dir()  line 1303   exactly one milestone in `in_progress`; refuses on
                                        none, refuses on several.

Status and decision rows take the first. Telemetry rows take the second —
`cmd_ledger_record --from-transcript` (1433), `--gate` (1525), `cmd_ledger_report` (1706).

So the tool already has grain-based routing and the telemetry layer does not use it. That is a
second name for one fact, which is the defect this milestone exists to delete everywhere else.

## The rule

> **A row goes to the ledger of the milestone that owns the row's grain.** A row naming no grain
> goes to the tree's root ledger, `pm/roadmap/ledger.jsonl`.

Status is never consulted. `_building_ledger_dir` is deleted outright, and three things leave with
it: the "no milestone is in progress" refusal, the "several milestones are in progress" refusal,
and the coupling between *recording* and *workflow state* that made the first of those a silent
data-loss condition (`0.4.0/recording-is-on-or-the-gate-is-red` is the story of that loss).

D1 in this milestone's `decisions.md` carries the argument and the rejected alternative.

## What it fixes that is not tidiness

- **Work on a `planning` milestone records.** Shaping a feature nobody has claimed yet lands
  against that feature. This is how the milestone's own design sessions get measured, and the
  first twenty minutes of the session that found all this are unrecoverable for exactly this
  reason.
- **Two milestones in flight stop being a refusal.** Not hypothetical: 0.3.0 and 0.4.0 are both
  live right now, on two branches, with two agents. Under the old rule a merged tree with both
  `in_progress` refuses every telemetry write with *"which one owns this row is the one thing this
  verb cannot know"* — which is true, and is also the wrong question. The row knows its grain; the
  grain knows its milestone.
- **`ledger report` keeps its argument.** `report [<milestone-id>]` already takes an explicit id;
  only its DEFAULT came from the in-progress lookup. The default becomes "every milestone with a
  ledger", or stays an explicit-id-required verb — decide it in the story, and note that a report
  defaulting to the whole tree is a different verb than one defaulting to the live milestone.

## The root ledger

`pm/roadmap/ledger.jsonl`, one file, for rows naming no grain. `pm ledger report` already prints a
`rows naming no grain` bucket — this gives that bucket a home rather than scattering its contents
into whichever milestone was building.

**D6 survives.** Attributed rows still live with their milestone, `retire` still removes them with
the directory, git is still the archive. Only unattributed rows outlive a milestone, which is
correct — they were never about it.

**`merge=union` must cover it.** `skills.py` writes `<roadmap>/*/ledger.jsonl merge=union` into
`.gitattributes`. A root ledger at `<roadmap>/ledger.jsonl` does **not** match that glob — one
directory level short — so the pattern has to grow or the root ledger conflicts on every parallel
branch. This is the single most likely thing to be got wrong here and it fails quietly, as a merge
conflict nobody attributes to this change.

## Ship criterion

`_building_ledger_dir` does not exist. Every `ledger record` form routes by the row's grain, at any
milestone status, including `todo`-category ones. A row naming no grain lands in
`pm/roadmap/ledger.jsonl` and is reported from there. `.gitattributes` gives the root ledger the
same `merge=union` the per-milestone ones have. `ledger report`'s default is decided and stated in
`--help`. No row that used to be written is now refused.

## Proof budget

  cases: 5-6
  tier: pyunit
  lands in: `tests/test_pm_ledger_record.py` and `tests/test_pm_ledger_report_sections.py`, both
    of which already exercise the routing indirectly through their fixtures
  what already covers this: the existing record cases assert a row lands in the building
    milestone's ledger — those INVERT rather than extend, becoming cases that prove the status is
    not consulted. New: a row against a `planning` milestone's feature lands; a row with two
    milestones in progress lands (previously a refusal); a grain-less row lands at the root; the
    root ledger's `merge=union` attribute is written; and `report` with no argument does what the
    story decided.

## Out of scope

How a row acquires its grain — `0.4.0/every-row-names-its-grain`. That feature is INDEPENDENT of
this one, not upstream of it: `ledger record --grain` already exists as the hand-entry form and
status rows already carry grains, so grain-first routing is testable the day it lands. Build this
one first anyway — it is what stops rows being refused. The gate that notices nothing is recording
— `0.4.0/recording-is-on-or-the-gate-is-red`. D6's per-milestone
model is NOT under review here: this feature keeps it and changes only how the milestone is
chosen.
