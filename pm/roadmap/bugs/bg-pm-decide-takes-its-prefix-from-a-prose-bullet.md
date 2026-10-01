---
id: bg-pm-decide-takes-its-prefix-from-a-prose-bullet
kind: bug
milestone: "ms-the-open-issues-close"
name: MAJOR pm decide takes its id prefix and ordinal from a prose bullet
status: open
caused_by:
changelog:
---

# pm-decide-takes-its-prefix-from-a-prose-bullet

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-pm-decide-takes-its-prefix-from-a-prose-bullet` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MAJOR. `next_entry_id` on a log whose last entry body holds `- R1 — is opt-in` and `- U2 - not needed` returns `U3`, not `D2`; a log citing `- D9 - the old id` after `## D2` returns `D10`. `pm decide` writes that heading and a ledger row: a wrong id that looks legitimate (rule 4).

## Root cause

`_ENTRY_POINTER` (src/agentic_sdlc/repo/pm/inventory.py) matches any prose bullet that opens with an id-shaped word and a dash, and the prefix follows the LAST matched line of the whole log.

## Fix

Count a pointer line only outside a `## ` entry body (before the first heading or in a condensed-index section), and take the prefix from headings first. Unit cases: the two logs above.
