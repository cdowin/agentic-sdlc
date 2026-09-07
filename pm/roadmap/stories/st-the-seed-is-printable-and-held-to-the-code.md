---
id: st-the-seed-is-printable-and-held-to-the-code
feature: ft-the-config-is-the-model
milestone: "ms-0.4.0"
name: pm config --seed prints the model, and a test holds it to the defaults
status: planning
owner:
depends_on: []
kind: story
---

# pm config --seed prints the model, and a test holds it to the defaults
A bumping consumer can read the model in one command, and the file it reads cannot drift from the
tool. `init` serves a new repo; nothing served the other ninety-nine percent of a tool's life,
which is bumps — and the seed is the surface that actually taught one adopting agent what the
conveyor is.

## Acceptance criteria

1. `pm config --seed` prints the current seed with its arguments and **writes nothing**. Exit 0.
2. A test compares every COMMENTED default in the seed to the code's actual default, failing **by
   name** on the first that drifts. This case is the feature: individual defaults are covered one
   key at a time by the gates that read them, and nothing has ever compared the two.
3. The declarations/knobs split is stated in the seed itself — a declaration is spelled out with
   its argument, a knob stays commented at its stock value — so it decides the next key rather
   than being re-argued per key.
4. **The byte-identical guarantee is restated as GATES-ONLY**, in `CLAUDE.md` and the CHANGELOG,
   with the workflow carve-out named: every gate key has a real default, and the FILE is not
   optional, because `[pm.states.*]` has nothing behind it and a tree without it has no working
   `pm`. The existing byte-identical test narrows to gates, which is what it was always asserting.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | one case: exit 0, the text, and `porcelain` unchanged | new |
| 2 | unit | the seed-vs-defaults comparison | new — this IS the feature |
| 4 | unit | the byte-identical case, narrowed to gate keys and asserting the workflow half REFUSES | amend |

## Out of scope

Making any currently-optional key required. A new required key still has to earn it the way
`[pm.states.*]` did.
