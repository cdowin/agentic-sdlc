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
// It works under the lead's claim of the issue and posts no claim of its own.

// ---- contract: begin
// Generated from plugin/contract by node tests/workflows.js --write. Do not edit.
const contract = {
  "x-tiers": {"bounded":"An oracle covers every behaviour that matters. A tight brief, a file list, the signatures, 15-30 min.","judgment":"1 or more behaviours have no oracle, or the task has a design choice. Also brief-writing, sub-lead, integration and a skeptic.","lead":"The plan, the chief of staff, every review, and a change the step-up rule names."},
  "x-roles": {"lead":"lead","brief_writer":"judgment","sub_lead":"judgment","worker":"bounded","integrator":"judgment","reviewer":"lead","skeptic":"judgment","spec_writer":"judgment","spec_designer":"lead","blast_radius":"lead"},
  "x-first-try": {"integrator":"bounded"},
  "x-capabilities": ["structured_output","model_per_spawn","effort_per_spawn","tool_restriction","worktree_per_task","parallel_spawn","follow_up","interrupt","usage_report","image_generation"],
  "x-optional-capabilities": ["image_generation"],
  "x-need-labels": {"image_generation":"needs:image-gen"},
  "x-limits": {"rework_rounds":2,"review_batch":5,"split_parts_min":2,"stale_claim_minutes":120,"clock_skew_minutes":5,"spec_rounds":1,"blast_radius_max":4},
  "x-transitions": {"planned":["briefed","escalated"],"briefed":["claimed"],"claimed":["building","briefed"],"building":["built","escalated","claimed"],"built":["integrated","escalated"],"integrated":["reviewed"],"reviewed":["done","rework","escalated"],"rework":["built","escalated","claimed"],"escalated":["briefed"],"done":[]},
}
const LIMITS = contract['x-limits']
const TIERS = Object.keys(contract['x-tiers'])
const ROLE_TIER = contract['x-roles']
const FIRST_TRY = contract['x-first-try']
const CAPABILITIES = contract['x-capabilities']
const HAS = ['enforced', 'instructed']
const TRANSITIONS = contract['x-transitions']
// higherTier: the tier a task runs at is the higher of the planned tier and the brief's tier.
// A brief may raise the tier, never lower it.
const higherTier = (a, b) => TIERS[Math.max(TIERS.indexOf(a), TIERS.indexOf(b))]
// hasCapability: the runtime has the capability when its status is enforced or instructed.
const hasCapability = (runtime, name) => {
  const c = (runtime.capabilities || {})[name]
  return Boolean(c && HAS.includes(c.status))
}
// The Claude profile: runtimes.json "claude" without the evidence. The default of args.runtime.
const CLAUDE_RUNTIME = {
  "provider": "claude",
  "tiers": {"bounded":{"model":"haiku"},"judgment":{"model":"sonnet"},"lead":{"model":"opus"}},
  "worktree_root": ".claude/worktrees",
  "agent_types": {"lead":"agentic-sdlc:chief-of-staff","brief_writer":"agentic-sdlc:brief-writer","sub_lead":"agentic-sdlc:developer","worker":"agentic-sdlc:worker","integrator":"agentic-sdlc:integrator","reviewer":"agentic-sdlc:reviewer","skeptic":"agentic-sdlc:reviewer","spec_writer":"agentic-sdlc:developer","spec_designer":"agentic-sdlc:developer","blast_radius":"agentic-sdlc:reviewer"},
  "capabilities": {"structured_output":{"status":"enforced"},"model_per_spawn":{"status":"enforced"},"effort_per_spawn":{"status":"unverified"},"tool_restriction":{"status":"enforced"},"worktree_per_task":{"status":"instructed"},"parallel_spawn":{"status":"enforced"},"follow_up":{"status":"unverified"},"interrupt":{"status":"unverified"},"usage_report":{"status":"unverified"},"image_generation":{"status":"absent"}},
}
// ---- contract: end
// A role spawns at its x-roles tier. A worker takes the tier of its part; judgment when that is unknown.
const DEFAULT_PART_TIER = 'judgment'

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
    at: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$', description: 'UTC time when the agent finished, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock.' },
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
    at: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$', description: 'UTC time when the agent finished, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock.' },
  },
}

const parts = args.parts || []
if (!args.issue || !args.branch || !args.base || !args.test || parts.length < LIMITS.split_parts_min) {
  throw new Error(`split needs args issue, branch, base, test and at least ${LIMITS.split_parts_min} parts`)
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
  { label: 'split', phase: 'Split', schema: splitSchema, ...spawn('sub_lead', ROLE_TIER.sub_lead) },
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
  { label: 'integrate', phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) },
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
