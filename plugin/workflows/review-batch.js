export const meta = {
  name: 'review-batch',
  description: 'One blind reviewer scores several results, judges pairs and lists cross-issue findings. Two skeptics check each major or critical finding; it stands only if both agree.',
  phases: ['Review', 'Skeptics'],
}

// args: { results: [{ id, diff, test }], decisions, rules, runtime }
//   results   the results to review; diff is a ref range or a patch, test is the command that proves it
//   decisions text of the design decisions the results must follow
//   rules     optional; the repo's code rules as text
//   runtime   optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
// The reviewer sees no author, no model name and no cost. One batch review finds
// cross-issue problems that single reviews miss.

// ---- contract: begin
// Generated from plugin/contract by node tests/workflows.js --write. Do not edit.
const contract = {
  "x-tiers": {"bounded":"An oracle covers every behaviour that matters. A tight brief, a file list, the signatures, 15-30 min.","judgment":"1 or more behaviours have no oracle, or the task has a design choice. Also brief-writing, sub-lead, integration and a skeptic.","lead":"The plan, the chief of staff, every review, and a change the step-up rule names."},
  "x-roles": {"lead":"lead","brief_writer":"judgment","sub_lead":"judgment","worker":"bounded","integrator":"judgment","reviewer":"lead","skeptic":"judgment","spec_writer":"judgment","spec_designer":"lead"},
  "x-first-try": {"integrator":"bounded"},
  "x-capabilities": ["structured_output","model_per_spawn","effort_per_spawn","tool_restriction","worktree_per_task","parallel_spawn","follow_up","interrupt","usage_report","image_generation"],
  "x-optional-capabilities": ["image_generation"],
  "x-need-labels": {"image_generation":"needs:image-gen"},
  "x-limits": {"rework_rounds":2,"review_batch":5,"split_parts_min":2,"stale_claim_minutes":120,"clock_skew_minutes":5,"spec_rounds":1},
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
  "agent_types": {"lead":"agentic-sdlc:chief-of-staff","brief_writer":"agentic-sdlc:brief-writer","sub_lead":"agentic-sdlc:developer","worker":"agentic-sdlc:worker","integrator":"agentic-sdlc:integrator","reviewer":"agentic-sdlc:reviewer","skeptic":"agentic-sdlc:reviewer","spec_writer":"agentic-sdlc:developer","spec_designer":"agentic-sdlc:developer"},
  "capabilities": {"structured_output":{"status":"enforced"},"model_per_spawn":{"status":"enforced"},"effort_per_spawn":{"status":"unverified"},"tool_restriction":{"status":"enforced"},"worktree_per_task":{"status":"instructed"},"parallel_spawn":{"status":"enforced"},"follow_up":{"status":"unverified"},"interrupt":{"status":"unverified"},"usage_report":{"status":"unverified"},"image_generation":{"status":"absent"}},
}
// ---- contract: end
const SKEPTICS_PER_FINDING = 2
const SEVERITIES = ['minor', 'major', 'critical']

// Contract shapes: reviewSchema and verdictSchema are copies of $defs review and verdict in
// plugin/contract/sdlc.schema.json. A workflow cannot import a file. tests/workflows.js fails
// when a copy drifts.

const reviewSchema = {
  type: 'object',
  required: ['scores', 'findings'],
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'correctness', 'code_rules', 'tests', 'scope'],
        properties: {
          id: { type: 'string' },
          correctness: { type: 'integer', minimum: 1, maximum: 5 },
          code_rules: { type: 'integer', minimum: 1, maximum: 5 },
          tests: { type: 'integer', minimum: 1, maximum: 5 },
          scope: { type: 'integer', minimum: 1, maximum: 5 },
        },
      },
    },
    pairs: {
      type: 'array',
      description: 'A judgment for each pair of results that solve alike or clash',
      items: {
        type: 'object',
        required: ['a', 'b', 'better', 'reason'],
        properties: {
          a: { type: 'string' },
          b: { type: 'string' },
          better: { type: 'string', description: 'The id of the better result, or tie' },
          reason: { type: 'string' },
        },
      },
    },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'ids', 'severity', 'claim', 'evidence', 'cross_issue'],
        properties: {
          id: { type: 'string', description: 'A short unique id for the finding' },
          ids: { type: 'array', items: { type: 'string' }, description: 'The results the finding touches' },
          severity: { type: 'string', enum: SEVERITIES },
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'File and line, or the command and its output' },
          cross_issue: { type: 'boolean', description: 'True when the problem spans 2 or more results' },
        },
      },
    },
  },
}

const verdictSchema = {
  type: 'object',
  required: ['agree', 'reason'],
  properties: {
    agree: { type: 'boolean', description: 'True only if you reproduced the problem from the evidence' },
    reason: { type: 'string' },
  },
}

const results = args.results || []
if (results.length === 0) throw new Error('review-batch needs args.results with at least 1 result')
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const runtime = args.runtime || CLAUDE_RUNTIME
// spawn: the model and the effort of the tier (when the runtime sets one), and the agent type of the role.
const spawn = (role, tier) => {
  const t = runtime.tiers[tier]
  return { model: t.model, ...(t.effort && { effort: t.effort }), agentType: runtime.agent_types[role] }
}

phase('Review')
const review = await agent(
  `Review these ${results.length} results as one batch. You do not know who wrote them. Judge only the diffs and the tests.
Results:
${results.map((r) => `- ${r.id}: diff ${r.diff}; test: ${r.test}`).join('\n')}
Design decisions the results must follow:
${args.decisions || '(none given)'}${rules}
1. Run each test. Score each result 1 to 5 on correctness, code rules, tests and scope.
2. For each pair that solves alike or clashes, say which is better and why.
3. List findings. Mark a finding cross_issue when it spans 2 or more results (a clash on a shared file, a mismatched interface, a duplicated helper).
4. Give each finding a severity of ${SEVERITIES.join(', ')} and evidence a second reader can check.`,
  { label: 'review', phase: 'Review', schema: reviewSchema, ...spawn('reviewer', ROLE_TIER.reviewer) },
)

phase('Skeptics')
const heavy = review.findings.filter((f) => f.severity !== 'minor')
const checked = await parallel(
  heavy.map((f) => async () => {
    const verdicts = await parallel(
      Array.from({ length: SKEPTICS_PER_FINDING }, (_, i) => () =>
        agent(
          `Try to disprove this finding. Check the evidence yourself. Set agree to true only if you reproduce the problem.
Finding ${f.id} (${f.severity}) on ${f.ids.join(', ')}: ${f.claim}
Evidence: ${f.evidence}
Results:
${results.filter((r) => f.ids.includes(r.id)).map((r) => `- ${r.id}: diff ${r.diff}; test: ${r.test}`).join('\n')}${rules}`,
          { label: `skeptic-${f.id}-${i + 1}`, phase: 'Skeptics', schema: verdictSchema, ...spawn('skeptic', ROLE_TIER.skeptic) },
        ),
      ),
    )
    return { ...f, verdicts, stands: verdicts.every((v) => v.agree) }
  }),
)

const standing = checked.filter((f) => f.stands)
const dropped = checked.filter((f) => !f.stands)
log(`${standing.length} of ${heavy.length} major or critical findings stand`)

return {
  scores: review.scores,
  pairs: review.pairs || [],
  findings: [...standing, ...review.findings.filter((f) => f.severity === 'minor')],
  dropped,
}
