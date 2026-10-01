---
id: ft-a-fresh-init-locks
kind: feature
milestone: "ms-the-open-issues-close"
name: A fresh init locks in any repo
status: done
reviewed:
depends_on: []
consumed_by: []
changelog: init's tooling pyproject locks in a repo with several top-level dirs.
order:
  - "st-init-pyproject-locks-with-many-dirs"
---

# A fresh init locks in any repo

https://github.com/cdowin/agentic-sdlc/issues/109. The tooling pyproject `init` writes fails `uv lock` when the repo has two or more top-level dirs.
