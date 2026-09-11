---
id: st-a-role-brief-states-the-tools-fact-not-a-projects-policy
kind: story
feature: ft-the-shipped-words-match-the-shipped-tool
milestone: "ms-a-consumer-can-take-the-bump"
name: a role brief states the tool's fact, not a project's policy
status: building
owner: agent
depends_on: []
changelog: The stock pm-operator, tech-writer and po briefs no longer bind bugs to the milestone-of-catch — that is a `bugs bind:` line in pm-operator's Project config fence, which `install-agents --force` names as missing from a fence kept from an older install — and po no longer calls `reviewing` the story terminal.
---

# a role brief states the tool's fact, not a project's policy

Issue: #23.

`installables/pm-operator.md:62`, checklist item 5, sits OUTSIDE the editable `## Project config`
block (`:14-29`) and says *"Bugs file under the milestone-of-catch."* That is a project judgement.
It is not even this package's own model, because since 0.6.0 a bug's `milestone:` is its PARENT, the
milestone that must close before it. `installables/tech-writer.md:60` carries the same policy (*"file
post-ship bugs under the milestone-of-catch"*), which #23 does not mention.

A consumer who binds bugs elsewhere has two options. They can override the line from the config block,
and the agent then reads two contradicting instructions. Or they can edit the stock body, and the file
drifts, has to be claimed in `[adopt] ours`, and loses every future update.

## Acceptance criteria

1. Neither stock body outside the config block names a milestone a bug should bind to. What remains
   is the tool's fact: *a bug's `milestone:` is its parent, and that milestone cannot close while the
   bug is open.*
2. The binding POLICY is a stock default line inside `pm-operator.md`'s Project config block, the same
   shape as its `pm tree:` line, so a project overwrites it without drifting the body.
3. Every other shipped brief under `installables/` has been read for the same milestone-of-catch
   policy and nothing else carries it (`git grep -n 'milestone-of-catch'` returns only the config block).
4. Both agents are re-installed here with `install-agents --force`, and `installables-current` passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 3 | — | the grep, quoted in the close | n/a |
| 4 | unit | tests/test_install.py byte-current | yes |

## Semver

Patch.

## Out of scope

Choosing a different stock default. `milestone-that-will-fix-it` is what the tool's model implies and
is the obvious default, but this story only moves the line.
