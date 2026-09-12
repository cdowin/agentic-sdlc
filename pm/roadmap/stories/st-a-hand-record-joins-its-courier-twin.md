---
id: st-a-hand-record-joins-its-courier-twin
kind: story
feature: ft-the-gates-agree-and-a-dispatch-counts-once
milestone: "ms-the-tool-agrees-with-itself"
name: a hand record joins its courier twin instead of adding a second dispatch
status: done
owner:
depends_on: []
changelog: `pm ledger report` counts a hand record carrying a courier row's `agent_id` as one dispatch and prints how many pairs it joined; `dispatch` now asks for `--agent-id` (#39).
done: b79c5c8 — report joins a hand record to its courier twin by agent_id
---

# a hand record joins its courier twin instead of adding a second dispatch

Issue: #39 (the body).

When no single story is `building`, the SubagentStop courier files a dispatch row naming no grain
in `<roadmap>/ledger.jsonl`. It carries the payload's `agent_id` (`cc-ledger-subagent.sh:336`). The
documented remedy is the `RECORDING THIS DISPATCH` block (`dispatch.py:170-177`) and the
`GDK_LEDGER_GRAIN` entry in `pm-execution.md`: *record it when the agent returns*, with
`pm ledger record --grain <id> --tokens-total N …`. That call appends a SECOND dispatch row to the
milestone ledger. Nothing links the pair, and `report` counts both. A tree that follows the docs
inflates its telemetry by construction, and the more carefully it attributes, the worse the
inflation.

**The join key is `agent_id`, and nothing else.** Both rows can carry it: `record` has had
`--agent-id` since before 0.8.0, the courier always passes it, and the rendered line never asked
for it. The issue also proposes matching on `agent_type` + `tool_calls` + `duration_s` within a
tolerance. **Refused: that is a guess from coincidence** (rule 9). A hand record without an
`agent_id` joins nothing, and is counted as it is today.

**The shape is the builder's, inside these contracts.** Ledger rows are append-only, and written
rows are never rewritten (0.4.0 D7). So the join happens either in the READER (the report counts one
dispatch per `agent_id` across every ledger it reads) or as an annotation row the reader resolves.
Whichever way it is done: the hand row's `grain` wins the attribution, and the courier row's
MEASURED numbers win the spend unless it has none. Record which one the builder chose, and why, with
`pm decide`.

## Acceptance criteria

1. The rendered `RECORDING THIS DISPATCH` block and `pm-execution.md` (source under
   `src/agentic_sdlc/repo/pm/guidance/`, re-installed with `--force`) both carry
   `--agent-id <the id the Agent tool returned>`.
2. A courier row with `agent_id: X` and no grain, plus a hand row with `--grain G --agent-id X`:
   `pm ledger report <milestone>` counts ONE dispatch, on G, and `rows naming no grain` no longer
   counts it.
3. The report prints a counted line naming how many courier/hand pairs it joined. Zero is printed as
   zero, never omitted (rule 11).
4. A hand row with an `agent_id` that matches no courier row is counted as one dispatch, as today.
5. The comparative form `pm ledger report <a> <b>` applies the same join, so its `delta` row carries
   no double count.
6. `dispatch`'s preamble line shapes are unchanged apart from the added flag, and the change is
   declared as a minor.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | the rendered-preamble case in the dispatch tests | amend |
| 2, 3 | unit | temp tree: one root-ledger courier row plus one milestone-ledger hand row, same `agent_id` | new, unless a report case can be amended |
| 4 | unit | the same case with a non-matching id | amend 2 |
| 5 | unit | the same tree, comparative form | amend 2 |

**Deliberately-broken probe:** revert the join, and confirm case 2 FAILS and names two dispatches.

## Semver

Minor: a new counted line in `report`, and a new flag in a rendered command.

## Out of scope

The self-attributing dispatch, where the courier copies the grain stamp out of the transcript. That
is `ft-a-concurrent-dispatch-attributes-itself`, in 0.10.0. The snapshot misplacement is the next
story.
