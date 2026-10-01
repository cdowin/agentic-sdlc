---
id: bg-denylist-alias-via-include-path-or-config-env
kind: bug
milestone: "ms-the-open-issues-close"
name: MAJOR the denylist still runs an alias set through include.path or GIT_CONFIG env
status: closed
caused_by:
changelog: The git denylist hook also refuses include.path, includeIf, GIT_CONFIG_* assignments and git config writes under alias., include. or includeIf.
---

# denylist-alias-via-include-path-or-config-env

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-denylist-alias-via-include-path-or-config-env` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MAJOR. cc-git-denylist.sh allows (exit 0) `git -c include.path=/tmp/evil.cfg zz`, `git -c includeIf.onbranch:main.path=/tmp/e zz`, `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0='!git reset --hard' git zz` and `GIT_CONFIG_PARAMETERS="'alias.zz=!git reset --hard'" git zz`; each runs an alias the hook cannot read. Probed by piping PreToolUse JSON to the hook under /bin/bash 3.2.

## Root cause

`git()` in the hook's JUDGE checks only a `-c`/`--config-env` key that starts with `alias.`; config that pulls in a file, and the env vars git reads as `-c`, are not seen. `git config alias.zz ...; git zz` is the same hole across two segments.

## Fix

Refuse a `-c`/`--config-env` key `include.path` or `includeif.*`, and a segment whose env prefix sets `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT` or `GIT_CONFIG_KEY_*`. Corpus B rows for each; keep `git -c user.name=x` an A row.
