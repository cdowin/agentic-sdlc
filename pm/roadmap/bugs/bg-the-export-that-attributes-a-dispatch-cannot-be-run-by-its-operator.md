---
id: bg-the-export-that-attributes-a-dispatch-cannot-be-run-by-its-operator
kind: bug
milestone: ms-nothing-is-hand-rolled
name: dispatch --grain leads with an export an agent operator cannot deliver, and never names the serial path that needs none
status: closed
caused_by:
changelog: The auto-loaded execution rule now names `agentic-sdlc dispatch --grain <id>`, the serial path that attributes a dispatch with no export at all, and the `pm ledger record --grain` form for an orchestrator that cannot export into the courier's environment.
---

# the export that attributes a dispatch cannot be run by its operator

**The tool did the right thing three times and the rows are still
unattributed.** Nothing here is a defect in the courier, the fallback or D2;
the defect is that the surface leads with the one mechanism its operator
cannot reach and never names the one they can.

## What the package already ships

Three layers, all working:

  1. **`agentic-sdlc dispatch --grain <id>`** renders the contract preamble,
     the grain's id/kind/status/brief, AND:

         export GDK_LEDGER_GRAIN=<id>
         agentic-sdlc pm ledger record --grain <id>

  2. The **arrival's `have:` line** names the courier and the env var.
  3. A **fallback** in `_grain_from_tree` (`pm/cli.py:2353`): exactly one story
     in progress, use it; none or several, omit the key and NAME them. Read off
     the row's own `tree` snapshot so the grain and the tree cannot disagree.

## The evidence, and it acquits all three

0.7.0's three dispatch rows carry full `usage` — the first token counts this
tree has ever held — and no grain:

    po                     21:58  stories_in_progress=[]
    verification-builder   22:53  stories_in_progress=[census, storage]
    verification-builder   23:01  stories_in_progress=[census, storage]

Row 1: no story was in progress, because the dispatch was story PLANNING before
the milestone opened. Rows 2 and 3: two stories were in flight, and the verb
refused to pick — *"which one this row is about is not something this verb may
pick"* — exactly as D2 requires, since a row against the wrong story is
uncorrectable.

**Correct three times. Useless three times.**

## Root cause

`export GDK_LEDGER_GRAIN=<id>` is rendered under *"RECORDING THIS DISPATCH —
rendered here, run by you"*, and the hook reads it from the environment of
whoever spawned the subagent.

**The operator this package is written for cannot do that.** An LLM
orchestrating through a harness's dispatch tool has no way to put a variable in
the environment the `SubagentStop` hook will see: shell state does not persist
between its tool calls, and the dispatch tool takes no environment. The export
is deliverable by a human at a terminal who then starts a session, and by nobody
else.

So the mechanism that attributes a PARALLEL dispatch is unavailable precisely to
the operator who parallelises, and the fallback it leans on is the one thing that
breaks when they do.

## Fix — a word, not a capability

**Name the serial path, because it is the one that works.** One story in
`building` at a time and attribution is automatic, with no export and no hand
entry. `dispatch --grain` should say so where it currently prints an export:
*"with one story in progress this is already attributed; the export is for
concurrent dispatch."*

**And lead with the after-the-fact form for a concurrent one.** `pm ledger
record --grain <id> --tokens-total N --tool-calls N --duration-s N` is
reachable by any operator, needs no environment, and `--tokens-total` is
already documented as *"what a subagent completion actually reports — ONE
number"* — which is exactly the figure a dispatch returns. It is the third line
`dispatch --grain` renders and the last one a reader gets to.

## Not done here, and why

**Backfilling these three rows is refused.** The hook already filed each one
with its measured `usage`, duration and tool calls; a hand row naming the grain
would double the duration and the tool calls for one dispatch. The ledger is
append-only and history is not rewritten. They stay in `rows naming no grain`,
where they are visible and true.

## Out of scope

Making the hook derive a grain. No hook event carries one, which is D2's whole
premise, and a derived grain is the guess D2 forbids.

Serialising dispatch as a rule. Concurrency has a real cost here already — a
shared worktree — and that is a different argument in the 0.6.0 handoff.

## What landed

Both halves of the fix, in `src/agentic_sdlc/repo/pm/guidance/pm-execution.md`
(the SOURCE; the installed `.claude/rules/` copy is re-rendered from it):

  * **The serial path is named**, because it is the one that works: one story
    `building` at a time and the row attributes itself, since the courier reads
    the tree at the moment the agent stops. No export, no hand entry.
  * **`pm ledger record --grain <id> --tokens-total N ...` is named as the form
    for an orchestrator that cannot export** into the courier's environment —
    which is any operator whose shell state does not persist between tool
    calls. `--tokens-total` is already documented as "what a subagent
    completion actually reports — ONE number", which is exactly what a dispatch
    hands back.
  * **`agentic-sdlc dispatch --grain <id>` is named at all**, for the first
    time, in a surface an orchestrator loads.

Held by `TestACapabilityIsCitedWhereItsOperatorStands`
(`bg-rule-11-is-gated-in-one-direction-only`), so the citation cannot quietly
leave again.
