---
id: 0.3.0/adopt-runs-where-the-bump-lives
milestone: "0.3.0"
name: adopt runs on a tree that tracks the bump as a feature
status: done
reviewed: docs/reviews/0.3.0-adopt-runs-where-the-bump-lives.md
phase:
depends_on: []
consumed_by: []
---

# adopt runs on a tree that tracks the bump as a feature

Sibling to `adopt-grades-what-the-project-owns`: that one is about a check inside the belt that
can never become true. This is about the belt never starting.

**The finding.** `adopt <version>` refuses before running any check:

```
agentic-sdlc: adopt v0.2.0: no milestone directory pm/roadmap/v0.2.0-* — refused,
              and nothing was written
```

It requires a milestone directory named for the version being adopted. NullBound does not have
one and will not: toolkit work there is folded into the OPEN milestone as a feature — a standing
convention, because a pin bump is a day of work and a milestone there is a month of game. So the
belt is not merely advisory on that consumer, as it is on Trail at 6/7; **it is unreachable.**

**What that cost.** The adopting agent performed all seven of the belt's checks by hand, in an
ad-hoc order it invented — pin bumped, installers run, config edited, gates run, PM validated —
and missed the flow, which is precisely what `config-updated` exercises. The belt for the exact
job was sitting there, correct and complete, and could not be run.

**A second, cheaper reason it was not found: the verb does not read as what it is.** In `--help`
it is one line under "Belts":

```
    agentic-sdlc adopt <version>
```

Beside `release <version>` and `close story|feature <id>` — all grain operations — `adopt
<version>` reads as a grain operation on a milestone. Nothing on that line says it means *adopt a
devkit pin*, and the agent read past it twice. `[adopt] pin_file` in the config is the only place
the actual meaning appears.

## Ship criterion

`adopt <version>` runs its checks on a tree that tracks the bump anywhere — a feature id, a story
id, or no grain at all — rather than requiring a milestone directory named for the version. The
version is what gets adopted; where the WORK is recorded is the project's business, the same way
`[pm.states.*]` is. And its `--help` line says what it adopts, in the line itself, so a reader
scanning the belts can tell it from `release`.

## Proof budget

  cases: 2-3
  tier: pyunit
  lands in: the adopt-belt test module
  what already covers this: the belt's checks are covered end to end on a tree shaped the way the
    belt expects. Nothing covers the entry condition, because until a consumer shaped differently
    tried to run it there was no reason to think the entry condition was one.

## Out of scope

Whether a bump SHOULD be a milestone. Several projects will want it to be, and this feature does
not take that away — it stops the belt requiring it.
