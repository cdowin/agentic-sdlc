---
name: bug-fix
description: Use when an issue reports a defect: something that worked before or should work now and does not. Gives a 6-step playbook - reproduce on the real surface, find the cause by elimination, commit the failing repro first, fix on top, prove on the same surface, report.
---

# Bug fix

Rule: every shipped line traces to run evidence. A guess that "might help" does not ship. If evidence refutes a hypothesis, revert what it motivated. Ship the smallest change the evidence justifies.

Git: commit on the issue branch. Push each commit. The failing-repro commit is in history before the fix commit.

1. Reproduce on the real surface.
   - The real surface is the one the user hits. Run the app, the CLI, the scene or the build. A mock is not the surface.
   - Godot game: run the scene headless with scripted input. Capture a log or a screenshot.
   - TypeScript CLI: run the command with the failing arguments.
   - Book build: run the build. Read the output.
   - If the bug does not reproduce, synthesize the trigger, tighten the conditions, or add logging until it fires.
   - Ask a person only with a stated reason that the surface cannot be reached. Drive the surface as far as it goes first. A question that running code can settle is never put to a person.

2. Find the cause by elimination.
   - List the candidate causes.
   - Pick the check that rules out the most candidates. Run it. Drop what the evidence refutes.
   - Do not guess. Confirm the surviving mechanism with run evidence before you write the fix.
   - Cap: 3 rounds of elimination. If no cause survives, stop. Report what you ruled out.

3. Commit the failing repro first.
   - Make it its own commit, before any fix.
   - Use a failing test if a cheap one exists on the affected path. If not, use a script or a scripted scene run that fails the same way.
   - Run it. Confirm it fails for the intended reason, not an unrelated one.
   - Prefer no new test over a bad test. A bad test checks mocks or current internals.
   - Never change a test or weaken an assertion to fit a wrong implementation.

4. Fix on top, in a later commit.
   - Make the smallest change that passes the repro and keeps nearby behavior.
   - If the fix crosses a function boundary, or changes a contract, a save format or a public API, say so in the report. The lead decides whether to run design-twice. This skill does not start it.
   - If the fix needs a spec that the oracle lacks, send the task back to the lead.

5. Prove on the same surface as step 1.
   - The original repro must now pass.
   - A unit test alone does not prove the bug is gone.
   - "Inconclusive" or the wrong surface is not a pass. Flag it.

6. Report.
   - State what was broken, the root cause, the fix and how you verified it.
   - Paste the failing repro output and the passing repro output verbatim.
   - Name the 2 commit SHAs: the repro, then the fix.
   - If you could not show the failure before the fix, say why. Name the closest check you used.

Adapted from pstack by Lauren Tan (MIT).
