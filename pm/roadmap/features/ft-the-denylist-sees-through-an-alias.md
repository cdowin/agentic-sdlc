---
id: ft-the-denylist-sees-through-an-alias
kind: feature
milestone: "ms-the-open-issues-close"
name: The git denylist sees through an alias
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
order:
  - "st-the-denylist-refuses-a-config-alias"
---

# The git denylist sees through an alias

https://github.com/cdowin/agentic-sdlc/issues/105. `git -c alias.zz='!git reset --hard' zz` exits 0 under `cc-git-denylist.sh` (probed at 2.2.0). Part 1 of the issue (the allowlist's scratch exemption) is obsolete.
