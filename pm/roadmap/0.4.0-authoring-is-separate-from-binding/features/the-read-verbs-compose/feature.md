---
id: 0.4.0/the-read-verbs-compose
milestone: "0.4.0"
name: A read verb emits every field you would filter on
status: building
reviewed:
phase:
depends_on: []
consumed_by: []
---

# A read verb emits every field you would filter on

**The trace.** Reviewing the 0.4.0 design, the agent reported a missing capability — *"there is no
way to search the pools; we need `pm list --grep`"* — and proposed a verb. The answer was:
`pm list | grep` already composes, you have a shell.

It was right, and the reason the agent did not reach for it is the actual defect: **`pm list`
emits `id, status, owner, feature` and NOT the name.** So `pm list | grep "cost row"` returns
nothing. The composable answer was correct and the payload made it fail, so the agent concluded
composition was impossible and invented a verb.

**A read verb that omits a field people filter on does not just inconvenience them — it teaches
them the tool cannot do it.**

## The rule

> **Read verbs emit lines; composition is the shell's job.** If you want a filter this package does
> not have, pipe it. If you cannot pipe it, the missing thing is a COLUMN, not a verb.

Stated in `--help` for every read verb and in the package's CLAUDE.md, so it decides the next
request instead of being re-argued. It is also the cheaper half of a bargain: every filter flag not
added is a flag not documented, not tested and not kept in sync with the fields.

## What changes

`pm list` gains the **name** column, and every read verb's `--help` names its columns in order,
because a column list is what makes a pipeline writable without reading source. `--json` for the
listing verbs, matching `pm vocabulary --json`, which already sets the precedent — one flag that
subsumes every filter flag nobody has to add.

**Existing filter flags stay.** `--status`, `--owner`, `--milestone`, `--kind` predate the rule and
removing them would break consumers for a purity nobody asked for. The rule governs the NEXT one.

## The general shape, worth naming once

Two discovery failures in one adoption, and they are the same shape. The agent hand-rolled the
seven-step adoption checklist because it never found `adopt`, whose seven checks were exactly that
list. The agent invented a search verb because `pm list` withheld the field. **In both cases the
capability existed and the surface did not advertise it at the moment of need.**

Both fixes are the same kind: say what you can already do, where someone is standing when they need
it. `adopt`'s `--help` line naming what it adopts (`0.3.0/adopt-runs-where-the-bump-lives`); a read
verb naming its columns; `pm config --seed` for a bumping consumer
(`0.4.0/the-config-is-the-model`). None is a new capability. All three are the surface admitting to
one.

## Ship criterion

`pm list` emits the name. Every read verb's `--help` names its columns in order and states the
composition rule. `--json` is available on the listing verbs. The rule is in the package's
CLAUDE.md so a future filter request is answered by policy rather than re-argued. No filter flag is
added by this feature.

## Proof budget

  cases: 2
  tier: pyunit
  lands in: `test_cli_surface.py`, which already asserts help text and output shape
  what already covers this: the listing verbs' columns are asserted, so adding one extends an
    existing case. New: `--json` round-tripping to the same fields the columns carry, which is the
    one thing that could silently diverge.

## Out of scope

Adding filter flags. That is the behaviour this feature exists to make unnecessary.
