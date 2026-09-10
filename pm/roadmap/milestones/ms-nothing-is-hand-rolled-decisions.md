Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ms-nothing-is-hand-rolled  — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-10 — the citation rule resolves the qualified form and says nothing about the bare one

`bg-a-decision-citation-resolves-to-the-wrong-milestone` asked for a rule where
**a bare `D<n>` outside its own decisions file is a finding.** Measured before
implementing, that rule is wrong far more often than it is right, and the
measurement is the whole argument.

    [doc] scope     33 bare `D<n>`, of which 32 are `check pm` GATE RULE IDS
                    — D12 (a belt is its checks), D4 (an undeclared status),
                    D9/D10 (the branch rules). Bare is CORRECT there: the gate
                    ids are one flat namespace that never restarts.
    pm/roadmap/     343 bare, ~273 with no gate context — decision citations,
                    against 20 in the qualified `<version>/D<n>` form.

**The two namespaces are indistinguishable by shape.** `check pm` declares
D1, D2, D4, D5, D6, D9, D10, D11, D12; milestone decisions run D1–D12 as well.
A gate that flagged the bare form would fire on 32 of 33 correct citations in
the always-loaded docs — rule 4's first sin inverted, a gate that reports drift
where there is none, which is the gate somebody deletes.

**Rejected: flag the bare form anyway and allow-marker the gate ids.** That is
32 `<!-- doc-scan:allow -->` markers in the surface an agent reads every
session, to catch a defect class that has bitten once. The marker exists for a
deliberate exception, not for the majority reading.

**Rejected: gloss-matching.** The original defect carried its own tell — ``D1
(`emit`, never execute)`` against a D1 titled *a parent does not close over
unresolved children* — so a rule could compare the parenthetical against the
decision's title. It is a heuristic over prose, it fails open on any citation
with no gloss, and a fuzzy gate is the one whose failures get re-run rather
than read.

**Taken:** the qualified form is resolved and the bare form is not read at all.
21 citations are graded today. What this does NOT catch is the exact defect
that filed the bug — a bare `D1` resolving to a real ruling that says something
else — and that is stated in the grain rather than implied away. Closing that
needs the tree to adopt `<version>/D<n>` as mandatory in grains, which is a
273-site migration and a decision of its own, not a line in this close.
