
Repo @REPO@, issue #@ISSUE@, branch `@BRANCH@` (pushed, cut from @BASE@; check it out).
Your first act, before any other work: post one comment on issue #@ISSUE@ whose first line is exactly
`WORKER STARTED branch=@BRANCH@ session=<your session URL, or unknown>`. The lead's watcher reads it
as the sign that you started.
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
- When done, post ONE comment on issue #@ISSUE@. Its first line is exactly
  `WORKER REPORT branch=@BRANCH@ head=<sha>`, with the head SHA you pushed. Name `@BRANCH@`, never a
  session mirror branch. Then: root cause or design, files, proof lines, not verified, and a
  **Done when** section that repeats each done-when line of the issue and marks it met (with its
  evidence) or not met (with why). A report without that section is incomplete.
- If blocked, post one comment whose first line is exactly `WORKER BLOCKED branch=@BRANCH@`, then one
  question, and stop.
- Before your last push, merge current main into `@BRANCH@` and run the project's fast pre-PR check
  (for example `make precheck`; budgets, PR body, version rule). Fix what it names: CI tests your
  branch merged with main.
- Time-box every check you run after that merge: `timeout 900 <cmd>`. Pass flags that keep a command
  from asking for input. If a check times out or waits on a prompt, post `WORKER BLOCKED branch=@BRANCH@`
  naming the command that hung and its last output line, then stop. Never go silent.
