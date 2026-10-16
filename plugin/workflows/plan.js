export const meta = {
  name: 'plan',
  description: 'Plan a wave. An architect drafts the task graph, brief-writers expand every task in parallel, spec agents write failing tests for each task with uncovered behaviours, a critic lists what is missing. Returns a contract graph, one brief and one issue draft per task, the specs, and the wave args. It files nothing.',
  phases: ['Graph', 'Briefs', 'Spec', 'Critic'],
}

// args: { goal, repo, branch, base, parent, rules, sources, runtime, solo, gate, setup, fix_lane }
//   goal     the parent issue (number or URL) or the text of the goal; the architect reads it
//   repo     owner/name
//   branch   the wave branch that integration pushes to
//   base     { ref, sha }: the frozen base. sha is the full 40-character SHA.
//   parent   optional; the parent issue number. Default: goal, when goal is a number.
//   rules    optional; the repo's code rules as text, passed to every agent
//   sources  optional; the order of authority when 2 sources give different numbers
//            (default: the oracle output, then the code, then the issue text, then the docs)
//   runtime  optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
//   solo     optional; true for 1 lead or a host with no GitHub issues. wave.claims is then 'solo'
//            and the lead posts no claim comments.
//   gate     optional; the repo gate command. A spec agent runs it on its spec commit.
//   setup    optional; a command each spec agent runs once in its fresh worktree before any test or
//            gate command (for example an engine import cache). wave gets it as wave.setup.
//   fix_lane optional; true or false. The graph gets it as graph.fix_lane. With no value the graph has none.
// The workflow files no issue and opens no pull request. The result is
// { status, graph, briefs, specs, issues, wave, problems, missing }. status is done, gaps (the critic
// listed missing work) or escalated (the graph or a spec fails a check after the redrafts).
// The Spec phase runs for each task whose oracle has uncovered behaviours not marked feel:. An entry
// that starts with feel: is play feel: a playtest proves it, not a failing test. A spec agent pushes stubs,
// failing tests and a usage sketch to its own branch spec/<task id>, cut fresh from base.sha. The task
// records the spec commit as spec_sha and its worker starts from that SHA, so the wave branch stays at
// base.sha and gets the spec only when the task merges. The spec tests are oracle files; the stubs are
// task files the worker fills in. A spec test not marked keep is scaffold: an oracle for the build
// only, listed in the task's scaffold, which wave deletes in the task's merge step. Each entry of specs is the spec with tier_before and tier_after. The lead deletes the merged
// spec/* branches with the task branches. A one_way task gets 2 designs and 1 judge first.
// The lead files 1 issue per draft in issues, writes each issue number into wave.graph, posts 1
// claim comment per task and puts its URL in wave.claims (with solo: no claims). Then it runs the wave
// workflow on wave.

// ---- contract: begin
// Generated from plugin/contract by node tests/workflows.js --write. Do not edit.
const contract = {
  "x-tiers": {"bounded":"An oracle covers every behaviour that matters. A tight brief, a file list, the signatures, 15-30 min.","judgment":"1 or more behaviours have no oracle, or the task has a design choice. Also brief-writing, sub-lead, integration and a skeptic.","lead":"The plan, the chief of staff, every review, and a change the step-up rule names."},
  "x-roles": {"lead":"lead","brief_writer":"judgment","sub_lead":"judgment","worker":"bounded","integrator":"judgment","reviewer":"lead","diff_reviewer":"bounded","skeptic":"judgment","spec_writer":"judgment","spec_designer":"lead","blast_radius":"lead"},
  "x-first-try": {"integrator":"bounded"},
  "x-capabilities": ["structured_output","model_per_spawn","effort_per_spawn","tool_restriction","worktree_per_task","parallel_spawn","follow_up","interrupt","usage_report","image_generation"],
  "x-optional-capabilities": ["image_generation"],
  "x-need-labels": {"image_generation":"needs:image-gen"},
  "x-limits": {"rework_rounds":2,"review_batch":5,"split_parts_min":2,"stale_claim_minutes":120,"clock_skew_minutes":5,"spec_rounds":1,"blast_radius_max":4},
  "x-severity-weights": {"holds":9,"major":3,"minor":1},
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

// TASK_REQUIRED and ORACLE_REQUIRED: copies of the required fields of $defs task and oracle in
// sdlc.schema.json. tests/workflows.js fails when they drift.
const TASK_REQUIRED = ['id', 'tier', 'blockers', 'files', 'oracle']
const ORACLE_REQUIRED = ['command', 'files', 'uncovered']
// taskShape: name each field a hand-built graph leaves out of a task or its oracle. A workflow runs it
// before any meaning check, which reads these fields.
function taskShape(g) {
  const out = []
  ;(g.tasks || []).forEach((t, i) => {
    const at = `task ${t && t.id !== undefined ? t.id : `#${i + 1}`}`
    if (!t || typeof t !== 'object') return out.push(`${at}: is not an object`)
    for (const k of TASK_REQUIRED) if (t[k] === undefined) out.push(`${at}: missing ${k}`)
    if (t.oracle === undefined) return
    if (!t.oracle || typeof t.oracle !== 'object') return out.push(`${at}: oracle is not an object`)
    for (const k of ORACLE_REQUIRED) if (t.oracle[k] === undefined) out.push(`${at}: oracle is missing ${k}`)
  })
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
// A reported gate must be green or red only on the spec tests' own asserts; the CLI knows no gate.
// t is the task; the CLI passes none and gets the red check only.
function specMeaning(s, t) {
  const out = []
  if (!s.red.failed) out.push('the spec command did not fail before the build; a green spec proves nothing')
  const stray = s.keep.filter((x) => !s.tests.includes(x))
  if (stray.length > 0) out.push(`keep names files that are not spec tests: ${stray.join(', ')}`)
  const amended = s.tests.filter((x) => !s.keep.includes(x) && !s.created.includes(x))
  if (amended.length > 0) out.push(`spec tests the spec did not create are not keep: ${amended.join(', ')}; a spec that amends a test marks it keep`)
  if (s.gate && !s.gate.passed) out.push(`the repo gate failed on the spec commit for a reason other than the spec tests' own red asserts: ${s.gate.line || s.gate.command}; fix it before you push`)
  if (t) {
    const own = overlap(s.tests, t.files)
    if (own.length > 0) out.push(`spec tests are inside the task files (${own.join(', ')}); the worker may not edit its own oracle`)
    const loose = s.stubs.filter((x) => overlap([x], t.files).length === 0)
    if (loose.length > 0) out.push(`stubs outside the task files: ${loose.join(', ')}`)
  }
  return out
}

// chainMeaning: the graph checks, where 2 tasks in 2 chains may edit the same file: they build on 2
// branches, and the converge step of wave merges them. A chain task waits only on tasks of its chain or
// on a task with no chain. A no-chain task that a chain task waits on may not reach a chain task through
// its blockers: it would wait on the converge, which waits on every chain task. A chain branch is no task
// branch. plan.js and wave.js hold the same function through the generated block.
function chainMeaning(g) {
  const chain = Object.fromEntries(g.tasks.map((t) => [t.id, t.chain || '']))
  const blockersOf = Object.fromEntries(g.tasks.map((t) => [t.id, t.blockers]))
  // reach: the first chain task in the blocker reach of id, or ''. A cycle or an unknown id ends the walk.
  const reach = (id, seen = new Set()) => {
    for (const b of blockersOf[id] || []) {
      if (seen.has(b) || !(b in chain)) continue
      seen.add(b)
      const x = chain[b] ? b : reach(b, seen)
      if (x) return x
    }
    return ''
  }
  const apart = g.tasks.flatMap((a, i) => g.tasks.slice(i + 1).filter((b) => chain[a.id] !== chain[b.id]).map((b) => `tasks ${a.id} and ${b.id} run in parallel and both edit `))
  const out = graphMeaning(g).filter((p) => !apart.some((x) => p.startsWith(x)))
  const branches = g.tasks.map((t) => t.branch || `${g.branch}-${t.id}`)
  for (const t of g.tasks.filter((x) => x.chain)) {
    for (const b of t.blockers) {
      if (chain[b] && chain[b] !== t.chain) out.push(`task ${t.id}: chain ${t.chain} waits on ${b}, which is not in it`)
      const x = b in chain && !chain[b] ? reach(b) : ''
      if (x) out.push(`task ${b}: chain ${t.chain} waits on it, but it waits on chain task ${x}`)
    }
    if (branches.includes(`${g.branch}-${t.chain}`)) out.push(`chain ${t.chain}: its branch ${g.branch}-${t.chain} is a task branch`)
  }
  return [...new Set(out)]
}
// $defs oracle of plugin/contract/sdlc.schema.json: the oracle of a task, a queue entry and a brief.
const oracleSchema = {
  "type": "object",
  "description": "The proof of a task. files is the inventory of every test or golden file that covers it, read before anyone says what the oracle covers.",
  "required": ["command","files","uncovered"],
  "properties": {
    "command": {"type":"string","minLength":1,"description":"The focused test command"},
    "files": {"type":"array","items":{"type":"string"}},
    "uncovered": {"type":"array","items":{"type":"string"},"description":"Behaviours no oracle file covers. Not empty means the tier is not bounded. An entry starting with feel: is play feel, proven by a playtest; a task with only such entries gets no spec agent."},
    "reach": {"type":"string","minLength":1,"description":"Optional command template with one {dir} placeholder, for example make unit SYS={dir}. The integrator runs it once for each test folder outside the focused oracle that references a changed file or class name."},
  },
}
// The Claude profile: runtimes.json "claude" without the evidence. The default of args.runtime.
const CLAUDE_RUNTIME = {
  "provider": "claude",
  "tiers": {"bounded":{"model":"haiku"},"judgment":{"model":"sonnet"},"lead":{"model":"opus"}},
  "worktree_root": ".claude/worktrees",
  "agent_types": {"lead":"agentic-sdlc:chief-of-staff","brief_writer":"agentic-sdlc:brief-writer","sub_lead":"agentic-sdlc:developer","worker":"agentic-sdlc:worker","integrator":"agentic-sdlc:integrator","reviewer":"agentic-sdlc:reviewer","diff_reviewer":"agentic-sdlc:reviewer","skeptic":"agentic-sdlc:reviewer","spec_writer":"agentic-sdlc:developer","spec_designer":"agentic-sdlc:developer","blast_radius":"agentic-sdlc:reviewer"},
  "capabilities": {"structured_output":{"status":"enforced"},"model_per_spawn":{"status":"enforced"},"effort_per_spawn":{"status":"unverified"},"tool_restriction":{"status":"enforced"},"worktree_per_task":{"status":"instructed"},"parallel_spawn":{"status":"enforced"},"follow_up":{"status":"unverified"},"interrupt":{"status":"unverified"},"usage_report":{"status":"unverified"},"image_generation":{"status":"absent"}},
}
// ---- contract: end
const DEFAULT_SOURCES = 'the oracle output, then the code, then the issue text, then the docs'

// Contract shapes: copies of $defs graph, brief and critique in plugin/contract/sdlc.schema.json,
// with $ref inlined. A workflow cannot import a file. tests/workflows.js fails when a copy drifts.
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
    removes: { type: 'array', items: { type: 'string' }, description: 'Optional: each symbol or path the done-when renames or deletes with no alias left. wave greps each on the target branch before a worker starts. Absent: the check agent reads them from the brief text.' },
    branch: { type: 'string' },
    chain: { type: 'string', minLength: 1, description: 'The chain of the task. The tasks of 1 chain build on 1 branch, <graph branch>-<chain>, and wait only on tasks of their chain. Tasks in 2 chains may edit the same file. When every chain task has ended, 1 converge step merges the chain branches into the graph branch, in the order each chain first appears in tasks, and runs the gate once. A task with no chain builds on the graph branch; when it waits on a chain task, it starts after the converge. A chain task may also wait on a task with no chain; the chain branch is then cut from the graph branch after that task merges, and that task may not wait on a chain task.' },
    split: { type: 'array', items: { type: 'string' }, description: 'Part names, x-limits.split_parts_min or more. A sub-lead writes the oracle and 1 brief per part, workers build the parts, an integrator merges them into the task branch.' },
    needs: { type: 'array', items: { type: 'string' }, description: 'Capabilities from x-capabilities that the task needs. Empty or absent: any agent may take it. An agent takes the task only when its runtime has every one (status enforced or instructed).' },
    one_way: { type: 'boolean', description: 'True when the task fixes a contract, a save format or a public API that callers depend on and that is costly to reverse. plan runs design-twice for it (2 designs, 1 adversarial judge) and never lowers its tier.' },
    risky: { type: 'boolean', description: 'True when the plan marks the change risky: a shared file many tasks read, a save or wire format, a public API, a deletion, or behaviour no oracle covers. Absent means false. A risky task gets 1 blast-radius check.' },
    spec_sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: "The full SHA of the spec commit on spec/<task id>. plan sets it only for a task it spec'd. wave starts the task branch from this SHA, never from a branch name." },
    resume_from: { type: 'string', minLength: 1, description: 'A full SHA, or a branch on the remote, that holds earlier work on the task. wave starts the task branch from it (it wins over spec_sha), merges the wave branch into it, and the worker continues that work.' },
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
    fix_lane: { type: 'boolean', description: 'Default false. When true, one lead-tier fix agent runs on the wave branch for a CRITICAL end-review finding, a convergence-guard major or a red converge gate. It does not count against rework_limit and runs at most once per wave.' },
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
    removes: { type: 'array', items: { type: 'string' }, description: 'Each symbol or path the done-when renames or deletes with no alias left. Empty or absent when none. wave greps each on the target branch.' },
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
    uncovered: { type: 'array', items: { type: 'string' }, description: 'Behaviours the old oracle and the spec still do not pin. Empty: the task may become bounded. An entry starting with feel: is play feel, proven by a playtest; a task with only such entries gets no spec agent.' },
    sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: 'The full SHA of the pushed spec commit' },
    gate: {
      type: 'object',
      required: ['command', 'passed'],
      description: 'Present when the plan has a gate. The repo gate run on the spec commit. passed is true when the gate is green, or when its only red is the failing asserts of the spec tests themselves; false when any other check is red (a lint, comment budget, format or type check on the stubs or spec tests) and you could not fix it.',
      properties: {
        command: { type: 'string', minLength: 1 },
        passed: { type: 'boolean' },
        line: { type: 'string', description: 'The last output line of the gate when passed is false' },
      },
    },
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
if (args.gate !== undefined && (typeof args.gate !== 'string' || !args.gate.trim())) throw new Error('args.gate must be a non-empty command string')
if (args.fix_lane !== undefined && typeof args.fix_lane !== 'boolean') throw new Error('args.fix_lane must be true or false')
if (args.setup !== undefined && (typeof args.setup !== 'string' || !args.setup.trim())) throw new Error('args.setup must be a command string: it runs once in each fresh worktree, before any test or gate command')
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
const pin = ({ fix_lane, ...g }) => ({ ...g, repo: args.repo, ...(parent && { parent }), branch: args.branch, base: args.base, rework_limit: LIMITS.rework_rounds, ...(args.fix_lane !== undefined && { fix_lane: args.fix_lane }) })
// problemsOf: the contract checks of the graph, and the fields each issue draft needs.
const problemsOf = (g) => [
  ...chainMeaning(g),
  ...g.tasks.flatMap((t) => [
    ...['title', 'outcome', 'area'].filter((k) => !t[k]).map((k) => `task ${t.id}: ${k} is empty; the issue draft needs it`),
    ...((t.done_when || []).length === 0 ? [`task ${t.id}: done_when is empty; the issue draft needs it`] : []),
    ...(t.needs || []).filter((n) => !NEED_LABELS[n]).map((n) => `task ${t.id}: needs ${n}, which has no label in x-need-labels`),
    ...unlistedWaits(g, t).map((x) => `task ${t.id}: brief says it needs ${x} merged, but ${x} is not a blocker`),
  ]),
]
// unlistedWaits: each task id of the graph that a brief line of t says it waits on ("needs 3 merged",
// "after 3 lands", "waits on 3"), but that is not a blocker of t. Only a whole task id counts.
const WAITS = /needs? .* merged|after .* (merged|lands)|waits? on/i
const unlistedWaits = (g, t) => {
  const waits = (t.brief || '').split('\n').filter((l) => WAITS.test(l))
  const named = (l, x) => new RegExp(`(^|[^\\w-])${x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![\\w-])`).test(l)
  return g.tasks.map((o) => o.id).filter((x) => x !== t.id && !t.blockers.includes(x) && waits.some((l) => named(l, x)))
}
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
// FEEL marks an uncovered entry as play feel, proven by a playtest. A task with only such entries
// (or none) gets no spec agent and keeps its tier.
const FEEL = 'feel:'
const needsSpec = (t) => t.oracle.uncovered.some((u) => !u.trim().startsWith(FEEL))
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
  const steps = [
    work,
    ...(args.setup ? [`Run the setup command once in your worktree, before any test or gate command: ${args.setup}. If it fails, stop: set red.failed false and put its error in red.line.`] : []),
    'Write stubs only inside the task files. Each body is not implemented.',
    'Write 1 failing check only for each uncovered behaviour that matters to a caller; leave the rest in uncovered. The check is a unit test, a scripted scene run or a golden-output compare. For a Godot 4 game, a scene run is a GDScript that extends SceneTree, drives the scene with scripted input and calls quit(1) on a wrong result; run it with godot --headless --script. Put the checks in files outside the task files. An entry that starts with feel: is play feel: write no check for it and leave it in uncovered.',
    'Set command to 1 command that runs the old oracle and the new checks.',
    'Run the command before you stop. It must fail for the intended reason. Put its last output line in red.line and set red.failed true.',
    ...(args.gate ? [`Run the repo gate on your spec commit: ${args.gate}. The spec tests fail on purpose; that red is yours. Fix every other red it shows (comment or doc budgets, lint, format, type checks on your stubs and spec tests) in a new commit, run the gate again, then push. Report gate: { command: "${args.gate}", passed, line }. passed is true only when the gate is green or its only red is your spec tests' failing asserts.`] : []),
    'Write a caller usage sketch of 5 to 15 lines.',
    'Commit by path. Push with plain git push: no rebase, no force, no squash. Report the full 40-character SHA.',
    'Write no implementation.',
    'List in uncovered every behaviour you still do not pin.',
    'Put in keep each check that meets the keep rule in AGENTS-AND-MODELS.md "Tests": it catches a silent wrong value or a broken use case a caller relies on, no other test proves the same claim, and it fails when the code it guards breaks. Also put in keep each test file that was there before your spec and that you amended. Every other check is scaffold: it guides the build and the wave deletes it.',
    `List in created each test file you added: a file not in the tree at ${args.base.sha}.`,
  ]
  return `Write the spec as code for this task, before anyone builds it.
${taskText(t)}
${steps.map((x, i) => `${i + 1}. ${x}`).join('\n')}${design ? `\nImplement this design: ${design}` : ''}${bad.length > 0 ? `\nYour last spec failed these checks. Fix each:\n- ${bad.join('\n- ')}` : ''}
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

// specChain: the spec of 1 task, design first when one_way, then up to x-limits.spec_rounds rewrites.
// It reads the graph and writes nothing to it, so the chains can run side by side.
async function specChain(t) {
  const design = t.one_way ? await designTwice(t) : ''
  const role = t.one_way ? 'spec_designer' : 'spec_writer'
  let spec
  let bad = []
  for (let round = 0; round <= LIMITS.spec_rounds; round++) {
    spec = { ...(await agent(specPrompt(t, design, bad, spec && spec.sha), { label: round === 0 ? `spec-${t.id}` : `spec-${t.id}-${round}`, phase: 'Spec', schema: specSchema, ...spawn(role, ROLE_TIER[role]) })), task: t.id }
    bad = [
      ...specMeaning(spec, t),
      ...(args.gate && !spec.gate ? [`the spec did not report the gate result (the plan has a gate: ${args.gate})`] : []),
      ...(args.gate && spec.gate && spec.gate.command !== args.gate ? [`the spec ran ${spec.gate.command}, not the gate ${args.gate}`] : []),
    ]
    if (bad.length === 0) break
  }
  return { t, spec, after: bad.length === 0 ? withSpec(t, spec) : t, bad }
}

// The chains run in parallel: the runtime caps the concurrent agents, and each chain pushes to its
// own branch spec/<task id>. The fold runs after all finish, in graph task order, so the result
// equals a serial run.
const chains = await parallel(graph.tasks.filter(needsSpec).map((t) => () => specChain(t)))
const failed = chains.flatMap((c) => c.bad.map((p) => `task ${c.t.id}: spec: ${p}`))
if (failed.length > 0) return escalate(graph, briefs, failed)
const specs = chains.map((c) => ({ ...c.spec, tier_before: c.t.tier, tier_after: c.after.tier }))
const specced = new Map(chains.map((c) => [c.t.id, c.after]))
graph = { ...graph, tasks: graph.tasks.map((x) => specced.get(x.id) || x) }
// The rerun of the checks proves a dropped tier: oracle files inventoried, nothing uncovered, and the
// worker does not edit its own oracle.
problems = problemsOf(graph)
if (problems.length > 0) return escalate(graph, briefs, problems, specs)

phase('Critic')
const critique = await agent(
  `Check this plan for completeness against the goal: ${args.goal}
Repo ${args.repo}. Read the goal and the code, then the plan:
${graph.tasks.map((t) => `## Task ${t.id} (${t.tier}); edits ${t.files.join(', ')}; blocked by ${t.blockers.join(', ') || 'none'}\nOracle: ${t.oracle.command}; uncovered: ${t.oracle.uncovered.join('; ') || 'none'}\n${t.brief}`).join('\n\n')}
List what is missing: a behaviour of the goal that no task builds, a task with no oracle, a missing blocker, a file a task needs but may not edit, a brief that names no winning source for a number, a place the tasks disagree on a name or a number, a brief line that says the task needs X merged, depends on or waits on a task or part X that is not in its blockers. One line per gap. You edit nothing.
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

if (args.solo) log('solo: post no claim comments; wave.claims is "solo"')
return {
  status: critique.complete && critique.missing.length === 0 ? 'done' : 'gaps',
  graph,
  briefs,
  specs,
  issues: graph.tasks.map(issueDraft),
  wave: { graph, claims: args.solo ? 'solo' : {}, ...(args.setup && { setup: args.setup }) },
  problems: [],
  missing: critique.missing,
}
