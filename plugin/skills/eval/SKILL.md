---
name: eval
description: Use before a release, when the lead asks whether a plugin change makes an agent do better. Load it for "eval", "A/B", "blind test", "does this skill help", "try the change first" or "should we promote this edit". Runs a blind A/B of an edited skill, agent file or brief template against the plugin on main. It never edits plugin files and never releases.
---

# Eval: a blind A/B of a plugin change before the release

Why: an edit that reads well can still make an agent do worse. A blind run shows the effect on real output. An agent that knows it is under test behaves differently, so the run must hide the test.

Variant A is the plugin on main. Variant B is the plugin with the change. This skill adds to the existing reviews. It does not replace them. It edits no plugin file. The release stays a version PR.

## Blinding rules

Keep all of these.

- The prompt reads like an organic user request. It states a goal, not the meta.
- No word like eval, test, judge, experiment, rubric, score, compare, benchmark, candidate or variant appears in any directory, file or prompt the agent sees.
- Directory and slug names are sanitized and project-shaped.
- Do not tell the agent that another run exists.
- Do not ask the agent to list the skills it used. Grade chain-following from the files it opened and the shape of the output, not from its own report.
- The judge sees outputs by sanitized label (X, Y). It never sees the variant name.
- One judge scores both outputs in one pass on one scale.
- Randomize which variant gets which label. Keep the key where the judge cannot read it.

## Steps

1. **Frame.** Name the change. State the behaviour that counts as success. Write a rubric of 3 to 6 concrete criteria. The rubric is for the judge only.
2. **Pick 1 organic task.** Prefer a known oracle: a golden output or a scripted scene run for a Godot game, a unit test for a TypeScript CLI, a build for a book. Write the prompt as a user would type it.
3. **Set up 2 sanitized work dirs,** one per variant, with the same project skeleton. Load the plugin from a local checkout in each: A from a checkout of main, B from a checkout with the change. Use the runtime's local-plugin option.
4. **Run each variant on the same prompt.** Cap: 2 runs per variant, 4 runs total. Use the same tier for both.
5. **Judge once.** One reviewer agent gets the rubric and the outputs under labels X and Y. It returns one score per criterion and one verdict.
6. **Read every output end to end.** The lead (`chief-of-staff`) compares its own read with the judge. A disagreement means the rubric is vague or the judge is biased. Say so. Do not promote.
7. **Give a verdict:** promote, hold or reject, with the evidence. Promote only when B wins on the rubric, B has no new critical finding and B needs no extra rework round. 4 runs are a signal, not proof. The risk: one task and a small sample can favour B by chance.
8. **Report** in the repo reporting style, with a numbered NEEDS YOU list first. Then give:
   - the change under test;
   - the rubric;
   - notes per run;
   - the judge verdict;
   - the lead synthesis;
   - the recommendation.

## Does not

- Edit a plugin file.
- Release or bump a version.
- Run more than 4 runs or 1 judge.

Adapted from pstack by Lauren Tan (MIT).
