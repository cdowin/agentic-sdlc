---
id: st-adopt-names-an-absent-installable
kind: story
feature: ft-adopt-names-what-is-absent
milestone: "ms-the-loop-proves-itself"
name: adopt names each absent installable and unarmed hooks
status: planning
owner:
depends_on: []
changelog: adopt names each installed file that is absent, and hooks that setup-hooks.sh never armed, instead of skipping them.
---

# adopt names each absent installable and unarmed hooks

## Acceptance criteria

1. An installable whose target file is absent prints one `absent: <path>` line and `adopt` exits 1.
2. A tree whose git hooks are not armed (no `core.hooksPath` or copied hooks, as
   `tools/setup-hooks.sh` writes them) prints one `unarmed:` line naming `setup-hooks.sh`.
3. A complete tree prints no new line; existing line shapes do not change.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | test_adopt.py: delete one installed workflow in a scratch tree | new |
| 2 | unit | test_adopt.py: a scratch tree with hooks unarmed | new |
| 3 | unit | test_adopt.py: the existing clean-tree case | amend |

Files: `src/agentic_sdlc/repo/belts.py::adopt` and its checks. Broken probe: delete a file from
a scratch copy and see `adopt` FAIL.

## Out of scope

`[dispatch]` and `[integrate]` (st-adopt-reads-every-workflow-section). A new verb.
