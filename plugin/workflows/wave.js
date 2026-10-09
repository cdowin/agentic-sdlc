export const meta = {
  name: 'wave',
  description: 'Run one wave of a contract graph: brief, build each task when its blockers are integrated, merge each green task into the wave branch 1 at a time, batched blind review beside the build, rework, 1 metrics row per task. Opens no PR.',
  phases: ['Brief', 'Build', 'Integrate', 'Review', 'Rework', 'Report'],
}

log(`wave ${args.graph ? `${args.graph.repo} ${args.graph.branch}: ${(args.graph.tasks || []).map((t) => `#${t.issue || t.id}`).join(' ')}` : 'with no args.graph'}`)

// args: { graph, started_at, claimed_at, claims, gate, regression, rules, decisions, runtime }
//   graph     a contract graph ($defs graph in plugin/contract/sdlc.schema.json). Check it first:
//             node plugin/contract/check.js graph <file>. graph.branch is the wave branch. It must be
//             on the remote at graph.base.sha before the run: every task branch starts on it.
//             A task with spec_sha (plan pushed its spec to spec/<task id>) starts on that SHA and
//             merges the wave branch into it, so the wave branch gets the red spec tests only with the
//             task. This holds for a build and for a split. A task with no spec_sha starts on the wave
//             branch: a spec/<task id> branch on the remote is never used by name.
//             A task with no brief gets a brief-writer. A task with split runs as a split.
//   started_at  required; ISO UTC time (the lead runs date -u +%Y-%m-%dT%H:%M:%SZ). The runtime forbids
//             Date, so the workflow reads no clock: this is its first known time.
//   claimed_at optional; task id -> ISO UTC time of the lead's claim comment. Default: started_at.
//   claims    task id -> the URL of the lead's claim comment on the task's issue (the contract
//             claim shape). The lead posts 1 claim per task before the run. A task with no claim
//             does not start, and neither does a task it blocks.
//   gate      optional; the local gate command. The integrator runs it after each merge, after the
//             oracle of the task.
//   regression optional; a command that runs the one load-bearing scenario. At the end of the wave,
//             1 agent runs it on graph.base.sha and 1 on the final wave head (2 agents, no retry).
//             Exit 0 means the scenario passes. A pass on the base and a fail on the head escalates
//             the wave. With no merge the lane is skipped. With no value nothing changes.
//   rules     optional; the repo's code rules as text, passed to every agent
//   decisions optional; the design decisions the reviewer must not report as findings
//   runtime   optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
// The workflow opens no pull request, merges nothing into main and deletes no branch. The lead owns
// the wave PR, CI, the merge and the cleanup after it.
//
// Order (x-transitions): planned -> briefed -> claimed -> building -> built -> integrated -> reviewed
// -> done | rework; rework -> built. A task starts when its blockers are integrated, not when a step
// ends. The brief of a blocked task starts when its blockers are building, so briefs do not take the
// slots ahead of the critical path. The lead accepts a worker report only when it is done, names the
// task and its branch, has a full SHA and a green focused test. Any other report stops the task.

// ---- contract: begin
// Generated from plugin/contract by node tests/workflows.js --write. Do not edit.
const contract = {
  "x-tiers": {"bounded":"An oracle covers every behaviour that matters. A tight brief, a file list, the signatures, 15-30 min.","judgment":"1 or more behaviours have no oracle, or the task has a design choice. Also brief-writing, sub-lead, integration and a skeptic.","lead":"The plan, the chief of staff, every review, and a change the step-up rule names."},
  "x-roles": {"lead":"lead","brief_writer":"judgment","sub_lead":"judgment","worker":"bounded","integrator":"judgment","reviewer":"lead","skeptic":"judgment","spec_writer":"judgment","spec_designer":"lead","blast_radius":"judgment"},
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
const dupes = (xs) => xs.filter((x, i) => xs.indexOf(x) !== i)
// norm: a POSIX path with no empty, . or resolvable .. segment and no trailing slash. './a/' is 'a'.
const norm = (p) => {
  const abs = p.startsWith('/')
  const out = []
  for (const seg of p.split('/')) {
    if (seg === '' || seg === '.') continue
    if (seg !== '..') out.push(seg)
    else if (out.length > 0 && out[out.length - 1] !== '..') out.pop()
    else if (!abs) out.push(seg)
  }
  return abs ? `/${out.join('/')}` : out.join('/') || '.'
}
// Paths collide when they are equal after norm or 1 is a directory of the other.
const collide = (a, b) => {
  const [x, y] = [norm(a), norm(b)]
  return x === y || x === '.' || y === '.' || x.startsWith(`${y}/`) || y.startsWith(`${x}/`)
}
const overlap = (as, bs) => as.flatMap((a) => bs.filter((b) => collide(a, b)).map((b) => (norm(a) === norm(b) ? a : `${a} and ${b}`)))

function graphMeaning(g) {
  const out = []
  if (g.rework_limit > LIMITS.rework_rounds) out.push(`rework_limit ${g.rework_limit} is over x-limits.rework_rounds ${LIMITS.rework_rounds}`)
  const ids = g.tasks.map((t) => t.id)
  for (const d of new Set(dupes(ids))) out.push(`tasks: id ${d} is not unique`)
  const byId = Object.fromEntries(g.tasks.map((t) => [t.id, t]))
  for (const t of g.tasks) {
    for (const b of t.blockers) if (!byId[b]) out.push(`task ${t.id}: blocker ${b} is not a task`)
    out.push(...tierMeaning(`task ${t.id}`, t))
    if (t.one_way && t.tier === 'bounded') out.push(`task ${t.id}: one_way, but tier bounded; a one-way door needs judgment or lead`)
    for (const n of t.needs || []) if (!CAPABILITIES.includes(n)) out.push(`task ${t.id}: needs ${n}, which is not in x-capabilities`)
    if (t.split && t.split.length < LIMITS.split_parts_min) out.push(`task ${t.id}: split has fewer than ${LIMITS.split_parts_min} parts`)
    for (const d of new Set(dupes(t.split || []))) out.push(`task ${t.id}: split part ${d} is not unique`)
  }
  // reach[id]: every task id that must finish before id starts.
  const reach = {}
  const visit = (id, trail) => {
    if (reach[id]) return reach[id]
    if (trail.includes(id)) {
      out.push(`tasks: blocker cycle ${[...trail, id].join(' -> ')}`)
      return new Set()
    }
    const r = new Set()
    for (const b of byId[id].blockers) {
      if (!byId[b]) continue
      r.add(b)
      for (const x of visit(b, [...trail, id])) r.add(x)
    }
    return (reach[id] = r)
  }
  ids.forEach((id) => visit(id, []))
  for (let i = 0; i < g.tasks.length; i++) {
    for (let j = i + 1; j < g.tasks.length; j++) {
      const a = g.tasks[i]
      const b = g.tasks[j]
      if (reach[a.id].has(b.id) || reach[b.id].has(a.id)) continue
      const both = overlap(a.files, b.files)
      if (both.length > 0) out.push(`tasks ${a.id} and ${b.id} run in parallel and both edit ${both.join(', ')}`)
    }
  }
  return out
}

// tierMeaning: a bounded task has an inventoried oracle that covers all, and does not edit it.
function tierMeaning(at, t) {
  if (t.tier !== 'bounded') return []
  const out = []
  if (t.oracle.uncovered.length > 0) out.push(`${at}: tier bounded, but the oracle does not cover ${t.oracle.uncovered.join('; ')}`)
  if (t.oracle.files.length === 0) out.push(`${at}: tier bounded needs the oracle files inventoried`)
  const own = overlap(t.files, t.oracle.files)
  if (own.length > 0) out.push(`${at}: a bounded worker may not edit its own oracle ${own.join(', ')}`)
  return out
}

// specMeaning: a spec is red before the build, its tests are not files the worker edits, its stubs are.
// t is the task; the CLI passes none and gets the red check only.
function specMeaning(s, t) {
  const out = []
  if (!s.red.failed) out.push('the spec command did not fail before the build; a green spec proves nothing')
  if (t) {
    const own = overlap(s.tests, t.files)
    if (own.length > 0) out.push(`spec tests are inside the task files (${own.join(', ')}); the worker may not edit its own oracle`)
    const loose = s.stubs.filter((x) => overlap([x], t.files).length === 0)
    if (loose.length > 0) out.push(`stubs outside the task files: ${loose.join(', ')}`)
  }
  return out
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
// tests/workflows.js checks every transition and metrics row this workflow writes against the contract.
const REVIEW_BATCH = LIMITS.review_batch
const BLAST_MAX = LIMITS.blast_radius_max
const REWORK_MIN_TIER = 'judgment'
const SEVERITIES = ['minor', 'major', 'critical']
const SKEPTICS_PER_FINDING = 2
const REVIEW_TRIES = 2
const UNAVAILABLE = 'unavailable'
const SECONDS_PER_DAY = 86400
const ISO_UTC = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z$/

// isoSeconds: seconds since 1970 of an ISO UTC string, or null. Plain arithmetic: the runtime forbids Date.
function isoSeconds(iso) {
  const m = typeof iso === 'string' && ISO_UTC.exec(iso)
  if (!m) return null
  const [y, mo, d, h, mi, sec] = m.slice(1).map(Number)
  const yy = mo <= 2 ? y - 1 : y
  const era = Math.floor(yy / 400)
  const yoe = yy - era * 400
  const doy = Math.floor((153 * (mo + (mo > 2 ? -3 : 9)) + 2) / 5) + d - 1
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy
  return (era * 146097 + doe - 719468) * SECONDS_PER_DAY + h * 3600 + mi * 60 + sec
}

// Contract shapes: copies of $defs brief, split, report, merge, review, verdict and blast in
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
  description: 'The output of a brief-writer for 1 task. Its tier is a recommendation: the task runs at the higher of the planned tier and this tier.',
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

const blastSchema = {
  type: 'object',
  description: 'The output of a blast-radius check: the 1 fact a change is safe because of, and how far it was proven. level: 1 said so, 2 pointed at a file:line, 3 walked the failure step by step, 4 ran code that calls the real function, 5 reproduced in the running app.',
  required: ['target', 'fact', 'level', 'proven', 'proof', 'risks', 'cleared'],
  properties: {
    target: { type: 'string', description: 'The task id or finding id checked' },
    fact: { type: 'string', minLength: 1 },
    level: { type: 'integer', minimum: 1, maximum: 5 },
    proven: { type: 'boolean' },
    proof: { type: 'string', description: 'The command and its last output lines. Empty below level 4.' },
    risks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'evidence'],
        properties: {
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'file:line, or the command and its output' },
        },
      },
    },
    cleared: { type: 'array', items: { type: 'string' }, description: 'What was checked and is fine, 1 line each' },
  },
}

// ---- Setup
const graph = args.graph
if (!graph || !graph.repo || !graph.branch || !graph.base || !graph.base.sha || !(graph.tasks || []).length) {
  throw new Error('wave needs args.graph: a contract graph with repo, branch, base.sha and at least 1 task')
}
if (isoSeconds(args.started_at) === null) {
  throw new Error('wave needs args.started_at: the ISO UTC time now (date -u +%Y-%m-%dT%H:%M:%SZ). The workflow cannot read the clock.')
}
if (args.regression !== undefined && (typeof args.regression !== 'string' || args.regression.trim() === '')) {
  throw new Error('args.regression must be a command string: the one load-bearing scenario, run on the base SHA and on the wave head')
}
const claimedAt = args.claimed_at || {}
const badClaimTimes = Object.entries(claimedAt).filter(([, t]) => isoSeconds(t) === null).map(([id]) => id)
if (badClaimTimes.length > 0) throw new Error(`args.claimed_at needs an ISO UTC time for: ${badClaimTimes.join(', ')}`)
// newest: the latest time any agent reported. A transition takes it.
let newest = args.started_at
function know(at) {
  const t = isoSeconds(at)
  if (t !== null && t > isoSeconds(newest)) newest = at
}

const runtime = args.runtime || CLAUDE_RUNTIME
const claims = args.claims || {}
const root = runtime.worktree_root
const wave = graph.branch
const limit = graph.rework_limit
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const gate = args.gate ? ` Then run the gate: ${args.gate}.` : ''
const issueOf = (t) => (t.issue ? `issue #${t.issue} of ${graph.repo}` : `task ${t.id} of ${graph.repo}`)
const merged = (m) => Boolean(m && m.oracle_passed && !m.escalation)
const FULL_SHA = new RegExp(reportSchema.properties.sha.pattern)
// verify: why the lead refuses a worker report for task (or part) id on branch, or '' when it accepts it.
function verify(r, id, branch) {
  if (!r) return 'the worker returned nothing'
  if (r.status !== 'done') return `the worker escalated: ${r.escalation || 'no question given'}`
  if (r.task !== id) return `the report names task ${r.task}, not ${id}`
  if (r.branch !== branch) return `the report names branch ${r.branch}, not ${branch}`
  if (!FULL_SHA.test(r.sha)) return `the report SHA ${r.sha} is not a full SHA`
  if (!r.test.passed) return `the focused test is red: ${r.test.line}`
  return ''
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
      integratedAt: null, order: 0, blasted: false, building: deferred(), integrated: deferred(),
    },
  ]),
)
// A blocker that is no task, or a blocker cycle, would wait forever: refuse a graph that fails a check.
const graphProblems = graphMeaning(graph)
if (graphProblems.length > 0) throw new Error(`the graph fails the contract checks: ${graphProblems.join('; ')}`)

const transitions = []
function move(id, to, extra = {}) {
  const s = tasks[id]
  if (!TRANSITIONS[s.state].includes(to)) throw new Error(`task ${id}: ${s.state} -> ${to} is not an allowed transition`)
  transitions.push({ task: id, from: s.state, to, at: newest, ...extra })
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
  // The contract tier rule: the brief may raise the planned tier, never lower it.
  return { brief: b.brief, files: b.files, oracle: b.oracle, tier: higherTier(t.tier, b.tier) }
}

// ---- Build
// start: the line that makes the worktree. With specSha (the task's spec_sha), it starts on that spec
// commit, then merges origin/<from>, so the worker gets the spec tests and the blockers' code. There is
// no fallback: a missing spec commit fails the line.
const start = (branch, from, specSha) =>
  specSha
    ? `git fetch -q origin && git worktree add -b ${branch} ${root}/${branch} ${specSha} && git -C ${root}/${branch} merge -q --no-edit origin/${from}`
    : `git fetch -q origin && git worktree add -b ${branch} ${root}/${branch} origin/${from}`
// startLog: 1 log line that says where a task branch starts.
const startLog = (id, t) => log(`${id}: starts from ${t.spec_sha ? `spec ${t.spec_sha}` : `${wave}, no spec`}`)
function workerPrompt({ id, what, text, branch, from, spec, files, test, oracleFiles, round }) {
  return `${what}
${text}
Work in your own worktree ${root}/${branch}. Make it first with this exact line:
${start(branch, from, spec)}
Edit only: ${files.join(', ')}.${oracleFiles.length > 0 ? ` Do not edit the oracle files: ${oracleFiles.join(', ')}.` : ''}
Run only the focused test: ${test}. Commit small and push after every commit: git push -q -u origin ${branch}. Open no pull request. Merge nothing.
If the brief is unclear or the test cannot pass without an edit outside your files, push what you have and set status to escalated. Do not guess.
Report task ${id}, round ${round}, branch ${branch}, the full 40-character SHA of your last push, and the test command with its last output line. When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`
}

function build(id, plan) {
  const s = tasks[id]
  startLog(id, s.task)
  return call(
    id,
    workerPrompt({ id, what: `Build ${issueOf(s.task)}.`, text: plan.brief, branch: s.branch, from: wave, spec: s.task.spec_sha, files: plan.files, test: plan.oracle.command, oracleFiles: plan.oracle.files, round: 0 }),
    { label: `build ${id}`, phase: 'Build', schema: reportSchema, ...spawn('worker', plan.tier) },
  )
}

// buildSplit: the split workflow as a plain function (a wave may not nest a workflow). It returns a
// report of the task branch, or null with s.reason set.
async function buildSplit(id, plan) {
  const s = tasks[id]
  startLog(id, s.task)
  const sp = await call(
    id,
    `Split ${issueOf(s.task)} into these parts: ${s.task.split.join(', ')}. Brief:
${plan.brief}
1. Cut branch ${s.branch}: ${start(s.branch, wave, s.task.spec_sha)}
2. The oracle of the whole task is: ${plan.oracle.command}. Add a focused filter of it for each part.
3. Write stubs for the seams between parts, so each part builds alone. Commit the stubs and push ${s.branch}.
4. Write 1 brief per part: its files (2 parts never edit the same file, and only files in ${plan.files.join(', ')}), its focused test, the oracle cases it must pass, what it must not touch.
5. Tier each part: bounded when the oracle covers it, judgment when it does not, lead when the step-up rule in AGENTS-AND-MODELS.md applies.
If the task does not split cleanly, set escalation and write no briefs.${rules}`,
    { label: `split ${id}`, phase: 'Build', schema: splitSchema, ...spawn('sub_lead', ROLE_TIER.sub_lead) },
  )
  if (!sp || sp.escalation || sp.briefs.length < LIMITS.split_parts_min) {
    s.reason = sp ? sp.escalation || `the split has fewer than ${LIMITS.split_parts_min} parts` : 'the sub-lead returned nothing'
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
  const refused = sp.briefs.map((b, i) => verify(parts[i], b.part, `${s.branch}-${b.part}`)).map((why, i) => why && `${sp.briefs[i].part}: ${why}`).filter(Boolean)
  if (refused.length > 0) {
    s.reason = `${refused.length} of ${parts.length} parts refused: ${refused.join('; ')}`
    return null
  }
  const m = await call(
    id,
    `Merge these part branches into ${s.branch}: ${parts.map((r) => `${r.branch} at ${r.sha}`).join(', ')}. Work in ${root}/${s.branch}.
Run the oracle: ${plan.oracle.command}. Fix what fails, and list each part you fixed in reworked.
Push ${s.branch}. Open no pull request. Report the full 40-character SHA of the push.
If the oracle cannot pass, set escalation and push what you have.
When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`,
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
Keep the worktree for the next merge. Open no pull request. Never touch main.
When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`
  const run = async () => {
    const before = waveHead
    let m = await call(id, prompt(false), { label: `merge ${id}`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', FIRST_TRY.integrator) })
    if (!merged(m)) {
      m = await call(id, prompt(true), { label: `merge ${id} step-up`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) })
    }
    s.merges.push(m)
    if (!merged(m)) return { ok: false, reason: m ? m.escalation || 'the merge is red' : 'the integrator returned nothing' }
    waveHead = m.sha
    s.order = ++mergeCount
    know(m.at)
    s.integratedAt = isoSeconds(m.at) === null ? newest : m.at
    return { ok: true, diff: `${before}...${report.sha}` }
  }
  const p = mergeChain.then(run)
  mergeChain = p.catch(() => null)
  return p
}

// regress: run the regression command once on a commit. Returns { sha, passed, line } or null when the agent returned nothing.
async function regress(side, sha, command) {
  const v = await call([], `Run 1 scenario of ${graph.repo} on commit ${sha}. Read only: edit nothing, commit nothing, push nothing, open no pull request.
1. git fetch -q origin && git worktree add --detach ${root}/regression-${side} ${sha}
2. In that worktree, run exactly: ${command}
3. Set agree to true when the command exits 0, and to false when it does not. Set reason to its last output line.
4. Remove the worktree: git worktree remove --force ${root}/regression-${side}${rules}`,
    { label: `regression ${side}`, phase: 'Report', schema: verdictSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  return v ? { sha, passed: v.agree, line: v.reason } : null
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

// ---- Blast radius: 1 check per risky task (once per wave) and per finding above minor, at most
// BLAST_MAX per wave. takeBlast counts before any await, so parallel reviews cannot pass the cap.
// A proof is input to the reviewer and the skeptics; it replaces neither.
let blastUsed = 0
function takeBlast() {
  if (blastUsed >= BLAST_MAX) return false
  blastUsed++
  return true
}
const renderBlast = (b) => `- ${b.target}: fact: ${b.fact}; level ${b.level}; ${b.proven ? 'proven' : 'unproven'}; risks: ${b.risks.map((r) => r.claim).join('; ') || 'none'}`
// blast: 1 check of target. It returns the proof with the real target id, or null when the call fails.
async function blast(owners, target, what, evidence) {
  const b = await call(
    owners,
    `Blast-radius check for ${what} of ${graph.repo}. Read only: edit, commit and push nothing in the repo. Run git fetch -q origin first. Write any proof script in a scratch directory outside the repo (mktemp -d) and delete it after.
Find the 1 fact the change is safe because of. Do not list callers: grep does that. Look where grep stops: the library source, timing, saved or wire formats, another reader of the same bytes.
Prove that fact by running code that calls the real function. Fail loud if you are wrong. Set level: 1 said so, 2 file:line, 3 walked the failure, 4 ran code, 5 reproduced in the running app. Set proven true only at level 4 or 5 with the command and its output in proof.
${evidence}${rules}`,
    { label: `blast ${target}`, phase: 'Review', schema: blastSchema, ...spawn('blast_radius', ROLE_TIER.blast_radius) },
  )
  return b ? { ...b, target } : null
}

async function review(batch) {
  const batchIds = batch.map((e) => e.id)
  // A risky task gets 1 check per wave, not 1 more on each rework round.
  const riskyIds = batchIds.filter((id) => tasks[id].task.risky && !tasks[id].blasted && takeBlast())
  for (const id of riskyIds) tasks[id].blasted = true
  const byId = Object.fromEntries(batch.map((e) => [e.id, e]))
  const taskProofs = (await parallel(riskyIds.map((id) => () => blast(id, id, `task ${id}`, `diff ${byId[id].diff}; test: ${byId[id].test}`)))).filter(Boolean)
  const proofText = taskProofs.length > 0 ? `\nBlast-radius proofs (input to weigh, not a verdict; run your own checks and keep every finding you would have made):\n${taskProofs.map(renderBlast).join('\n')}` : ''
  let rv = null
  for (let i = 0; i < REVIEW_TRIES && !rv; i++) {
    rv = await call(
      batchIds,
      `Review these ${batch.length} results of ${graph.repo} as 1 batch. They are merged on the wave branch ${wave}. You do not know who wrote them. Judge only the diffs and the tests. Read only: edit, commit and push nothing. Run git fetch -q origin first.
Results:
${batch.map((e) => `- ${e.id}: diff ${e.diff}; test: ${e.test}`).join('\n')}${proofText}
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
  // Blast the worst findings first; the cap is taken before any await.
  const picked = [...heavy].sort((a, b) => SEVERITIES.indexOf(b.severity) - SEVERITIES.indexOf(a.severity)).filter(() => takeBlast())
  const blastSkipped = heavy.filter((f) => !picked.includes(f)).map((f) => f.id)
  if (blastSkipped.length > 0) log(`blast cap ${BLAST_MAX} reached: no blast-radius check for ${blastSkipped.join(', ')}`)
  const findingProofs = await parallel(
    picked.map((f) => () => blast(inBatch(f), f.id, `finding ${f.id} (${f.severity}) on ${f.ids.join(', ')}`, `Claim: ${f.claim}\nEvidence: ${f.evidence}`)),
  )
  const proofOf = Object.fromEntries(findingProofs.filter(Boolean).map((b) => [b.target, b]))
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
${batch.filter((e) => f.ids.includes(e.id)).map((e) => `- ${e.id}: diff ${e.diff}; test: ${e.test}`).join('\n')}${proofOf[f.id] ? `\nBlast-radius proof (weigh it; reproduce the problem yourself before you agree):\n${renderBlast(proofOf[f.id])}` : ''}${rules}`,
            { label: `skeptic ${f.id} ${i + 1}`, phase: 'Review', schema: verdictSchema, ...spawn('skeptic', ROLE_TIER.skeptic) },
          ),
        ),
      )
      return { ...f, stands: verdicts.every((v) => v && v.agree) }
    }),
  )
  const standing = [...named.filter((f) => f.severity === 'minor'), ...checked.filter((f) => f.stands)]
  reviews.push({ ids: batchIds, scores: rv.scores, pairs: rv.pairs || [], findings: standing, dropped: checked.filter((f) => !f.stands).map((f) => f.id), blast: [...taskProofs, ...Object.values(proofOf)], blast_skipped: blastSkipped })
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
    { label: `rework ${id} ${s.rounds}`, phase: 'Rework', schema: reportSchema, ...spawn('worker', higherTier(s.tier, REWORK_MIN_TIER)) },
  )
  const refused = verify(r, id, `${s.branch}-r${s.rounds}`)
  if (refused) return stop(id, 'escalated', `rework round ${s.rounds}: ${refused}`)
  know(r.at)
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
  const lacks = (t.needs || []).filter((n) => !hasCapability(runtime, n))
  if (lacks.length > 0) return stop(id, 'escalated', `needs ${lacks.join(', ')}; runtime ${runtime.provider} lacks it, so a peer that has it takes the task`)
  if (!claims[id]) return stop(id, null, 'no claim: the lead posts 1 claim comment per task and passes its URL in args.claims')
  const building = await Promise.all(t.blockers.map((b) => tasks[b].building.promise))
  if (!building.every(Boolean)) return stop(id, null, `blocker ${t.blockers.filter((b, i) => !building[i]).join(', ')} did not start`)
  const plan = await brief(id)
  if (!plan) return stop(id, 'escalated', 'the brief-writer returned nothing')
  const badBrief = tierMeaning(`brief ${id}`, plan)
  if (badBrief.length > 0) return stop(id, 'escalated', badBrief.join('; '))
  // A brief's files and oracle replace the plan's: run the graph check again on the updated graph.
  const widened = graphMeaning({ ...graph, tasks: graph.tasks.map((x) => (x.id === id ? { ...x, ...plan } : tasks[x.id].plan ? { ...x, ...tasks[x.id].plan } : x)) })
  if (widened.length > 0) return stop(id, 'escalated', widened.join('; '))
  s.plan = plan
  s.tier = plan.tier
  move(id, 'briefed')
  const integrated = await Promise.all(t.blockers.map((b) => tasks[b].integrated.promise))
  if (!integrated.every(Boolean)) return stop(id, null, `blocker ${t.blockers.filter((b, i) => !integrated[i]).join(', ')} was not integrated`)
  move(id, 'claimed', { reason: claims[id] })
  move(id, 'building')
  s.building.resolve(true)
  const r = t.split ? await buildSplit(id, plan) : await build(id, plan)
  const refused = t.split && !r ? s.reason : verify(r, id, s.branch)
  if (refused) return stop(id, 'escalated', refused)
  know(r.at)
  if (r.notes) s.notes.push(r.notes)
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
// Regression lane: base first, then head, 2 agents at most. red on both and fixed are records, not escalations.
let regression
if (args.regression) {
  if (mergeCount === 0) {
    regression = { command: args.regression, skipped: 'nothing merged on the wave branch, so the head is the base' }
  } else {
    const base = await regress('base', graph.base.sha, args.regression)
    const head = await regress('head', waveHead, args.regression)
    const verdict = !base || !head ? 'unknown' : base.passed && !head.passed ? 'regressed' : base.passed ? 'ok' : head.passed ? 'fixed' : 'red on both'
    regression = { command: args.regression, base, head, verdict }
  }
}
const regressionEscalation = !regression || !['regressed', 'unknown'].includes(regression.verdict) ? [] : [{
  task: 'regression', state: 'escalated',
  reason: regression.verdict === 'regressed'
    ? `the scenario "${regression.command}" passes on base ${regression.base.sha} and fails on head ${regression.head.sha}: ${regression.head.line}`
    : `the scenario "${regression.command}" has no result for ${[!regression.base && 'the base', !regression.head && 'the head'].filter(Boolean).join(' and ')}`,
}]
const result = (s) => (s.state === 'done' ? 'merged' : s.state === 'escalated' ? 'escalated' : 'failed')
const metrics = ids
  .filter((id) => tasks[id].agents > 0)
  .map((id) => {
    const s = tasks[id]
    const sp = runtime.tiers[s.tier]
    return {
      task: id, provider: runtime.provider, tier: s.tier, model: sp.model, ...(sp.effort && { effort: sp.effort }),
      agents: s.agents, elapsed_s: Math.max(0, isoSeconds(s.integratedAt || newest) - isoSeconds(claimedAt[id] || args.started_at)),
      rework_rounds: s.rounds, findings: s.findings, result: result(s), tokens: UNAVAILABLE, cost_usd: UNAVAILABLE,
    }
  })
const open = ids.filter((id) => tasks[id].state !== 'done')
log(`${ids.length - open.length} of ${ids.length} tasks done on ${wave} at ${waveHead}; ${open.length} need the lead${regression ? `; regression: ${regression.verdict || 'skipped'}` : ''}`)

return {
  branch: wave,
  sha: waveHead,
  done: ids.filter((id) => tasks[id].state === 'done'),
  ...(regression && { regression }),
  escalations: [...open.map((id) => ({ task: id, state: tasks[id].state, reason: tasks[id].reason })), ...regressionEscalation],
  tasks: ids.map((id) => {
    const s = tasks[id]
    return { task: id, issue: s.task.issue, state: s.state, tier: s.tier, branch: s.branch, rounds: s.rounds, notes: s.notes, reports: s.reports, merges: s.merges }
  }),
  reviews,
  metrics,
  transitions,
}
