export const meta = {
  name: 'plan',
  description: 'Plan a wave. An architect drafts the task graph, brief-writers expand every task in parallel, spec agents write failing tests for each task with uncovered behaviours, a critic lists what is missing. Returns a contract graph, one brief and one issue draft per task, the specs, and the wave args. It files nothing.',
  phases: ['Graph', 'Briefs', 'Spec', 'Critic'],
}

// args: { goal, repo, branch, base, parent, rules, sources, runtime }
//   goal     the parent issue (number or URL) or the text of the goal; the architect reads it
//   repo     owner/name
//   branch   the wave branch that integration pushes to
//   base     { ref, sha }: the frozen base. sha is the full 40-character SHA.
//   parent   optional; the parent issue number. Default: goal, when goal is a number.
//   rules    optional; the repo's code rules as text, passed to every agent
//   sources  optional; the order of authority when 2 sources give different numbers
//            (default: the oracle output, then the code, then the issue text, then the docs)
//   runtime  optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
// The workflow files no issue and opens no pull request. The result is
// { status, graph, briefs, specs, issues, wave, problems, missing }. status is done, gaps (the critic
// listed missing work) or escalated (the graph or a spec fails a check after the redrafts).
// The Spec phase runs for each task whose oracle has uncovered behaviours. A spec agent pushes stubs,
// failing tests and a usage sketch to its own branch spec/<task id>, cut fresh from base.sha. The task
// records the spec commit as spec_sha and its worker starts from that SHA, so the wave branch stays at
// base.sha and gets the spec only when the task merges. The spec tests are oracle files; the stubs are
// task files the worker fills in. A spec test not marked keep is scaffold: an oracle for the build
// only, listed in the task's scaffold, which wave deletes in the task's merge step. Each entry of specs is the spec with tier_before and tier_after. The lead deletes the merged
// spec/* branches with the task branches. A one_way task gets 2 designs and 1 judge first.
// The lead files 1 issue per draft in issues, writes each issue number into wave.graph, posts 1
// claim comment per task and puts its URL in wave.claims. Then it runs the wave workflow on wave.

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
// Each keep test is a spec test; every other spec test is scaffold, and only a file the spec created
// may be scaffold: a spec that amends a test marks it keep. check.js sees no git, so created is the
// spec's own report; wave deletes only the scaffold that git shows as added since the base.
// t is the task; the CLI passes none and gets the red check only.
function specMeaning(s, t) {
  const out = []
  if (!s.red.failed) out.push('the spec command did not fail before the build; a green spec proves nothing')
  const stray = s.keep.filter((x) => !s.tests.includes(x))
  if (stray.length > 0) out.push(`keep names files that are not spec tests: ${stray.join(', ')}`)
  const amended = s.tests.filter((x) => !s.keep.includes(x) && !s.created.includes(x))
  if (amended.length > 0) out.push(`spec tests the spec did not create are not keep: ${amended.join(', ')}; a spec that amends a test marks it keep`)
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
const DEFAULT_SOURCES = 'the oracle output, then the code, then the issue text, then the docs'

// Contract shapes: copies of $defs graph, brief and critique in plugin/contract/sdlc.schema.json,
// with $ref inlined. A workflow cannot import a file. tests/workflows.js fails when a copy drifts.
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

const taskSchema = {
  type: 'object',
  description: '1 task: 1 outcome, 1 branch, 1 worker. Tasks with no blocker path between them run in parallel, so their files must not overlap.',
  required: ['id', 'tier', 'blockers', 'files', 'oracle'],
  properties: {
    id: { type: 'string', minLength: 1, description: 'Unique in the graph. The issue number as text when the task is 1 issue.' },
    issue: { type: 'integer' },
    title: { type: 'string', description: 'The issue title' },
    outcome: { type: 'string', description: '1 sentence: what is true when the task is done' },
    done_when: { type: 'array', items: { type: 'string' }, description: 'The checks that prove the outcome, 1 line each' },
    area: { type: 'string', description: 'The area: label of the issue, without the area: prefix' },
    tier: { type: 'string', enum: ['bounded', 'judgment', 'lead'], description: 'The planned tier. The task runs at the higher of this tier and the tier of its brief.' },
    blockers: { type: 'array', items: { type: 'string' }, description: 'Task ids that must be integrated before this task starts' },
    files: { type: 'array', minItems: 1, items: { type: 'string' }, description: 'The only files the worker may edit' },
    oracle: oracleSchema,
    brief: { type: 'string' },
    branch: { type: 'string' },
    split: { type: 'array', items: { type: 'string' }, description: 'Part names, x-limits.split_parts_min or more. A sub-lead writes the oracle and 1 brief per part, workers build the parts, an integrator merges them into the task branch.' },
    needs: { type: 'array', items: { type: 'string' }, description: 'Capabilities from x-capabilities that the task needs. Empty or absent: any agent may take it. An agent takes the task only when its runtime has every one (status enforced or instructed).' },
    one_way: { type: 'boolean', description: 'True when the task fixes a contract, a save format or a public API that callers depend on and that is costly to reverse. plan runs design-twice for it (2 designs, 1 adversarial judge) and never lowers its tier.' },
    risky: { type: 'boolean', description: 'True when the plan marks the change risky: a shared file many tasks read, a save or wire format, a public API, a deletion, or behaviour no oracle covers. Absent means false. A risky task gets 1 blast-radius check.' },
    spec_sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: "The full SHA of the spec commit on spec/<task id>. plan sets it only for a task it spec'd. wave starts the task branch from this SHA, never from a branch name." },
    scaffold: { type: 'array', items: { type: 'string' }, description: "The spec tests not marked keep: an oracle for the build only. plan sets it only for a task it spec'd. The integrator deletes those added since the base in the task's merge step, when its checks pass without them." },
  },
}

const graphSchema = {
  type: 'object',
  description: 'A wave: the tasks of 1 parent, their blockers and the base they build on. The plan workflow writes it; the wave workflow reads it.',
  required: ['repo', 'branch', 'base', 'rework_limit', 'tasks'],
  properties: {
    repo: { type: 'string', minLength: 1, description: 'owner/name' },
    parent: { type: 'integer', description: 'The parent issue number' },
    branch: { type: 'string', minLength: 1, description: 'The wave branch that integration pushes to' },
    base: {
      type: 'object',
      required: ['ref', 'sha'],
      properties: {
        ref: { type: 'string', minLength: 1 },
        sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: 'The frozen base. Every task branch starts here or on the wave branch.' },
      },
    },
    rework_limit: { type: 'integer', minimum: 0, description: 'At most x-limits.rework_rounds' },
    tasks: { type: 'array', minItems: 1, items: taskSchema },
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

const critiqueSchema = {
  type: 'object',
  description: 'The output of a completeness critic on a plan: what the tasks and briefs leave out',
  required: ['complete', 'missing'],
  properties: {
    complete: { type: 'boolean', description: 'True only when the tasks and briefs cover the whole goal' },
    missing: { type: 'array', items: { type: 'string' }, description: 'Each gap, 1 line: the behaviour, file, test or decision that no task covers. Empty when complete.' },
  },
}

const specSchema = {
  type: 'object',
  description: 'The output of a spec agent for 1 task: the spec as code, committed and pushed to its own branch spec/<task id>, cut from the graph base, before the build. The worker cuts its task branch from it. The spec agent owns tests; the worker never edits them.',
  required: ['task', 'kind', 'tests', 'keep', 'created', 'stubs', 'sketch', 'command', 'red', 'uncovered', 'sha'],
  properties: {
    task: { type: 'string' },
    kind: { type: 'string', enum: ['test', 'scene', 'golden'], description: 'test: a unit or integration test. scene: a scripted scene run whose exit code or log is checked (for example a Godot 4 headless run with scripted input). golden: a golden output the command compares.' },
    tests: { type: 'array', minItems: 1, items: { type: 'string' }, description: 'Paths of the failing tests, scene scripts or golden files. They become oracle files.' },
    keep: { type: 'array', items: { type: 'string' }, description: 'The tests that meet the keep rule (AGENTS-AND-MODELS.md, Tests), and every test the spec amended. Each is in tests. Every other test is scaffold: an oracle for the build only, deleted by the wave.' },
    created: { type: 'array', items: { type: 'string' }, description: 'The spec tests this spec created: not in the tree at the graph base. A test not in created was there before and is keep.' },
    stubs: { type: 'array', items: { type: 'string' }, description: 'Paths of the stub files the worker fills in. Each is inside the task files.' },
    sketch: { type: 'string', minLength: 1, description: 'The caller usage sketch: 5 to 15 lines of how a caller uses the signatures' },
    command: { type: 'string', minLength: 1, description: 'The focused command. It runs the old oracle and the new spec tests.' },
    red: {
      type: 'object',
      required: ['line', 'failed'],
      properties: {
        line: { type: 'string', description: 'The last output line of the command before the build' },
        failed: { type: 'boolean', description: 'True: the command failed before the build, for the intended reason' },
      },
    },
    uncovered: { type: 'array', items: { type: 'string' }, description: 'Behaviours the old oracle and the spec still do not pin. Empty: the task may become bounded.' },
    sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: 'The full SHA of the pushed spec commit' },
    notes: { type: 'string', description: '3 lines or fewer. Say what you did not verify.' },
  },
}

const designSchema = {
  type: 'object',
  description: '1 design of a one-way task: signatures and a usage sketch, no files written',
  required: ['task', 'approach', 'signatures', 'sketch'],
  properties: {
    task: { type: 'string' },
    approach: { type: 'string', minLength: 1, description: 'The idea in 2 sentences' },
    signatures: { type: 'string', minLength: 1, description: 'Every public signature, as code' },
    sketch: { type: 'string', minLength: 1 },
    risks: { type: 'array', items: { type: 'string' } },
  },
}

const pickSchema = {
  type: 'object',
  description: 'The verdict of an adversarial judge on 2 designs',
  required: ['pick', 'flaws_a', 'flaws_b', 'reason'],
  properties: {
    pick: { type: 'string', enum: ['a', 'b'] },
    flaws_a: { type: 'array', items: { type: 'string' }, description: 'How a caller misuses design a, or a later change breaks it' },
    flaws_b: { type: 'array', items: { type: 'string' } },
    reason: { type: 'string', minLength: 1 },
  },
}
const DESIGNS = ['a', 'b'] // the cap: x-limits is not used; 2 designs per one-way door
// The lens of each designer, so the 2 designs differ.
const LENS = { a: 'the smallest public surface', b: 'the surface that is hardest for a caller to misuse' }

if (!args.goal || !args.repo || !args.branch || !args.base || !args.base.ref || !new RegExp(graphSchema.properties.base.properties.sha.pattern).test(args.base.sha || '')) {
  throw new Error('plan needs args goal, repo, branch and base { ref, sha } with a 40-character sha')
}
const runtime = args.runtime || CLAUDE_RUNTIME
const spawn = (role, tier) => {
  const t = runtime.tiers[tier]
  return { model: t.model, ...(t.effort && { effort: t.effort }), agentType: runtime.agent_types[role] }
}
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const sources = args.sources || DEFAULT_SOURCES
const parent = args.parent || (Number.isInteger(args.goal) ? args.goal : undefined)
const NEED_LABELS = contract['x-need-labels']

// The wave facts come from args, never from the architect: it cannot know the frozen base.
const pin = (g) => ({ ...g, repo: args.repo, ...(parent && { parent }), branch: args.branch, base: args.base, rework_limit: LIMITS.rework_rounds })
// problemsOf: the contract checks of the graph, and the fields each issue draft needs.
const problemsOf = (g) => [
  ...graphMeaning(g),
  ...g.tasks.flatMap((t) => [
    ...['title', 'outcome', 'area'].filter((k) => !t[k]).map((k) => `task ${t.id}: ${k} is empty; the issue draft needs it`),
    ...((t.done_when || []).length === 0 ? [`task ${t.id}: done_when is empty; the issue draft needs it`] : []),
    ...(t.needs || []).filter((n) => !NEED_LABELS[n]).map((n) => `task ${t.id}: needs ${n}, which has no label in x-need-labels`),
  ]),
]
const escalate = (graph, briefs, problems, specs = []) => ({ status: 'escalated', graph, briefs, specs, issues: [], wave: null, problems, missing: [] })
// neighbours: every task of the graph with its files and blockers, so an agent sees what runs beside it.
const neighbours = (g) => g.tasks.map((o) => `- ${o.id}: edits ${o.files.join(', ')}; blocked by ${o.blockers.join(', ') || 'none'}`).join('\n')

phase('Graph')
let graph
let problems = []
for (let round = 0; round <= LIMITS.rework_rounds; round++) {
  const redo = problems.length > 0 ? `\nYour last draft failed these checks. Fix each one and return the whole graph again:\n- ${problems.join('\n- ')}\n` : ''
  graph = pin(await agent(
    `Plan the wave for this goal: ${args.goal}
Repo ${args.repo}. Wave branch ${args.branch}, cut from ${args.base.ref} at ${args.base.sha}.
Read the goal, CLAUDE.md and the code it touches. Then draft the task graph:
1. One outcome per task. A task a worker finishes in 15-30 minutes, on 1 branch. Give each task its issue text: a title, the outcome in 1 sentence, done_when (the checks that prove it, 1 line each) and its area (the area: label without the prefix).
2. Set blockers so the steps follow dependency depth: a task lists only the tasks whose output it needs. Tasks with no blocker path between them run in parallel.
3. List the files each task edits. The list is intent, not a fence: a worker may edit any file no parallel task lists (rule: "File lists" in AGENTS-AND-MODELS.md). Two tasks that run in parallel share no file and no directory. When 2 tasks need the same file, make one block the other.
4. Give each task an oracle: the focused test command, the inventory of every test or golden file that covers it (read them), and the behaviours no file covers in uncovered. A test file the task writes or updates goes in its files too: the worker may edit an oracle file in its list, never one outside it. A task whose oracle files you have not read is not bounded.
5. Set the tier from the oracle: bounded only when uncovered is empty and the oracle files are not in the task's files. Judgment when a behaviour has no oracle. Lead when the step-up rule in AGENTS-AND-MODELS.md applies. A brief-writer may raise the tier later, never lower it.
6. Set split to ${LIMITS.split_parts_min} or more unique part names when 1 oracle proves the task but it is too large for 1 worker. The parts edit different files.
7. Set needs only when a task requires a capability that not every agent has. Allowed names: ${CAPABILITIES.join(', ')}. Today only ${Object.keys(NEED_LABELS).join(', ')} differs between agents. Name no provider or model: any agent may take a task that lists no needs.
8. Set one_way true only for a task that fixes a contract, a save format or a public API. Most tasks are not one_way.
9. Set risky true only for a task whose change could break something far from its files: a shared file, a save or wire format, a public API, a deletion, or behaviour no oracle covers. Most tasks are not risky. A risky task gets 1 blast-radius check after it is integrated; the wave runs at most ${LIMITS.blast_radius_max} checks in all.
Return the graph. Any agent may build any task; do not route by provider.${rules}${redo}`,
    { label: round === 0 ? 'architect' : `architect-${round}`, phase: 'Graph', schema: graphSchema, ...spawn('lead', ROLE_TIER.lead) },
  ))
  problems = problemsOf(graph)
  if (problems.length === 0) break
  log(`graph round ${round}: ${problems.length} problem(s)`)
}
if (problems.length > 0) return escalate(graph, [], problems)

phase('Briefs')
const briefs = await parallel(
  graph.tasks.map((t) => () =>
    agent(
      `Write the brief for task ${t.id} of the wave on ${args.repo}, goal: ${args.goal}
The task: ${t.outcome} Files ${t.files.join(', ')}; blockers ${t.blockers.join(', ') || 'none'}; oracle ${t.oracle.command}; planned tier ${t.tier}.
The whole graph, so you see the neighbours and their files:
${neighbours(graph)}
Follow the brief-writer checklist. Read the oracle files and list in oracle.uncovered every behaviour they do not cover. Recommend a tier from that list: bounded only when nothing is uncovered; say why. The task runs at the higher of the planned tier and yours.
The brief names the files the task edits (intent, not a fence) and the oracle files outside them the worker must not touch, and gives exact signatures.
The brief states which source wins when 2 sources give different numbers (counts, limits, names, versions). Use this order unless the task needs another: ${sources}. Name the winning source for each number the task uses.
Keep files inside the task's files unless the brief says why a file is missing, and then add it. Name no provider or model.${rules}`,
      { label: `brief-${t.id}`, phase: 'Briefs', schema: briefSchema, ...spawn('brief_writer', ROLE_TIER.brief_writer) },
    ).then((b) => ({ ...b, task: t.id })),
  ),
)

// The brief-writer read the oracle files, so its files and oracle replace the architect's draft.
// The tier follows the contract tier rule: the brief may raise it, never lower it.
const byTask = Object.fromEntries(briefs.map((b) => [b.task, b]))
graph = {
  ...graph,
  tasks: graph.tasks.map((t) => {
    const b = byTask[t.id]
    return { ...t, tier: higherTier(t.tier, b.tier), files: b.files, oracle: b.oracle, brief: b.brief }
  }),
}
problems = problemsOf(graph)
if (problems.length > 0) {
  log(`${problems.length} problem(s) after the briefs; the critic is skipped`)
  return escalate(graph, briefs, problems)
}

phase('Spec')
const specBranch = (t) => `spec/${t.id}`
const taskText = (t) => `Task ${t.id} of the wave on ${args.repo}, goal: ${args.goal}
Files: ${t.files.join(', ')}. Oracle: ${t.oracle.command}; uncovered: ${t.oracle.uncovered.join('; ')}.
Brief:
${t.brief}
The whole graph, so you see the neighbours and their files:
${neighbours(graph)}`

// designTwice: 2 designers with different lenses, then 1 adversarial judge. Returns the winner as text.
async function designTwice(t) {
  const designs = await parallel(
    DESIGNS.map((k) => () =>
      agent(
        `Design the public surface of a one-way task: a contract, a save format or a public API that is costly to reverse.
${taskText(t)}
1. Read the code the task touches. Write no file, commit nothing.
2. Design for ${LENS[k]}.
3. Give the approach in 2 sentences, every public signature as code, a caller usage sketch of 5 to 15 lines, and the risks.
Name no provider or model.${rules}`,
        { label: `design-${t.id}-${k}`, phase: 'Spec', schema: designSchema, ...spawn('spec_designer', ROLE_TIER.spec_designer) },
      ).then((d) => ({ ...d, task: t.id })),
    ),
  )
  const show = (d, k) => `## Design ${k}\n${d.approach}\nSignatures:\n${d.signatures}\nSketch:\n${d.sketch}`
  const p = await agent(
    `Judge 2 designs of a one-way task. Attack both. You edit nothing.
${taskText(t)}
${designs.map((d, i) => show(d, DESIGNS[i])).join('\n\n')}
1. For each design, find the caller that misuses it and the later change that breaks it. List them in flaws_a and flaws_b.
2. Pick the design whose flaws cost less to live with. Say why in reason.${rules}`,
    { label: `pick-${t.id}`, phase: 'Spec', schema: pickSchema, ...spawn('reviewer', ROLE_TIER.reviewer) },
  )
  const win = designs[DESIGNS.indexOf(p.pick)]
  const flaws = p.pick === 'a' ? p.flaws_a : p.flaws_b
  return `${win.approach}\nSignatures:\n${win.signatures}\nSketch:\n${win.sketch}\nThe judge found these flaws in it; guard against each: ${flaws.join('; ') || 'none'}`
}

// specPrompt: round 0 cuts spec/<task id> fresh from base.sha, so a spec branch left by an earlier
// wave with the same task id is never reused. A rewrite (prev set) starts from the last round's commit.
function specPrompt(t, design, bad, prev) {
  const branch = specBranch(t)
  const work = prev
    ? `Work on branch ${branch}. Run git fetch -q origin. Start from ${prev}, the commit of your last round.`
    : `Work on branch ${branch}, cut fresh from ${args.base.sha}. Run git fetch -q origin. If origin already has ${branch}, it is left from an earlier wave: delete it with git push -q origin --delete ${branch}. Never build on it. Then cut ${branch} from ${args.base.sha} and push it.`
  return `Write the spec as code for this task, before anyone builds it.
${taskText(t)}
1. ${work}
2. Write stubs only inside the task files. Each body is not implemented.
3. Write 1 failing check only for each uncovered behaviour that matters to a caller; leave the rest in uncovered. The check is a unit test, a scripted scene run or a golden-output compare. For a Godot 4 game, a scene run is a GDScript that extends SceneTree, drives the scene with scripted input and calls quit(1) on a wrong result; run it with godot --headless --script. Put the checks in files outside the task files.
4. Set command to 1 command that runs the old oracle and the new checks.
5. Run the command before you stop. It must fail for the intended reason. Put its last output line in red.line and set red.failed true.
6. Write a caller usage sketch of 5 to 15 lines.
7. Commit by path. Push with plain git push: no rebase, no force, no squash. Report the full 40-character SHA.
8. Write no implementation.
9. List in uncovered every behaviour you still do not pin.
10. Put in keep each check that meets the keep rule in AGENTS-AND-MODELS.md "Tests": it catches a silent wrong value or a broken use case a caller relies on, no other test proves the same claim, and it fails when the code it guards breaks. Also put in keep each test file that was there before your spec and that you amended. Every other check is scaffold: it guides the build and the wave deletes it.
11. List in created each test file you added: a file not in the tree at ${args.base.sha}.${design ? `\nImplement this design: ${design}` : ''}${bad.length > 0 ? `\nYour last spec failed these checks. Fix each:\n- ${bad.join('\n- ')}` : ''}
Name no provider or model.${rules}`
}

// withSpec: the task after its spec. The spec tests join the oracle files, the brief gets the sketch,
// spec_sha records the spec commit, so wave starts only this task from it. The stubs are task files:
// the worker fills them in; only the spec tests are oracle files. A scaffold test is an oracle for the build
// only: it counts for the tier here, and scaffold tells wave to delete it. A test that was in the oracle
// before the spec is never scaffold.
// This is the one deliberate tier drop of the contract, so higherTier is not used here: judgment
// becomes bounded when nothing is uncovered; lead and one_way never drop.
const withSpec = (t, s) => ({
  ...t,
  oracle: { command: s.command, files: [...new Set([...t.oracle.files, ...s.tests])], uncovered: s.uncovered },
  tier: t.tier === 'judgment' && !t.one_way && s.uncovered.length === 0 ? 'bounded' : t.tier,
  spec_sha: s.sha,
  scaffold: s.tests.filter((x) => !s.keep.includes(x) && !t.oracle.files.includes(x)),
  brief: `${t.brief}\n\nCaller usage sketch (from the spec step):\n${s.sketch}\n\nSpec tests, already on ${specBranch(t)} at ${s.sha}: ${s.tests.join(', ')}. They are oracle files: do not edit them. Stubs: ${s.stubs.join(', ') || 'none'}. The stubs are task files, not spec tests: fill them in. Cut your branch from ${s.sha}.`,
})

const specs = []
// Serial on purpose: 1 spec at a time keeps the agent load bounded (x-limits.spec_rounds per task).
for (const t of graph.tasks.filter((x) => x.oracle.uncovered.length > 0)) {
  const design = t.one_way ? await designTwice(t) : ''
  const role = t.one_way ? 'spec_designer' : 'spec_writer'
  let spec
  let bad = []
  for (let round = 0; round <= LIMITS.spec_rounds; round++) {
    spec = { ...(await agent(specPrompt(t, design, bad, spec && spec.sha), { label: round === 0 ? `spec-${t.id}` : `spec-${t.id}-${round}`, phase: 'Spec', schema: specSchema, ...spawn(role, ROLE_TIER[role]) })), task: t.id }
    bad = specMeaning(spec, t)
    if (bad.length === 0) break
  }
  if (bad.length > 0) return escalate(graph, briefs, bad.map((p) => `task ${t.id}: spec: ${p}`), specs)
  const after = withSpec(t, spec)
  specs.push({ ...spec, tier_before: t.tier, tier_after: after.tier })
  graph = { ...graph, tasks: graph.tasks.map((x) => (x.id === t.id ? after : x)) }
}
// The rerun of the checks proves a dropped tier: oracle files inventoried, nothing uncovered, and the
// worker does not edit its own oracle.
problems = problemsOf(graph)
if (problems.length > 0) return escalate(graph, briefs, problems, specs)

phase('Critic')
const critique = await agent(
  `Check this plan for completeness against the goal: ${args.goal}
Repo ${args.repo}. Read the goal and the code, then the plan:
${graph.tasks.map((t) => `## Task ${t.id} (${t.tier}); edits ${t.files.join(', ')}; blocked by ${t.blockers.join(', ') || 'none'}\nOracle: ${t.oracle.command}; uncovered: ${t.oracle.uncovered.join('; ') || 'none'}\n${t.brief}`).join('\n\n')}
List what is missing: a behaviour of the goal that no task builds, a task with no oracle, a missing blocker, a file a task needs but may not edit, a brief that names no winning source for a number, a place the tasks disagree on a name or a number. One line per gap. You edit nothing.
Set complete true only when you found no gap.${rules}`,
  { label: 'critic', phase: 'Critic', schema: critiqueSchema, ...spawn('reviewer', ROLE_TIER.reviewer) },
)

// issueDraft: the issue text of 1 task. The lead files it; it writes the issue numbers of the blockers.
const issueDraft = (t) => ({
  task: t.id,
  title: t.title,
  labels: [`area:${t.area}`, ...(t.needs || []).map((n) => NEED_LABELS[n])],
  body: [
    ...(parent ? [`Parent: #${parent}`, ''] : []),
    `Outcome: ${t.outcome}`,
    '',
    'Done when:',
    ...t.done_when.map((d) => `- [ ] ${d}`),
    '',
    `Oracle: \`${t.oracle.command}\`. Files: ${t.oracle.files.join(', ') || 'none'}. Uncovered: ${t.oracle.uncovered.join('; ') || 'none'}.`,
    `Tier: ${t.tier}. Files to edit: ${t.files.join(', ')}.`,
    ...(t.one_way ? ['One-way door: designed twice, judged by an adversarial pass.'] : []),
    ...(t.blockers.length > 0 ? [`Blocked by tasks: ${t.blockers.join(', ')}.`] : []),
    ...(t.split ? [`Split into parts: ${t.split.join(', ')}.`] : []),
    '',
    'Brief:',
    t.brief,
  ].join('\n'),
})

return {
  status: critique.complete && critique.missing.length === 0 ? 'done' : 'gaps',
  graph,
  briefs,
  specs,
  issues: graph.tasks.map(issueDraft),
  wave: { graph, claims: {} },
  problems: [],
  missing: critique.missing,
}
