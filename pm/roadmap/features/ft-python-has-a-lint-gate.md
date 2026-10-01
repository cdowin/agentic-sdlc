---
id: ft-python-has-a-lint-gate
kind: feature
milestone: "ms-the-loop-proves-itself"
name: Python has a pinned lint gate, like shell
status: building
reviewed:
depends_on: []
consumed_by: []
changelog: none
order:
  - "st-ruff-is-a-pinned-dev-gate"
---

# Python has a pinned lint gate, like shell

Shell has `check shell` with a pinned shellcheck. Python has no lint at all. ruff goes in the
`dev` dependency group, so rule 1 (runtime deps) holds. It is this repo's gate, not a shipped
one.

## Ship criterion

`make lint` runs one pinned ruff version, is listed in this repo's `[gates] extra`, and passes
on the tree.

## Proof budget

  cases: 0 new
  tier: -
  lands in: -
  what already covers this: the gate itself, run by `gates-extra --run lint`.
