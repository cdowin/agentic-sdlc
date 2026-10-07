# Agents and models

Which agent and which model to use for which work. This file is the single source. The
plugin skill `agents-and-models` and `codex/AGENTS.md` point here.

## Rules for every spawn

1. **Set the model on every spawn.** Never inherit it. Use `model` on the spawn call, or
   `model:` in the agent file. The spawn call overrides the agent file.
2. **Sonnet is the default.** When unsure, use Sonnet. Move to Opus only when the brief
   cannot be made complete.
3. **Effort is capped at `high`.** Do not ask for more.
4. **Record the choice** in the brief: agent, model, and why in one line.

## Which model

| Model | Use it for |
|---|---|
| Haiku | Bulk lookups and triage: search, list, count, label, sort many small items. |
| Sonnet | The default. Issue upkeep. Mechanical edits. Doc and skill text. CI config. Routine builds from a complete brief. Tests. Screenshots and previews. Data updates by hand. |
| Opus | Design and process reviews. Convention or architecture design. Ambiguous bugs. Cross-repo plans. Anything with irreversible risk (history rewrite, delete). The integrator and every review. |

## The developer step-up rule

A developer starts on Sonnet. Step it up to Opus when the change does any of these:

- changes a contract, a signature that other systems call, or a save format;
- spans more than 1 system;
- touches generation or spatial logic;
- has a likely design fork, or its premise may be wrong.

The lead, the integrator and every review stay on Opus. Pass the choice on each spawn, so
the brief records it.

## Roles

| Role | Agent file | Model | When to use it |
|---|---|---|---|
| Developer | `agents/developer.md` | sonnet (opus by the step-up rule) | Build one issue on its own branch, with its proof. |
| Reviewer | `agents/reviewer.md` | opus | One pass over a risky change: state, schema, saved format, input. |
| Architect | `agents/architect.md` | opus | Design on an issue: options, trade-offs, the plan as a checklist. |
| Simplifier | `agents/simplifier.md` | sonnet | A simplicity pass after the code works, before the review. |
| Test writer | `agents/test-writer.md` | sonnet | Add or trim tests, under the test budget. |
| Tech writer | `agents/tech-writer.md` | sonnet | Bring docs to the present tense; keep always-loaded docs under budget. |
| Lookup | (none; a plain spawn) | haiku | Bulk search, triage, counts. |

## Claude or Codex

- Each task has 1 doer label. Claude takes `agent:claude` work. Codex takes `agent:codex`
  work. The label names the agent best suited to the task. By default, work that is mostly
  images goes to Codex.
- Every agent delivers the full vertical slice: art, code, data, wiring and proof. No agent
  stops for another. It merges its own PR when CI is green, then removes its worktree and
  local branch.
- In Codex, the primary session integrates and reviews architecture. Delegate only
  independent, bounded work. For straightforward code or a focused review, delegate to
  `gpt-6-luna` at low effort, with a precise brief, scope and acceptance criteria. Give an
  independent review a distinct risk angle. Do not add agents without a clear cost benefit.
- The author of the code owns its proof. Run each proof once.
