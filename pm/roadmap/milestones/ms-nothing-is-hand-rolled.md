---
id: "ms-nothing-is-hand-rolled"
kind: milestone
name: nothing is hand-rolled
status: planning
depends_on: ["ms-the-rule-reaches-the-work"]
branch: milestone/0.7.0-nothing-is-hand-rolled
version: 0.7.0
changelog:
order:
  - "bg-an-unknown-agent-type-is-recorded-as-a-dispatch"
  - "bg-a-decision-citation-resolves-to-the-wrong-milestone"
  - "bg-the-brief-undercounts-the-coupling-it-argues-from"
  - "ft-an-agent-is-a-registered-kind"
  - "ft-the-storage-layer-is-named-and-the-engine-stops-reaching-through-it"
  - "ft-a-phase-declares-what-it-hands-an-agent"
  - "ft-a-hand-rolled-command-is-a-missing-verb"
  - "ft-the-record-is-harvested-not-pushed"
  - "ft-the-suite-is-measured-like-the-source"
  - "ft-a-source-shaped-guard-is-named-as-one"
---

# 0.7.0 — nothing is hand-rolled

> ## Northstar: **if the operator had to hand-roll it, the tool is missing a verb; if an agent had to
> discover it, the phase is missing a declaration.** 0.6.0 made contracts REACH a dispatched agent.
> They arrive generic. The phase the agent is standing in knows what it needs and does not say.

0.6.0 proved that nothing repo-specific reaches a dispatched agent at spawn, and shipped
`agentic-sdlc dispatch` to fix it. It works, and it renders the same preamble whether the agent is
about to write code at `story building` or grade it at `feature reviewing`. **The carrier landed;
the payload is still generic.** That is the first half.

The second half came out of reading `orca-sdlc-kit`
([`docs/research/2026-09-08-orca-sdlc-kit.md`](../../../docs/research/2026-09-08-orca-sdlc-kit.md))
and, more usefully, out of watching how 0.6.0 was actually closed. **Eight things the operator
computed with `python3 -` during that close are facts the tree already holds and no verb will
answer.** One of them — the hard-rule citation count — is why the milestone brief said "roughly 600,
rule 4 alone 194" when the tree says 1,107 and 314. A number nobody can ask for is a number that
goes stale in the document that quotes it.

## The measurement

**No agent roster exists.** Twelve definitions ship through `install-agents`; `install.py` holds no
roster the code can be asked, and the `--by agent <type>` answer is a free string. Probed on this
tree: `pm feature building <id> --by agent wombat` was accepted and written to the ledger **twice**.
The tool will record a dispatch to an agent it does not ship.

**Eight hand-rolled commands in one close**, against three that were verbs and were used
(`install-* --diff`, `changelog`, `verify --plan`) — the control that makes the other eight a
finding rather than a mood:

    prose/code census over src/          ran by hand 6 times; only test_prose_census.py knows it
    prose/code census over tests/        nothing measures tests/ at all
    hard-rule citation count             the brief was 2x wrong for want of it
    AST-guard vs behaviour split         8,075 lines nobody has ever sorted
    per-module test growth in a range    git diff + regex, by hand, to argue a ceiling
    candidate agent transcripts          the ledger's own missing input
    which milestone declares a version   simulated semver-gate.yml in bash to find a live bug
    test-case count                      three different numbers, all called "the count"

**The suite is 36,295 lines and 10,830 of them are English.** `tests/` is 19% docstring and 11%
comment against `src/`'s 22% total — the essay style is gated in `src/` by the prose census, and
leaked into `tests/` where nothing measures it. The honest ratio is 20,604 lines of test code to
14,000 of source code, 1.47:1. The fat is the prose and the unsorted self-policing, not the tests.

## The shape of the fix

**A phase is the binding site, and it is already a table.** `[pm.arrive.<kind>.<status>]` carries
`ask`, `answers` and `have` today. What it does not carry is what to hand an agent that arrives
here. That is a fourth key, not a new mechanism, and it keeps `0.5.0/D1` intact: the tool RENDERS
the brief; the operator or an outer runner executes it.

**An agent is a registered kind.** The roster is asked of the code, the way `pm_cli.commands()` and
`cli.KNOWN_GATES` are, so an unknown type is refused by name listing what exists. A consumer's own
roster is theirs (rule 8) — what ships is the mechanism and the shipped twelve.

**A hand-rolled command is a missing verb, and the census is the feature list.** Each of the eight
becomes a verb, a flag on an existing verb, or a written reason why not. `pm ledger record` already
takes `--from-transcript` and cannot find one; that is a locator, not a capability.

**The storage layer is named, and the engine stops reaching through it.** Asked directly: is the
markdown handling separated from the SDLC? Measured, no. `core/markdown.py` is 65 lines of fence
scanning and is not the markdown layer; the real one is 385 lines buried mid-file in a 2,817-line
`model.py` that is simultaneously the config loader, the storage engine, the id grammar and the work
provider. **164 calls reach the storage mechanics from 13 modules outside it, against 71 to the
semantic layer** — the engine reaches THROUGH the abstraction 2.3x more often than it uses it, and
`field_of(path: Path, key)` at 89 sites means that many places hard-code *a grain is a file*.

`core/apply.py` already shows the fix: *"the one place this package mutates a filesystem"*, enforced
by `test_boundaries.py`. That rule was applied to WRITES and never to READS.

**A gate measures the suite the way it measures the source.** The prose census extends to `tests/`
with its own ceiling and its own argument, so the cut is a gate rather than an afternoon. The
source-shaped guards get named as such, because "8,075 lines police our own AST" is either the best
money in the repo or the tool checking its own homework, and nobody has ever sorted which.

## Constraints this milestone must respect

**The tool registers what it RENDERS and declares what it never runs.** Agents, prompts and specs
are registered because they are payload. Make targets are declared and never executed (`[verify]`).
**A registry of commands the tool would run is the plugin framework `0.5.0/D1` rejected** — that
line does not move, and everything this milestone wants sits on the near side of it.

**`sdlc work <item>` is not in scope, and the reason is rule 9.** A verb that advances an item to
its next phase requires the tool to know what "next" is, and `SDLC.md` says outright that it has no
opinion about which state may follow which. Making it legal means declaring a phase SEQUENCE — which
is defensible, is not a transition table (`0.5.0/D3`: the unit is the state arrived at, so backwards
stays an ordinary arrival), and is a `pm decide` rather than an implementation detail. **The arrival
is already the binding site**; a single entry point is a convenience built on top of a declared
sequence, and it comes after, not first.

**No line-count target on `tests/`.** The prose ceiling exists to make growth an argument somebody
makes, not a number somebody hits. Being over after removing all rot is a legitimate outcome to
state (`0.6.0/D7`, and the same reasoning that moved the ceiling rather than the reasoning).

## Ship criterion

An agent type this package does not ship is refused by name, listing the roster, wherever a type is
accepted — and the roster is asked of the code rather than listed twice.

A phase declares what it hands an agent, and `dispatch` renders THAT rather than a generic preamble;
a phase that declares nothing renders what it renders today.

Every one of the eight hand-rolled commands is a verb, a flag, or a written reason why not — and the
count that the 0.6.0 brief got wrong is one of the things a verb now answers.

`tests/` is measured the way `src/` is, with its own declared ceiling and its own argument, and the
source-shaped guards are named as a set rather than inferred by grepping for `ast.parse`.

No module outside the storage layer and a named exemption class passes a `Path` to ask what a grain
says, and `test_boundaries.py` enforces it the way it already enforces the write side.

## Risks

- **The census invites a verb nobody needs.** Eight hand-rolled commands is evidence, not a mandate;
  a verb whose only caller was one afternoon of this session is worse than the `python3 -` that
  produced it. Each one earns its place or gets the written reason instead.
- **A fourth key on `[pm.arrive.*]` is a config-surface change**, and rule 5 says a WORKFLOW key
  refuses BY NAME when absent. The absent case here is the common one and must stay silent.
- **This milestone is about the tool answering for itself, so its own brief is the test case.** The
  citation-count defect above is in the document that argued the constraint. If 0.7.0 ships a number
  nobody can ask for, it has disproved itself.
