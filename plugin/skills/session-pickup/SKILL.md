---
name: session-pickup
description: Resume an issue a prior agent left (branch, WORKER comments, commits, PR). Read the trail, prove its head once, go on from there.
---

# Session pickup: resume, do not redo

The prior trail is the input. Read it; do not re-derive it.

1. **Read the trail** of this repo and this issue only: the issue and its comments
   (`gh issue view N --comments`), its `WORKER` lines, the branch (`git fetch origin`,
   `git log origin/main..origin/<branch>`) and any PR (`gh pr list --search "<issue#>"`).
2. **Check the owner.** A `WORKER STARTED` or a commit on the branch in the last 60 minutes means
   a live worker: stop and say so. A branch whose remote head is not a descendant of the last
   reported head was rewritten: stop and ask.
3. **Diff done against pending.** Put the issue's done-when beside the commits and name the
   resume point in one line. Do not redo a pushed commit or restart from scratch.
4. **Prove the inherited head once** with the repo's proof command. A prior "passed" in a comment
   is not proof; a red run is the new fact to start from.
5. **Push every commit to the same branch.** Never force-push. Open no PR.

## Reply

A NEEDS YOU list first, if a person must act. Then where the prior agent stopped, what you
inherited, the resume point and the next step.

Adapted from pstack by Lauren Tan (MIT).
