export const meta = {
  name: 'review-batch',
  description: 'One blind reviewer scores several results, judges pairs and lists cross-issue findings. Two skeptics check each major or critical finding; it stands only if both agree.',
  phases: ['Review', 'Skeptics'],
}

// args: { results: [{ id, diff, test }], decisions, rules }
//   results   the results to review; diff is a ref range or a patch, test is the command that proves it
//   decisions text of the design decisions the results must follow
//   rules     optional; the repo's code rules as text
// The reviewer sees no author, no model name and no cost. One batch review finds
// cross-issue problems that single reviews miss.

const REVIEW_MODEL = 'opus'
const SKEPTIC_MODEL = 'sonnet'
const SKEPTICS_PER_FINDING = 2
const SEVERITIES = ['minor', 'major', 'critical']

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
  { label: 'review', phase: 'Review', schema: reviewSchema, model: REVIEW_MODEL, agentType: 'reviewer' },
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
          { label: `skeptic-${f.id}-${i + 1}`, phase: 'Skeptics', schema: verdictSchema, model: SKEPTIC_MODEL, agentType: 'reviewer' },
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
