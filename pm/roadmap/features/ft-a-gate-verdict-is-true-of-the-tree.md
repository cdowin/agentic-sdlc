---
id: ft-a-gate-verdict-is-true-of-the-tree
kind: feature
milestone: "ms-a-consumer-can-take-the-bump"
name: a gate verdict is true of the tree
status: done
reviewed: docs/reviews/2026-09-11-0.8.0-a-gate-verdict-is-true-of-the-tree.md
depends_on: []
consumed_by: []
changelog: none
order:
  - "st-a-roster-that-omits-a-stock-on-rule-says-so"
  - "st-check-doc-reads-a-code-span-across-a-line-break"
  - "st-the-semver-gate-admits-the-next-hotfix"
  - "st-a-state-the-ledger-shows-held-is-not-called-never-held"
---

# a gate verdict is true of the tree

Issues: #19 #26 #27 #30.

Four verdicts in one release that were false, in both directions rule 4 names:

    PASS over drift     #19  a pre-0.6.0 `[pm] checks` roster follows the D3 retirement message,
                             D11 goes silent with the RETIRED_FIELDS loop inside it, and 259
                             findings print PASS
                        #26  `check doc` reads code spans one line at a time, so a status call
                             wrapped across a line break is invisible (and so is the shipped one)
    FAIL over no drift  #27  semver-gate admits the first hotfix on a release and refuses the
                             second; the consumer merged over the red check
    a WARN that lies    #30  U1 says "never held" by reading only CURRENT statuses, so every
                             transient rung on a tree at rest looks unused, and the ledger holds
                             the rows that show otherwise

They are separate modules: `pm/vocabulary.py` + `checks/pm.py`, `checks/doc.py`,
`installables/ci-semver-gate.yml`, and `pm/inventory.py` + `checks/pm.py`. **#19 and #30 both touch
`checks/pm.py`**, and so does `ft-every-printed-command-runs-in-a-stock-consumer` (the D11/D12 hint
strings), so those three run serially.

## Ship criterion

A deliberately broken probe for each story, in a scratch copy of a fixture:

- a pre-0.6.0 roster over retired fields is not PASS without saying which stock-on rules it omits;
- a wrapped undeclared status call FAILs;
- `0.28.4.1 → 0.28.4.2` over a done `0.28.4` passes, and a bump that is neither a hotfix nor a done
  milestone's version is still refused;
- a state named in the ledger's `status` rows is not reported as never held.

**Accepted means closed on GitHub:** #19, #26, #27 and #30 are each closed with a comment citing this
feature and its commit hash(es) (SDLC.md §2).

## Proof budget

  cases: 6–8. These are gate semantics, so each story needs the probe that turns the gate red
    (the ladder's rule).
  tier: unit for the three Python gates; the semver-gate block is shell inside YAML, and its current
    test pattern decides its tier. Search first
  lands in: tests/test_check_pm*.py, the check doc tests, the ci-semver-gate tests
  what already covers this: each gate has cases for what it catches. None has the case that shows it
    going silent (#19, #26) or refusing a legitimate input (#27).
