---
id: ft-the-shipped-words-match-the-shipped-tool
kind: feature
milestone: "ms-a-consumer-can-take-the-bump"
name: the shipped words match the shipped tool
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-the-auto-loaded-rule-is-true-at-this-version"
  - "st-a-role-brief-states-the-tools-fact-not-a-projects-policy"
  - "st-the-rendered-protocol-describes-the-check-that-runs"
  - "st-the-readme-a-consumer-copies-from-is-current"
---

# the shipped words match the shipped tool

Issues: #32 #23 #33 #34 #35, plus the `pm-execution.md` audit left open on #15.

Four surfaces a consumer cannot edit, or copies from verbatim, still describe 0.4/0.5 behaviour at
v0.7.0:

- **the auto-loaded rule** (`pm/guidance/pm-execution.md`), which is installed into every consumer
  and loaded on every `pm/roadmap/**` edit;
- **two role briefs** (`installables/pm-operator.md:62`, `installables/tech-writer.md:60`). The
  second of these is not in #23;
- **the rendered protocol** (`conveyor/steps.py:1613`, rendered into `docs/sdlc-protocol.md:37`);
- **the README's Install, Wiring and adoption blocks**.

Nothing new is built here. What earns the slot is that each is **a lie the kit installs** (rule 4's
second sin). Where one can be tied to what it describes cheaply, the story does that too, so the
drift cannot come back.

**This feature lands first.** `st-check-doc-reads-a-code-span-across-a-line-break` in
`ft-a-gate-verdict-is-true-of-the-tree` depends on its first story.

## Ship criterion

The installed rule, the two briefs, the rendered protocol and the README make no claim that the
v0.8.0 tool contradicts. A consumer with no `reviewing` feature state and one with it both read an
installed rule that is true for them. Every release a README reader can bump across has notes they can
reach from the README.

**Accepted means closed on GitHub:** #32, #23, #33, #34 and #35 are each closed with a comment citing
this feature and its commit hash(es) (SDLC.md §2). #15 is closed too if its audit was the last thing
open on it. Otherwise it gets a comment saying what remains.

## Proof budget

  cases: 2–4. Most of this is text, and text is proven by the existing byte-current and doc gates.
  tier: unit
  lands in: tests/test_install.py (byte-current), tests/test_conveyor_steps.py (description ↔ check)
  what already covers this: `installables-current` holds each copy to its source, but nothing
    holds a SOURCE to the behaviour it describes. The one new case worth writing binds each belt-
    registry description to its check (#33's third fix), so a renamed behaviour cannot keep its old
    sentence.
