---
id: ft-a-close-reconciles-the-plans-ahead
kind: feature
milestone: "ms-the-mistake-surfaces-where-it-is-made"
name: a close reconciles the plans ahead
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a close reconciles the plans ahead

Issue: #92.

A milestone that changes foundational contracts leaves every later milestone's plan written
against contracts that no longer hold. Nothing in the close reconciles the two, so a consumer
hand-writes a "forward plans match" feature on each such milestone and risks forgetting it.

## Decided (do not re-plan)

- **Opt-in per milestone:** a `reconcile: forward` frontmatter field on the milestone. Absent
  means today's behaviour exactly. No `[pm]` switch: the choice is per milestone.
- **The record is a shared doc beside the milestone:** `<stem>-reconcile.md`, minted by
  `pm new reconcile <milestone>` from a packaged template (on demand, like `new handoff`). It
  holds: a `## Contracts` table (contract, what the plan said, what the code does, the file that
  states it), a `## Forward grains updated` list of grain ids, and a `## Needs you` list for new
  or dead forward features (never added to the tree silently).
- **Checks, read-only:** the record exists; its contracts table has at least one row, or the
  single line `none changed`; every grain id in `## Forward grains updated` resolves; and each
  forward MILESTONE that owns one of those grains has a `decisions.md` heading that names this
  milestone's id. Unresolvable ids are findings, not guesses.
- **Where it gates:** a `forward-reconciled` step in the release belt (stock release steps; it
  answers TRUE with "not declared" for a milestone without `reconcile: forward`), and
  `pm ready-for milestone <id>` names a missing or incomplete record as a blocker. `check pm`
  WARNs for an `in_progress` milestone with `reconcile: forward` and no record (rule 11).
- **The dispatch:** `agentic-sdlc dispatch --reconcile <milestone-id>` renders the brief for the
  pass: the milestone's merged range (its branch against the mainline), the forward milestones
  in `releases.md` `order:` after it, and the record's path and sections. Rendered, never a copy.
- README row, `--help`, the `run-the-sdlc` skill's close section and the pm-execution rule name
  the step (rule 11); re-install the guidance.

## Ship criterion

- A milestone with `reconcile: forward` and no record: `release` refuses on
  `forward-reconciled`, `ready-for milestone` names it, `check pm` WARNs.
- With a complete record and a decision in each touched forward milestone, all three pass.
- A milestone without the field behaves byte-identically to 0.16.0.
- `dispatch --reconcile <id>` prints the range and the forward milestones.

## Proof budget

  cases: about 6 — record census (missing, empty table, unresolved id, missing decision, complete), dispatch render
  tier: temp tree; the release step through its unit-level check function, not a full belt run
  lands in: tests for ready_for.py, conveyor/steps.py, dispatch.py
  what already covers this: nothing reads a reconcile record today.
