---
name: prototype
description: Use when a design question is open and running code can answer it: "which layout", "which interaction", "which timing", "which approach", "try a few options", "spike". Load it to settle the question with throwaway variants behind 1 switcher. It is not for a build with a settled design; use the normal build path for that.
---

# Prototype: settle a design question by running it

A prototype is a throwaway instrument. It makes a decision cheap. It is not code to ship.

Speed matters more than polish here. Code quality does not matter. The care goes into picking the right design.

## Steps

1. **Scope the decision.** Write the one question the prototype answers. Write the evidence that will answer it. Examples: which HUD layout in a Godot game, which output format for a TypeScript CLI, which page layout for a book. If there is no decision to make, do not prototype. Use the normal build path.

2. **Apply the ask-or-run rule.**
   - FORBIDDEN: never ask a person a question that running code can settle.
   - Running code settles timing, output, fit, whether it renders, performance and which approach works. Run it and observe.
   - Ask a person only for taste or priority that no run can show. Then show the variants. Do not ask in prose.

3. **Build it throwaway.** Work in a scratch directory outside production source, for example `scratch/<issue#>-<slug>/`. Use the smallest stack that shows the idea. Write no tests, no abstractions and no production framework. Do not commit it to the product tree. If you commit it at all, commit it on the issue branch only, and delete it before merge.

4. **Put the variants behind 1 switcher.** Build 2 or more variants. Use buttons, a keypress or a CLI flag to switch. Label each variant. Build at most 4 variants per round.

5. **Verify by running it.** Use the surface that matches the question.
   - Visual: take a screenshot of each variant.
   - Behavior or timing: log or print the observed output.
   - The observation is the test. Write no assertions.

6. **Report.** Give these items:
   - The variants you tried.
   - The evidence for each.
   - The tradeoffs.
   - One recommendation.
   - The scratch path.

   State plainly that the prototype is throwaway and not shippable. Hand the chosen direction to the normal build. The real build commits normally.

   If the choice is a one-way door (a contract, a save format or a public API), say so in the report. Then `plan` can apply design-twice.

Adapted from pstack by Lauren Tan (MIT).
