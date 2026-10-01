---
id: ft-check-reads-the-verify-rungs
kind: feature
milestone: "ms-the-open-issues-close"
name: check reads the [verify] rungs
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-check-refuses-a-chained-rung"
---

# check reads the [verify] rungs

https://github.com/cdowin/agentic-sdlc/issues/103. A chained `[verify]` rung is refused only when a reader runs it; no `check` gate reads it, so it is found late.
