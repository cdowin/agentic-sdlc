---
id: bg-denylist-export-trailing-n-bypass
kind: bug
milestone: "ms-the-backlog-is-empty"
name: MINOR denylist passes export GIT_CONFIG_COUNT=1 -n although bash exports it
status: closed
caused_by:
changelog: none
---

# denylist-export-trailing-n-bypass

<!-- `milestone:` is the parent, and it is the only binding — a bug nested in a
     milestone must close before it does. Not committing to it now? `pm remove
     <milestone> bg-denylist-export-trailing-n-bypass` returns it to the pool, where it gates nothing and is
     counted. `caused_by:` (optional) names the one feature whose change made
     it — set with `--caused-by`, or leave it empty rather than invent one. -->

## Symptom

MINOR. `export GIT_CONFIG_COUNT=1 -n` passes `cc-git-denylist.sh` (exit 0). `bash -c 'export GIT_CONFIG_COUNT=1 -n; env'` shows GIT_CONFIG_COUNT=1, so bash exports it. This is the exported-GIT_CONFIG_* route that D1 says the hook refuses.

## Root cause

`sets_env` collects flags from every `-` word in the args, also from words after the names. A trailing `-n` makes `'n' not in flags` false, so the names are not read as exports.

## Fix

Read flags only from the leading `-` words, up to the first name or `--`. Add `B export GIT_CONFIG_COUNT=1 -n` to the self-test corpus.
