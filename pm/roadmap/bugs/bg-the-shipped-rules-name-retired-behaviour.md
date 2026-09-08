---
id: bg-the-shipped-rules-name-retired-behaviour
kind: bug
milestone: "ms-a-move-is-an-event"
name: the shipped rule and skill assert behaviour this package retired
status: closed
caused_by:
---

# the shipped rule and skill assert behaviour this package retired

Two agent-facing files that `install-skills` writes into every consumer, and that load themselves
into every session, state things that are false. This is one defect with two instances, and the class
matters more than either.

**`.claude/rules/pm-execution.md`:**

> Creation too: `pm new milestone|feature|story|bug` scaffolds to the schema.

False — see `bg-the-new-verbs-mint-a-compound-id`. This is the sentence that let that bug survive a
release: the scaffold hands back a shape the tree does not use, and the only auto-loaded rule on the
subject vouches for it.

**`.claude/skills/pm-operations/SKILL.md`** (from `install-skills --force` at v0.4.0), ~line 185:

> ids stay canonical forever […], **ROADMAP.md keeps one row per shipped milestone permanently**

`ROADMAP.md` was retired in 0.3.0 and replaced by `pm roadmap` + `releases.md`. A consumer adopting
the skill reads an instruction to maintain a file this package stopped writing two releases ago.
Reported in GitHub issue #8.

## Why it is a class, not two typos

`ft-documented-behaviour-is-the-behaviour` (0.4.0) gated the DOCS. These are neither docs nor code —
they are **installed instructions to an operator**, and nothing grades them against the behaviour
they describe. Rule 11's operator *"is usually an LLM with no memory of last week"*, which is exactly
the reader who cannot tell that a shipped rule has gone stale.

An agent that trusts an installed rule over the tool's actual output is behaving correctly. The
defect is ours.

## Fix

Both sentences corrected. Then the harder half: the installed rule and skill go through whatever
`check doc` does for the rest of the repo, or `adopt`'s `installables-current` gains a claim that the
retired names do not appear in them. A grep for retired verbs and filenames across the installables
would have caught both.

## Alongside

`pm new <kind> <parent> <slug>` refuses a missing `--name` with `feature '<id>' does not exist yet —
a new one needs a name`. Accurate, but it reads as "this grain is missing" before "you omitted a
flag", and `--help` does not mark `--name` required. A one-line reword.
