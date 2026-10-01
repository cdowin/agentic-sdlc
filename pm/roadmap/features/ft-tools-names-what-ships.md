---
id: ft-tools-names-what-ships
kind: feature
milestone: "ms-the-loop-proves-itself"
name: tools/ names what ships to a consumer
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog: none
order:
  - "st-tools-readme-names-the-boundary"
---

# tools/ names what ships to a consumer

`tools/hooks/*`, `tools/dev/gdk_gate.sh` and `tools/dev/agent-worktree.sh` are installed copies
that ship (`install.py`). `tools/dev/pm_migrate.py` and `tools/publish_index.py` do not. Nothing
says so, and the `dev/` name suggests the opposite.

## Ship criterion

`tools/README.md` names every file under `tools/`, its installer source, or "dev-only".

## Proof budget

  cases: 1
  tier: unit
  lands in: tests/test_install.py
  what already covers this: test_install.py holds installed copies byte-current; add a case that
  every file under tools/ is named in the README.
