---
id: bg-denylist-misses-an-exported-config-env
kind: bug
milestone: ms-the-backlog-is-empty
name: the denylist misses GIT_CONFIG_* exported in an earlier command
status: closed
caused_by:
changelog: The git denylist hook refuses a Bash command that assigns or exports GIT_CONFIG_PARAMETERS, GIT_CONFIG_COUNT, GIT_CONFIG_KEY_* or GIT_CONFIG_VALUE_*.
---

# the denylist misses GIT_CONFIG_* exported in an earlier command

## Symptom

MINOR. `export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0=...` in one Bash call, then `git zz` in the next, runs an alias the hook cannot read. Found while fixing bg-denylist-alias-via-include-path-or-config-env (2.3.0).

## Root cause

`cc-git-denylist.sh` reads one command at a time and checks env assignments only on the `git` command itself.

## Fix

Refuse any Bash command that exports or assigns `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_*` or `GIT_CONFIG_VALUE_*`, git or not.
