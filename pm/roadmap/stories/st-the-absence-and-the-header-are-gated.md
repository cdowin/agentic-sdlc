---
id: st-the-absence-and-the-header-are-gated
feature: ft-a-document-points-at-what-it-cannot-hold
milestone: "ms-0.4.0"
name: The absence and the missing header are both gated
status: done
owner:
depends_on: ["st-the-template-gets-a-minting-path"]
kind: story
---

# The absence and the missing header are both gated

Two questions the tree could answer and never asked, plus the surface that fires on the words a
person types.

## The absence — `check pm`, as a READY warning

A milestone in an `in_progress` category with no `handoff.md` warns, naming `pm new handoff <id>`.
It joins the existing READY family (no `branch:`, empty `## Ship criterion`, no `phase:`, no
stories) rather than minting a new `D` id, because it is the same question those ask: *this grain
is past todo and something a cold reader needs is missing.*

**`in_progress` only, not every started milestone.** The first cut fired on `done` too, which on
any consumer's tree is one warning per historical milestone — noise, and a handoff is a cold-start
aid nobody needs for finished work.

**Why the tree could not answer before:** `MILESTONE_OPTIONAL_SLOTS` was imported by exactly one
module, `templates/__init__.py` — the *writer*. No gate and no read verb knew `handoff.md` was a
slot, so `pm status` listed thirteen features and never mentioned the missing doc.

## The header — `check grain-shape`

A shared doc not opening with a known `SLOT_HEADER` is a finding naming the repair and the literal
line. It lands here because this gate already reads every grain document's lines, so the check
costs one comparison and no second open.

The header is *"the one channel that reaches a dispatched subagent"* (`model.SLOT_HEADER`'s own
comment), so a doc that lost it is silently unguided. `templates._header_wanted` has always known
how to spot that, and only ran on `pm new`.

**The gate is not stricter than the writer**: any known header passes, retired wordings included.
A gate that reddened a doc `pm new` calls correct would be a gate people turn off.

## The skill — the only surface that fires on "write me a handoff"

`.claude/skills/handoff/SKILL.md`, shipped through `pm install-skills` and `pm init`. Argued
against and overruled, with the reasoning in `decisions.md` D6: a template guides only once you
open it, a header only once the file exists, a cap only after you have written too much. **A skill
description is the only surface that matches the words somebody says.**

It **routes** — `pm new handoff`, the template, what counts as derivable. A skill that restated the
template would reproduce the bug it exists to prevent, so its test asserts a length ceiling.

## Acceptance criteria

1. An `in_progress` milestone with no handoff warns and names the verb; a `done` one does not.
   Proven by `tests/test_pm_gate.py::ReadyIsAStampWithACheck::test_each_warning_fires_on_the_
   scaffold_and_is_silent_on_a_filled_grain`, extended — the fixture now mints a handoff, and the
   count moved 5 → 6.
2. A shared doc that lost its instruction line is a `NO HEADER` finding naming the repair and the
   line. Proven by `tests/test_grain_shape.py::test_a_shared_doc_that_lost_its_instruction_line_
   is_a_finding` — the case that would have caught this repo's own hand-authored handoff.
3. The skill installs, its description carries the words people type, it names `pm new handoff`,
   and it stays under 100 lines. Proven by `tests/test_pm_guidance.py::test_the_handoff_skill_is_
   findable_by_the_words_people_type`.
4. `pm init`'s documented file set grows by exactly one entry, cross-checked against the install
   tables. Proven by `tests/test_init_verb.py`'s two roster cases.

## Close

done: `checks/pm.py` (the READY warning, `in_progress`-only), `checks/grain_shape.py`
(`_header_line` + the `NO HEADER` finding, reading `model.KNOWN_SLOT_HEADERS`),
`guidance/handoff.md` + `skills.py` (the skill and its install plan), and four test modules.
finding: the first cut warned on `done` milestones — one line per historical milestone on every
consumer's tree. Narrowed to `in_progress`, which is also what the doc is FOR.
