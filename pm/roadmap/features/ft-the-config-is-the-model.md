---
id: ft-the-config-is-the-model
milestone: ms-0.4.0
name: The config states the model, and every gate default is still real
status: planning
reviewed:
phase:
depends_on: ["ft-the-pools-are-the-tables"]
consumed_by: []
kind: feature
order:
  - "st-the-seed-is-printable-and-held-to-the-code"
---

# The config states the model, and every gate default is still real

**The measured finding.** The thing that taught the NullBound adopting agent what the conveyor IS
was not the README and not `--help` — it was `project-devkit.toml`, where each key sits at its
stock value with its argument beside it. And the reason that agent missed the conveyor is that it
never saw the file: `init` writes it for a repo that has none, and a bumping consumer gets nothing.
**The best teaching surface in the package was the one a consumer could not reach.**

## Declarations and knobs want opposite treatment

Two different things live in this file:

- **Declarations** — what this project's model IS: `[pm.states.*]`, the pool dirs, `version_at`.
  Reading these tells you how the system thinks, so they are spelled out in full and argued where
  they sit. The shape of the config is the shape of the model.
- **Knobs** — thresholds and toggles: `cap`, `[tests] budget`, `exclude_prefixes`. These teach
  nothing and stay commented at their stock value, invisible until needed.

The file already does this by habit — *"every section is COMMENTED OUT and carries the stock
default, with ONE exception, `[pm.states.*]`, which is LIVE"*. Naming the split makes it a rule
that decides the NEXT key rather than a pattern each key re-argues.

## The honesty rule is halved, not dropped

Today: *"a repo with no devkit.toml behaves byte-identically to one declaring every commented
default."* That conflates two claims, and only one of them survives contact with a tool that has a
workflow half:

1. **Every key has a real default** — an absent key behaves exactly like its stock value. This is a
   CORRECTNESS property, it is what makes a default trustworthy, and it stays, tested.
2. **The file itself is optional** — this is an ADOPTION claim and it is now false. A PM tree
   cannot work without a declared flow; `[pm.states.*]` proves it by refusing every work-moving
   verb, which is exactly how one consumer's CLI went dead.

So: **every GATE key has a real default; the FILE is not optional.** The package already says the
distinction out loud one sentence later — *"a GATE ships stock defaults and a commented default IS
the default. A WORKFLOW does not"* — and has never generalised it. The byte-identical test narrows
to gates, which is what it was always really asserting.

## Two things follow

**`pm config --seed` prints the current seed with its arguments**, so a BUMPING consumer can diff
its file against the model in one command. `init` serves a new repo; nothing serves the other
ninety-nine percent of a tool's life, which is bumps.

**A test holds the seed's commented defaults to the code's actual defaults.** A teaching surface
that drifts from the tool is worse than an absent one, because it is confidently wrong — and this
seed is now load-bearing documentation, not a courtesy.

## Ship criterion

Every declaration in the seed is live or spelled out with its argument; every knob is commented at
its stock value. A test asserts each commented default equals the code's default, failing by name
on the first that drifts. `pm config --seed` prints the seed and writes nothing. The
byte-identical guarantee is restated as gates-only, in the file and in the CHANGELOG, with the
workflow carve-out named rather than implied.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: the config module's test, beside the existing default-reading cases
  what already covers this: individual defaults are covered one key at a time by the gates that
    read them. Nothing compares the SEED TEXT to those defaults, which is the drift this feature
    exists to stop — that case is the feature.

## Out of scope

Making any currently-optional key required. The rule change is about what the file IS, not about
adding declarations; a new required key still has to earn it the way `[pm.states.*]` did.
