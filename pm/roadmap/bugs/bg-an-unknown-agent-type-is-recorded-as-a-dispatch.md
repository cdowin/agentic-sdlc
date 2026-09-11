---
id: bg-an-unknown-agent-type-is-recorded-as-a-dispatch
kind: bug
milestone: 
name: an unknown agent type is recorded as a dispatch
status: open
caused_by:
changelog: An agent type outside the installed roster is refused by name instead of recorded: `--by agent <type>` resolves against a roster the code is asked for, so a typo can no longer reach the ledger and be totalled in `pm ledger report`'s per-actor block.
---

# an unknown agent type is recorded as a dispatch

**It runs first because it is the model, not a defect in it** — the same reason
`bg-a-bug-is-a-grain-nested-in-a-parent` opened 0.6.0. Every other grain in this milestone assumes
an agent is a KIND the tool can resolve. Today it is a free string.

## Symptom

Probed on this tree while planning this milestone:

    $ agentic-sdlc pm feature building ft-a-read-verb-is-a-declaration --by agent wombat
    [pm] feature ft-a-read-verb-is-a-declaration: done -> building

Accepted, and written to `ledgers/ms-the-rule-reaches-the-work.jsonl` **twice** — a `disposition`
row and a `rung.leave` row, both carrying `"value": "agent wombat"`. `pm ledger report`'s
`time per actor` block will happily total the work done by an agent this package does not ship.

## Root cause

`install-agents` writes twelve definitions and `install.py` holds no roster the CODE can be asked —
only entries in `PLANS['install-agents']`, which is a delivery list, not a vocabulary. The
`--by agent <type>` answer is validated as a FLAG (does this state declare it?) and never as a
VALUE.

That is the gap `pm_cli.commands()` and `cli.KNOWN_GATES` already close for their own rosters. An
answer is *"recorded as a claim and never verified"* by design (0.5.0/D3) — but *"never verified"*
was meant to cover **whether the claim is TRUE**, not whether the thing it names exists. `--by me`
and `--by agent developer` are claims; `--by agent wombat` is a typo the tree will carry forever.

## Fix

The roster is asked of the code, and a type outside it is refused BY NAME listing what exists —
`check pm`'s D4 shape for states, applied to agents. A project's own roster is the project's
(rule 8), so what ships is the mechanism plus the twelve; a tree that installed none declares none
and the check stays silent, the way `[emit]` does.

## Out of scope

Verifying that the named agent actually ran. That is unobservable from here (0.6.0/D6) and the
`REGISTERED`-line lesson applies: count and name, never assert.
