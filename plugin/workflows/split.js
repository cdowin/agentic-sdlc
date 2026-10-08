export const meta = {
  name: 'split',
  description: 'Split one issue across parallel workers on part branches, then integrate. A sub-lead writes the oracle and the briefs, workers build, the sub-lead merges and pushes.',
  phases: ['Split', 'Build', 'Integrate'],
}

// args: { issue, branch, base, parts, test, rules, runtime }
//   issue   issue number or URL; the sub-lead reads it
//   branch  the integration branch; each part builds on <branch>-<part>
//   base    the ref the branch is cut from
//   parts   array of 2 or more parts. Each part is a name, or { name, test } with the focused
//           test command of that part (for example a --test-name-pattern)
//   test    the command that runs the whole-issue oracle
//   rules   optional; the repo's code rules as text, passed to every agent
//   runtime optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
// The workflow opens no pull request. The PR, the CI gate and the merge stay with the main agent.

// The Claude profile: the parts of runtimes.json "claude" that this workflow reads.
const CLAUDE_RUNTIME = {
  tiers: { bounded: { model: 'haiku' }, judgment: { model: 'sonnet' }, lead: { model: 'opus' } },
  worktree_root: '.claude/worktrees',
  agent_types: { sub_lead: 'developer', worker: 'worker', integrator: 'integrator' },
}
// Role to tier: x-roles in plugin/contract/sdlc.schema.json. A worker takes the tier of its part.
const SUB_LEAD_TIER = 'judgment'
const INTEGRATOR_TIER = 'judgment'
const DEFAULT_PART_TIER = 'judgment'
const MIN_PARTS = 2

// Contract shapes: copies of $defs split, report and merge in plugin/contract/sdlc.schema.json.
// A workflow cannot import a file. tests/workflows.js fails when a copy drifts.
const splitSchema = {
  type: 'object',
  required: ['oracle', 'briefs', 'escalation'],
  properties: {
    oracle: { type: 'string', description: 'Path of the test or golden file that proves the whole issue' },
    stubs: { type: 'array', items: { type: 'string' }, description: 'Paths of the stub files committed to the branch' },
    briefs: {
      type: 'array',
      items: {
        type: 'object',
        required: ['part', 'files', 'brief', 'tier', 'test'],
        properties: {
          part: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
          brief: { type: 'string', description: 'Tight brief: outcome, files, the oracle cases this part must pass, what to leave alone' },
          test: { type: 'string', description: 'The command that runs the focused test of this part only' },
          tier: { type: 'string', enum: ['bounded', 'judgment', 'lead'], description: 'judgment when the oracle does not cover the behaviour; lead when the step-up rule applies' },
        },
      },
    },
    escalation: { type: 'string', description: 'Empty when the issue splits cleanly. Otherwise the question for the lead.' },
  },
}

const reportSchema = {
  type: 'object',
  required: ['task', 'branch', 'sha', 'status', 'test'],
  properties: {
    task: { type: 'string', description: 'The task id or part name from the brief' },
    branch: { type: 'string' },
    sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: 'The full SHA of the last pushed commit' },
    status: { type: 'string', enum: ['done', 'escalated'] },
    test: {
      type: 'object',
      required: ['command', 'line', 'passed'],
      properties: {
        command: { type: 'string' },
        line: { type: 'string', description: 'The last output line of the focused test' },
        passed: { type: 'boolean' },
      },
    },
    round: { type: 'integer', minimum: 0, description: '0 for the first build, 1 or more for a rework round' },
    escalation: { type: 'string', description: 'Set when status is escalated. Stop and ask; do not guess.' },
    notes: { type: 'string', description: '3 lines or fewer. Say what you did not verify.' },
  },
}

const mergeSchema = {
  type: 'object',
  required: ['branch', 'sha', 'merged', 'oracle_passed', 'reworked'],
  properties: {
    branch: { type: 'string' },
    sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: 'The full SHA of the pushed integration branch' },
    merged: { type: 'array', items: { type: 'string' }, description: 'The branches merged, in order' },
    skipped: { type: 'array', items: { type: 'string' }, description: 'Each skipped branch and why, 1 line each' },
    oracle_passed: { type: 'boolean' },
    reworked: { type: 'array', items: { type: 'string' }, description: 'Parts the sub-lead had to fix' },
    escalation: { type: 'string' },
    notes: { type: 'string' },
  },
}

const parts = args.parts || []
if (!args.issue || !args.branch || !args.base || !args.test || parts.length < MIN_PARTS) {
  throw new Error('split needs args issue, branch, base, test and at least 2 parts')
}
const runtime = args.runtime || CLAUDE_RUNTIME
// spawn: the model and the effort of the tier (when the runtime sets one), and the agent type of the role.
const spawn = (role, tier) => {
  const t = runtime.tiers[tier] || runtime.tiers[DEFAULT_PART_TIER]
  return { model: t.model, ...(t.effort && { effort: t.effort }), agentType: runtime.agent_types[role] }
}
const partNames = parts.map((p) => (typeof p === 'string' ? p : p.name))
const partTests = parts.filter((p) => typeof p !== 'string' && p.test).map((p) => `${p.name}: ${p.test}`)
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''

phase('Split')
const plan = await agent(
  `Read issue ${args.issue}. Cut branch ${args.branch} from ${args.base}.
Split the work into these parts: ${partNames.join(', ')}.
1. Write the oracle first: a test or golden file that fails now and passes when the whole issue is done. The run command is: ${args.test}
   Tests given for the parts: ${partTests.length > 0 ? partTests.join('; ') : 'none'}
2. Write stubs for the seams between parts, so each part builds alone.
3. Commit the oracle and the stubs to ${args.branch} and push.
4. Write one brief per part. Each brief gives the focused test command of the part (a filter of the oracle that runs this part only), and names the files the part may edit, the oracle cases it must pass, and what it must not touch. 2 parts never edit the same file.
5. Tier each part. Use bounded when the oracle covers the behaviour. Use judgment when it does not (UI judgment, lazy or eager control flow). Use lead when the step-up rule in AGENTS-AND-MODELS.md applies.
If the issue does not split cleanly, set escalation and write no briefs.${rules}`,
  { label: 'split', phase: 'Split', schema: splitSchema, ...spawn('sub_lead', SUB_LEAD_TIER) },
)

if (plan.escalation) {
  return { branch: args.branch, status: 'escalated', escalation: plan.escalation, builds: [] }
}

phase('Build')
const builds = await parallel(
  plan.briefs.map((b) => () => {
    const partBranch = `${args.branch}-${b.part}`
    const worktree = `${runtime.worktree_root}/${partBranch}`
    return agent(
      `${b.brief}
Work in your own worktree ${worktree}. Make it first with this exact line:
git worktree add -b ${partBranch} ${worktree} origin/${args.branch}
Edit only: ${b.files.join(', ')}.
Run the focused test of your part: ${b.test}. Do not run the whole oracle; the integrator runs it. Commit small and push after every commit. Open no pull request.
If the brief is unclear or the oracle cannot pass without an edit outside your files, stop and set status to escalated. Do not guess.
Report task ${b.part}, the full 40-character SHA of your last push, and the test command with its last output line.${rules}`,
      { label: `build-${b.part}`, phase: 'Build', schema: reportSchema, ...spawn('worker', b.tier) },
    )
  }),
)

const stuck = builds.filter((r) => r.status !== 'done' || !r.test.passed)
if (stuck.length > 0) {
  log(`${stuck.length} of ${builds.length} parts escalated or red; integration skipped`)
  return {
    branch: args.branch,
    status: 'escalated',
    escalation: stuck.map((r) => `${r.task}: ${r.escalation || `focused test red: ${r.test.line}`}`).join('\n'),
    builds,
  }
}

phase('Integrate')
const merged = await agent(
  `Merge these part branches into ${args.branch}: ${builds.map((r) => `${r.branch} at ${r.sha}`).join(', ')}.
Run the oracle: ${args.test}. Fix what fails, and list each part you fixed in reworked.
Push ${args.branch}. Open no pull request. Report the full 40-character SHA of the push.
If the oracle cannot pass, set escalation and push what you have.${rules}`,
  { label: 'integrate', phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', INTEGRATOR_TIER) },
)

return {
  branch: merged.branch,
  status: merged.oracle_passed && !merged.escalation ? 'done' : 'escalated',
  sha: merged.sha,
  oracle_passed: merged.oracle_passed,
  reworked: merged.reworked,
  escalation: merged.escalation || '',
  builds,
}
