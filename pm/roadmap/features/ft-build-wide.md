---
id: ft-build-wide
kind: feature
milestone: "ms-build-wide-integrate-once"
name: Builders spot-check and stop, the lead proves a batch once
status: building
reviewed:
depends_on: []
consumed_by: []
# Optional story ids allowed to build concurrently within this feature.
parallel_stories:
changelog:
---

# Builders spot-check and stop, the lead proves a batch once

Batch 1 of the plan: docs (L1), hooks (L2), checks (L5). godot-devkit's spot tier (L6) is
tracked in godot-devkit. Issues #121, #122, #124, #125.

## Ship criterion

The docs, hooks and checks match the plan's model, and `make check` and `make unit` pass on the
integrated batch.
