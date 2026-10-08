export const meta = {
  name: 'split',
  description: 'Split one issue across parallel workers on part branches, then integrate. A sub-lead writes the oracle and the briefs, workers build, the sub-lead merges and pushes.',
  phases: ['Split', 'Build', 'Integrate'],
}

// args: { issue, branch, base, parts, test, rules }
//   issue  issue number or URL; the sub-lead reads it
//   branch the integration branch; each part builds on <branch>-<part>
//   base   the ref the branch is cut from
//   parts  array of 2 or more parts. Each part is a name, or { name, test } with the focused
//          test command of that part (for example a --test-name-pattern)
//   test   the command that runs the whole-issue oracle
//   rules  optional; the repo's code rules as text, passed to every agent
// The workflow opens no pull request. The PR, the CI gate and the merge stay with the main agent.

const SUBLEAD_MODEL = 'sonnet'
const WORKER_MODEL = 'haiku'
const OPUS_MODEL = 'opus'
const WORKTREE_DIR = '.claude/worktrees'
const MIN_PARTS = 2

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
          tier: { type: 'string', enum: ['haiku', 'sonnet', 'opus'], description: 'sonnet when the oracle does not cover the behaviour; opus when the step-up rule applies' },
        },
      },
    },
    escalation: { type: 'string', description: 'Empty when the issue splits cleanly. Otherwise the question for the lead.' },
  },
}

const buildSchema = {
  type: 'object',
  required: ['part', 'branch', 'sha', 'status'],
  properties: {
    part: { type: 'string' },
    branch: { type: 'string' },
    sha: { type: 'string' },
    status: { type: 'string', enum: ['done', 'escalated'] },
    escalation: { type: 'string', description: 'Set when status is escalated. Stop and ask; do not guess.' },
    notes: { type: 'string' },
  },
}

const integrateSchema = {
  type: 'object',
  required: ['branch', 'sha', 'oracle_passed', 'reworked'],
  properties: {
    branch: { type: 'string' },
    sha: { type: 'string' },
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
4. Write one brief per part. Each brief gives the focused test command of the part (a filter of the oracle that runs this part only), and names the files the part may edit, the oracle cases it must pass, and what it must not touch.
5. Tier each part. Use haiku when the oracle covers the behaviour. Use sonnet when it does not (UI judgment, lazy or eager control flow). Use opus when the step-up rule in AGENTS-AND-MODELS.md applies.
If the issue does not split cleanly, set escalation and write no briefs.${rules}`,
  { label: 'split', phase: 'Split', schema: splitSchema, model: SUBLEAD_MODEL, agentType: 'developer' },
)

if (plan.escalation) {
  return { branch: args.branch, status: 'escalated', escalation: plan.escalation, builds: [] }
}

phase('Build')
const modelFor = { haiku: WORKER_MODEL, sonnet: SUBLEAD_MODEL, opus: OPUS_MODEL }
const builds = await parallel(
  plan.briefs.map((b) => () => {
    const partBranch = `${args.branch}-${b.part}`
    const worktree = `${WORKTREE_DIR}/${partBranch}`
    return agent(
      `${b.brief}
Work in your own worktree ${worktree}. Make it first with this exact line:
git worktree add -b ${partBranch} ${worktree} origin/${args.branch}
Edit only: ${b.files.join(', ')}.
Run the focused test of your part: ${b.test}. Do not run the whole oracle; the integrator runs it. Commit small and push after every commit. Open no pull request.
If the brief is unclear or the oracle cannot pass without an edit outside your files, stop and set status to escalated. Do not guess.${rules}`,
      {
        label: `build-${b.part}`,
        phase: 'Build',
        schema: buildSchema,
        model: modelFor[b.tier] || SUBLEAD_MODEL,
        agentType: 'worker',
      },
    )
  }),
)

const stuck = builds.filter((r) => r.status !== 'done')
if (stuck.length > 0) {
  log(`${stuck.length} of ${builds.length} parts escalated; integration skipped`)
  return { branch: args.branch, status: 'escalated', escalation: stuck.map((r) => `${r.part}: ${r.escalation}`).join('\n'), builds }
}

phase('Integrate')
const merged = await agent(
  `Merge these part branches into ${args.branch}: ${builds.map((r) => `${r.branch} at ${r.sha}`).join(', ')}.
Run the oracle: ${args.test}. Fix what fails, and list each part you fixed in reworked.
Push ${args.branch}. Open no pull request.
If the oracle cannot pass, set escalation and push what you have.${rules}`,
  { label: 'integrate', phase: 'Integrate', schema: integrateSchema, model: SUBLEAD_MODEL, agentType: 'integrator' },
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
