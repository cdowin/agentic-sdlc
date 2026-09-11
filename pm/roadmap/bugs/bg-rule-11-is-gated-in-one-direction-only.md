---
id: bg-rule-11-is-gated-in-one-direction-only
kind: bug
milestone: ms-nothing-is-hand-rolled
name: a citation is checked for resolving and a capability is never checked for being cited — 13 of 48 verbs
status: open
caused_by:
changelog: none
---

# rule 11 is gated in one direction only

**Why an agent hand-rolled three capabilities this package ships, in the
milestone named `nothing is hand-rolled`.** Not discipline — a missing boolean.

## The measurement

Of **48** routed verbs, **13** are named in no surface an ORCHESTRATOR loads
(`CLAUDE.md`, `SDLC.md`, `.claude/rules/*.md`, `.claude/skills/*/SKILL.md`),
matched as an invocation rather than a bare word:

    named NOWHERE an operator or an agent loads (8)
      check hooks   check repo-hygiene   check shell   gates-extra
      pm bug        pm get               pm milestone  pm next

    in an agent DEFINITION only, and in no auto-loaded surface (5)
      check budget  check doc  dispatch  lesson record  lesson show

**`dispatch` is the one that cost this session.** It is cited in the shipped
agent definitions — which are the PAYLOAD handed TO a dispatched agent — and in
nothing the agent doing the DISPATCHING reads. So the verb whose entire purpose
is to be run at the moment of dispatch is advertised to everyone except the
operator at that moment.

## Root cause — 0.6.0 fixed the payload and never measured the carrier

`ft-a-surface-reaches-its-reader-or-it-is-decoration` opened with a probe:
a dispatched agent received **zero** lines of this project's surfaces. Sweep 1
fixed that from the payload side — every definition now names its role's verbs,
and `test_every_verb_an_agent_definition_names_resolves_against_the_cli`
resolves all 71 citations against the router.

**Both shipped tests run the same direction.**

    definition -> non-empty   test_every_agent_definition_names_the_verbs_...
    definition -> CLI         test_every_verb_an_agent_definition_names_...
    CLI -> surface            NOTHING

So **"every verb a definition names exists"** is a boolean, and **"every verb is
declared where its operator reads"** is prose. Rule 11 is two claims and only
one of them can fail.

(Both halves were first written here as double negatives — "no verb exists that
no surface names" — which is the same claim with the action removed.
`bg-the-always-loaded-surface-states-properties-not-procedures` is that habit
measured.)

The same asymmetry one surface over: `pm ledger report` prints **13** sections
and its `--help` declares **3** with their columns in order
(`bg-a-read-verb-names-three-of-its-thirteen-sections`). Citations are checked
for resolving; capabilities are not checked for being cited.

## What it cost, measured

Three capabilities hand-rolled in one session, each already shipped:

  * `agentic-sdlc dispatch --grain <id>` — renders the contract preamble, the
    grain, the ladder, the vocabulary AND the attribution export. Three dispatch
    prompts were written by hand instead, and all three dispatch rows landed
    unattributed.
  * `ledger report`'s `gate cost` section — `runs`, `first_ms`, `last_ms`,
    `delta_ms`, both censuses. Reproduced by hand in Python.
  * `ledger report`'s `session deltas` section — differences a cumulative
    courier's rows. Reproduced by hand, and the hand version nearly reported
    1.1 BILLION tokens by summing what that section knows to difference.

## Fix — invert the test that exists

The primitive is already built. `tests/test_install.py:1832` assembles every
routed verb from the router's OWN tables (`pm_cli.commands()`,
`root_cli.KNOWN_GATES`, `driver.CLOSE_OPERATIONS`, `install.PLANS`,
`ready_for.KINDS`, `ledger_commands()`) — `pm cli.commands()` was added in 0.6.0
for precisely this census, and is used today only in the resolving direction.

  1. **Every routed verb is cited in at least one surface its operator loads**,
     with a NAMED exemption roster carrying a reason per entry, in the shape
     `CONFIG_IMPORT_ALLOWLIST` already uses — and the stale-entry half, so an
     exemption for a verb that no longer exists fails the build. Fails today at
     13 of 48.
  2. **Every section a read verb PRINTS is named in its `--help`.** Fails today
     at 3 of 13.

Then the cheap surface edits the gate demands: `dispatch --grain <id>` belongs
in `.claude/rules/pm-execution.md`, which is the surface an orchestrator is
standing in at the moment it dispatches.

## Why a gate rather than a better rule

Rule 11 already says this, in words, twice. The words did not hold — and the
milestone that wrote them is the one whose own brief mis-stated a citation count
by 2x (`bg-the-brief-undercounts-the-coupling-it-argues-from`). 0.6.0's
northstar is the argument: *an instruction that does not reach the work is not
an instruction, and a gate that cannot fail is not a gate.* This is the second
half applied to the first.

## Out of scope

Naming every verb in the always-loaded file. `CLAUDE.md` is held to a length
target on purpose; the gate asks for ONE surface an operator loads, and the
auto-loaded rule and the skill are both that.

Restating what a verb does. `ft-prose-that-restates-a-verb-is-rendered-or-gone`
rules on that: a pointer, never a paraphrase.
