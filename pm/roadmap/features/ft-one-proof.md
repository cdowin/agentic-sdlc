---
id: ft-one-proof
kind: feature
milestone: "ms-build-wide-integrate-once"
name: A batch is proven once, and a close writes status only
status: building
reviewed:
depends_on: []
consumed_by: []
# Optional story ids allowed to build concurrently within this feature.
parallel_stories:
changelog:
---

# A batch is proven once, and a close writes status only

Batch 2 of `docs/design/2.0.0-build-wide-integrate-once.md`. Issues #119, #120, #123, #125.

## Ship criterion

`integrate` exists and is the only verb that proves; close and release write status and run no gate; the cut list is deleted.
