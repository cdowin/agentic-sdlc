---
id: "ms-the-rule-reaches-the-work"
kind: milestone
name: the rule reaches the work
status: planning
depends_on: ["ms-a-move-is-an-event"]
branch:
version: 0.6.0
order:
  - "ft-the-dispatch-carries-the-contract"
  - "ft-a-guard-declares-its-violation-corpus"
  - "ft-a-shared-surface-owns-a-contract-test"
  - "ft-prose-that-restates-a-verb-is-rendered-or-gone"
  - "ft-the-changelog-is-a-field-and-a-verb"
  - "ft-a-read-verb-is-a-declaration"
  - "ft-a-warning-is-actionable-where-it-fires"
  - "bg-the-milestone-scaffold-still-mints-the-version"
  - "bg-pm-set-writes-a-scalar-its-own-gate-refuses"
  - "ft-the-vocabulary-is-constants-not-literals"
---

# 0.6.0 — the rule reaches the work

> ## Northstar: **an instruction that does not reach the work is not an instruction, and a gate that
> cannot fail is not a gate.** 0.5.0 spent a day finding second scoreboards in the CODE. Every one of
> them had a twin in the INSTRUCTIONS, and nothing was looking there.

0.5.0 closed thirteen features and found 93 review findings, 29 of them blocking. Sorting those
findings by what would have prevented each is the whole brief for this milestone, because they were
not random — they fell into four shapes, and three are mechanisable.

## What 0.5.0 measured, and could not act on

**Nothing repo-specific reaches a dispatched agent at spawn** (#15, measured in this repo, not
inherited). Not `CLAUDE.md` and its eleven hard rules. Not `.claude/rules/pm-execution.md` — 224
lines, `paths: pm/roadmap/**`. Not any skill BODY, at spawn or ever. The agent plans its approach in
a window where stdlib-only, the exit-code contract and the ladder do not exist for it, and — hard
rule 11's exact failure mode — with no signal that they exist.

Roughly 35 agents were dispatched during 0.5.0 and every brief hand-pasted a house-rules preamble.
That was assumed redundant. **It was the only carrier those contracts had.**

**Five tests asserted something true in a way that could not fail when it became false** (#14). A
derived-field guard walked `ast.Return` in a function whose only return is a bare name, so a planted
`suggested_action` — the exact opinion-shaped field rule 9 forbids — was invisible while the guard
reported 4-of-4. A "never a gate" case used constant-returning closures on a non-git tree, so no check
in it could observe the filesystem the bug wrote to. **Every one of them was cited to the orchestrator
as proof the property held.**

**351 of 359 warnings on a real consumer tree are unactionable** (#12). Rule 11 says absence is a
finding; it does not say every finding must be shouted forever. A surface people learn to scroll past
is a surface that has stopped working.

**Five shipped sentences contradicted shipped behaviour** — the seed said the reverse of `[emit]`'s
default, `telemetry-live` described an installer that had changed, the auto-loaded rule instructed
`pm story reviewing`, which exits 2. Meanwhile `docs/sdlc-protocol.md`, the one RENDERED document,
went through 22 grains in a day and never drifted once.

## The shape of the fix

**Contracts reach the work, or they are decoration.** A contract that must reach a dispatched agent
before its first tool call has exactly one home: the dispatch prompt. So the package generates that
preamble from the hard rules rather than an operator retyping it — retyping is how it drifted five
times in one day.

**A guard declares its own violation corpus, and a gate replays it.** The hook corpus is the shipped
precedent: `prepare-commit-msg --self-test` replays its own cases and `check hooks` counts which hooks
have one. A source-shaped guard with no corpus becomes a named line, never silence.

**Render, never restate.** Any sentence in a shipped file describing what a verb does is generated
from the verb or is a pointer to it. This is the single highest-yield rule available and the evidence
is already in the tree: the rendered document is the only one that never drifted.

**A shared surface owns a contract test.** Four of 0.5.0's blocking findings were one shape — a new
WRITER met an old READER, both halves individually correct, no test of either failing. `developer.md`
gained a checklist item asking builders to enumerate readers, but a checklist is a reminder; the suite
is the enforcement.

## And the last hand-maintained scoreboard

`ft-the-changelog-is-a-field-and-a-verb` widens the theme by one axis, deliberately. The rest of this
milestone is about instructions that cannot reach the work; the changelog is a DOCUMENT that cannot
check itself against the tree — but it is the same defect, one fact stored twice with no way to
disagree out loud.

0.3.0 retired `ROADMAP.md` because `order:` plus `pm roadmap` said it without a second copy.
`CHANGELOG.md` is the last one left, and 0.5.0's own `## Unreleased` is the argument: 469 lines,
roughly twelve agent authors, two concurrent editors who had to be told about each other, no binding
between any entry and the grain it describes, and an order that is append-order rather than the
`order:` the milestone already declares.

So the northstar reads a little wider than its title: **an instruction that cannot reach the work is
not an instruction; a gate that cannot fail is not a gate; and a document that cannot be checked
against the tree is not a record.**

## Constraints this milestone must respect

**The hard-rule NUMBERS are a public API.** Roughly 600 citations across source, tests and hooks —
`rule 4` alone appears 194 times. The list cannot be renumbered, reordered or merged; trimming happens
INSIDE a rule and anything new appends. Any plan that reorganises them is a 600-site migration wearing
a tidy-up's clothes.

**Do not grow the always-loaded file to fix this.** `CLAUDE.md` is 163 lines against a documented 200
target, and over-long files are followed LESS well. The answer is placement, not volume.

## Ship criterion

A dispatched agent receives this project's contracts before its first tool call, from a surface the
package generates rather than an operator retypes.

Every source-shaped guard in the tree declares a violation corpus and a gate replays it; a guard
without one is named, never silent.

No shipped file states what a verb does in prose that the verb does not generate.

`check pm`'s warnings are actionable at the rung they fire on — a warning nobody can act on where they
are standing is a defect, not information.

## Risks

- **This milestone is about instructions, so its own instructions are the test case.** If 0.6.0 ships
  a rule nobody can reach, it has disproved itself.
- **The temptation is a bigger `CLAUDE.md`.** Every measurement here says the opposite.
- **`pm new milestone <ver>` still mints the VERSION as the id** — `ms-0.6.0`, renamed by hand to get
  this file. That is the unlanded half of #8, and it is this milestone's own scaffolding failing at the
  thing 0.4.0 named.
