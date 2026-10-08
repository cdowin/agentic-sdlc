export const meta = {
  name: 'plan',
  description: 'Plan a wave. An architect drafts the task graph, brief-writers expand every task in parallel, a critic lists what is missing. Returns a contract graph and one brief per task. It files nothing.',
  phases: ['Graph', 'Briefs', 'Critic'],
}

// args: { goal, repo, branch, base, parent, rules, sources, runtime }
//   goal     the parent issue (number or URL) or the text of the goal; the architect reads it
//   repo     owner/name
//   branch   the wave branch that integration pushes to
//   base     { ref, sha }: the frozen base. sha is the full 40-character SHA.
//   parent   optional; the parent issue number
//   rules    optional; the repo's code rules as text, passed to every agent
//   sources  optional; the order of authority when 2 sources give different numbers
//            (default: the oracle output, then the code, then the issue text, then the docs)
//   runtime  optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
// The workflow files no issue and opens no pull request. The main agent files the issues
// from the graph and the briefs. The result is { status, graph, briefs, problems, missing }.

// The Claude profile: the parts of runtimes.json "claude" that this workflow reads.
const CLAUDE_RUNTIME = {
  tiers: { judgment: { model: 'sonnet' }, lead: { model: 'opus' } },
  agent_types: { lead: 'chief-of-staff', brief_writer: 'brief-writer', reviewer: 'reviewer' },
}
// Role to tier: x-roles in plugin/contract/sdlc.schema.json.
const ARCHITECT_TIER = 'lead'
const BRIEF_WRITER_TIER = 'judgment'
const CRITIC_TIER = 'lead'
// x-limits.rework_rounds: how many times the architect may redraft a graph that fails the meaning checks.
const REWORK_ROUNDS = 2
// x-capabilities: the names a task may list in needs.
const CAPABILITIES = [
  'structured_output', 'model_per_spawn', 'effort_per_spawn', 'tool_restriction', 'worktree_per_task',
  'parallel_spawn', 'follow_up', 'interrupt', 'usage_report', 'image_generation',
]
const DEFAULT_SOURCES = 'the oracle output, then the code, then the issue text, then the docs'

// Contract shapes: copies of $defs graph, brief and critique in plugin/contract/sdlc.schema.json.
// A workflow cannot import a file. tests/workflows.js fails when a copy drifts.
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
    tier: { type: 'string', enum: ['bounded', 'judgment', 'lead'] },
    blockers: { type: 'array', items: { type: 'string' }, description: 'Task ids that must be integrated before this task starts' },
    files: { type: 'array', minItems: 1, items: { type: 'string' }, description: 'The only files the worker may edit' },
    oracle: oracleSchema,
    brief: { type: 'string' },
    branch: { type: 'string' },
    needs: { type: 'array', items: { type: 'string' }, description: 'Capabilities from x-capabilities that the task needs. Empty or absent: any agent may take it. An agent takes the task only when its runtime has every one (status enforced or instructed).' },
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

const critiqueSchema = {
  type: 'object',
  description: 'The output of a completeness critic on a plan: what the tasks and briefs leave out',
  required: ['complete', 'missing'],
  properties: {
    complete: { type: 'boolean', description: 'True only when the tasks and briefs cover the whole goal' },
    missing: { type: 'array', items: { type: 'string' }, description: 'Each gap, 1 line: the behaviour, file, test or decision that no task covers. Empty when complete.' },
  },
}

if (!args.goal || !args.repo || !args.branch || !args.base || !args.base.ref || !/^[0-9a-f]{40}$/.test(args.base.sha || '')) {
  throw new Error('plan needs args goal, repo, branch and base { ref, sha } with a 40-character sha')
}
const runtime = args.runtime || CLAUDE_RUNTIME
const spawn = (role, tier) => {
  const t = runtime.tiers[tier]
  return { model: t.model, ...(t.effort && { effort: t.effort }), agentType: runtime.agent_types[role] }
}
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const sources = args.sources || DEFAULT_SOURCES

// The meaning checks of check.js for a graph, as far as plan can break them: a copy of graphMeaning
// and tierMeaning. Run `node plugin/contract/check.js graph` on the result as well.
const norm = (p) => p.replace(/\/+/g, '/').replace(/^(\.\/)+/, '').replace(/\/$/, '')
const collide = (a, b) => {
  const [x, y] = [norm(a), norm(b)]
  return x === y || x === '.' || y === '.' || x.startsWith(`${y}/`) || y.startsWith(`${x}/`)
}
const overlap = (as, bs) => as.flatMap((a) => bs.filter((b) => collide(a, b)).map((b) => (norm(a) === norm(b) ? a : `${a} and ${b}`)))
const meaning = (g) => {
  const out = []
  if (g.rework_limit > REWORK_ROUNDS) out.push(`rework_limit ${g.rework_limit} is over ${REWORK_ROUNDS}`)
  const byId = {}
  for (const t of g.tasks) {
    if (byId[t.id]) out.push(`tasks: id ${t.id} is not unique`)
    byId[t.id] = t
  }
  for (const t of g.tasks) {
    for (const b of t.blockers) if (!byId[b]) out.push(`task ${t.id}: blocker ${b} is not a task`)
    for (const n of t.needs || []) if (!CAPABILITIES.includes(n)) out.push(`task ${t.id}: needs ${n}, which is not a capability`)
    if (t.tier === 'bounded') {
      if (t.oracle.uncovered.length > 0) out.push(`task ${t.id}: tier bounded, but the oracle does not cover ${t.oracle.uncovered.join('; ')}`)
      if (t.oracle.files.length === 0) out.push(`task ${t.id}: tier bounded needs the oracle files inventoried`)
      const own = overlap(t.files, t.oracle.files)
      if (own.length > 0) out.push(`task ${t.id}: a bounded worker may not edit its own oracle ${own.join(', ')}`)
    }
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
  g.tasks.forEach((t) => visit(t.id, []))
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
// The wave facts come from args, never from the architect: it cannot know the frozen base.
const pin = (g) => ({ ...g, repo: args.repo, ...(args.parent && { parent: args.parent }), branch: args.branch, base: args.base, rework_limit: REWORK_ROUNDS })

phase('Graph')
let graph
let problems = []
for (let round = 0; round <= REWORK_ROUNDS; round++) {
  const redo = problems.length > 0 ? `\nYour last draft failed these checks. Fix each one and return the whole graph again:\n- ${problems.join('\n- ')}\n` : ''
  graph = pin(await agent(
    `Plan the wave for this goal: ${args.goal}
Repo ${args.repo}. Wave branch ${args.branch}, cut from ${args.base.ref} at ${args.base.sha}.
Read the goal, CLAUDE.md and the code it touches. Then draft the task graph:
1. One outcome per task. A task a worker finishes in about an hour, on 1 branch.
2. Set blockers so the steps follow dependency depth: a task lists only the tasks whose output it needs. Tasks with no blocker path between them run in parallel.
3. List the files each task may edit. Two tasks that run in parallel share no file and no directory. When 2 tasks need the same file, make one block the other.
4. Give each task an oracle: the focused test command, the inventory of every test or golden file that covers it (read them), and the behaviours no file covers in uncovered. A task whose oracle files you have not read is not bounded.
5. Set the tier from the oracle: bounded only when uncovered is empty and the oracle files are not in the task's files. Judgment when a behaviour has no oracle. Lead when the step-up rule in AGENTS-AND-MODELS.md applies.
6. Set needs only when a task requires a capability that not every agent has. Allowed names: ${CAPABILITIES.join(', ')}. Today only image_generation differs between agents. Name no provider or model: any agent may take a task that lists no needs.
Return the graph. Any agent may build any task; do not route by provider.${rules}${redo}`,
    { label: round === 0 ? 'architect' : `architect-${round}`, phase: 'Graph', schema: graphSchema, ...spawn('lead', ARCHITECT_TIER) },
  ))
  problems = meaning(graph)
  if (problems.length === 0) break
  log(`graph round ${round}: ${problems.length} problem(s)`)
}
if (problems.length > 0) {
  return { status: 'escalated', graph, briefs: [], problems, missing: [] }
}

phase('Briefs')
const briefs = await parallel(
  graph.tasks.map((t) => () =>
    agent(
      `Write the brief for task ${t.id} of the wave on ${args.repo}, goal: ${args.goal}
The task: files ${t.files.join(', ')}; blockers ${t.blockers.join(', ') || 'none'}; oracle ${t.oracle.command}; draft tier ${t.tier}.
The whole graph, so you see the neighbours and their files:
${graph.tasks.map((o) => `- ${o.id}: edits ${o.files.join(', ')}; blocked by ${o.blockers.join(', ') || 'none'}`).join('\n')}
Follow the brief-writer checklist. Read the oracle files and list in oracle.uncovered every behaviour they do not cover. Set tier from that list: bounded only when nothing is uncovered; say why.
The brief names the files the worker may edit and the files it must not touch, and gives exact signatures.
The brief states which source wins when 2 sources give different numbers (counts, limits, names, versions). Use this order unless the task needs another: ${sources}. Name the winning source for each number the task uses.
Keep files inside the task's files unless the brief says why a file is missing, and then add it. Name no provider or model.${rules}`,
      { label: `brief-${t.id}`, phase: 'Briefs', schema: briefSchema, ...spawn('brief_writer', BRIEF_WRITER_TIER) },
    ).then((b) => ({ ...b, task: t.id })),
  ),
)

// The brief-writer read the oracle files, so its files, oracle and tier replace the architect's draft.
const byTask = Object.fromEntries(briefs.map((b) => [b.task, b]))
graph = {
  ...graph,
  tasks: graph.tasks.map((t) => {
    const b = byTask[t.id]
    return { ...t, tier: b.tier, files: b.files, oracle: b.oracle, brief: b.brief }
  }),
}
problems = meaning(graph)
if (problems.length > 0) {
  log(`${problems.length} problem(s) after the briefs; the critic is skipped`)
  return { status: 'escalated', graph, briefs, problems, missing: [] }
}

phase('Critic')
const critique = await agent(
  `Check this plan for completeness against the goal: ${args.goal}
Repo ${args.repo}. Read the goal and the code, then the plan:
${graph.tasks.map((t) => `## Task ${t.id} (${t.tier}); edits ${t.files.join(', ')}; blocked by ${t.blockers.join(', ') || 'none'}\nOracle: ${t.oracle.command}; uncovered: ${t.oracle.uncovered.join('; ') || 'none'}\n${t.brief}`).join('\n\n')}
List what is missing: a behaviour of the goal that no task builds, a task with no oracle, a missing blocker, a file a task needs but may not edit, a brief that names no winning source for a number, a place the tasks disagree on a name or a number. One line per gap. You edit nothing.
Set complete true only when you found no gap.${rules}`,
  { label: 'critic', phase: 'Critic', schema: critiqueSchema, ...spawn('reviewer', CRITIC_TIER) },
)

return {
  status: critique.complete && critique.missing.length === 0 ? 'done' : 'gaps',
  graph,
  briefs,
  problems: [],
  missing: critique.missing,
}
