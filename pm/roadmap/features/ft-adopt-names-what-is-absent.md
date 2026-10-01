---
id: ft-adopt-names-what-is-absent
kind: feature
milestone: "ms-the-loop-proves-itself"
name: adopt names every absent piece of the setup
status: done
reviewed:
depends_on: []
consumed_by: []
changelog: adopt names each absent installed file, unarmed hooks, and a [dispatch] contract that is missing or outside [doc] scope.
order:
  - "st-adopt-names-an-absent-installable"
  - "st-adopt-reads-every-workflow-section"
---

# adopt names every absent piece of the setup

DeepWiki proposed a `doctor` verb. 2.0.0 retired `preflight`, the same idea, so this grows
`adopt` instead. Today `adopt` skips an installable that is absent (`belts.py::adopt`,
`if not target.is_file(): continue`) and never reads `[dispatch]` or `[integrate]`. Rule 11:
absence is a finding.

## Ship criterion

`adopt <version>` on a tree with a deleted CI workflow, unarmed hooks, and a `[dispatch]`
contract outside `[doc]` scope prints one named line for each and exits 1.

## Proof budget

  cases: 3 to 4
  tier: unit
  lands in: tests/test_adopt.py
  what already covers this: test_adopt.py covers pin, drifted installables and refused config
  keys. Nothing covers an absent file or the two unread sections.
