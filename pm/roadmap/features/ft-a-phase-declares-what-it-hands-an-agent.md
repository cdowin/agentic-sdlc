---
id: ft-a-phase-declares-what-it-hands-an-agent
kind: feature
milestone: 
name: a phase declares what it hands an agent
status: planning
reviewed:
depends_on: ["ft-an-agent-is-a-registered-kind"]
consumed_by: []
changelog:
---

# a phase declares what it hands an agent

**The milestone's first half, and the direct continuation of 0.6.0.** That milestone proved nothing
repo-specific reaches a dispatched agent at spawn and shipped `agentic-sdlc dispatch` to carry it.
The carrier works. The payload is generic: the same preamble renders whether the agent is about to
write code at `story building` or grade it at `feature reviewing`.

Chris's framing, and it is the right one: **we are relying on discoverability where we could be
explicit.** The agent can find `CLAUDE.md`, the ladder and the vocabulary because `dispatch` names
them. What it cannot find is what THIS PHASE wants, because nothing declares it.

## The binding site already exists

`[pm.arrive.<kind>.<status>]` is a table keyed on exactly the thing that should decide the brief —
the state a grain is arriving at. It carries three keys:

    ask     = "what is building this?"        the question
    answers = ["--by me", "--by agent <type>"] both replies, pre-typed
    have    = { "<path>" = "<why>" }           capabilities bound to this state

A fourth is the whole feature:

    dispatch = { role = "developer", agent = "claude", prompt = "briefs/developer.md" }

`role` selects from `ft-an-agent-is-a-registered-kind`'s roster. `prompt` POINTS at a file the
project authored — never inlined, for the reason `[dispatch] contracts` already gives: a 163-line
paste in every brief is volume, and the fix is placement.

## It renders; it never runs

`0.5.0/D1` is not bent here and this section is the argument. The tool emits a COMPLETE, DECLARED
dispatch — role, agent, contract pointers, the phase's own prompt — at the moment the operator moves
the grain. Something else executes it: a person, a shell loop, an MCP client, an outer runner. That
is what `have:` and `next:` already do at every arrival; this is the same breadcrumb with the brief
attached.

**The difference it makes is that the brief stops being written from memory.** Six agents were
dispatched during 0.6.0 and every prompt was hand-composed by the orchestrator.

## What must stay silent

Rule 5: a WORKFLOW key refuses BY NAME when its section is absent — but **absent is the common case
here**, and a phase that declares no `dispatch` must render exactly what it renders today. A tree
that declares none must be byte-identical to one before this feature. That is the first test.

## Ship criterion

`[pm.arrive.<kind>.<status>] dispatch` is read, and `agentic-sdlc dispatch --grain <id>` renders the
brief the grain's CURRENT state declares — role, agent and the project's prompt pointer — rather than
a generic preamble.

A `role` outside the roster is exit 2 naming the roster; a `prompt` resolving to no file is exit 2
naming the path (the rule `[dispatch] contracts` already holds).

**A phase declaring no `dispatch` renders byte-identically to 0.6.0**, proven by a case that
compares the two.

The arrival itself names the brief where the operator is standing, the way `have:` does.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_dispatch.py` (the verb's own module) and `tests/test_config_seed.py` (the
    seed carries the key commented at the value the code holds — rule 5's byte-identical guarantee)
  what already covers this: `TheDispatchCanBeRECORDED` proved the preamble grows a section without
    disturbing the rest; the byte-identical case is that shape inverted.

## Out of scope

`sdlc work <item>` — a single entry point that advances a grain to its next phase. It needs the tool
to know what "next" is, and rule 9 says it has no opinion; making it legal means declaring a phase
SEQUENCE, which is a `pm decide` and a milestone of its own. The arrival is already the binding site
and this feature does not need it.

Executing anything. Ever.
