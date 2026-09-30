---
id: ft-a-project-declares-its-required-lines
kind: feature
milestone: "ms-the-mistake-surfaces-where-it-is-made"
name: a project declares its required lines
status: done
reviewed: docs/reviews/2026-09-29-0.17.0-pm-lanes.md
depends_on: []
consumed_by: []
changelog: `[pm.required.<kind>] lines` declares line prefixes a grain body must carry: `pm new` writes each one, a move to an in_progress state and `check pm` warn while one is missing or empty, and the new stock `required-lines` story-belt check refuses `close story` until each has a value — so every `close story` prints one more check line and `ready-for story` counts one more check, even with nothing declared.
---

# a project declares its required lines

Issues: #80, #91, #96.

A consumer's own gate required a `Destination:` line (and later `Scenarios:`) in every story.
`pm new story` did not write one, so the gate failed later, in every lane, not at the flip: 39
stories at once in one case. The gates are the consumer's (rule 8). What this package owns is
letting a project DECLARE the lines a grain body carries, and saying so where the operator
stands.

## Decided (do not re-plan)

- **`[pm.required.<kind>]`, a WORKFLOW key** (rule 5: no stock default, nothing behind it; absent
  means no lines are required, and nothing is read). Shape: `lines = ["Destination:",
  "Scenarios:"]`, each a line PREFIX the body must hold. Validated in `core/config.py`: a list of
  non-empty strings, else exit 2 by name.
- **`pm new <kind>` scaffolds each declared line** as `<prefix> ` followed by a placeholder the
  check recognises as empty (for example `<prefix> <!-- required -->`). A re-scaffold of an
  existing grain fills a missing line and touches no other byte (rule 3).
- **The move reports, the belt refuses** (rule 9). `pm <kind> <in_progress state> <id>` writes
  the status and prints one `WARN` line per missing or empty required line, naming the key.
  `check pm` joins the same WARN family for an `in_progress` grain. The story belt gains a
  `required-lines` check: `close story` refuses while a required line is missing or empty.
  `ready-for story` asks it too.
- Seed carries the section commented, with a one-line example. The pm-operations skill names
  the key where it talks about templates (rule 11), then `pm install-skills --force`.
- A value is never validated against a meaning (`Scenarios: none` is a value). Only presence
  and non-empty.

## Ship criterion

- With `[pm.required.story] lines = ["Destination:"]`, `pm new story` writes a `Destination:`
  line; `pm story building` on a story without it prints a WARN naming the key; `close story`
  refuses it; with the line filled all three are quiet.
- A tree with no `[pm.required.*]` behaves byte-identically to 0.16.0.

## Proof budget

  cases: 1 config-shape case, 1 scaffold case, 1 WARN case, 1 belt refusal; seed test moves
  tier: unit / temp tree
  lands in: tests for core/config.py, pm new, checks/pm.py, conveyor/steps.py
  what already covers this: the empty-section WARN for `## Acceptance criteria`; this is the same family for declared lines.
