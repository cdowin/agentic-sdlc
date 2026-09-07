---
id: ft-prose-that-restates-a-verb-is-rendered-or-gone
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: prose that restates a verb is rendered or gone
status: reviewing
reviewed: docs/reviews/2026-09-07-0.6.0-prose-that-restates-a-verb.md
depends_on: []
consumed_by: []
changelog: `check doc` now reports a shipped sentence naming a `pm <kind> <status>` call whose status the project's own `[pm.states.<kind>]` does not declare — the shape that shipped an auto-loaded rule instructing `pm story reviewing`, which exits 2. A tree that declares no flow reports nothing rather than inventing a vocabulary.
---

# prose that restates a verb is rendered or gone

**The rendered document is the only one that never drifted.** `docs/sdlc-protocol.md` went through 22
grains in a day without a single wrong sentence, because a gate holds it byte-current against the
step lists it renders. Over the same day, **five shipped sentences contradicted shipped behaviour**:
the seed said the reverse of `[emit]`'s default, `telemetry-live` described an installer that had
changed, and the auto-loaded rules file instructed `pm story reviewing`, which exits 2 because the
seed declares no review word for a STORY.

Nothing was reading any of them. `check doc` already held this repo's prose to its **paths** and its
**make targets** — a dead path in a backtick span is a finding, a `make` target no Makefile declares
is a finding. **An INVOCATION is the same kind of claim about the tree, and it was the one nobody
checked.**

## What is mechanisable, and what is not

Honest scope, because a rule that cannot fail would be this feature committing the defect it exists
to catch:

- **A CLI call whose STATE the project never declared** — mechanisable, and it is the one that
  shipped. `pm story reviewing <id>` is graded against `[pm.states.story]`, which the project itself
  declares. Rule 9's edge holds: this READS the vocabulary rather than deciding what a story
  vocabulary should be, and a project that declares `reviewing` for a story makes the same sentence
  legal.
- **A seed value disagreeing with a code default** — already gated. `tests/test_config_seed.py`
  compares the two key by key and fails by name; that is how `[emit]`'s reversed default would be
  caught today.
- **A sentence paraphrasing what a verb DOES** ("`--force` re-applies nothing") — **not mechanisable
  here.** Grading prose against behaviour is a different mechanism, and `test_install.py` already
  takes the one tractable slice of it: the sentences that send a consumer to `--force` must name what
  it costs. Attempting the general case would ship a rule nobody could keep green.

So the rule that lands is the sharp one, and this file says out loud which half it does not cover.

## Ship criterion

`check doc` reports a shipped sentence naming a `pm <kind> <status>` call whose status the project's
own `[pm.states.<kind>]` does not declare, naming the declared set so the fix is in the finding.

A tree that declares no flow reports nothing rather than inventing a vocabulary.

The deliberate negative citations in this repo — prose correctly SAYING a call exits 2 — use the
gate's existing `<!-- doc-scan:allow -->` escape, never a code change. There are two.

## Proof budget

  cases: 6
  tier: pyunit
  lands in: a new `tests/test_check_doc.py` — this gate had NO test module, because `REPO_ROOT` is
    captured at import and `relative_to` raises on a scratch tree. A `rel()` helper at the five
    reporting sites made one possible; converting the constant belongs to the vocabulary sweep.
  what already covers this: `check doc`'s path and make-target rules are the harness — this is a
    third claim on the same scan, not a new family.

## Out of scope

Grading prose against behaviour in general. Named above and rejected there.

Renaming or renumbering anything. Rule 6.
