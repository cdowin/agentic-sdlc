---
id: ft-a-nested-dispatch-carries-the-stamp
kind: feature
milestone: "ms-the-backlog-is-empty"
name: A nested dispatch carries its parent's stamp
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-nested-dispatch-carries-the-stamp"
---

# A nested dispatch carries its parent's stamp

https://github.com/cdowin/agentic-sdlc/issues/117. The dispatch guard that refused nested dispatch was cut in 2.0.0. What is left: no text
says a builder may fan out, and a subagent it starts carries no GDK-STAMP, so its spend is filed
against no grain. The SubagentStop courier already copies a prompt's GDK-STAMP line.

## Ship criterion

A subagent started by a builder files its dispatch row on the builder's grain.
