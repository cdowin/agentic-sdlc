---
id: bg-the-gate-help-names-one-of-its-four-rule-families
kind: bug
milestone:
name: check pm's opening line names the drift family and not the other three it runs
status: open
caused_by:
changelog: none
---

# the gate help names one of its four rule families

Found by the 50-module docstring audit in `st-every-module-opens-with-one-true-sentence`, which
judged it **kept, imperfect** rather than fixing it — correctly, because it is a consumer `--help`
surface under rule 6 and widening it is a minor bump, not a docstring edit.

## Symptom

`agentic-sdlc check pm --help` opens:

    check pm — the active PM tree's statuses do not contradict each other.

That is the **D family** and it is one of four the gate runs. The default roster, three lines
further down the same surface, is `D1/D2/D4/D5/D6/D11 + U1/U2/U3/U4/U5 + V1/V4/V5/V7`:

    D   statuses contradicting each other        — what the sentence describes
    U   RECORDING: a courier wired and writing nothing, a declared state no grain
        ever held, a grain that arrived with no disposition
    V   INTEGRITY: frontmatter, bindings that resolve to a grain of the right kind,
        an acyclic graph, a sequence naming a grain the parent does not hold
    R   the PLAN: a milestone on no plan, a version a release does not carry (opt-in)

Plus the `READY` and `WARN` families, which are neither drift nor integrity: a section a grain
scaffolded and never filled, a milestone past `todo` with no handoff.

## Root cause

**The sentence was true when it was written and the gate grew three families since.** Exactly the
shape of `bg-a-read-verb-names-three-of-its-thirteen-sections` — there, `pm ledger report`'s
`--help` named three of twenty-two blocks for the same reason — and exactly what rule 11 is for: a
reader standing in this surface learns the gate checks status drift, so the integrity and recording
rules are capabilities they do not know they have.

It is NOT the same defect as that one in one respect: the roster IS on this surface, enumerated by
rule id, three lines below. So this is an opening sentence that undersells its own page rather than
a capability with no mention anywhere. That is why it is a bug and not a blocker.

## Fix

One sentence, naming the four things the gate answers rather than one. The roster below it already
carries the detail, so the first line only has to stop being narrower than the page it opens.

**It is a minor bump** (rule 6: a `--help` line shape, and consumers grep these), so it lands in a
release that is already minor and it gets a `changelog:` sentence. A `changelog: none` on this
would be the quiet kind of lie.

The test that bites is the one the ledger-report bug already built: a gate comparing what a surface
NAMES against what the thing actually does. `tests/test_pm_ledger_report_sections.py::TestTheHelpNamesEveryBlockItPrints`
parses the roster out of `--help` rather than restating it; the equivalent here is the rule-id
roster against `KNOWN_RULES`, in both directions.

## Out of scope

The other gates' opening lines. A sweep across all five is a census and this is the one a reader
was standing in when they noticed; `agentic-sdlc check <gate> --help` for each is how somebody
would start it.
