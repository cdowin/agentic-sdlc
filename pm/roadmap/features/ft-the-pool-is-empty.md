---
id: ft-the-pool-is-empty
kind: feature
milestone: "ms-the-backlog-is-empty"
name: The pool bugs close
status: done
reviewed:
depends_on: []
consumed_by: []
changelog: none
order:
  - "st-ruff-findings-cleared"
---

# The pool bugs close

The two pool bugs: bg-ruff-waives-44-findings and bg-denylist-misses-an-exported-config-env.

## Ship criterion

Both bugs are closed by a commit with a test or a gate that fails without it.
