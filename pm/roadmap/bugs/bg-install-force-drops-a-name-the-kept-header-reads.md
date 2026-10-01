---
id: bg-install-force-drops-a-name-the-kept-header-reads
kind: bug
milestone: "ms-the-open-issues-close"
name: MAJOR install --force drops a header name the kept header itself reads
status: closed
caused_by:
changelog: none
---

# install-force-drops-a-name-the-kept-header-reads

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-install-force-drops-a-name-the-kept-header-reads` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MAJOR. A cc-git-denylist.sh header `MY_REL="release"` + `PROTECTED_BRANCHES="main master $MY_REL"` comes back from `install --force` as `PROTECTED_BRANCHES="main master $MY_REL"` with `MY_REL=` deleted: the branch `release` is silently unprotected (under `set -u` the hook dies and fails open). Probed with `install.carry_config_block` on the packaged body.

## Root cause

`_carry_block` and `retired_names` (src/agentic_sdlc/repo/install.py) build `mentioned` from the packaged BODY only; a name the kept header itself reads is never counted as read.

## Fix

Add the words of the kept block's non-declaration text (the right-hand sides) to `mentioned`, or drop a name only when no kept line references `$NAME`/`${NAME`. Unit case: a helper var read by a kept key survives the carry.
