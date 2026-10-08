export const meta = {
  name: 'wave',
  description: 'Run one wave of a contract graph: brief, build each task when its blockers are integrated, merge each green task into the wave branch 1 at a time, batched blind review beside the build, rework, 1 metrics row per task. Opens no PR.',
  phases: ['Brief', 'Build', 'Integrate', 'Review', 'Rework', 'Report'],
}

log(`wave ${args.graph ? `${args.graph.repo} ${args.graph.branch}: ${(args.graph.tasks || []).map((t) => `#${t.issue || t.id}`).join(' ')}` : 'with no args.graph'}`)

// args: { graph, gate, rules, decisions, runtime }
//   graph     a contract graph ($defs graph in plugin/contract/sdlc.schema.json). Check it first:
//             node plugin/contract/check.js graph <file>. graph.branch is the wave branch. It must be
//             on the remote at graph.base.sha before the run: every task branch starts on it.
//             A task with no brief gets a brief-writer. A task with split runs as a split.
//   gate      optional; the local gate command. The integrator runs it after each merge, after the
//             oracle of the task.
//   rules     optional; the repo's code rules as text, passed to every agent
//   decisions optional; the design decisions the reviewer must not report as findings
//   runtime   optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
// The workflow opens no pull request, merges nothing into main and deletes no branch. The lead owns
// the wave PR, CI, the merge and the cleanup after it.
//
// Order (x-transitions): planned -> briefed -> claimed -> building -> built -> integrated -> reviewed
// -> done | rework; rework -> built. A task starts when its blockers are integrated, not when a step
// ends. The brief of a blocked task starts when its blockers are building, so briefs do not take the
// slots ahead of the critical path. Only a red oracle stops a task: a green report with notes merges.

// The Claude profile: the parts of runtimes.json "claude" that this workflow reads.
const CLAUDE_RUNTIME = {
  provider: 'claude',
  tiers: { bounded: { model: 'haiku' }, judgment: { model: 'sonnet' }, lead: { model: 'opus' } },
  worktree_root: '.claude/worktrees',
  agent_types: { brief_writer: 'brief-writer', sub_lead: 'developer', worker: 'worker', integrator: 'integrator', reviewer: 'reviewer', skeptic: 'reviewer' },
  capabilities: {},
}
// Copies of x-roles, x-first-try, x-limits and x-transitions in plugin/contract/sdlc.schema.json.
// tests/workflows.js checks every transition and metrics row this workflow writes against the contract.
const ROLE_TIER = { brief_writer: 'judgment', sub_lead: 'judgment', integrator: 'judgment', reviewer: 'lead', skeptic: 'judgment' }
const FIRST_TRY_TIER = { integrator: 'bounded' }
const REVIEW_BATCH = 5
const SPLIT_PARTS_MIN = 2
const TRANSITIONS = {
  planned: ['briefed', 'escalated'],
  briefed: ['claimed'],
  claimed: ['building', 'briefed'],
  building: ['built', 'escalated', 'claimed'],
  built: ['integrated', 'escalated'],
  integrated: ['reviewed'],
  reviewed: ['done', 'rework', 'escalated'],
  rework: ['built', 'escalated', 'claimed'],
  escalated: ['briefed'],
  done: [],
}
const TIER_ORDER = ['bounded', 'judgment', 'lead']
const REWORK_MIN_TIER = 'judgment'
const HAS = ['enforced', 'instructed']
const SEVERITIES = ['minor', 'major', 'critical']
const SKEPTICS_PER_FINDING = 2
const REVIEW_TRIES = 2
const UNAVAILABLE = 'unavailable'
const MS_PER_S = 1000

// Contract shapes: copies of $defs brief, split, report, merge, review and verdict in
// plugin/contract/sdlc.schema.json, with $ref inlined. A workflow cannot import a file.
// tests/workflows.js fails when a copy drifts.
const oracleSchema = {
  type: 'object',
  description: 'The proof of a task. files is the inventory of every test or golden file that covers it, read before anyone says what the oracle covers.',
  required: ['command', 'files', 'uncovered'],
  properties: {
    command: { type: 'string', minLength: 1, description: 'The focused test command' },
    files: { type: 'array', items: { type: 'string' } },
    uncovered: { type: 'array', items: { type: 'string' }, description: 'Behaviours no oracle file covers. Not empty means the tier is not bounded.' },
  },
}

const briefSchema = {
  type: 'object',
  description: 'The output of a brief-writer for 1 task',
  required: ['task', 'brief', 'files', 'oracle', 'tier', 'why'],
  properties: {
    task: { type: 'string' },
    brief: { type: 'string', minLength: 1 },
    files: { type: 'array', minItems: 1, items: { type: 'string' } },
    oracle: oracleSchema,
    tier: { type: 'string', enum: ['bounded', 'judgment', 'lead'] },
    why: { type: 'string' },
  },
}

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

// ---- Setup
const graph = args.graph
if (!graph || !graph.repo || !graph.branch || !graph.base || !graph.base.sha || !(graph.tasks || []).length) {
  throw new Error('wave needs args.graph: a contract graph with repo, branch, base.sha and at least 1 task')
}
const runtime = args.runtime || CLAUDE_RUNTIME
const root = runtime.worktree_root
const wave = graph.branch
const limit = graph.rework_limit
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const gate = args.gate ? ` Then run the gate: ${args.gate}.` : ''
const issueOf = (t) => (t.issue ? `issue #${t.issue} of ${graph.repo}` : `task ${t.id} of ${graph.repo}`)
const maxTier = (a, b) => TIER_ORDER[Math.max(TIER_ORDER.indexOf(a), TIER_ORDER.indexOf(b))]
const green = (r) => Boolean(r && r.test && r.test.passed)
const merged = (m) => Boolean(m && m.oracle_passed && !m.escalation)
const has = (need) => {
  const c = (runtime.capabilities || {})[need]
  return Boolean(c && HAS.includes(c.status))
}
// spawn: the model and the effort of the tier (when the runtime sets one), and the agent type of the role.
const spawn = (role, tier) => {
  const t = runtime.tiers[tier]
  return { model: t.model, ...(t.effort && { effort: t.effort }), agentType: runtime.agent_types[role] }
}
const deferred = () => {
  let resolve
  const promise = new Promise((r) => (resolve = r))
  return { promise, resolve }
}

const ids = graph.tasks.map((t) => t.id)
const tasks = Object.fromEntries(
  graph.tasks.map((t) => [
    t.id,
    {
      task: t, state: 'planned', tier: t.tier, branch: t.branch || `${wave}-${t.id}`, plan: null, agents: 0, rounds: 0,
      findings: { critical: 0, major: 0, minor: 0 }, reports: [], merges: [], notes: [], reason: '',
      claimedAt: 0, integratedAt: 0, order: 0, building: deferred(), integrated: deferred(),
    },
  ]),
)
// A blocker that is no task, or a blocker cycle, would wait forever: refuse the graph.
for (const t of graph.tasks) for (const b of t.blockers) if (!tasks[b]) throw new Error(`task ${t.id}: blocker ${b} is not a task`)
const seen = new Set()
while (seen.size < ids.length) {
  const ready = ids.filter((id) => !seen.has(id) && tasks[id].task.blockers.every((b) => seen.has(b)))
  if (ready.length === 0) throw new Error(`blocker cycle among tasks ${ids.filter((id) => !seen.has(id)).join(', ')}`)
  ready.forEach((id) => seen.add(id))
}

const transitions = []
function move(id, to, extra = {}) {
  const s = tasks[id]
  if (!TRANSITIONS[s.state].includes(to)) throw new Error(`task ${id}: ${s.state} -> ${to} is not an allowed transition`)
  transitions.push({ task: id, from: s.state, to, at: new Date().toISOString(), ...extra })
  s.state = to
}
function stop(id, to, reason) {
  const s = tasks[id]
  if (to) move(id, to, { reason })
  s.reason = reason
  s.building.resolve(false)
  s.integrated.resolve(false)
  log(`${id}: ${s.state}: ${reason}`)
}
// call: 1 agent for 1 or more tasks. Each task counts the agent. A failed spawn returns null.
async function call(owners, prompt, opts) {
  for (const id of [].concat(owners)) tasks[id].agents++
  try {
    return await agent(prompt, opts)
  } catch (e) {
    log(`${opts.label}: ${e.message}`)
    return null
  }
}

// ---- Brief
async function brief(id) {
  const s = tasks[id]
  const t = s.task
  if (t.brief) return { brief: t.brief, files: t.files, oracle: t.oracle, tier: t.tier }
  const b = await call(
    id,
    `Write the brief for ${issueOf(t)}, task ${id}. Read only: edit, commit and push nothing.
The code of its blockers (${t.blockers.join(', ') || 'none'}) lands on the wave branch: read origin/${wave} after git fetch -q origin.
The plan says: tier ${t.tier}; files ${t.files.join(', ')}; oracle ${t.oracle.command} (files: ${t.oracle.files.join(', ') || 'none'}; uncovered: ${t.oracle.uncovered.join('; ') || 'none'}).
Write what a worker needs to finish with no judgment call: the files, each signature exactly, each trap quoted from the source, the oracle and its focused command. Inventory the oracle files and list each behaviour they do not cover. Tier it: bounded only when the oracle covers every behaviour; judgment when 1 or more is uncovered; lead when the step-up rule in AGENTS-AND-MODELS.md applies.${rules}`,
    { label: `brief ${id}`, phase: 'Brief', schema: briefSchema, ...spawn('brief_writer', ROLE_TIER.brief_writer) },
  )
  if (!b) return null
  // The tier never drops below the plan, and a bounded tier needs an oracle that covers every behaviour.
  const tier = maxTier(maxTier(t.tier, b.tier), b.oracle.uncovered.length > 0 ? 'judgment' : 'bounded')
  return { brief: b.brief, files: b.files, oracle: b.oracle, tier }
}

// ---- Build
function workerPrompt({ id, what, text, branch, from, files, test, oracleFiles, round }) {
  return `${what}
${text}
Work in your own worktree ${root}/${branch}. Make it first with this exact line:
git fetch -q origin && git worktree add -b ${branch} ${root}/${branch} origin/${from}
Edit only: ${files.join(', ')}.${oracleFiles.length > 0 ? ` Do not edit the oracle files: ${oracleFiles.join(', ')}.` : ''}
Run only the focused test: ${test}. Commit small and push after every commit: git push -q -u origin ${branch}. Open no pull request. Merge nothing.
If the brief is unclear or the test cannot pass without an edit outside your files, push what you have and set status to escalated. Do not guess.
Report task ${id}, round ${round}, branch ${branch}, the full 40-character SHA of your last push, and the test command with its last output line.${rules}`
}

function build(id, plan) {
  const s = tasks[id]
  return call(
    id,
    workerPrompt({ id, what: `Build ${issueOf(s.task)}.`, text: plan.brief, branch: s.branch, from: wave, files: plan.files, test: plan.oracle.command, oracleFiles: plan.oracle.files, round: 0 }),
    { label: `build ${id}`, phase: 'Build', schema: reportSchema, ...spawn('worker', plan.tier) },
  )
}

// buildSplit: the split workflow as a plain function (a wave may not nest a workflow). It returns a
// report of the task branch, or null with s.reason set.
async function buildSplit(id, plan) {
  const s = tasks[id]
  const sp = await call(
    id,
    `Split ${issueOf(s.task)} into these parts: ${s.task.split.join(', ')}. Brief:
${plan.brief}
1. Cut branch ${s.branch} from origin/${wave}: git fetch -q origin && git worktree add -b ${s.branch} ${root}/${s.branch} origin/${wave}
2. The oracle of the whole task is: ${plan.oracle.command}. Add a focused filter of it for each part.
3. Write stubs for the seams between parts, so each part builds alone. Commit the stubs and push ${s.branch}.
4. Write 1 brief per part: its files (2 parts never edit the same file, and only files in ${plan.files.join(', ')}), its focused test, the oracle cases it must pass, what it must not touch.
5. Tier each part: bounded when the oracle covers it, judgment when it does not, lead when the step-up rule in AGENTS-AND-MODELS.md applies.
If the task does not split cleanly, set escalation and write no briefs.${rules}`,
    { label: `split ${id}`, phase: 'Build', schema: splitSchema, ...spawn('sub_lead', ROLE_TIER.sub_lead) },
  )
  if (!sp || sp.escalation || sp.briefs.length < SPLIT_PARTS_MIN) {
    s.reason = sp ? sp.escalation || `the split has fewer than ${SPLIT_PARTS_MIN} parts` : 'the sub-lead returned nothing'
    return null
  }
  const parts = await parallel(
    sp.briefs.map((b) => () =>
      call(
        id,
        workerPrompt({ id: b.part, what: `Build part ${b.part} of ${issueOf(s.task)}.`, text: b.brief, branch: `${s.branch}-${b.part}`, from: s.branch, files: b.files, test: b.test, oracleFiles: plan.oracle.files, round: 0 }),
        { label: `build ${id} ${b.part}`, phase: 'Build', schema: reportSchema, ...spawn('worker', b.tier) },
      ),
    ),
  )
  const red = parts.filter((r) => !green(r))
  if (red.length > 0) {
    s.reason = `${red.length} of ${parts.length} parts are red or missing`
    return null
  }
  const m = await call(
    id,
    `Merge these part branches into ${s.branch}: ${parts.map((r) => `${r.branch} at ${r.sha}`).join(', ')}. Work in ${root}/${s.branch}.
Run the oracle: ${plan.oracle.command}. Fix what fails, and list each part you fixed in reworked.
Push ${s.branch}. Open no pull request. Report the full 40-character SHA of the push.
If the oracle cannot pass, set escalation and push what you have.${rules}`,
    { label: `split-merge ${id}`, phase: 'Build', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) },
  )
  if (!merged(m)) {
    s.reason = m ? m.escalation || 'the part merge is red' : 'the part integrator returned nothing'
    return null
  }
  return { task: id, branch: s.branch, sha: m.sha, status: 'done', round: 0, test: { command: plan.oracle.command, line: 'the oracle passed after the part merge', passed: true } }
}

// ---- Integrate: 1 branch at a time, the first try on its x-first-try tier, the step-up on its x-roles tier.
let mergeChain = Promise.resolve()
let waveHead = graph.base.sha
let mergeCount = 0
function integrate(id, report) {
  const s = tasks[id]
  const prompt = (resolve) => `You integrate task ${id} into the wave branch ${wave} of ${graph.repo}. Merge 1 branch: ${report.branch} at ${report.sha}.
1. If the worktree ${root}/${wave} is missing, make it: git fetch -q origin && git worktree add -B ${wave} ${root}/${wave} origin/${wave}
   Otherwise, in it: git fetch -q origin && git merge -q --ff-only origin/${wave}
2. In it: git merge --no-ff --no-commit ${report.sha}
3. On a conflict: ${resolve ? 'resolve it when both sides are clear; keep the behaviour of both. When the 2 sides change the same contract in 2 ways, run git merge --abort and set escalation to the files.' : 'run git merge --abort and set escalation to the conflicting files. Do not resolve it.'}
4. Run the oracle of the task: ${s.plan.oracle.command}.${gate}
5. Green: git commit -q -m "Merge ${report.branch} into ${wave}" && git push -q origin ${wave}. Report branch ${wave}, merged [${report.branch}], oracle_passed true and the full 40-character SHA of the push.
   Red: git merge --abort. Report oracle_passed false and the last output line in escalation.
Keep the worktree for the next merge. Open no pull request. Never touch main.${rules}`
  const run = async () => {
    const before = waveHead
    let m = await call(id, prompt(false), { label: `merge ${id}`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', FIRST_TRY_TIER.integrator) })
    if (!merged(m)) {
      m = await call(id, prompt(true), { label: `merge ${id} step-up`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) })
    }
    s.merges.push(m)
    if (!merged(m)) return { ok: false, reason: m ? m.escalation || 'the merge is red' : 'the integrator returned nothing' }
    waveHead = m.sha
    s.order = ++mergeCount
    s.integratedAt = Date.now()
    return { ok: true, diff: `${before}...${report.sha}` }
  }
  const p = mergeChain.then(run)
  mergeChain = p.catch(() => null)
  return p
}

// ---- Review beside the build: batches of REVIEW_BATCH integrated results, flushed when the build ends.
const queue = []
const inflight = new Set()
const reviews = []
function track(p) {
  inflight.add(p)
  p.then(() => inflight.delete(p))
  return p
}
function enqueue(entry) {
  queue.push(entry)
  if (queue.length >= REVIEW_BATCH) track(review(queue.splice(0, REVIEW_BATCH)))
}

async function review(batch) {
  const batchIds = batch.map((e) => e.id)
  let rv = null
  for (let i = 0; i < REVIEW_TRIES && !rv; i++) {
    rv = await call(
      batchIds,
      `Review these ${batch.length} results of ${graph.repo} as 1 batch. They are merged on the wave branch ${wave}. You do not know who wrote them. Judge only the diffs and the tests. Read only: edit, commit and push nothing. Run git fetch -q origin first.
Results:
${batch.map((e) => `- ${e.id}: diff ${e.diff}; test: ${e.test}`).join('\n')}
Design decisions the results must follow (they are not findings):
${args.decisions || '(none given)'}${rules}
1. Run each test. Score each result 1 to 5 on correctness, code rules, tests and scope.
2. For each pair that solves alike or clashes, say which is better and why.
3. List findings. Mark a finding cross_issue when it spans 2 or more results.
4. Give each finding a severity of ${SEVERITIES.join(', ')} and evidence a second reader can check.`,
      { label: `review ${batchIds.join(' ')}`, phase: 'Review', schema: reviewSchema, ...spawn('reviewer', ROLE_TIER.reviewer) },
    )
  }
  if (!rv) {
    for (const id of batchIds) {
      move(id, 'reviewed')
      stop(id, 'escalated', 'the review returned nothing')
    }
    return
  }
  const inBatch = (f) => f.ids.filter((x) => batchIds.includes(x))
  const named = rv.findings.filter((f) => inBatch(f).length > 0)
  const heavy = named.filter((f) => f.severity !== 'minor')
  const checked = await parallel(
    heavy.map((f) => async () => {
      const verdicts = await parallel(
        Array.from({ length: SKEPTICS_PER_FINDING }, (_, i) => () =>
          call(
            inBatch(f),
            `Try to disprove this finding. Check the evidence yourself. Set agree to true only if you reproduce the problem. Read only.
Finding ${f.id} (${f.severity}) on ${f.ids.join(', ')}: ${f.claim}
Evidence: ${f.evidence}
Results:
${batch.filter((e) => f.ids.includes(e.id)).map((e) => `- ${e.id}: diff ${e.diff}; test: ${e.test}`).join('\n')}${rules}`,
            { label: `skeptic ${f.id} ${i + 1}`, phase: 'Review', schema: verdictSchema, ...spawn('skeptic', ROLE_TIER.skeptic) },
          ),
        ),
      )
      return { ...f, stands: verdicts.every((v) => v && v.agree) }
    }),
  )
  const standing = [...named.filter((f) => f.severity === 'minor'), ...checked.filter((f) => f.stands)]
  reviews.push({ ids: batchIds, scores: rv.scores, pairs: rv.pairs || [], findings: standing, dropped: checked.filter((f) => !f.stands).map((f) => f.id) })
  for (const f of standing) for (const id of inBatch(f)) tasks[id].findings[f.severity]++
  // A cross-issue finding goes to the result merged last: it was built on top of the others.
  const owner = (f) => inBatch(f).reduce((a, b) => (tasks[b].order > tasks[a].order ? b : a))
  for (const id of batchIds) {
    move(id, 'reviewed')
    const own = standing.filter((f) => f.severity !== 'minor' && owner(f) === id)
    if (own.length === 0) move(id, 'done')
    else if (tasks[id].rounds < limit) track(rework(id, own))
    else stop(id, 'escalated', `findings ${own.map((f) => f.id).join(', ')} stand after ${tasks[id].rounds} rework rounds`)
  }
}

// ---- Rework: 1 round per finding set on a new branch from the wave branch; it merges and is reviewed again.
async function rework(id, findings) {
  const s = tasks[id]
  s.rounds++
  move(id, 'rework', { round: s.rounds, reason: findings.map((f) => f.id).join(', ') })
  const r = await call(
    id,
    workerPrompt({
      id,
      what: `Rework ${issueOf(s.task)}, round ${s.rounds}. Its code is already on ${wave}. Fix exactly these review findings, nothing else:`,
      text: findings.map((f) => `- ${f.id} ${f.severity}: ${f.claim} Evidence: ${f.evidence}`).join('\n'),
      branch: `${s.branch}-r${s.rounds}`, from: wave, files: s.plan.files, test: s.plan.oracle.command, oracleFiles: s.plan.oracle.files, round: s.rounds,
    }),
    { label: `rework ${id} ${s.rounds}`, phase: 'Rework', schema: reportSchema, ...spawn('worker', maxTier(s.tier, REWORK_MIN_TIER)) },
  )
  if (!green(r)) return stop(id, 'escalated', r ? r.escalation || `rework oracle red: ${r.test.line}` : 'the rework agent returned nothing')
  s.reports.push(r)
  move(id, 'built')
  const m = await integrate(id, r)
  if (!m.ok) return stop(id, 'escalated', m.reason)
  move(id, 'integrated')
  enqueue({ id, diff: m.diff, test: s.plan.oracle.command })
}

// ---- The graph: every task runs at once and waits on its blockers.
async function runTask(id) {
  const s = tasks[id]
  const t = s.task
  const lacks = (t.needs || []).filter((n) => !has(n))
  if (lacks.length > 0) return stop(id, 'escalated', `needs ${lacks.join(', ')}; runtime ${runtime.provider} lacks it, so a peer that has it takes the task`)
  const building = await Promise.all(t.blockers.map((b) => tasks[b].building.promise))
  if (!building.every(Boolean)) return stop(id, null, `blocker ${t.blockers.filter((b, i) => !building[i]).join(', ')} did not start`)
  const plan = await brief(id)
  if (!plan) return stop(id, 'escalated', 'the brief-writer returned nothing')
  s.plan = plan
  s.tier = plan.tier
  move(id, 'briefed')
  const integrated = await Promise.all(t.blockers.map((b) => tasks[b].integrated.promise))
  if (!integrated.every(Boolean)) return stop(id, null, `blocker ${t.blockers.filter((b, i) => !integrated[i]).join(', ')} was not integrated`)
  // The lead claimed the graph before the run; the claim covers each task from here.
  move(id, 'claimed')
  s.claimedAt = Date.now()
  move(id, 'building')
  s.building.resolve(true)
  const r = t.split ? await buildSplit(id, plan) : await build(id, plan)
  if (!green(r)) return stop(id, 'escalated', r ? r.escalation || `oracle red: ${r.test.line}` : s.reason || 'the worker returned nothing')
  if (r.escalation || r.notes) s.notes.push(r.escalation || r.notes)
  s.reports.push(r)
  move(id, 'built')
  const m = await integrate(id, r)
  if (!m.ok) return stop(id, 'escalated', m.reason)
  move(id, 'integrated')
  s.integrated.resolve(true)
  enqueue({ id, diff: m.diff, test: plan.oracle.command })
}

phase('Build')
await Promise.all(ids.map(runTask))
for (;;) {
  if (inflight.size > 0) await Promise.all([...inflight])
  else if (queue.length > 0) track(review(queue.splice(0, REVIEW_BATCH)))
  else break
}
await mergeChain

// ---- Report: 1 metrics row per task that started an agent. This runtime reports no usage.
phase('Report')
const result = (s) => (s.state === 'done' ? 'merged' : s.state === 'escalated' ? 'escalated' : 'failed')
const metrics = ids
  .filter((id) => tasks[id].agents > 0)
  .map((id) => {
    const s = tasks[id]
    const sp = runtime.tiers[s.tier]
    return {
      task: id, provider: runtime.provider, tier: s.tier, model: sp.model, ...(sp.effort && { effort: sp.effort }),
      agents: s.agents, elapsed_s: s.claimedAt ? Math.round(((s.integratedAt || Date.now()) - s.claimedAt) / MS_PER_S) : 0,
      rework_rounds: s.rounds, findings: s.findings, result: result(s), tokens: UNAVAILABLE, cost_usd: UNAVAILABLE,
    }
  })
const open = ids.filter((id) => tasks[id].state !== 'done')
log(`${ids.length - open.length} of ${ids.length} tasks done on ${wave} at ${waveHead}; ${open.length} need the lead`)

return {
  branch: wave,
  sha: waveHead,
  done: ids.filter((id) => tasks[id].state === 'done'),
  escalations: open.map((id) => ({ task: id, state: tasks[id].state, reason: tasks[id].reason })),
  tasks: ids.map((id) => {
    const s = tasks[id]
    return { task: id, issue: s.task.issue, state: s.state, tier: s.tier, branch: s.branch, rounds: s.rounds, notes: s.notes, reports: s.reports, merges: s.merges }
  }),
  reviews,
  metrics,
  transitions,
}
