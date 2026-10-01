---
id: st-init-pyproject-locks-with-many-dirs
kind: story
feature: ft-a-fresh-init-locks
milestone: "ms-the-open-issues-close"
name: init's tooling pyproject locks in a repo with two or more top-level dirs
status: building
owner:
depends_on: []
changelog: init's tooling pyproject declares no package to discover, so uv lock works in a repo with several top-level dirs.
---

# init's tooling pyproject locks in a repo with two or more top-level dirs

https://github.com/cdowin/agentic-sdlc/issues/109.

## Acceptance criteria

1. `installables/project-pyproject.toml` stops setuptools auto-discovery (e.g.
   `[tool.setuptools] py-modules = []`, or a static version with no build) so `uv lock` succeeds.
2. A fresh-project case with two top-level dirs runs `uv lock` (offline-safe: skip with a reason
   when uv cannot resolve without network).

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | integration | test_init_verb.py: two dirs, init, uv lock | new |
