
Repo @REPO@, issue #@ISSUE@, branch `@BRANCH@` (pushed, cut from @BASE@; check it out).
Read the repo's CLAUDE.md and README.md first. Read the issue and its comments: the issue is the brief
(outcome, done when). Reuse before you build. Never invent behavior beyond the issue; for a design
choice, post WORKER BLOCKED with one question and stop. For a bug, reproduce it first (a test that
fails before the fix), then fix the cause.

Done when: the issue's Done when holds and every gate below passes:
@GATE@

Rules:
- Push after every commit to `@BRANCH@`. Open no PR: the lead lands it.
- Commit messages name the issue (`Refs #@ISSUE@`). Add no comment that restates the code.
- Push your first commit within 30 minutes. A branch with no commit and no report for 60 minutes is stalled.
- When done, post ONE comment on issue #@ISSUE@ that starts with `WORKER REPORT`: head SHA, root cause
  or design, files, proof lines, not verified. If blocked, post one comment that starts with
  `WORKER BLOCKED` with one question, and stop.
