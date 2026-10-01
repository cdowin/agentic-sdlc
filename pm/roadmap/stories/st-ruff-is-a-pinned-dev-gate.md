---
id: st-ruff-is-a-pinned-dev-gate
kind: story
feature: ft-python-has-a-lint-gate
milestone: "ms-the-loop-proves-itself"
name: ruff is a pinned dev-only gate in [gates] extra
status: planning
owner:
depends_on: []
changelog: none
---

# ruff is a pinned dev-only gate in [gates] extra

## Acceptance criteria

1. `ruff==<pin>` is in the `dev` dependency group in `pyproject.toml` and `uv.lock`; no runtime
   dependency is added.
2. A `lint` Make target runs `uv run ruff check src tests tools` with a small rule set that
   passes today (start at `E9`, `F`), configured in `pyproject.toml`.
3. `lint` is listed in this repo's `[gates] extra`; `gates-extra --run lint` passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1-3 | - | `gates-extra --run lint` on the branch | - |

Broken probe: add an unused import in a scratch file and see `lint` FAIL.

## Out of scope

Shipping ruff to consumers. `ruff format`. Fixing findings beyond the starting rule set.
