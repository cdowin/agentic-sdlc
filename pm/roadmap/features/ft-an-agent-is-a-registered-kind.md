---
id: ft-an-agent-is-a-registered-kind
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: an agent is a registered kind
status: planning
reviewed:
depends_on: []
consumed_by: ["ft-a-phase-declares-what-it-hands-an-agent"]
changelog:
---

# an agent is a registered kind

The foundation the rest of the milestone stands on. `bg-an-unknown-agent-type-is-recorded-as-a-dispatch`
is the defect; this is the vocabulary that closes it.

## What exists today

Twelve definitions ship through `install-agents`. `install.py` knows them as entries in
`PLANS['install-agents']` — a DELIVERY list, keyed by destination path. Nothing exposes them as a
roster, so `--by agent <type>` takes any string and `pm ledger report`'s per-actor block totals work
against names the package never shipped.

Two rosters in this tree already do it right and are the pattern to copy: `pm_cli.commands()`
(hoisted in 0.6.0 for exactly this reason — a test was re-deriving it) and `cli.KNOWN_GATES`.

## The shape

A roster asked of the code, not listed twice. The kind is the definition's own `name:` frontmatter —
identity lives in frontmatter (0.4.0), and the filename is where the file lives, not what the agent
is. A type outside it is refused BY NAME listing what exists, the way an undeclared state is
(`check pm` D4).

**Rule 8 binds here.** The twelve are what THIS package ships; a consumer edits them after install
and rule 8 says we know nothing about which they keep. So the roster is read from what is
INSTALLED in the consuming tree, with the shipped twelve as what `install-agents` puts there — not
a constant naming twelve roles every project must have.

**A tree with no installed agents declares no roster and the check stays silent**, the way `[emit]`
does for a tree that wires no sink (0.4.0/D5). Refusing a free string on a tree that installed
nothing would break every consumer who dispatches by hand.

## Ship criterion

The roster is a function of the installed definitions, asked once, with no second list anywhere —
and a test proves adding a definition changes the roster with nothing else edited.

`--by agent <type>` outside the roster is refused at exit 2 naming the roster; nothing is written
and no ledger row lands. Watched failing at HEAD with `wombat`.

A tree that installed no definitions accepts what it accepts today, and a test says so.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_install.py` (it holds the installed set to its source already) and
    `tests/test_pm_verbs.py` (the arrival's answer grammar lives there)
  what already covers this: `test_every_roster_agent_carries_model_and_an_editable_config_section`
    walks the definitions today — it is the nearest reader and the roster should come from whatever
    it walks, not from a parallel list.

## Out of scope

Verifying the named agent ran. Unobservable from here; 0.6.0/D6's ruling — count and name, never
assert — applies unchanged.

Choosing a consumer's roles (rule 8).
