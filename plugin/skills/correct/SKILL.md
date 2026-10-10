---
name: correct
description: Use when the operator or a reviewer corrects an agent for a mistake already corrected before, when a review finding repeats, or when the lead is asked to "stop this from happening again". Finds the mistakes agents repeat in a repo and makes each class impossible at the highest level that works.
---

# Correct: make a repeated mistake impossible

Every contributor is an agent. It sees only the files it opened, copies the nearest example, and takes the shortest path that passes. Make the repo so a change that looks right in one file is right in the whole repo.

The lead runs this playbook, or a brief names it.

## Steps

1. Mine the mistakes. Read these sources:
   - recent commits and reverts;
   - review findings: the `review` results of past waves and the skeptics' notes;
   - rework rounds in reports and PR comments;
   - the repo agent instruction files;
   - comments that explain a workaround.

   Group the mistakes into classes. A class counts once it has happened 2 times. Give 2 or more references per class: a commit, a finding or a comment.

2. Bound the load. Take at most 5 classes per run, the most frequent first. File each other class as an issue for the backlog.

3. Fix each class at the highest level that works. Top first:
   1. Architecture. One owner per piece of state. One supported way per task. Hide internals so the wrong import fails. One source of truth in place of hand-synced lists. Delete the old way and the dead code an agent would copy.
   2. Types. Make the bad state unwritable.
   3. Lint or CI check. The error message names the file, type or function to use instead. If the bad pattern is already common, fail only when a change adds more.
   4. Test of behavior. Fix or delete a test that would still pass if every function it calls, or every import, returned undefined or nothing.
   5. Docs or agent rules. Last. Use them only for judgment calls. Nothing fails when an agent skips them.

   Go down a level only when the level above cannot work. Write why in the reply.

4. Prove each check. A new lint, CI check or test must fail on a real past mistake.
   1. Check out or replay the commit or code that had the mistake.
   2. Run the check. It must fail.
   3. Run it on the fixed code. It must pass.
   4. Record the failing commit or file and the command.

   A check never proved on a real past mistake is not done. Run the same command locally and in CI. In this kit CI is the 1 job `ci`, which runs once on the wave PR. Put a new check in `./checks` or `tests/run.sh`. Never add a per-push or per-PR job. An exception goes on the offending line with a reason, an expiry date and the approval of a person.

5. Commit once per class, on the issue branch. The worker pushes every commit. The lead hands the fix of each class to a worker as a normal task, with the check as its oracle. Do not force-push, rebase or squash.

6. Keep the rule table. Put a table in the repo's agent instruction file:

   | Rule | Enforcer (file or command) | Level (1 to 5) |
   |---|---|---|

   A rule with no enforcer above level 5 is a docs rule. When the operator corrects an agent, fix the mistake, then add the row. If the row exists and nothing enforces it, that is a repeat. Raise it to a higher level in the same change. Drop the row when the mistake can no longer happen. Keep the table short: The instruction file has a line budget that `./checks` tests. A long table becomes a pointer plus the enforcing files.

## Example

Class: workers call a raw file API in 6 files, and 2 reviews flagged it.
- Level 1: add 1 wrapper module that owns all file access. Move the 6 callers to it. Delete the raw calls.
- If a caller must stay raw, go to level 3: a lint that fails with "use `io/files` instead of the raw file API" and fails only when a change adds a call.
- Proof: replay the commit with the raw call. The lint fails. Run it on the fixed tree. It passes.

A second class: a hand-synced list of ids drifts. Generate the list from 1 source. A test fails when the generated file differs from the source.

## Reply

Use ASD-STE100. Per class, give:
1. the evidence;
2. the level picked;
3. why no higher level worked;
4. the proof command and its result, failing then passing.

Adapted from pstack by Lauren Tan (MIT).
