---
id: st-nested-dispatch-carries-the-stamp
kind: story
feature: ft-a-nested-dispatch-carries-the-stamp
milestone: "ms-the-backlog-is-empty"
name: A builder may start subagents, and each carries its GDK-STAMP
status: building
owner:
depends_on: []
changelog:
---

# A builder may start subagents, and each carries its GDK-STAMP

https://github.com/cdowin/agentic-sdlc/issues/117.

## Acceptance criteria

1. The rendered brief (`dispatch.py`) says: you may start subagents for independent parts of this
   grain; put this brief's GDK-STAMP line first in each subagent's prompt; you answer for their
   results in your report.
2. The stock `developer` definition and the run-the-sdlc guidance say the same in one sentence;
   this repo's installed copies are re-installed byte-current.
3. A courier case: a SubagentStop payload whose prompt starts with the parent's GDK-STAMP files
   its row on that grain.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | test_dispatch.py brief case | amend |
| 2 | unit | test_install.py byte-current | existing |
| 3 | integration | test_hooks_payloads.py subagent courier case | amend or existing |
