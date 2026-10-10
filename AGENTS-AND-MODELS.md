# Agents and models

Which agent and which model to use for which work. This file is the single source. The
plugin skill `agents-and-models` and `codex/AGENTS.md` point here.

## Rules for every spawn

1. **Set the model on every spawn.** Never inherit it. Use `model` on the spawn call, or
   `model:` in the agent file. The spawn call overrides the agent file.
2. **Pick the tier by oracle coverage.** See "Which model". When unsure, use Sonnet.
3. **Effort is capped at `high`.** Do not ask for more. A higher setting adds cost and
   time and does not remove the need for a review.
4. **Use a fixed-tool agent type when the runtime supports it.** Claude agents with a
   fixed tool list boot at about 10k tokens. All-tools agents boot at about 60k. The
   exposed Codex collaboration wrapper has no tool allowlist or agent-type selector.
5. **Record the choice** in the brief: agent, model, and why in one line.
6. **A worker that cannot finish stops and asks.** It reports what it needs. It does not
   guess. An escalation costs less than a wrong merge.

## Which model

An oracle is a golden file or an exact test that fails when the behaviour that matters is
wrong. The tier follows how much of that behaviour the oracle covers.

The contract (`plugin/contract/`) names 3 tiers and no model. `runtimes.json` maps each
tier to a model per provider. In Claude: bounded is Haiku, judgment is Sonnet, lead is Opus.
In Codex: bounded is `gpt-6-luna` high, judgment is `gpt-6-sol` low, and lead is
`gpt-6-sol` medium. Luna is cheap enough to run high; Sol rarely needs more than medium. The profile records the verified model ids, efforts and runtime limits.

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
lead and every review stay on Opus. The integrator runs on Sonnet, as the table says. In a
wave it merges 1 branch at a time on Haiku first, and steps up to Sonnet on a conflict or a
red oracle (`x-first-try` in the contract). A
skeptic that checks one finding may run on Sonnet. Pass the choice on each spawn, so the
brief records it.

## The spec step

`plan` runs it after the briefs, for each task whose oracle lists uncovered behaviours. 1 agent
at a time. A Sonnet developer writes stubs, failing tests and a caller usage sketch on branch
`spec/<task id>`, cut fresh from the base. The task records the spec commit as `spec_sha`; the
worker, or the sub-lead of a split, starts from that commit. A one-way door (a
contract, a save format or a public API) is the step-up rule: 2 Opus designers, 1 Opus judge
that attacks both, then 1 Opus writer, 4 agents in total. Any other task: 1 writer plus at
most 1 rewrite (`x-limits.spec_rounds`). The oracle may be a unit test, a scripted scene run
(for example Godot 4 headless) or a golden output. After the spec, judgment drops to bounded
when nothing stays uncovered. Lead and one-way tasks never drop. The worker never edits a spec test
(`spec.tests`, in `oracle.files`). The stubs are task files: the worker fills them in. The spec
writes a check only for an uncovered behaviour that matters to a caller, and marks each test
`keep` or scaffold ("Tests" below).
Adapted from pstack by Lauren Tan (MIT).

## Tests

Every agent that writes, briefs or reviews tests follows these rules. Other files point here.

- **Keep rule.** A test stays only when all 3 are true: (1) it catches a silent wrong value or a
  broken use case that a caller relies on; (2) no other test proves the same claim; (3) it fails
  when the code it guards breaks.
- **Scaffold.** A test that only helps build a task is scaffolding. A spec test is scaffold unless
  the spec marks it `keep`, and it may do so only when the test meets the keep rule. A scaffold
  test is an oracle for the build only: it counts for the tier of its task. The wave deletes the
  scaffold tests in 1 commit before the wave PR.
- **Deleting a test** needs 1 line in the commit message: the test that still proves the claim, or
  "no caller relies on it". It needs no other proof.
- **A fix** amends an existing test or a table row. It adds a new test only when no test can
  host the case.
- **Budget.** A PR adds at most 0.5 test lines per added code line; the `test-budget` check warns
  above it. A repo sets a suite cap (`suite_max` total test lines, or `suite_ratio` test lines per
  code line); the check fails over the cap. Over the cap, delete by the keep rule before you add.
- A test is a representative sample: 1 case per kind of input, plus the edges. Do not sweep
  every combination (each page, frame, resolution or theme).
- Generated test data counts against the budget: goldens, snapshots, recorded runs and
  fixtures. The `test-budget` check fails a repo over its byte limit (default 5,000,000).
- When a change takes away the job of a harness, delete the harness in the same change.
- Working code, deployed, with feedback from its users is the real test. A suite only
  guards what that feedback found.
- A worker may create and edit every test file in its task's list, oracle files included. It
  must not weaken an existing assertion unless the brief says so. Which files it may edit:
  "File lists" below.

## File lists

Every agent that plans, briefs, builds or merges a task follows these rules.

- A task's file list is the plan's intent and the input to the parallel-clash check. It is
  not a fence.
- A worker may edit any file its outcome needs, except a file in the list of a task that can
  run at the same time (no blocker path between the 2 tasks). The workflow gives it those files
  as "do not touch". The parts of a split follow the same rule.
- The worker lists every file it edits outside its own list in `extra_files` of its report.
- A task's own test files are never frozen. An oracle file in the task's list is the worker's
  to edit. Only an oracle file outside the list stays read-only, for example a spec test. A
  bounded task lists no oracle file: its oracle stays as it is.
- The integrator checks the changed files against the tasks that run beside the task and are
  not merged yet. It escalates only a real clash: such a task owns the file.
- A worker stops only for a real design fork, or when its outcome needs a file it must not
  touch. A file outside its own list is not a reason to stop.

## Roles

| Role | Agent file | Model | When to use it |
|---|---|---|---|
| Developer | `agents/developer.md` | sonnet (opus by the step-up rule) | Build one issue on its own branch, with its proof. |
| Reviewer | `agents/reviewer.md` | opus | One pass over a risky change: state, schema, saved format, input. |
| Architect | `agents/architect.md` | opus | Design on an issue: options, trade-offs, the plan as a checklist. |
| Simplifier | `agents/simplifier.md` | sonnet | A simplicity pass after the code works, before the review. |
| Test writer | `agents/test-writer.md` | sonnet | Add or trim tests by the rules in "Tests". |
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
  `needs:image-gen` (the contract capability `image_generation`). A task with no `needs:` label is open to any agent. An agent takes a
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
  `gpt-6-luna` at high effort, with a precise brief, scope and acceptance criteria. Give an
  independent review a distinct risk angle. Do not add agents without a clear cost benefit.
- The tier of each role is `x-roles` in `plugin/contract/sdlc.schema.json`, for every
  runtime. `runtimes.json` maps each tier and role to the model and agent type of a runtime.
- The Codex collaboration wrapper has no agent-type selector and no tool allowlist. Role
  names in its brief are instructions.
- Set Codex `model` and `reasoning_effort` on every spawn, with `fork_turns="none"`. The
  evidence in `runtimes.json` comes from spawns with that setting.
- Each runtime has its own `worktree_root` in `runtimes.json`. The Codex wrapper shares the
  filesystem; a worktree path in a brief does not enforce write confinement.
- The author of the code owns its proof. Run each proof once.
