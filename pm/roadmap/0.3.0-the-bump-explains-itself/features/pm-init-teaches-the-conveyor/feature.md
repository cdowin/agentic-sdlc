---
id: 0.3.0/pm-init-teaches-the-conveyor
milestone: "0.3.0"
name: pm init teaches the conveyor, and an unused state is drift
status: done
reviewed: docs/reviews/0.3.0-pm-init-teaches-the-conveyor.md
phase:
depends_on: []
consumed_by: []
---


# pm init teaches the conveyor, and an unused state is drift

**The finding.** In the Trail adoption the agent hit `check pm` exit 2 ("this tree declares no
flow"), ran `pm init`, saw it print `appended the flow to devkit.toml:
[pm.states.milestone|feature|story|bug]`, watched `check pm` go green, and moved on. The states
were adopted as a CONFIG FIX. Nobody then asked whether the tree used them. It did not:
`building`, `reviewing`, `accepted` and `packaging` appeared **zero times** across 85 grains —
the tree only ever held `planning`, `ready` and `done`, and had for its whole life.

Every gate was green while that was true. **D4 asks "is this word declared", never "is this word
used"**, so a tree using two of eight states is indistinguishable from one using all eight. The
tool's most valuable idea — the conveyor — was invisible to the tool.

It also has a mechanical cost, not just a conceptual one: the ledger only takes `gate` cost rows
while a milestone is `in_progress`, so on that tree `check budget` reported "last measured:
nothing yet" and `verify --plan` had nothing to print. **The ladder is where the measurements
live**, and a project that never leaves the endpoints never gets them.

**The same feature from the other side, on the NullBound adoption.** That tree never declared a
flow at all, and the agent shipped a green `make check` over a PM CLI that was refusing every
work-moving verb. Asked afterward why it had not noticed, the answer was specific and fixable:

**the best writing about the conveyor in either package is in a file only new repos get.**
`project-devkit.toml` argues `[pm.states.*]` superbly — "the ONE LIVE SECTION in this file", why
there is no runtime fallback behind it, why `accepted` and `packaging` are `in_progress`, why a
word meaning finished-but-not-delivered belongs in `done`. `init` writes that file for a repo that
does not have one. **A consumer bumping a pin never sees a line of it**, and neither README
carries the argument. What the bumping agent read instead was godot-devkit's "Install — two pins",
which names two installer commands and one config key and does not mention the flow at all.

`pm vocabulary` is the one command that says the quiet part — it prints `(undeclared)` and then
the whole seed — and nothing routes anyone to it. It is not in the install path, not in the bump
path, and not in `check pm`'s error, which names `pm init` instead.

## Ship criterion

`pm init` prints the ladder it wrote AGAINST THE TREE — per kind, which declared states the tree
currently uses and which it has never used — so the sentence "this project now declares 8
milestone states; your tree uses 3" is on screen at the moment of adoption. And `check pm` gains
a rule for a declared-but-never-used state, reported as a WARN with the count, so the fact stays
visible after the install scrolls away.

## Proof budget

  cases: 3-4
  tier: pyunit
  lands in: the existing `pm init` and `check pm` test modules
  what already covers this: nothing — there is no assertion anywhere that relates the declared
    state set to the state set in use. That gap IS the bug.
