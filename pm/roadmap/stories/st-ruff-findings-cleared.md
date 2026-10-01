---
id: st-ruff-findings-cleared
kind: story
feature: ft-the-pool-is-empty
milestone: "ms-the-backlog-is-empty"
name: The ruff waivers are gone
status: done
owner:
depends_on: []
changelog: none
---

# The ruff waivers are gone

Closes bg-ruff-waives-44-findings.

## Acceptance criteria

1. Every finding under `[tool.ruff.lint.per-file-ignores]` is fixed and the table is deleted.
2. An F811 or F841 that hid a dead test is named in the report with what the test now checks.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | - | `gates-extra --run lint` and `make unit` | - |
