---
id: st-grain-shape-knows-the-reconcile-file
kind: story
feature: ft-small-shapes-hold
milestone: "ms-the-open-issues-close"
name: grain-shape reads <stem>-reconcile.md as a slot, not a note
status: building
owner:
depends_on: []
changelog: none
---

# grain-shape reads <stem>-reconcile.md as a slot, not a note

https://github.com/cdowin/agentic-sdlc/issues/106.

## Acceptance criteria

1. `checks/grain_shape.py::FRONTMATTERLESS_SLOTS` includes the reconcile file
   (`RECONCILE_FILE_NAME`), classified and capped like the handoff.
2. A reconcile file no longer counts as a note in the census line.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | test_grain_shape.py | new |
