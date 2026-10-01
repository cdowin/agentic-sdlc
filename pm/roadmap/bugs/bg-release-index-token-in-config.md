---
id: bg-release-index-token-in-config
kind: bug
milestone: ms-the-backlog-is-empty
name: release index token in config
status: closed
caused_by:
changelog: none
---

# release index token in config

## Symptom

NIT. `.github/workflows/release.yml (the index branch step)`: the token is left in `site/.git/config`; an unauthenticated `ls-remote` on a private repo falls through to an orphan init. Source: 1.0.0-milestone/X3 (issue #108; graded live at 2.3.0).

## Root cause

See the review record named in Symptom.

## Fix

Use an auth header and an authenticated `ls-remote`.
