---
id: bg-install-skills-has-no-withdrawal-report
kind: bug
milestone: 
name: pm install-skills has no withdrawal report and no --since
status: open
caused_by:
changelog:
---

# pm install-skills has no withdrawal report and no --since

From the 0.8.0 milestone review, R9 (`docs/reviews/2026-09-11-0.8.0-milestone-review.md`). It is the
sixth installer, and it is the one that does not say what a bump withdrew. 0.8.0 gave the other five
`install-*` verbs the withdrawal census and `--since <version>`. `pm install-skills --since` is
`unknown flag`, exit 2, and a withdrawn skill or rule file would go unnamed.

Filed to the pool rather than held against 0.8.0, because it is a new flag and a new report line on
a verb 0.8.0 did not otherwise change.

## Fix

`pm install-skills` reads the same `RETIREMENTS` table through the same `retired_since` and takes
`--since`, so all six installers answer the question one way.
