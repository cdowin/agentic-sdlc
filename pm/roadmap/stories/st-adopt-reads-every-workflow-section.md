---
id: st-adopt-reads-every-workflow-section
kind: story
feature: ft-adopt-names-what-is-absent
milestone: "ms-the-loop-proves-itself"
name: adopt reads [dispatch] and [integrate], and a contract outside [doc] scope is a finding
status: building
owner:
depends_on: []
changelog: adopt reads [dispatch] and [integrate], and names a dispatch contract that is missing or outside [doc] scope.
---

# adopt reads [dispatch] and [integrate], and a contract outside [doc] scope is a finding

## Acceptance criteria

1. `adopt` loads `[dispatch]` and `[integrate]` through `belts.py::_config_readers`; a malformed
   one is refused by name at exit 2, as the other sections are.
2. A `[dispatch]` contract path that does not exist prints one finding line; exit 1.
3. A contract path that exists but is outside `[doc]` scope prints one finding line; exit 1.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | test_adopt.py refused-config case, one row per new section | amend |
| 2, 3 | unit | test_adopt.py: scratch devkit.toml with a bad and an out-of-scope contract | new |

Reuse `dispatch.py`'s contract-path check; do not write a second one. Reuse the `[doc]` scope
reader from `checks/doc.py`.

## Out of scope

Changing what `dispatch` itself refuses.
