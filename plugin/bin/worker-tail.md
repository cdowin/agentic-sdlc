
Repo @REPO@, issue #@ISSUE@, branch `@BRANCH@` (pushed, cut from @BASE@; check it out).
The brief above is the task; with no brief, the issue is. How to work (tests, merging, checks, the shape
of the report) comes from the brief and the repo's CLAUDE.md, and they win over this tail. This tail is
only the protocol the lead's watcher and flow read.

Your first act, before any other work: post one comment on issue #@ISSUE@ whose first line is exactly
`WORKER STARTED branch=@BRANCH@ session=<your session URL, or unknown>`. The lead's watcher reads it
as the sign that you started.

These must pass before you report `passed`:
@GATE@

Rules:
- Push after every commit to `@BRANCH@`. Open no PR: the lead lands it.
- Post each comment from a file or a quoted heredoc (`gh issue comment N --body-file -`), never
  inside double quotes.
- Commit messages name the issue (`Refs #@ISSUE@`).
- Push your first commit within 30 minutes. A branch with no commit and no report for 60 minutes is stalled.
- When done, and only when every gate above passed, post ONE comment on issue #@ISSUE@. Its first line
  is exactly `WORKER REPORT branch=@BRANCH@ head=<sha> passed`, with the head SHA you pushed. flow lands
  no report without `passed`. Name `@BRANCH@`, never a session mirror branch.
- If blocked, or a gate stays red, post one comment whose first line is exactly
  `WORKER BLOCKED branch=@BRANCH@`, then one question (or the red command and its last line), and stop.
- Time-box every command: `timeout 900 <cmd>`. Pass flags that keep a command from asking for input.
  If a command times out or waits on a prompt, post `WORKER BLOCKED branch=@BRANCH@`
  naming the command that hung and its last output line, then stop. Never go silent.
