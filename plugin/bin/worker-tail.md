
Repo @REPO@, issue #@ISSUE@, branch `@BRANCH@` (pushed, cut from @BASE@; check it out).
The brief above is the task; with no brief, the issue is. The brief and the repo's CLAUDE.md say how
to work and win over this tail, which is only the protocol the lead's watcher reads.

1. First act, before any other work: post one comment on issue #@ISSUE@ whose first line is exactly
   `WORKER STARTED branch=@BRANCH@ session=<your session URL, or unknown>`.
2. Push after every commit to `@BRANCH@`, with `Refs #@ISSUE@` in the message. Open no PR.
3. Post each comment from a file or a quoted heredoc (`gh issue comment N --body-file -`).
4. The proof, before you report `passed`:
@GATE@
5. When done and the proof passed, post ONE comment whose first line is exactly
   `WORKER REPORT branch=@BRANCH@ head=<sha> passed`, with the head SHA you pushed, then what you saw.
6. If blocked, or the proof stays red, post one comment whose first line is exactly
   `WORKER BLOCKED branch=@BRANCH@`, then one question or the red command and its last line, and stop.
7. Never go silent. Time-box every command (`timeout 900 <cmd>`); if one times out or waits on a
   prompt, post `WORKER BLOCKED branch=@BRANCH@` naming the command that hung and its last line.
