---
id: bg-a-dispatch-nobody-records-leaves-the-spend-surface-empty
kind: bug
milestone: "ms-the-rule-reaches-the-work"
name:
status: open
caused_by:
changelog:
---

# a dispatch nobody records leaves the spend surface empty

**Measured today, in this milestone: six agents dispatched, `0 dispatch row(s)` in the ledger.**
Every spend column `pm ledger report` prints — dispatches, in, out, cache_create, cache_read,
tokens_total, tool_calls, duration_s — is `-` for all seventeen grains. The wall-clock half works
(2974s building, 636s reviewing, 6410s closed, rolled up correctly). The spend half has never held
one row, on this tree, across five milestones.

## Symptom

    $ agentic-sdlc pm ledger report ms-the-rule-reaches-the-work
    [ledger:report] ms-the-rule-reaches-the-work — spend per grain —
      0 dispatch row(s), 29 status row(s), 17 grain(s)

`check pm` U4 says so on every single run, and has been correct the whole time:

    WARN  cc-ledger-session.sh and cc-ledger-subagent.sh are wired in
    .claude/settings.json and no dispatch/session row has EVER landed in
    pm/roadmap/ — last hook-written row: never.

## Root cause — two halves, and only one of them is the tool's

**The harness half.** Whether a session fires `Stop`/`SubagentStop` here depends on the session's
project root, not on `.claude/settings.json`. A session rooted above this checkout runs the whole
milestone and fires nothing. `GDK_LEDGER_ROOT` exists for exactly this and nothing sets it. That is
an environment fact and the package cannot fix it — U4's message already says so, in full.

**The reach half, and this one IS ours.** `GDK_LEDGER_GRAIN` is the one `GDK_LEDGER_*` value no hook
event carries, so **nothing exports it for you** — the guidance says as much. The orchestrator
dispatching an agent knows the grain; nothing asks it to say so, and nothing offers to record the
dispatch afterwards. Rule 11's own test, asked honestly: *could someone hand-roll a thing this
package already does, and would anything have stopped them?* Six dispatches went by. Nothing stopped
anyone. `pm ledger record` exists, is documented, and was not reached for once.

## Why this is not just U4 doing its job

**U4 is a warning that has been correct and unactioned long enough to become furniture** — the exact
351-of-359 defect `ft-a-warning-is-actionable-where-it-fires` is landing in this milestone, sitting
in the one surface that measures every other one. It fires on `check pm`, which the operator runs
after editing the PM tree. The moment a dispatch could be recorded is the moment an agent RETURNS,
and no surface is standing there.

`bg-a-hand-recorded-dispatch-cannot-carry-a-total` (closed here) landed `--tokens-total`, so a
returned subagent's one reported number can now be written down. **That closed "cannot record it".
This is "nothing asks".**

## Fix — the reach, not the harness

The cheapest layer, in rule 11's words (*a word, a column, a warning, a caller — never a new
capability*):

  * **`pm feature|story building <id> --by agent <type>` already records WHO.** It is the arrival
    that knows a dispatch is starting and it is where `GDK_LEDGER_GRAIN` would be named. A `have:`
    line there — the ledger courier, and the env var it needs — costs one line and puts the
    capability in the surface somebody is standing in.
  * **`agentic-sdlc dispatch` (0.6.0) is the other half.** It renders a preamble at exactly the
    moment a dispatch begins and already takes `--grain`. It can print the `GDK_LEDGER_GRAIN` export
    and the `pm ledger record` line the operator will want on return. It renders; the operator runs.
  * **U4 should say how long it has been true.** *"never"* over five milestones reads the same as
    *"never"* over one afternoon, and those are different facts.

## Out of scope

Making the tool export anything, spawn anything, or fire a hook. Hard rule 2, and D1 (`emit`, never
execute). The package tells you the command; the operator runs it.

Fixing the harness's project-root behaviour. Not this package's, and U4 already names it.
