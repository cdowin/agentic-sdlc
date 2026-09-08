---
id: bg-the-brief-undercounts-the-coupling-it-argues-from
kind: bug
milestone: "ms-nothing-is-hand-rolled"
name: the brief undercounts the coupling it argues from
status: open
caused_by:
changelog: none
---

# the brief undercounts the coupling it argues from

## Symptom

`ms-the-rule-reaches-the-work` says, in the section headed *Constraints this milestone must
respect*:

> **The hard-rule NUMBERS are a public API.** Roughly 600 citations across source, tests and hooks —
> `rule 4` alone appears 194 times.

Measured over the 476 tracked `*.py`/`*.md`/`*.sh`/`*.toml` files outside `.claude/worktrees/`,
case-insensitive `\brule [0-9]+\b`: **1,107 citations, `rule 4` alone 314.**

The number is off by ~2x, and it is off in the direction that makes the constraint look CHEAPER
than it is. The sentence exists to stop somebody renumbering the hard rules; it undersells the
hazard it is warning about by 500 sites.

## Root cause

**Nobody could ask.** The count was produced once, by hand, by whoever wrote the brief, and then
quoted forward through three milestones. There is no verb that answers *"how many times is rule N
cited, and where"*, so the number could not be refreshed, could not be checked at review, and could
not go red when it drifted.

That is this milestone's northstar with a worked example: a hand-rolled measurement becomes a
citation, the citation becomes a constraint, and the constraint is argued from a number the tree
disagrees with.

## Fix

Two halves, and the second is the one that matters.

  * Correct the number where it is quoted.
  * **Make it askable.** `ft-a-hand-rolled-command-is-a-missing-verb` owns this: a verb that reports
    the citation census per rule, so the next brief quotes a command's output rather than a memory.

## Out of scope

Gating on the count. A rising citation count is not a defect — it is what a rule being USED looks
like. What is a defect is a document asserting a number nobody can reproduce.
