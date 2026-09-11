---
id: bg-the-always-loaded-surface-states-properties-not-procedures
kind: bug
milestone: ms-nothing-is-hand-rolled
name: CLAUDE.md is 1.8 negatives per positive and 6 of 11 rules open with a prohibition; a constraint fires only from inside the mistake
status: closed
caused_by:
changelog: Rule 11 in the always-loaded CLAUDE.md now states its read side as a MOVE with a trigger — before writing a script to measure the tree, ask it, naming the four verbs that answer — beside the property it already asserted.
---

# the always-loaded surface states properties, not procedures

The operator here is an LLM with no memory of last week (rule 11's own premise).
It acts on a NEXT ACTION. Most of this surface states a property the code must
have, which is a different sentence aimed at a different reader.

## The measurement

Negative markers against positive ones, across every surface an operator loads:

    surface                          lines   neg   pos   neg/line
    CLAUDE.md                          152    82    45       0.54
    SDLC.md                            147    49    40       0.33
    .claude/rules/pm-execution.md      193    66    66       0.34
    .claude/skills/pm-operations        181    67    62       0.37
    TOTAL (6 files)                    800   302   256       0.38

**`CLAUDE.md` — the one file that is always loaded — is the most negative of
the six, at 1.8 negatives per positive.** And **6 of the 11 hard rules open with
a prohibition**: stdlib ONLY; boots NOTHING; touches ONLY; knows NOTHING; never
infer; GATES-ONLY.

## The distinction that actually predicts behaviour

Not negative-vs-positive. **Constraint-vs-procedure** — and this session is the
n=1 experiment, from what the operator did rather than what it says it read.

**Reached the work:**

  * **Rule 10** — *"Prove it once: before a new case, name the one that already
    covers this."* Obeyed four times unprompted (the fuzz module, WriteFidelity,
    the guard roster, the budget cases). A trigger and an action.
  * **Rule 4** — *"Prove the census matches intent; a gate scanning 0 files
    FAILS."* Five gates probed with planted drift before being trusted. A
    procedure with a vivid consequence.
  * **The ladder table** — *you changed X, run Y.* A lookup. Used on every
    commit.

**Did not reach the work:**

  * **Rule 11's READ side** — violated six times in one session by the operator
    who had read it. It states what a SURFACE must be; it gives a reader no
    moment and no move. The author-facing half ("name the absence") was obeyed
    all day: seven findings filed by name.
  * **Rules 1 and 8** — never fired, because nothing prompted them. A
    prohibition is only reachable from inside the mistake.

**A constraint fires when you are already doing the wrong thing. A procedure
fires when you start.** For a reader with no memory, only the second one is
available.

## The fix this implies, on rule 11 specifically

Rule 11's read side currently describes a property of surfaces. The operator-
facing form of the same rule is one line with a trigger:

    Before writing a script to measure this tree, ask it:
      pm ledger report   spend, clock, gate cost, session deltas
      pm list            any grain, as lines
      check <gate>       every static rule
      dispatch --grain   the contract an agent needs

That sentence would have caught six hand-rolled censuses today. The prohibition
form — *a capability nobody can find is a capability you do not have* — is true,
memorable, and caught none of them, because it is addressed to whoever writes
the package rather than whoever is standing in it.

## What this is NOT

**Not an argument for softening the constraints.** Rules 1-3 are load-bearing
and their prohibition form is correct: they exist to stop a specific act, and
"stdlib only, forever" is exactly as long as it needs to be. A gate that FAILS
is the desired outcome in this project, so a raw negativity count over-reads —
which is why the evidence above is behavioural rather than lexical.

**Not a rewrite of the hard rules.** 0.6.0 put `CLAUDE.md` through four
questions — CUT, POINTER, TRIGGERED, KEEP — and held rule numbers 1-11 fixed,
for the reason `bg-the-brief-undercounts` gives: the numbers are a public API
with four-figure citations. **This is a fifth question that pass never asked** —
*does this rule give its reader a move?* — and it is answerable per rule without
renumbering anything.

## Out of scope

The negativity of the gate OUTPUT. A finding should name what is wrong; that is
rule 4 and it is working.

## Out of scope, and deliberately

Any claim that this caused the `dispatch` failure. **That one was absence** —
the verb is in no surface the orchestrator loads
(`bg-rule-11-is-gated-in-one-direction-only`), and no amount of framing fixes a
line that is not there. Framing explains why the rule did not send the operator
LOOKING; the gate is what makes the line exist.

## What landed

**Rule 11 gains its operator-facing form, beside the property it already
states** — the fifth question 0.6.0's pass never asked, answered for the one
rule this session proved it on, without touching a rule number:

    Before you write a script to measure this tree, or paste a prompt, ASK IT:
    `pm ledger report` (spend, clock, gate cost, session deltas), `pm list`,
    `check <gate>`, `agentic-sdlc dispatch --grain <id>`.

The sentence names the moment ("before you write a script"), the move ("ask
it"), and the four surfaces that answer. It also carries its own evidence: this
milestone's orchestrator hand-rolled three of those having read the rule.

`CLAUDE.md` goes 152 -> 180 lines against a documented ~200 target.

**Only rule 11, deliberately.** The other ten are not rewritten: rules 1-3 are
load-bearing prohibitions whose form is correct, the numbers are a public API
with four-figure citations, and a sweep of all eleven on one session's n=1
evidence would be the confident reconstruction rule 4 is about. The fifth
question is now asked and answered once, on the rule that failed, and the rest
stay as they are until something measures them failing.
