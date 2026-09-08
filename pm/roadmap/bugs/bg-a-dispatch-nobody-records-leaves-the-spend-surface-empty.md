---
id: bg-a-dispatch-nobody-records-leaves-the-spend-surface-empty
kind: bug
milestone: "ms-the-rule-reaches-the-work"
name:
status: open
caused_by:
changelog: A dispatch can now be recorded from the surface it starts in: `pm story|feature building --by agent <type>` names the ledger courier and the `GDK_LEDGER_GRAIN` it needs on its `have:` line, `agentic-sdlc dispatch --grain <id>` renders the export and a pasteable `pm ledger record` line, and `check pm` U4 says how long "never" has been true.
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

## What landed — 0.6.0

All three, and none of them a new capability.

**The `have:` line.** `[pm.arrive.feature.building]` and `[pm.arrive.story.building]` in
`devkit.toml` gained a second entry, and the seed's commented example gained the matching node. What
`pm story building <id> --by agent <type>` now prints, beside the worktree line it already printed:

    have: tools/hooks/cc-ledger-subagent.sh is installed — records this dispatch's spend when
    GDK_LEDGER_GRAIN=<id> is exported before the spawn; `pm ledger record --grain <id>` files it by
    hand on return

**`dispatch --grain` renders both commands.** `_recording()` in `dispatch.py`, emitted only with
`--grain`, and it renders — the operator runs (D1, and hard rule 2):

    RECORDING THIS DISPATCH — rendered here, run by you:
      export GDK_LEDGER_GRAIN=<id>
      # on return, add what the agent reported: --tokens-total N --duration-s N --tool-calls N
      agentic-sdlc pm ledger record --grain <id> --agent-type <role>

The printed line is proven to be one the verb ACCEPTS —
`tests/test_dispatch.py::TheDispatchCanBeRECORDED::test_the_record_line_it_prints_is_one_the_verb_ACCEPTS`
lifts the exact rendered string out of the preamble and runs it in a scratch tree. A printed command
that errors is worse than none.

**U4 says how long.** `_recording_span()` reads the oldest row already in the ledgers this branch
walks — no new file, no new stamp:

    last hook-written row: never in the 2d 9h these ledgers have been recording

It says how long THESE LEDGERS have been recording, not how many milestones the tree has had, which
is the fact the rows can actually support. The rule-4 probe is
`test_how_long_never_has_been_true_is_read_off_the_oldest_row`: a 40d plant says `40d`, a 3h plant
says `3h`, and a tree with nothing dateable says `never.` with no span rather than inventing one.

## What this does NOT fix, and it is the larger half

**The harness half is untouched and is not the package's.** Measured again while closing this
milestone: this orchestrating session's project root is the checkout's PARENT, so this repo's
`.claude/settings.json` was never loaded — proven independently by running `git commit` with no
pathspec and watching it reach git unblocked by `cc-commit-pathspec.sh`. No `Stop` or `SubagentStop`
hook fired for any of the agents dispatched during this close, and none could have.

So the spend surface is still empty on this tree, and the honest claim is narrower than "fixed": a
dispatch can now be recorded from the surface it starts in, by an operator who reads the line. Four
agents were dispatched closing this milestone and their totals were recorded by hand from the lines
this bug added. That is the reach half working; the harness half needs `GDK_LEDGER_ROOT` in the
environment, which no file in this repo can set.
