---
id: bg-integrate-calls-a-failed-commit-a-conflict
kind: bug
milestone: ms-integrate-takes-the-whole-batch
name: integrate calls a failed merge commit a conflict
status: open
caused_by:
changelog:
---

# integrate calls a failed merge commit a conflict

## Symptom

MAJOR (rule 4). On the 2.1.0 release PR, CI ran `integrate` in a runner with no git identity. git refused the merge commit (`fatal: empty ident name`), and `integrate` printed `lane st-lane: origin/feat/st-lane conflicts with the batch, and the merge was aborted` and told the operator to resolve a conflict that does not exist.

## Root cause

`integrate` maps any non-zero `git merge` exit to a conflict. It does not check whether the index holds unmerged paths.

## Fix

After a failed merge, name a conflict only when `git diff --name-only --diff-filter=U` lists paths; otherwise print git's own stderr line as the cause. Test: a lane that merges cleanly in a repo with no identity names the identity error, not a conflict.
