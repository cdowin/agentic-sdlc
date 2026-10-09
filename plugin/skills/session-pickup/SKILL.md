---
name: session-pickup
description: Use when you start a session on an issue that already has a branch, claim comments, commits or a draft PR. Use it when a prior agent stopped, timed out or was cancelled, or when a lead is told to "continue" or "take over".
---

# Session pickup: resume, do not redo

The prior trail is authoritative input. Read it; do not re-derive it.

1. **Locate the trail.** Read this repo's remote and this issue only. Do not read other repos' sessions or private chats.
   - Issue: body, task list, comments (`gh issue view N --comments`).
   - Claim comments: first line `agentic-sdlc:claim`, then a JSON block.
   - Branch: `git fetch origin`, `git log origin/<issue#>-<slug>`, `git diff origin/main...origin/<branch>`.
   - PR: `gh pr list --search "<issue#>"`. Read its state and checks.
2. **Find the owner.** Use the claim rules in the contract. The owner is the earliest `claimed` comment that no later `released` comment of the same lead cancels and no later claim supersedes. GitHub's comment created_at gives the order. The client `at` field does not.
   - The owner is not you and the claim is not stale: stop and say so.
   - A claim is stale when the comment created_at and the last commit time of the remote branch are both older than 120 minutes.
   - To take over: post a claim with `supersedes` (URL of the stale comment) and `resume_sha` (the remote branch head). Read the comments again before your first push.
   - Branch not on the remote: resume from the claim's `base_sha`.
   - Remote head is not a descendant of `resume_sha`: someone rewrote the branch. Stop and escalate.
3. **Rebuild the state from facts, not memory.** Record the remote head SHA, what landed (`git log`), the task state (planned, briefed, claimed, building, built, integrated, reviewed, rework, escalated, done), the rework round (limit 2) and the open questions in comments.
4. **Diff done against pending.** Put the issue's outcome or task list beside the commits. Name the resume point in one line. Do not re-run a finished repro. Do not redo a pushed commit. Do not restart "from scratch".
5. **Route the rest.** Pick one verdict:
   - continue the build;
   - hand a finished branch to review;
   - do rework (same worker as before);
   - ship a finished result;
   - escalate a failed or rewritten run, with one question for a person.
   Name the playbook that fits (bug-fix, prototype, hillclimb or project-verify) in words only. That playbook owns the rest.
6. **Prove the inherited claim once.** Run the task's focused test on the branch head. A prior "tests pass" in a comment is not proof. If the test fails, that is the new fact. Start from it.
7. **Push every commit you make to the same branch.** Do not force-push. Open no PR per task. The wave PR runs CI once.

## Reply

A numbered NEEDS YOU list first, if a person must act. Then:

- where the prior agent stopped;
- what you inherited and what you redid (aim: nothing redone);
- the resume point;
- the verdict and the next step.

Adapted from pstack by Lauren Tan (MIT).
