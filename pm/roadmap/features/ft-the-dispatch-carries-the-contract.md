---
id: ft-the-dispatch-carries-the-contract
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: the dispatch carries the contract
status: reviewing
reviewed: docs/reviews/2026-09-07-0.6.0-the-dispatch-carries-the-contract.md
depends_on: []
consumed_by: []
order:
  - "st-the-dependency-rule-states-its-real-reason"
changelog: `agentic-sdlc dispatch [--grain <id>] [--role <name>]` renders the preamble a dispatched agent needs before its first tool call: the project's contract POINTERS from the new `[dispatch]` declaration, plus its ladder, gate roster and state vocabulary read from `[verify]`/`[checks]`/`[pm.states.*]` — so the derived half is never retyped. The shipped agent definitions point at it instead of carrying a hand-edited project block.
---

# the dispatch carries the contract

**Nothing repo-specific reaches a dispatched agent at spawn.** Not `CLAUDE.md` and its eleven hard
rules. Not `.claude/rules/pm-execution.md` — 224 lines, `paths: pm/roadmap/**`, which loads on a file
match the agent has not made yet. Not any skill BODY, at spawn or ever. The agent plans its approach
in a window where stdlib-only, the exit-code contract and the ladder do not exist for it, and — hard
rule 11's exact failure mode — **with no signal that they exist.**

Roughly 35 agents were dispatched during 0.5.0 and every brief hand-pasted a house-rules preamble.
That was assumed redundant. It was the only carrier those contracts had, and retyping is how five
shipped sentences came to contradict shipped behaviour in a single day.

## The same defect is already in the shipped agent definitions

Every file under `.claude/agents/` opens with a hand-maintained block:

    ## Project config (yours to edit after install)
    project:         <one line: what this is, and its stack>
    per-change gate: make precommit
    full gate:       make milestone
    pm tree:         pm/roadmap/

Three of those four are **already declared in `devkit.toml`** — `[verify]` names the rungs, `[pm]`
names the roadmap, `[checks]` names the gate roster. The block is a second copy an operator edits
after install, in thirteen files, with nothing able to say when it drifts. That is `ROADMAP.md` and
`CHANGELOG.md` a third time.

## The shape

**A contract that must reach a dispatched agent before its first tool call has exactly one home: the
dispatch prompt.** So the package renders it:

    agentic-sdlc dispatch [--grain <id>] [--role <name>]

**What it RENDERS is what the tool already knows** — the ladder from `[verify]`, the gate roster from
`[checks]`, the state vocabulary from `[pm.states.*]`, the exit-code contract, and the grain's own
id, status and file. None of that is retyped, so none of it can drift.

**What it POINTS AT is what the project authored** — `[dispatch] contracts`, a declared list of paths.
The preamble does not copy them. Copying is how a 163-line file becomes a 163-line paste in every
brief, and the milestone's own constraint says the answer is placement, not volume. It names them and
says read them first, which is the rule 11 fix: the measured failure was not that the agent disobeyed
the rules, it was that **it had no signal they existed.**

**A declared contract path that resolves to nothing is exit 2.** A pointer to a missing file is the
D1 defect, and a preamble that names a file nobody can open is worse than one that names none.

## Ship criterion

A dispatched agent receives this project's contracts before its first tool call, from a surface the
package generates rather than an operator retypes.

`agentic-sdlc dispatch` renders: the project line, the declared contract pointers, the ladder, the
gate roster, the vocabulary, the exit-code contract, and — with `--grain` — that grain's id, status
and document path. Every derived part comes from the same reader the verb it describes uses.

`[dispatch]` is a WORKFLOW key (hard rule 5): it has nothing behind it, the reader refuses BY NAME
when it is absent, and a declared path that does not resolve is exit 2.

The shipped agent definitions stop carrying a hand-typed project block and point at the verb instead,
so the thirteen copies become one rendering.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: a new `tests/test_dispatch.py` — this is a new verb with its own config section, and the
    nearest existing module (`test_cli_surface.py`) grades surfaces rather than rendering
  what already covers this: nothing. `test_install.py` holds the agent definitions to their SOURCE,
    which is why the hand-typed block is byte-current and still wrong — it proves the copy was
    installed faithfully, never that what it says is true.

## Out of scope

Dispatching. The package renders a preamble; it does not spawn an agent, choose a model, or know
what a subagent is. Rule 2 and rule 8 both.

Copying a contract's TEXT into the preamble. Named above and rejected there.
