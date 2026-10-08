# Agents and models

Which agent and which model to use for which work. This file is the single source. The
plugin skill `agents-and-models` and `codex/AGENTS.md` point here.

## Rules for every spawn

1. **Set the model on every spawn.** Never inherit it. Use `model` on the spawn call, or
   `model:` in the agent file. The spawn call overrides the agent file.
2. **Pick the tier by oracle coverage.** See "Which model". When unsure, use Sonnet.
3. **Effort is capped at `high`.** Do not ask for more. A higher setting adds cost and
   time and does not remove the need for a review.
4. **Spawn a fixed-tool agent type.** An agent with a fixed tool list boots at about 10k
   tokens. An all-tools agent boots at about 60k, because it loads every MCP schema.
5. **Record the choice** in the brief: agent, model, and why in one line.
6. **A worker that cannot finish stops and asks.** It reports what it needs. It does not
   guess. An escalation costs less than a wrong merge.

## Which model

An oracle is a golden file or an exact test that fails when the behaviour that matters is
wrong. The tier follows how much of that behaviour the oracle covers.

The contract (`plugin/contract/`) names 3 tiers and no model. `runtimes.json` maps each
tier to a model per provider. In Claude: bounded is Haiku, judgment is Sonnet, lead is Opus.

| Model (tier) | Use it for |
|---|---|
| Haiku (bounded) | A task that has an oracle covering the behaviour that matters, a file list, signatures and known traps, sized 15-30 min. Also bulk lookups and triage. |
| Sonnet (judgment) | Judgment with no oracle: UI, contracts, harness. Brief-writing. A sub-lead that splits an issue across Haiku workers and integrates the results. Issue upkeep, doc and skill text, CI config. The default when unsure. |
| Opus (lead) | The plan. The chief of staff (the main agent). Every review (a skeptic that checks one finding may run on Sonnet). Design and process reviews. Ambiguous bugs. Anything with irreversible risk (history rewrite, delete). |

Rules:

- **Widen the oracle or use Sonnet.** When the oracle does not cover the behaviour (for
  example UI judgment, or lazy versus eager control flow), add a test that covers it. If
  you cannot, give the task to Sonnet.
- **Have Sonnet write the Haiku briefs.** In a measured run, Sonnet brief-writers wrote
  better Haiku briefs than the lead did. They also re-tiered 3 of 5 issues by oracle
  coverage.
- **Review in batches.** One blind review of 7 results cost about 28k Opus tokens per
  result. Single reviews cost about 45k. The batch found 12 cross-issue problems that
  single reviews missed.

## Judge cost in dollars

- Judge a tier by dollars per merged task. Count the worker, the sub-lead, the review and
  the rework. Do not judge by tokens: a token costs a different amount in each tier.
- Look up the current price of each model before you compare. Do not copy prices into
  this file. They change.
- Reference point, measured 2026-10-08 on a 48-issue port of a Python tool to TypeScript:
  a Haiku worker with a tight brief and an oracle merged with no critical finding. Haiku
  costs 1/20 of Sonnet and 1/40 of Opus per token. Where the oracle did not cover the
  behaviour, Sonnet won 2 of 2 blind paired trials. A Sonnet sub-lead took 3.6-4.3 min
  per issue, with 0 rework.

## The developer step-up rule

A developer starts on Sonnet. Step it up to Opus when the change does any of these:

- changes a contract, a signature that other systems call, or a save format;
- spans more than 1 system;
- touches generation or spatial logic;
- has a likely design fork, or its premise may be wrong.

The rule stays. Its triggers are the cases where no oracle can cover the behaviour. The
lead and every review stay on Opus. The integrator runs on Sonnet, as the table says. A
skeptic that checks one finding may run on Sonnet. Pass the choice on each spawn, so the
brief records it.

## Roles

| Role | Agent file | Model | When to use it |
|---|---|---|---|
| Developer | `agents/developer.md` | sonnet (opus by the step-up rule) | Build one issue on its own branch, with its proof. |
| Reviewer | `agents/reviewer.md` | opus | One pass over a risky change: state, schema, saved format, input. |
| Architect | `agents/architect.md` | opus | Design on an issue: options, trade-offs, the plan as a checklist. |
| Simplifier | `agents/simplifier.md` | sonnet | A simplicity pass after the code works, before the review. |
| Test writer | `agents/test-writer.md` | sonnet | Add or trim tests, under the test budget. |
| Tech writer | `agents/tech-writer.md` | sonnet | Bring docs to the present tense; keep always-loaded docs under budget. |
| Brief writer | `agents/brief-writer.md` | sonnet | Turn one issue into a worker brief with a tier recommendation. Read only. |
| Worker | `agents/worker.md` | haiku | Build one task from a tight brief that has an oracle. |
| Integrator | `agents/integrator.md` | sonnet | Merge the task branches of a wave, run the gate once, push. Opens no PR. |
| Chief of staff | `agents/chief-of-staff.md` | opus | The main thread: plans, runs workflows, owns the PR, CI and merge. |
| Lookup | a fixed-tool read-only spawn (Read, Grep, Glob, Bash) | haiku | Bulk search, triage, counts. |

## Any agent

- Route by capability and claim. Claude and Codex are peers. The rules rank no provider:
  no bias for quality or for subscription. Only the capabilities a runtime declares differ.
  Today the only one that differs is image generation.
- A task that needs a capability has a `needs:<capability>` label. Today the only one is
  `needs:image-gen`. A task with no `needs:` label is open to any agent. An agent takes a
  task only when it has every capability the task needs. `plugin/contract/runtimes.json`
  lists what each runtime has.
- Ownership is the claim on the issue (the `claim` shape in `plugin/contract/`), not a
  label. Any free agent claims the next unclaimed task. A planner may add a soft `prefer:`
  note to a brief. It never blocks an agent.
- Every agent delivers the full vertical slice: art, code, data, wiring and proof. No agent
  stops for another. It merges its own PR when CI is green, then removes its worktree and
  local branch.
- In Codex, the primary session integrates and reviews architecture. Delegate only
  independent, bounded work. For straightforward code or a focused review, delegate to
  `gpt-6-luna` at low effort, with a precise brief, scope and acceptance criteria. Give an
  independent review a distinct risk angle. Do not add agents without a clear cost benefit.
- The author of the code owns its proof. Run each proof once.
