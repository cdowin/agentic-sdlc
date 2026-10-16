export const meta = {
  name: 'flow',
  description: 'Run a queue of ready, claimed issues as a loop: brief each task just in time, start a worker when a slot frees and the machine load allows, lease the files of each task from its start to its landing, and land each green report at once into the group branch of its parent issue (gate and reach green). Closes and prunes each landed task. When every task of a parent has landed, merges the default branch into its group branch, runs the full suite once and on green opens 1 PR that closes the parent and merges itself on green; red files 1 holds finding. Each worker finding is classified, and 1 agent votes on the open finding it matches or files it; only a holds finding stops a landing, with 1 fix agent in its group. Queued findings start in priority order. Each landing gets 1 cheap diff review, and each args.review_every landings (default 6) 1 blind batched review at the lead tier; both only file or vote findings, and no landing waits on them. No chain, no converge. Never pushes to main.',
  phases: ['Check', 'Brief', 'Build', 'Integrate', 'Review', 'Ship', 'Report'],
}

log(`flow ${args.repo || '(no repo)'}: ${Array.isArray(args.queue) ? args.queue.map((e) => `#${e && e.issue}`).join(' ') : args.queue ? `query ${args.queue}` : 'no args.queue'}`)

// flow: a loop over ready, claimed issues. Each task leases its files from its start to its landing; a task
// whose files are leased waits until the holder lands, then starts from the new head of its group branch.
// A green report lands at once into the group branch of its parent issue (1 per parent, named
// <parent>-<slug>), 1 landing at a time per group branch; 2 groups land in parallel. Main is always
// shippable: flow lands only into a group branch, only over a green gate (and reach), and never pushes to
// main. When every task of a parent has landed, flow merges main into the group branch, runs the full suite
// once there and on green opens 1 PR per group branch into main, set to merge itself on green.
// A red gate that is red on the pre-merge tip too is base red: it holds only that group branch.
// args: { repo, base, queue, started_at, claimed_at, claims, gate, converge_gate, setup, max_load, cpus, review_every, rules, answers, runtime }
//   repo      the owner/name of the repo.
//   base      { ref, sha }: the default branch and its SHA. A group branch that is not on the remote is
//             made at base.sha.
//   queue     the ready issues in start order ($defs queue, the items of tasks): each has issue, parent,
//             group (<parent>-<slug>), tier, files (the lease), oracle, and body (the issue body, verbatim).
//             A queued finding also has finding { kind, severity, votes, minutes }: the findings take the
//             places findings hold in the queue, holds first, then in priority order (x-severity-weights[severity] x votes x
//             minutes, at least 1 minute); ready issues keep their places.
//             Or a gh command string: the first agent runs it and returns the queue.
//   started_at required; ISO UTC time (date -u +%Y-%m-%dT%H:%M:%SZ). The workflow reads no clock.
//   claimed_at optional; issue -> ISO UTC time of the lead's claim comment.
//   claims    issue -> the URL of the lead's claim comment, or 'solo'. A task with no claim does not start.
//   gate      optional; the repo gate. The worker runs it, and the integrator runs it after each landing.
//   converge_gate optional; the full suite. It runs once per group branch, after every task of the parent
//             landed and the default branch is merged in. Green: 1 PR (Closes #<parent>) that merges itself
//             on green. Red: no PR, 1 holds finding, the group stays open. Default: gate. With neither,
//             the flow opens no PR.
//   setup     optional; a command every agent runs once in a fresh worktree before any test or gate.
//   max_load  optional; a positive number: the load average per core. Before each new task starts, 1
//             first-try agent reads uptime and the CPU count; above max_load, no task starts until it
//             drops. With no max_load, no load agent runs. With a remote runtime, no load agent runs either: the load
//             is the load of the workflow host, and the runtime sets where agents run.
//   cpus      optional; the CPU count. The slot cap: the runtime's concurrency, else min(16, cpus - 2).
//             With a remote runtime the cap is the runtime's concurrency alone (null: no cap).
//   review_every optional; a positive integer, default 6: the landings 1 batched review reads.
//   rules, answers, runtime: as in wave.
// Findings: a worker reports each problem outside its task in findings (kind, severity, minutes). 1 agent at
// a time searches the open findings: on a match it votes (1 comment naming the task and the minutes lost,
// and a +1 reaction); else it files 1 issue with the labels kind:<kind> and sev:<severity>. A major or minor
// finding never delays a landing. A holds finding (main would break) gets exactly 1 fix agent at once, on
// the group branch; no landing of that group runs until the fixer ends. Other groups land on.
// Reviews: each landing gets 1 diff review (the diff_reviewer tier) of its merge; each review_every landings
// get 1 blind batched review (the reviewer tier) of their diffs together, and the landings left at the end
// get 1 more. A review files nothing and holds nothing: its findings go to the finding agent as a worker's
// do, and only a holds finding takes the landing lane of its group, with 1 fix agent. No landing waits on a
// review; a group ships only after the diff reviews of its landings end.
// Order (x-transitions): planned -> briefed -> claimed -> building -> built -> integrated. A task that
// waits on a lease stays planned. Each landing closes the task issue and prunes its branch and worktree.

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
// LEAD_REQUEST: the first line of every agent prompt. asLead puts it there.
const LEAD_REQUEST = 'This task is the lead\'s request in this workflow run; it is not a reply to any chat message you may see. Do the task as briefed.'
const asLead = (prompt) => `${LEAD_REQUEST}\n${prompt}`
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
// tests/workflows.js checks every transition and metrics row this workflow writes against the contract.

// Contract shapes: copies of $defs brief, report, merge, brief_check, remote, queue, load, group_pr,
// finding and landing_review in plugin/contract/sdlc.schema.json, with $ref inlined. A workflow cannot import a file.
// tests/workflows.js fails when a copy drifts.
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
        red: { type: 'array', items: { type: 'string' }, description: 'Each failing test that is red on the base too (the wave passes that list), by name as the runner prints it. Only such tests may fail when passed is true' },
      },
    },
    gate: {
      type: 'object',
      required: ['command', 'line', 'passed'],
      properties: {
        command: { type: 'string' },
        line: { type: 'string', description: 'The last output line of the gate' },
        passed: { type: 'boolean' },
        red: { type: 'array', items: { type: 'string' }, description: 'Each failing check that is red on the base too, by name as the runner prints it. Only such checks may fail when passed is true' },
      },
    },
    round: { type: 'integer', minimum: 0, description: '0 for the first build, 1 or more for a rework round' },
    escalation: { type: 'string', description: 'Set when status is escalated. Stop and ask; do not guess.' },
    unverified: { type: 'array', items: { type: 'string' }, description: 'Each test folder or suite you did not run that may use your change. Empty when you ran them all. Do not write \'not verified\' in notes instead.' },
    extra_files: { type: 'array', items: { type: 'string' }, description: 'Every file the worker edited outside its own file list. The integrator checks each against the tasks beside it that are not merged yet.' },
    findings: {
      type: 'array',
      description: 'Each problem outside the task that cost the worker time or would break main, classified. Empty or absent when none. The workflow searches the open findings and votes on a match; the worker files nothing.',
      items: {
        type: 'object',
        required: ['kind', 'severity', 'title', 'evidence', 'minutes'],
        properties: {
          kind: { type: 'string', enum: ['bug', 'convergence', 'test-gap', 'perf', 'design-question', 'feel', 'docs'] },
          severity: { type: 'string', enum: ['holds', 'major', 'minor'], description: 'holds only when main would break: a red gate, a crash, data loss, a broken save, a shipped feature that stops working' },
          title: { type: 'string', minLength: 1 },
          evidence: { type: 'string', minLength: 1, description: 'What a second reader can check: the command, its last output line, the file' },
          minutes: { type: 'integer', minimum: 0, description: 'The minutes the problem cost this worker' },
        },
      },
    },
    browser_s: { type: 'number', minimum: 0, description: 'Seconds the browser test runs of this agent took; 0 when none' },
    lock_wait_s: { type: 'number', minimum: 0, description: 'Seconds this agent waited for a machine-wide browser lock before them; 0 when none' },
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
    red: { type: 'array', items: { type: 'string' }, description: 'A wave merge: each failing test of the oracle or the gate that is red on the base too, by name as the runner prints it. Only such tests may fail when oracle_passed is true' },
    reproved: { type: 'boolean', description: 'A wave merge: false when the merge had no conflict and the merged tree is the tree the worker proved, so only the gate ran; true when the oracle ran again' },
    reworked: { type: 'array', items: { type: 'string' }, description: 'Parts the sub-lead had to fix' },
    scaffold: { type: 'object', required: ['deleted', 'kept', 'test'], description: 'The scaffold step of a wave merge, after the oracle passed: the scaffold tests deleted, those kept, and the check run without them.', properties: { deleted: { type: 'array', items: { type: 'string' } }, kept: { type: 'array', items: { type: 'string' } }, test: { type: 'object', required: ['command', 'line', 'passed'], properties: { command: { type: 'string' }, line: { type: 'string', description: 'The last output line, or not run' }, passed: { type: 'boolean', description: 'True only when a check ran and passed' } } } } },
    escalation: { type: 'string' },
    base_red: { type: 'object', required: ['kind', 'check', 'line', 'tip'], description: 'A wave merge that is red, but not by the task: kind base when the same check is red on the pre-merge tip too, kind infra when the check could not run (a harness, tool or machine error, not a test result). Empty when the red is the task\'s.', properties: { kind: { type: 'string', enum: ['base', 'infra'] }, check: { type: 'string', description: 'The red check command' }, line: { type: 'string', description: 'Its last output line on the pre-merge tip, or the infra error' }, tip: { type: 'string', pattern: '^[0-9a-f]{40}$', description: 'The full SHA of the pre-merge tip of the target branch' } } },
    browser_s: { type: 'number', minimum: 0, description: 'Seconds the browser test runs of this agent took; 0 when none' },
    lock_wait_s: { type: 'number', minimum: 0, description: 'Seconds this agent waited for a machine-wide browser lock before them; 0 when none' },
    closed: { type: 'boolean', description: 'A wave merge: true when this merge closed the task issue, after the merge was validated and pushed; false when it closed nothing' },
    pruned: { type: 'boolean', description: 'A wave merge: true when the merged task branch is deleted on the remote and its worktree removed; the converge: each chain branch. Only a branch that is an ancestor of the target' },
    pruned_branch: { type: 'string', description: 'The branches deleted on the remote, space-separated; empty when none' },
    kept: { type: 'array', items: { type: 'string' }, description: 'Each issue, branch or worktree the close step kept, and why, 1 line each' },
    reach: { type: 'array', description: 'A wave task merge with oracle.reach: each test folder outside the focused oracle that references a changed file or class name, the reach command run for it, and whether it passed. A red not on the base is the task\'s.', items: { type: 'object', required: ['dir', 'command', 'passed'], properties: { dir: { type: 'string' }, command: { type: 'string' }, passed: { type: 'boolean' } } } },
    gone: { type: 'array', items: { type: 'string' }, description: 'A wave task merge: each path the merge deleted or renamed away (git diff --name-status -M: the path of a D line, the old path of an R line), nothing else; empty when none' },
    notes: { type: 'string' },
    at: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$', description: 'UTC time when the agent finished, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock.' },
  },
}

const briefCheckSchema = {
  type: 'object',
  description: "The check of a brief before a task gets a worker. missing: each asked path of its Files list that is not on the commit its branch starts from nor on its target branch; a missing path sends the task back to a brief-writer. hits: each symbol or path the brief removes, and the files on the target branch that still reference it; a hit outside the task's files, or in an oracle file the task does not own, stops the task for the lead.",
  required: ['tasks'],
  properties: {
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['task', 'missing', 'hits'],
        properties: {
          task: { type: 'string' },
          missing: { type: 'array', items: { type: 'string' }, description: 'The asked paths that do not exist; empty when all exist or none was asked' },
          hits: {
            type: 'array',
            description: '1 entry per removed symbol or path; empty when nothing was asked',
            items: {
              type: 'object',
              required: ['symbol', 'files'],
              properties: {
                symbol: { type: 'string' },
                files: { type: 'array', items: { type: 'string' }, description: 'The files on the target branch that contain the symbol; empty when none' },
              },
            },
          },
        },
      },
    },
  },
}

const remoteSchema = {
  type: 'object',
  description: 'What an earlier run of the same graph left on the remote, read before a wave starts. wave skips a task whose merge commit is there and resumes a task whose branch is there.',
  required: ['merges', 'heads'],
  properties: {
    merges: { type: 'array', items: { type: 'string' }, description: 'The subject of each merge commit since the base on the branches the prompt names, verbatim' },
    heads: {
      type: 'array',
      description: 'Each named branch that is on the remote, with its head',
      items: {
        type: 'object',
        required: ['branch', 'sha'],
        properties: {
          branch: { type: 'string' },
          sha: { type: 'string', pattern: '^[0-9a-f]{40}$' },
        },
      },
    },
  },
}


const queueSchema = {
  type: 'object',
  description: 'The ready, claimed issues a flow runs, in the order they start. Each lands in its group branch: 1 per parent issue, named <parent>-<slug>.',
  required: ['tasks'],
  properties: {
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['issue', 'parent', 'group', 'tier', 'files', 'oracle'],
        properties: {
          issue: { type: 'integer', minimum: 1 },
          parent: { type: 'integer', minimum: 1 },
          group: { type: 'string', pattern: '^[0-9]+-[a-z0-9-]+$', description: 'The group branch of the parent: <parent>-<slug>' },
          tier: { type: 'string', enum: ['bounded', 'judgment', 'lead'] },
          files: { type: 'array', items: { type: 'string' }, description: 'The files the task leases from its start to its landing' },
          oracle: oracleSchema,
          body: { type: 'string', description: 'The issue body, verbatim' },
          finding: {
            type: 'object',
            description: 'Set when the issue is a queued finding. The flow takes queued findings holds first, then in priority order (x-severity-weights[severity] x votes x minutes, at least 1 minute) in the queue places findings hold; ready issues keep their places.',
            required: ['severity', 'votes', 'minutes'],
            properties: {
              kind: { type: 'string', enum: ['bug', 'convergence', 'test-gap', 'perf', 'design-question', 'feel', 'docs'] },
              severity: { type: 'string', enum: ['holds', 'major', 'minor'] },
              votes: { type: 'integer', minimum: 1 },
              minutes: { type: 'integer', minimum: 0 },
            },
          },
        },
      },
    },
  },
}

const loadSchema = {
  type: 'object',
  description: 'The load of the machine before a flow starts an agent: the 1-minute load average and the CPU count.',
  required: ['load', 'cpus'],
  properties: {
    load: { type: 'number', minimum: 0, description: 'The 1-minute load average, as uptime prints it' },
    cpus: { type: 'integer', minimum: 1, description: 'The count of online CPUs' },
  },
}

const groupPrSchema = {
  type: 'object',
  description: 'The ship step of a flow group branch, once every task of its parent has landed: the default branch merged in by a merge commit, the full suite run once on that head, and on green 1 PR into the default branch that closes the parent and merges itself on green. open: the sub-issues of the parent that are still open; any open sub-issue means no PR.',
  required: ['group', 'sha', 'suite', 'pr', 'auto_merge', 'open'],
  properties: {
    group: { type: 'string' },
    sha: { type: 'string', pattern: '^[0-9a-f]{40}$', description: 'The full SHA of the group head the full suite ran on' },
    suite: {
      type: 'object',
      required: ['command', 'line', 'passed'],
      properties: {
        command: { type: 'string' },
        line: { type: 'string', description: 'The last output line of the full suite, or the merge or harness error' },
        passed: { type: 'boolean', description: 'True only when the full suite ran and exited 0' },
      },
    },
    pr: { type: 'string', description: 'The URL of the group PR; empty when none was opened' },
    auto_merge: { type: 'boolean', description: 'True when gh pr merge --auto --merge exited 0 on the PR' },
    open: { type: 'array', items: { type: 'string' }, description: 'The open sub-issues of the parent, as #N; empty when all are closed' },
    escalation: { type: 'string', description: 'Set when the full suite is red or the merge of the default branch has a conflict' },
    at: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$', description: 'UTC time when the agent finished, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock.' },
  },
}

const findingSchema = {
  type: 'object',
  description: '1 classified finding, filed once as an issue with the labels kind:<kind> and sev:<severity>. Before filing, the agent searches the open findings; on a match it votes instead of filing. Priority = x-severity-weights[severity] x votes x minutes (at least 1). Severity holds: main would break (a red gate, a crash, data loss, a broken save, a shipped feature that stops working); only holds stops a landing, and it gets 1 fix agent.',
  required: ['kind', 'severity', 'title', 'evidence', 'url', 'minutes', 'voted', 'votes'],
  properties: {
    kind: { type: 'string', enum: ['bug', 'convergence', 'test-gap', 'perf', 'design-question', 'feel', 'docs'] },
    severity: { type: 'string', enum: ['holds', 'major', 'minor'] },
    title: { type: 'string', minLength: 1 },
    evidence: { type: 'string', minLength: 1, description: 'What a second reader can check: the command, its last output line, the SHA' },
    url: { type: 'string', description: 'The URL of the finding issue, or of the open finding it voted on; empty when the filing failed' },
    minutes: { type: 'integer', minimum: 0, description: 'The minutes lost to the problem: the filing and every vote, summed' },
    voted: { type: 'boolean', description: 'True when an open finding matched and the agent voted on it (1 comment naming its task and the minutes lost, and a +1 reaction) instead of filing a new issue' },
    votes: { type: 'integer', minimum: 1, description: 'The votes on the finding now: 1 for the filing plus 1 per vote comment' },
  },
}

const landingReviewSchema = {
  type: 'object',
  description: 'A review of flow landings: a diff review of 1 landing (diff_reviewer tier), or a blind batched review of the last args.review_every landings (reviewer tier). The review files nothing and holds nothing: the flow files or votes each finding, and only a holds finding gets 1 fix agent on its group branch.',
  required: ['landings', 'findings'],
  properties: {
    landings: { type: 'array', minItems: 1, items: { type: 'string' }, description: 'The task ids of the landings the review read' },
    findings: {
      type: 'array',
      description: 'Each problem the review found in those landings, classified. Empty when none.',
      items: {
        type: 'object',
        required: ['task', 'kind', 'severity', 'title', 'evidence', 'minutes'],
        properties: {
          task: { type: 'string', description: 'The task id of the landing the problem is in; 1 of landings' },
          kind: { type: 'string', enum: ['bug', 'convergence', 'test-gap', 'perf', 'design-question', 'feel', 'docs'] },
          severity: { type: 'string', enum: ['holds', 'major', 'minor'], description: 'holds only when main would break: a red gate, a crash, data loss, a broken save, a shipped feature that stops working' },
          title: { type: 'string', minLength: 1 },
          evidence: { type: 'string', minLength: 1, description: 'What a second reader can check: the file and line, or the command and its last output line' },
          minutes: { type: 'integer', minimum: 0, description: 'The minutes the problem cost the reviewer; 0 when it cost none' },
        },
      },
    },
  },
}

// ---- Setup
if (!args.repo || !args.base || !args.base.ref || !args.base.sha) throw new Error('flow needs args.repo and args.base: { ref, sha } of the default branch')
const queueArg = args.queue
if (!(Array.isArray(queueArg) && queueArg.length > 0) && !(typeof queueArg === 'string' && queueArg.trim() !== '')) {
  throw new Error('flow needs args.queue: the ready issues ($defs queue tasks), or a gh command that lists them')
}
// ---- shared helpers: begin
// Written once here; node tests/workflows.js --write copies this block into flow.js. A difference between
// the two files is a hook each file defines itself: onBase, filesBeside, redText, extraAsk, staleSkip,
// briefOf and STALE. isoSeconds, know, resetup, badSha, verify, doNotTouch, workerPrompt, makeWave and
// staleAfter are written only here.
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
// newest: the latest time any agent reported. A transition takes it.
let newest = args.started_at
function know(at) {
  const t = isoSeconds(at)
  if (t !== null && t > isoSeconds(newest)) newest = at
}
// resetup(where): the setup sentence for a step after a merge. It runs even when the worktree exists already.
const resetup = (where) => (args.setup ? `Run the setup command again in ${where}, even though the worktree exists: the merge can move files and leave a stale cache (skip it when you aborted the merge). Run it before any oracle or gate command: ${args.setup}. If it fails, report that error in escalation and stop. ` : '')
const FULL_SHA = new RegExp(reportSchema.properties.sha.pattern)
// badSha: a report SHA that is no commit: not 40 hex characters, or a placeholder of zeros.
const badSha = (sha) => !FULL_SHA.test(sha) || /^0+$/.test(sha)
// verify: why the lead refuses a worker report for task (or part) id on branch, or '' when it accepts it.
function verify(r, id, branch) {
  if (!r) return 'the worker returned nothing'
  if (r.status !== 'done') return `the worker escalated: ${r.escalation || 'no question given'}`
  if (r.task !== id) return `the report names task ${r.task}, not ${id}`
  if (r.branch !== branch) return `the report names branch ${r.branch}, not ${branch}`
  if (badSha(r.sha)) return `the report SHA ${r.sha} is not a full SHA`
  if (!r.test.passed) return `the focused test is red: ${r.test.line}`
  const own = notBase(r.test.red)
  if (own.length > 0) return `the focused test is red: ${own.join(', ')}${onBase}`
  if (args.gate) {
    if (!r.gate) return `the gate was not run: report gate for ${args.gate}`
    if (!r.gate.passed) return `the gate is red: ${r.gate.line}`
    const gateOwn = notBase(r.gate.red)
    if (gateOwn.length > 0) return `the gate is red: ${gateOwn.join(', ')}${onBase}`
  }
  return ''
}
// doNotTouch(id): the files of the tasks beside id. A worker may edit any other file its outcome needs.
const doNotTouch = (id) => [...new Set(filesBeside(id))]
// workerPrompt: the file list is intent, not a fence (rule: "File lists" in AGENTS-AND-MODELS.md). avoid is
// the files of the tasks that can run at the same time. An oracle file in the list is the worker's to edit.
function workerPrompt({ id, what, text, branch, makeLine, files, avoid, test, oracleFiles, round }) {
  const locked = oracleFiles.filter((f) => overlap([f], files).length === 0)
  return `${what}
${text}
${remote ? `Build on branch ${branch}. Where you work is yours to choose (a worktree is one way). Set the branch up first with this exact line:` : `Work in your own worktree ${root}/${branch}. Make it first with this exact line:`}
${makeLine}${setupLine(dirOf(branch))}
Your files: ${files.join(', ')}. You may also edit any other file your outcome needs; list each one in extra_files.
Do not touch these files, because tasks that run at the same time own them: ${avoid.join(', ') || 'none'}.
Your test files are yours to edit, oracle files in your list included; do not weaken an existing assertion unless the brief says so.${locked.length > 0 ? ` Do not edit these oracle files, which you do not own: ${locked.join(', ')}.` : ''}
Run only the focused test: ${test}.${workerGate}${redText('yours')} ${TIMES} Commit small and push after every commit: git push -q -u origin ${branch}. Open no pull request. Merge nothing.${extraAsk}
For a how-to question under a decided design (which file, which mechanism, which token), pick the option that keeps the issue's decisions and the repo rules, build it, and name the choice in notes. Escalate only a question the issue does not answer about what the user sees, hears or reads, or when the test cannot pass without a file you must not touch. Quote where in the issue you looked. To escalate, push what you have and set status to escalated.
Report task ${id}, round ${round}, branch ${branch}, the full 40-character SHA of your last push (run git rev-parse HEAD after it; never a placeholder such as zeros), the test command with its last output line, and extra_files. When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`
}
// makeWave: step 1 of a merge into target: its worktree, made once, then fast-forwarded to the remote.
const makeWave = (target) => (remote
  ? `1. Get branch ${target} at the head of origin/${target} in your checkout: git fetch -q origin, create the branch from origin/${target} if you have none (where you work is yours to choose), then git merge -q --ff-only origin/${target}${setupLine(`${dirOf(target)}, only when you make it here`, '   ')}`
  : `1. If the worktree ${root}/${target} is missing, make it: git fetch -q origin && git worktree add -B ${target} ${root}/${target} origin/${target}${setupLine(`${root}/${target}, only when you make it here`, '   ')}
   Otherwise, in it: git fetch -q origin && git merge -q --ff-only origin/${target}`)
const ABSORBED = /\babsorb|\balready (did|done|built|covered|covers)|nothing left/i
const esc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const names = (text, x) => new RegExp(`(^|[^\\w-])${esc(x)}(?![\\w-])`).test(text)
// namesTask(line, x): a line of notes names task x as a task. An id with a digit or a hyphen ('x-1', 'x2')
// is rare in prose and matches as a bare word. Any other id ('a', 'ui') is also an English word, so it
// matches only as a reference: 'task a', 'tasks #a', or the id after #, a backtick or a quote.
const namesTask = (line, x) => (/[\d-]/.test(x) ? names(line, x) : new RegExp(`(\\btasks? #?[\`"']?|[\`"'#])${esc(x)}(?![\\w-])`, 'i').test(line))
function staleAfter(id, gone, notes) {
  const absorbed = ids.filter((x) => x !== id && notes.split('\n').some((l) => ABSORBED.test(l) && namesTask(l, x)))
  if (gone.length === 0 && absorbed.length === 0) return
  for (const x of ids) {
    const s = tasks[x]
    if (x === id || staleSkip(x, id)) continue
    const text = briefOf(x)
    const paths = gone.filter((f) => overlap([f], filesOf(x)).length > 0 || text.includes(f))
    const done = absorbed.filter((y) => y === x || names(text, y))
    const why = [...(paths.length > 0 ? [`the ${STALE.by} of ${id} deleted or renamed ${paths.join(', ')}`] : []), ...(done.length > 0 ? [`the notes of ${id} say it absorbed ${done.join(', ')}`] : [])]
    if (why.length === 0) continue
    s.stale = [...(s.stale || []), ...why]
    log(`${x}: ${why.join('; ')}; its brief goes back to a brief-writer ${STALE.when}`)
  }
}
// ---- shared helpers: end
if (isoSeconds(args.started_at) === null) {
  throw new Error('flow needs args.started_at: the ISO UTC time now (date -u +%Y-%m-%dT%H:%M:%SZ). The workflow cannot read the clock.')
}
if (args.cpus !== undefined && !(Number.isInteger(args.cpus) && args.cpus > 0)) throw new Error('args.cpus must be the CPU count of the machine, a positive integer')
if (args.max_load !== undefined && !(typeof args.max_load === 'number' && args.max_load > 0)) throw new Error('args.max_load must be a positive number: the load average per core above which no new task starts')
if (args.review_every !== undefined && !(Number.isInteger(args.review_every) && args.review_every > 0)) throw new Error('args.review_every must be a positive integer: the landings 1 batched review reads')
if (args.converge_gate !== undefined && (typeof args.converge_gate !== 'string' || args.converge_gate.trim() === '')) {
  throw new Error('args.converge_gate must be a command string: the full suite, run once on each group branch before its PR')
}
if (args.setup !== undefined && (typeof args.setup !== 'string' || args.setup.trim() === '')) {
  throw new Error('args.setup must be a command string: it runs once in each fresh worktree, before any test or gate')
}
if (args.setup) log(`setup: ${args.setup}; each agent runs it once in each fresh worktree before any test or gate`)
const claimedAt = args.claimed_at || {}

const repo = args.repo
const base = args.base
const runtime = args.runtime || CLAUDE_RUNTIME
const solo = args.claims === 'solo'
const SOLO = 'solo: 1 lead, no claim lock'
const claims = solo ? {} : args.claims || {}
const claimOf = (id) => (solo ? SOLO : claims[id])
const root = runtime.worktree_root
// remote: the runtime may run each agent anywhere (an agent_types entry can be a dispatcher that returns the same
// schema). A prompt then names the work (branch, base, brief, oracle, gate, report) and no path under root; a
// worktree is one way to build on branch B from base S, not the contract. dirOf names a checkout; mine starts
// a follow-up sentence about the worker's own checkout; newBranch is the line that makes a branch from a base.
const remote = runtime.remote === true
const dirOf = (name) => (remote ? `your checkout of ${name}` : `${root}/${name}`)
const mine = (name) => (remote ? `Your checkout of ${name}` : `Your worktree ${root}/${name}`)
const newBranch = (branch, base) => (remote ? `git fetch -q origin; build on branch ${branch}, made from ${base}` : `git fetch -q origin && git worktree add -b ${branch} ${root}/${branch} ${base}`)
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const answers = args.answers || {}
const gate = args.gate ? ` Then run the gate: ${args.gate}.` : ''
const setupText = (where) => (args.setup ? ` Run the setup command once in ${where}, before any test, oracle or gate command: ${args.setup}. If it fails, report that error in escalation and stop.` : '')
const setupLine = (where, indent = '') => (args.setup ? `\n${indent}${setupText(where).trim()}` : '')
const spawn = (role, tier) => {
  const t = runtime.tiers[tier]
  return { model: t.model, ...(t.effort && { effort: t.effort }), agentType: runtime.agent_types[role] }
}
// A reach run that is red is red for the landing too, whatever oracle_passed says. flow has no base-red
// list: any red test of a report or a merge is the task's.
// notBase: flow has no base-red list, so every red test of a report is the task's. onBase adds no words.
const notBase = (red) => red || []
const onBase = ''
const merged = (m) => Boolean(m && m.oracle_passed && !m.escalation && (m.red || []).length === 0 && !(m.reach || []).some((x) => !x.passed))

const tasks = {}
// call: 1 agent for 0 or more tasks. Each task counts the agent. A failed spawn returns null.
async function call(owners, prompt, opts) {
  for (const id of [].concat(owners)) tasks[id].agents++
  try {
    return await agent(asLead(prompt), opts)
  } catch (e) {
    log(`${opts.label}: ${e.message}`)
    return null
  }
}

// ---- Queue: the entries as given, or the answer of 1 read-only agent that runs the gh command.
let entries = Array.isArray(queueArg) ? queueArg : null
if (!entries) {
  phase('Check')
  const q = await call([], `List the ready, claimed issues of ${repo} for a flow. Read only: edit, commit and push nothing, open no pull request.
1. Run exactly: ${queueArg}
2. For each issue it lists, in that order, read gh issue view <n> --repo ${repo} --json body,labels and report: issue; body, verbatim; parent, from its "Parent: #N" line; group, the branch <parent>-<slug>, where slug is the parent title in lower case, at most 3 words joined by -; files, the paths of its Files part; oracle: command, the command of its Proof or Oracle part, files, the test files that command runs, uncovered, each behaviour of its Done when that no test covers; tier, its tier: label (bounded, judgment or lead), else judgment.
   An issue with a sev: label is a finding: report finding: severity, from its sev: label; kind, from its kind: label; votes, 1 plus the count of its comments that start with "+1 from "; minutes, the "Minutes lost: N" of its body plus the "cost N minutes" of each such comment.
3. Leave out an issue with no parent or no Proof part.${rules}`,
  { label: 'queue', phase: 'Check', schema: queueSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  if (!q) throw new Error(`the queue agent returned nothing for: ${queueArg}`)
  entries = q.tasks
}
const QUEUE_REQUIRED = queueSchema.properties.tasks.items.required
const queueProblems = entries.flatMap((e, i) => {
  const at = `queue entry ${e && e.issue !== undefined ? e.issue : `#${i + 1}`}`
  if (!e || typeof e !== 'object') return [`${at}: is not an object`]
  const out = QUEUE_REQUIRED.filter((k) => e[k] === undefined).map((k) => `${at}: missing ${k}`)
  if (e.oracle) out.push(...ORACLE_REQUIRED.filter((k) => e.oracle[k] === undefined).map((k) => `${at}: oracle is missing ${k}`))
  if (typeof e.group === 'string' && !e.group.startsWith(`${e.parent}-`)) out.push(`${at}: group ${e.group} is not <parent>-<slug> of parent ${e.parent}`)
  return out
})
for (const d of new Set(dupes(entries.map((e) => e && e.issue)))) queueProblems.push(`queue: issue ${d} is not unique`)
if (queueProblems.length > 0) throw new Error(`args.queue does not match the contract queue shape: ${queueProblems.join('; ')}`)
// priority: severity weight x votes x minutes lost (at least 1 minute, so a vote with no time still counts).
// Holds findings start first whatever their priority: main breaks until they land.
const WEIGHTS = contract['x-severity-weights']
const priority = (f) => (WEIGHTS[f.severity] || 0) * Math.max(1, f.votes || 1) * Math.max(1, f.minutes || 0)
const holdsFirst = (a, b) => (b.severity === 'holds') - (a.severity === 'holds') || priority(b) - priority(a)
const queued = entries.filter((e) => e.finding).sort((a, b) => holdsFirst(a.finding, b.finding))
if (queued.length > 0) {
  let k = 0
  entries = entries.map((e) => (e.finding ? queued[k++] : e))
  log(`findings in priority order: ${queued.map((e) => `#${e.issue} ${e.finding.severity} ${priority(e.finding)}`).join(', ')}`)
}

for (const e of entries) {
  const id = String(e.issue)
  tasks[id] = {
    task: { ...e, id }, state: 'planned', tier: e.tier, group: e.group, branch: `${e.issue}-${e.group.slice(String(e.parent).length + 1)}`,
    plan: null, agents: 0, merges: [], reports: [], notes: [], reason: '', integratedAt: null, order: 0, startNo: 0,
  }
}
// Queue order, not Object.keys: an object lists integer keys in numeric order.
const ids = entries.map((e) => String(e.issue))
const groups = [...new Set(ids.map((id) => tasks[id].group))]
const issueOf = (t) => `issue #${t.issue} of ${repo}`
// The slot cap: the runtime's concurrency, else (Claude Code) min(16, CPUs - 2) tasks at once.
const CLAUDE_CAP_MAX = 16
const CLAUDE_CAP_SPARE = 2
const cap = runtime.concurrency || (!remote && runtime.provider === 'claude' && args.cpus ? Math.max(1, Math.min(CLAUDE_CAP_MAX, args.cpus - CLAUDE_CAP_SPARE)) : null)
const slots = cap || ids.length
log(cap ? `slot cap: ${cap} task${cap === 1 ? '' : 's'} at once; ${ids.length} in the queue; ${groups.length} group branch${groups.length === 1 ? '' : 'es'}` : `slot cap: ${remote ? 'set by the runtime' : 'unknown (pass args.cpus)'}; ${ids.length} tasks may start at once`)
// The load is the load of the workflow host. A remote runtime sets where agents run, so the flow reads none.
if (args.max_load) log(remote ? 'max_load: not read on the workflow host; the runtime sets where agents run' : `max_load: ${args.max_load} per core; no task starts above it`)
if (solo) log(SOLO)

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
  log(`${id}: ${s.state}: ${reason}`)
}

// ---- Leases: a task holds its files from its start to its landing or its stop.
const leases = new Map()
const filesOf = (x) => (tasks[x].plan || tasks[x].task).files
// filesBeside(id): the files the other running tasks lease (the list doNotTouch gives a worker).
const filesBeside = (id) => [...leases.entries()].filter(([x]) => x !== id).flatMap(([, f]) => f)
// leasedBy(id, files): the first other task whose lease overlaps files, or undefined.
const leasedBy = (id, files) => [...leases.keys()].find((x) => x !== id && overlap(files, leases.get(x)).length > 0)
function clashStep(id, report) {
  const open = [...leases.keys()].filter((x) => x !== id)
  if (open.length === 0) return ''
  return `
   The worker reports these files outside its list: ${(report.extra_files || []).join(', ') || 'none'}. Check them, and every other file in git diff --cached --name-only, against these tasks, which run beside it and have not landed:
${open.map((x) => `   - ${x}: ${leases.get(x).join(', ')}`).join('\n')}
   A changed file in one of those lists is a clash: run git merge --abort and set escalation to "clash: <file> is owned by task <id>". Any other file outside the list is fine.`
}

// ---- Brief: just in time, when the task takes a slot.
const READY_PARTS = { outcome: /^outcome/i, 'done when': /^done[ -]when/i, files: /^files/i, proof: /^(proof|oracle)/i, decisions: /^decisions?\b/i }
const headingsOf = (body) => body.split('\n').map((l) => (/^\s*(?:#{1,6}\s+(.+)|\*\*([^*]+)\*\*|([A-Za-z][\w -]{0,30}):)/.exec(l) || []).slice(1).find(Boolean)).filter(Boolean).map((h) => h.trim())
const bodyOf = (id) => tasks[id].task.body
const missingParts = (id) => Object.keys(READY_PARTS).filter((p) => !(p === 'decisions' && answers[id]) && !headingsOf(bodyOf(id)).some((h) => READY_PARTS[p].test(h)))
const answersText = (id) => (answers[id] ? `\nThe lead's answers. They win over every other line of this brief:\n${answers[id]}` : '')
const answersRule = (id) => (answers[id] ? `\nThe lead answered these questions. Your text may not contradict or narrow them:\n${answers[id]}` : '')
const NO_WIDEN = 'Keep the files of the issue. A file you add that another running task leases makes the flow run the 2 tasks one after the other.'

async function brief(id, stale) {
  const s = tasks[id]
  const t = s.task
  const own = { files: t.files, oracle: t.oracle, tier: t.tier }
  const body = bodyOf(id)
  const missing = body ? missingParts(id) : []
  if (!stale && body && missing.length === 0) {
    log(`${id}: the brief is the issue body as written`)
    return { ...own, brief: `${body}${answersText(id)}` }
  }
  const ask = stale
    ? `The brief is stale: ${stale.join('; ')}. Write the whole brief again for the code on origin/${s.group} now: name only paths that exist there (git ls-tree -r --name-only origin/${s.group}), or that the task creates (mark each such path "creates"). Keep the outcome. The brief as written:\n${(s.plan && s.plan.brief) || body || '(none)'}`
    : body
    ? `The issue lacks these parts of a ready issue: ${missing.join(', ')}. Write only those parts. Do not restate or change the rest of the issue. The issue as written:\n${body}`
    : 'Write what a worker needs to finish with no judgment call: the files, each signature exactly, each trap quoted from the source, the oracle and its focused command.'
  const b = await call(
    id,
    `Write the brief for ${issueOf(t)}, task ${id}. Read only: edit, commit and push nothing.
The code lands on ${s.group}: read origin/${s.group} after git fetch -q origin.
The queue says: tier ${t.tier}; files ${t.files.join(', ')}; oracle ${t.oracle.command} (files: ${t.oracle.files.join(', ') || 'none'}; uncovered: ${t.oracle.uncovered.join('; ') || 'none'}).
${ask}
Inventory the oracle files and list each behaviour they do not cover. Tier it: bounded only when the oracle covers every behaviour; judgment when 1 or more is uncovered; lead when the step-up rule in AGENTS-AND-MODELS.md applies. ${NO_WIDEN}${answersRule(id)}${rules}`,
    { label: `brief ${id}`, phase: 'Brief', schema: briefSchema, ...spawn('brief_writer', ROLE_TIER.brief_writer) },
  )
  if (!b) return null
  const tier = higherTier(t.tier, b.tier)
  if (!body || stale) return { brief: `${b.brief}${answersText(id)}`, files: b.files, oracle: b.oracle, tier, removes: b.removes || [] }
  return {
    brief: `${body}\n\n${b.brief}${answersText(id)}`,
    files: missing.includes('files') ? b.files : t.files,
    oracle: missing.includes('proof') ? b.oracle : t.oracle,
    removes: b.removes || [],
    tier,
  }
}

// toFind: the paths of files that must exist already: not a path the brief marks "creates" in its sentence.
const CREATES = /\b(creates?|new file)\b/i
const toFind = (files, text) => files.filter((f) => !text.split(/\n|\.\s/).some((l) => l.includes(f) && CREATES.test(l)))
// briefCheck: 1 read-only agent over entries {id, paths, removes, brief}. Returns id -> {missing, hits}, or null.
async function briefCheck(list, label, at) {
  const ask = (e) => [
    e.paths.length > 0 ? ` at ${heads[tasks[e.id].group]} and origin/${tasks[e.id].group}: ${e.paths.join(' ')}` : '',
    e.removes === null
      ? `\n  removes: read them from the brief: each symbol or path its Done when or the lead's answers rename or delete with no alias left. Grep each on origin/${tasks[e.id].group}.\n  Brief:\n${e.brief.split('\n').map((l) => `    ${l}`).join('\n')}`
      : e.removes.length > 0 ? `\n  removes, grep on origin/${tasks[e.id].group}: ${e.removes.join(' ')}` : '',
  ].join('')
  const bc = await call(list.map((e) => e.id), `Check the brief of each task below, before any worker starts. Read only: edit, commit and push nothing, open no pull request.
1. git fetch -q origin
2. paths (after "at"): a path exists when git cat-file -e <commit>:<path> or git cat-file -e origin/<target>:<path> exits 0 (a directory counts). Else it is missing.
3. removes: for each symbol or path, run git grep -n -F -- <symbol> origin/<target> (add -w for an identifier) and report the files with a hit.
Report 1 entry per task: task; missing, the paths that do not exist ([] when all exist or none was asked); hits, 1 per symbol or path with its files ([] when nothing is removed).
Tasks:
${list.map((e) => `- ${e.id}${ask(e)}`).join('\n')}${rules}`,
    { label, phase: at, schema: briefCheckSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  if (!bc) {
    log(`${label}: the agent returned nothing`)
    return null
  }
  const out = new Map()
  for (const e of list) {
    const r = (bc.tasks || []).find((x) => x.task === e.id) || {}
    out.set(e.id, {
      missing: (r.missing || []).filter((f) => e.paths.includes(f)),
      hits: (r.hits || []).filter((h) => (e.removes === null || e.removes.includes(h.symbol)) && (h.files || []).length > 0),
    })
  }
  return out
}

// writeBrief: the brief of id, checked. A missing path or a stale mark sends it to a brief-writer once;
// stale again, the task stops with no worker. Returns null when the task stopped.
async function writeBrief(id) {
  const s = tasks[id]
  const fail = (reason) => { stop(id, 'escalated', reason); return null }
  let stale = s.stale
  s.stale = null
  let rebriefs = stale ? 1 : 0
  for (;;) {
    const plan = await brief(id, stale)
    if (!plan) return fail('the brief-writer returned nothing')
    const badBrief = tierMeaning(`brief ${id}`, plan)
    if (badBrief.length > 0) return fail(badBrief.join('; '))
    const removes = plan.removes === undefined ? null : plan.removes
    const paths = toFind(plan.files, plan.brief)
    if (paths.length > 0 || removes === null || removes.length > 0) {
      const got = await briefCheck([{ id, paths, removes, brief: plan.brief }], `check ${id}`, 'Brief')
      if (!got) return fail('the brief check returned nothing: its paths and the callers of what it removes are unchecked, so no worker starts')
      const { missing, hits } = got.get(id)
      if (missing.length > 0) {
        if (rebriefs > 0) return fail(`the new brief still names paths that do not exist: ${missing.join(', ')}`)
        rebriefs++
        stale = [`these paths of its Files list do not exist on ${s.group}: ${missing.join(', ')}`]
        log(`${id}: ${stale[0]}; it goes back to a brief-writer`)
        continue
      }
      const gone = hits.map((h) => h.symbol)
      const outside = hits.map((h) => ({ ...h, files: h.files.filter((f) => !gone.includes(f) && overlap([f], plan.files).length === 0) })).filter((h) => h.files.length > 0)
      if (outside.length > 0) return fail(`removes ${outside.map((h) => h.symbol).join(', ')}: callers outside the files of ${id}: ${outside.map((h) => `${h.symbol} in ${h.files.join(', ')}`).join('; ')}. Widen the files or re-split.`)
    }
    const reach = s.task.oracle.reach
    s.plan = reach && !plan.oracle.reach ? { ...plan, oracle: { ...plan.oracle, reach } } : plan
    s.tier = plan.tier
    return s.plan
  }
}

// ---- Build
const TIMES = 'When a test run drives a browser, time it: report browser_s, the seconds the browser runs took, and lock_wait_s, the seconds you waited for a machine-wide browser lock first (0 when none).'
const FINDINGS_ASK = `Report each problem outside your task that cost you time or would break main in findings: kind, 1 of the kinds the report shape lists; severity holds only when main would break (a red gate, a crash, data loss, a broken save, a shipped feature that stops working), else major or minor; title; evidence a second reader can check; and minutes, the minutes it cost you. File no issue: the flow searches the open findings and votes on a match.`
// redText and extraAsk: workerPrompt hooks. flow has no base-red list; its worker prompt asks for findings.
const redText = () => ''
const extraAsk = `\n${FINDINGS_ASK}`
const workerGate = args.gate ? ` Then run the gate once: ${args.gate}. Fix what it reports in your files, or escalate. Report the gate in gate: command, passed, last output line.` : ''
// startTask: the line that makes the worktree at the head of the group branch the flow knows now. A task
// whose branch is on the remote resumes from it and merges that head.
function startTask(id) {
  const s = tasks[id]
  const head = heads[s.group]
  if (remote) return `git fetch -q origin; build on branch ${s.branch}, ${s.resume ? `reset to ${s.resume}, with ${head} merged into it (git merge -q --no-edit ${head})` : `made from ${head}`}`
  return s.resume
    ? `git fetch -q origin && git worktree add -B ${s.branch} ${root}/${s.branch} ${s.resume} && git -C ${root}/${s.branch} merge -q --no-edit ${head}`
    : newBranch(s.branch, head)
}
const QUOTED = /["“][^"”\n]{3,}["”]|^\s*>/m
async function work(owners, prompt, opts, branch) {
  let r = await call(owners, prompt, opts)
  if (r && r.status === 'done' && badSha(r.sha)) {
    log(`${opts.label}: the report SHA ${r.sha} is no commit; it goes back to the worker once`)
    r = (await call(owners, `${prompt}

You reported the SHA ${r.sha}, which is no commit. ${mine(branch)} exists: continue there. Push the branch if it is not pushed, run git rev-parse HEAD, and report that full 40-character SHA. Never report a placeholder.`, { ...opts, label: `${opts.label} sha` })) || r
  }
  if (!r || r.status !== 'escalated' || QUOTED.test(r.escalation || '')) return r
  log(`${opts.label}: the escalation quotes no line of the issue; it goes back to the worker once`)
  return call(owners, `${prompt}

You escalated once already, with no quote from the issue: ${r.escalation || 'no question given'}
${mine(branch)} exists: continue there and do not make it again (if it is gone: ${remote ? `git fetch -q origin and build on branch ${branch} from origin/${branch} again` : `git fetch -q origin && git worktree add ${root}/${branch} origin/${branch}`}). If the issue answers the question, or it is a how-to question, build it and name the choice in notes. Else escalate again and quote the line of the issue where you looked.`, { ...opts, label: `${opts.label} again` })
}
function build(id, plan) {
  const s = tasks[id]
  log(`${id}: starts from ${s.group} at ${heads[s.group]}${s.resume ? `, resuming ${s.resume}` : ''}`)
  return work(
    id,
    workerPrompt({ id, what: `Build ${issueOf(s.task)}.`, text: `${plan.brief}${s.resume ? `\nThis branch resumes earlier work on the task from ${s.resume}. Read git log ${heads[s.group]}..HEAD first and continue that work; do not redo it.` : ''}`, branch: s.branch, makeLine: startTask(id), files: plan.files, avoid: doNotTouch(id), test: plan.oracle.command, oracleFiles: plan.oracle.files, round: 0 }),
    { label: `build ${id}`, phase: 'Build', schema: reportSchema, ...spawn('worker', plan.tier) },
    s.branch,
  )
}

// ---- Land: 1 landing at a time on each group branch; 2 groups land at the same time.
// heads: the head of each group branch, from the remote check, then from each landing.
const heads = {}
const queues = {}
function serial(target, run) {
  const p = (queues[target] || Promise.resolve()).then(run)
  queues[target] = p.catch(() => null)
  return p
}
let mergeCount = 0
const EXIT_CODE = ' A check is green only when it exits 0: read its exit code, not its last output line.'
const proofStep = (id, report, target) => `4. ${resetup(dirOf(target))}If step 2 had no conflict and git write-tree prints the tree of ${report.sha} (git rev-parse ${report.sha}^{tree}), the merged tree is the tree the worker proved: do not run the oracle again; keep the worker's proof (${report.test.line}) and set reproved false. Otherwise run the oracle of the task: ${tasks[id].plan.oracle.command}, and set reproved true.${gate}${reachStep(id)}${EXIT_CODE}`
const reachStep = (id) => {
  const reach = tasks[id].plan.oracle.reach
  return reach ? ` Then, in every case, run reach: list the test folders that reference a changed file (git diff --name-only HEAD) or a changed class name, drop the folders of the oracle files (${tasks[id].plan.oracle.files.join(', ') || 'none'}), and run ${reach} for each remaining folder with {dir} replaced by it. Report each run in reach: dir, command, passed (true when it exits 0). Step 5 decides on it.` : ''
}
// keepBranch: a branch the flow never deletes: a group branch, the base, main.
const keepBranch = (b) => [...groups, 'main', base.ref].includes(b)
function claimGuard(id, branches) {
  if (solo) return 'This is a solo run: there is no other claim to check.'
  const issue = tasks[id].task.issue
  const other = ids.filter((x) => x !== id && claims[x]).map((x) => claims[x])
  return `No other open claim may name ${branches.join(' or ')}: read gh issue view ${issue} --repo ${repo} --json comments -q '.comments[].body', and the claim comments of the other tasks of this flow (${other.join(' ') || 'none'}). When an open claim for a task other than ${id} names one of these branches, close nothing and delete nothing: add "<branch>: named by the open claim <url>" to kept.`
}
function pruneStep(id, report, target, n) {
  const s = tasks[id]
  const branches = [report.branch]
  const kept = branches.filter(keepBranch)
  if (kept.length > 0) {
    log(`${id}: ${kept.join(' ')} is a group or base branch: the landing closes and deletes nothing`)
    return `\n${n}. Close nothing and delete nothing: ${kept.join(' ')} is a branch the workflow keeps. Report closed false, pruned false, pruned_branch "" and kept ["${kept.join(' ')}: kept branch"].`
  }
  const proof = `Oracle: ${s.plan.oracle.command}: <its last output line in step 4, or the worker's proof "${report.test.line}" when you kept it>.${args.gate ? ` Gate: ${args.gate}: <its last output line>.` : ''}`
  return `
${n}. Close and prune, only when the landing is validated: step 5 was green and the push of step ${n - 1} printed no error. When the merge is red, aborted or not pushed, close nothing and delete nothing: report closed false and pruned false. ${claimGuard(id, branches)}
   (a) gh issue close ${s.task.issue} --repo ${repo} --comment "Merged ${report.branch} into ${target} at <the full SHA of the push>. ${proof}" Report closed true when it exits 0.
   (b) git fetch -q origin. For each of these branches: ${branches.join(' ')}. When it is on the remote and git merge-base --is-ancestor origin/<branch> origin/${target} exits 0, delete it: git push -q origin --delete <branch>. Name the exact branch; never a pattern. Else keep it: add "<branch>: not merged into ${target}" to kept. Never delete ${target}, another group branch or main.
   (c) For each of those branches: ${remote ? 'remove its local checkout when you made one, and git branch -D <branch>, each only when present. Keep your checkout of ' + target + '.' : 'git worktree remove --force ' + root + '/<branch> and git branch -D <branch>, each only when present. Keep the worktree ' + root + '/' + target + '.'}
   Report pruned true only when (b) and (c) ran for every branch, and pruned_branch: the branches deleted, space-separated. A failed close or delete does not fail the landing: keep oracle_passed true, set closed or pruned false and say why in kept.`
}
// ---- Base red: a red gate that is red on the pre-merge tip too holds only that group branch.
const holds = {}
const heldGroup = {}
const notTask = (m, before) => {
  const b = m && m.base_red
  if (!b || !args.gate || b.check !== args.gate || badSha(b.tip) || b.tip !== before) return false
  return b.kind === 'base' || (b.kind === 'infra' && m.escalation === b.line)
}
function holdOf(target, b) {
  const key = `${target}\n${b.check}`
  if (!holds[key]) {
    const fix = b.kind === 'base' ? `fix ${b.check} on ${target} (red at ${b.tip} before the merge)` : `fix the harness or machine error of ${b.check}`
    holds[key] = { kind: b.kind, target, check: b.check, line: b.line, tip: b.tip, owner: 'lead', next: `${fix}, then run the flow again`, holds: [] }
    heldGroup[target] = holds[key]
    log(`base red on ${target}: ${b.kind}: ${b.check}: ${b.line}; no task of ${target} starts or lands until the lead fixes it`)
  }
  return holds[key]
}
function hold(id, h, why) {
  h.holds.push(id)
  tasks[id].held = h
  stop(id, null, `held by ${h.kind} red on ${h.target}: ${h.check}: ${h.line}${why ? `; ${why}` : ''}`)
}
const baseRedStep = args.gate ? `When the oracle is red, the red is the task's: leave base_red out. When only the gate (${args.gate}) is red, find whose red it is: note the pre-merge tip (git rev-parse HEAD), run git merge --abort, then run the gate once on that tip. When it is red there too, set base_red: kind base, check ${args.gate}, its last output line on the tip, and the tip SHA. When the gate could not run at all on the merged tree (a harness, tool or machine error, not a test result) and could not run on the tip either, with the same error, set base_red: kind infra, check ${args.gate}, that error as line (the same text as escalation), and the tip SHA. When the gate ran green on the tip, the red is the task's: leave base_red out. ` : 'The red is the task\'s: leave base_red out. '
function integrate(id, report) {
  const s = tasks[id]
  const target = s.group
  const prompt = (resolve, tip) => `You land task ${id} in the group branch ${target} of ${repo}. Merge 1 branch: ${report.branch} at ${report.sha}.
${makeWave(target)}
2. In it: git merge --no-ff --no-commit ${report.sha}${clashStep(id, report)}
3. On a conflict: ${resolve ? 'resolve it when both sides are clear; keep the behaviour of both. When the 2 sides change the same contract in 2 ways, run git merge --abort and set escalation to the files.' : 'run git merge --abort and set escalation to the conflicting files. Do not resolve it.'}
${proofStep(id, report, target)}
5. Green (the gate passed, the oracle when it ran${s.plan.oracle.reach ? ', and every reach run passed' : ''}): git commit -q -m "Merge ${report.branch} into ${target}". Report branch ${target}, merged [${report.branch}] and oracle_passed true.
   Red${s.plan.oracle.reach ? ' (a reach red counts: name its folder and last output line in escalation)' : ''}: report oracle_passed false and the last output line in escalation. ${baseRedStep}Then run git merge --abort when the merge is still in progress. Stop: commit nothing, push nothing, close nothing and delete nothing.
6. git push -q origin ${target}. Report the full 40-character SHA of the push. Then report in gone each path the merge deleted or renamed away: git diff --name-status -M ${tip} <the merge commit of step 5>: the path of each D line and the old path of each R line, nothing else; [] when none.${pruneStep(id, report, target, 7)}
Keep ${remote ? `your checkout of ${target}` : `the worktree ${root}/${target}`} for the next landing. Open no pull request. Never touch main. ${TIMES}
When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`
  const run = async () => {
    if (heldGroup[target]) return { ok: false, base: heldGroup[target], reason: `${target} is held by base red` }
    const before = heads[target]
    let m = await call(id, prompt(false, before), { label: `merge ${id}`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', FIRST_TRY.integrator) })
    if (!merged(m)) {
      m = await call(id, prompt(true, before), { label: `merge ${id} step-up`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) })
    }
    s.merges.push(m)
    if (!merged(m) && notTask(m, before)) return { ok: false, base: m.base_red, reason: `${m.base_red.kind} red on ${target}: ${m.base_red.check}: ${m.base_red.line}` }
    if (!merged(m)) return { ok: false, reason: m ? m.escalation || 'the merge is red' : 'the integrator returned nothing' }
    if (badSha(m.sha)) return { ok: false, reason: `the landing SHA ${m.sha} is not a full SHA` }
    heads[target] = m.sha
    s.order = ++mergeCount
    know(m.at)
    s.integratedAt = isoSeconds(m.at) === null ? newest : m.at
    staleAfter(id, m.gone || [], `${report.notes || ''}\n${m.notes || ''}`)
    if (m.closed) s.closedAt = s.integratedAt
    if (m.pruned) s.pruned = true
    if (m.closed || m.pruned || (m.kept || []).length > 0) log(`${id}: ${m.closed ? `issue #${s.task.issue} closed; ` : ''}${m.pruned ? `deleted ${m.pruned_branch}` : 'no branch deleted'}${(m.kept || []).length > 0 ? `; kept ${m.kept.join('; ')}` : ''}`)
    return { ok: true, from: before, to: m.sha }
  }
  return serial(target, run)
}
// staleAfter: a landing that deleted or renamed a path, or whose notes say it absorbed a task, marks each
// task of the same group that has not started; its brief goes back to a brief-writer when it starts.
// staleAfter is shared; these hooks are flow's own: staleSkip(x, id), briefOf(x) and the 2 words of the log.
const staleSkip = (x, id) => { const s = tasks[x]; return Boolean(s.before || s.reason || s.state !== 'planned' || s.group !== tasks[id].group || s.startNo > 0) }
const briefOf = (x) => bodyOf(x) || ''
const STALE = { by: 'landing', when: 'when it starts' }

// ---- Findings: 1 agent at a time searches the open findings of the kind; on a match it votes (1 comment
// naming who found it and the minutes lost, and a +1 reaction), else it files 1 issue labelled kind:<kind>
// and sev:<severity>. 1 at a time, so 2 reports of 1 problem in this flow make 1 issue and 1 vote.
const FINDINGS_LANE = '#findings'
const findings = []
function fileFinding(f, who, label, why, g) {
  return serial(FINDINGS_LANE, async () => {
    const minutes = f.minutes || 0
    const a = await call([], `File or vote on 1 finding on ${repo}. Edit, commit and push nothing, and open no pull request.
The finding: kind ${f.kind}, severity ${f.severity}, title ${JSON.stringify(f.title)}. Evidence: ${f.evidence}. It cost ${who} ${minutes} minutes.
1. Search the open findings: gh issue list --repo ${repo} --state open --label kind:${f.kind} --limit 100 --json number,title,url,body. A match is an open finding of the same problem: the same failing check, file or symptom, in other words.
2. On a match, vote and file nothing: gh issue comment <n> --repo ${repo} --body "+1 from ${who}: cost ${minutes} minutes. Evidence: ${f.evidence}", then gh api repos/${repo}/issues/<n>/reactions -f content=+1. Report voted true; url, the URL of the match; votes, 1 plus the count of its comments that start with "+1 from" (yours included); minutes, the "Minutes lost: N" of its body plus the "cost N minutes" of each such comment.
3. No match: make the labels when missing: gh label create kind:${f.kind} --repo ${repo} --force and gh label create sev:${f.severity} --repo ${repo} --force. Then gh issue create --repo ${repo} --label kind:${f.kind} --label sev:${f.severity} --title ${JSON.stringify(f.title)} --body "Severity ${f.severity}: ${why}

Evidence: ${f.evidence}
Minutes lost: ${minutes}"
   Report voted false, votes 1, minutes ${minutes}, and url: the issue URL it printed ("" when it failed).
4. Report kind ${f.kind}, severity ${f.severity}, and the title and evidence as given.${rules}`,
    { label, phase: 'Integrate', schema: findingSchema, ...spawn('integrator', FIRST_TRY.integrator) })
    const row = { group: g, by: who, ...(a || { kind: f.kind, severity: f.severity, title: f.title, evidence: f.evidence, url: '', minutes, voted: false, votes: 1 }) }
    row.priority = priority(row)
    findings.push(row)
    log(`${label}: ${row.voted ? `voted on ${row.url} (${row.votes} votes)` : row.url ? `filed ${row.url}` : 'the filing failed'}: ${row.severity} ${row.kind}: ${row.title}; priority ${row.priority}`)
    return row
  })
}

// ---- Holds: a holds finding gets exactly 1 fix agent (1 per finding URL, else per group and title). It runs
// in the landing lane of its group, so no landing of that group runs until it ends; other groups land on.
// Green: the fix is on the group branch. Not green: the group is held for the lead.
const fixers = {}
const fixes = []
const heldByFinding = []
let fixCount = 0
function fixOnce(g, f) {
  const key = f.url || `${g}\n${f.title}`
  if (fixers[key]) {
    log(`${g}: ${f.url || f.title} has its fix agent already`)
    return null
  }
  return (fixers[key] = true)
}
async function runFix(g, f, who, test) {
  if (heldGroup[g]) return false
  const n = ++fixCount
  const id = `fix-${n}`
  const branch = `${g}-fix-${n}`
  log(`${g}: holds finding ${f.url || f.title}: 1 fix agent on ${branch}; no task of ${g} lands until it ends`)
  const r = await work(
    [],
    workerPrompt({
      id,
      what: `Fix 1 holds finding on the group branch ${g} of ${repo} at ${heads[g]}: main would break if it took this branch. No task of ${g} lands until you end.`,
      text: `${f.title}\nEvidence: ${f.evidence}\nFound by ${who}${f.url ? `; the finding is ${f.url}` : ''}. Fix exactly this, nothing else. Keep 1 path for each behaviour. When the test${args.gate ? ' and the gate are' : ' is'} green, also push the fix to the group branch as a fast-forward: git push -q origin HEAD:${g}. Never push to ${base.ref}.`,
      branch, makeLine: newBranch(branch, heads[g]),
      files: ['the files the evidence names'], avoid: doNotTouch(id), test, oracleFiles: [], round: 0,
    }),
    { label: `fix ${g}`, phase: 'Integrate', schema: reportSchema, ...spawn('worker', 'lead') },
    branch,
  )
  const refused = verify(r, id, branch)
  fixes.push({ group: g, finding: f.url || f.title, branch, ...(refused ? { reason: refused } : { sha: r.sha }) })
  if (!refused) {
    know(r.at)
    heads[g] = r.sha
    log(`${g}: the fix agent fixed ${f.url || f.title} at ${r.sha}`)
    return true
  }
  const h = { kind: 'holds', target: g, check: f.title, line: f.evidence, tip: heads[g], owner: 'lead', next: `fix ${f.url || f.title} on ${g} (the fix agent: ${refused}), then run the flow again`, holds: [] }
  heldGroup[g] = h
  heldByFinding.push(h)
  log(`${g}: the fix agent did not fix ${f.url || f.title}: ${refused}; no task of ${g} lands until the lead fixes it`)
  return false
}

// ---- Ship: when every task of a group has landed (in this flow or an earlier one), 1 integrator merges
// the default branch into the group branch (a merge commit), runs args.converge_gate (the full suite) once
// on that head and, on green, opens 1 PR into the default branch that closes the parent and sets it to
// merge itself on green. Red: it pushes nothing and opens no PR; 1 first-try agent files 1 holds finding,
// and the group stays open. Main merges only a green group. Several groups ship at the same time.
const SUITE = args.converge_gate || args.gate
const shipped = {}
const ships = []
const groupDone = (g) => ids.filter((id) => tasks[id].group === g).every((id) => tasks[id].before || tasks[id].state === 'integrated')
const parentOf = (g) => tasks[ids.find((id) => tasks[id].group === g)].task.parent
function shipWhenDone(g) {
  if (shipped[g] || !groupDone(g)) return
  if (!SUITE) {
    shipped[g] = Promise.resolve()
    log(`${g}: every task landed; no converge_gate or gate, so the flow opens no PR: the lead runs the full suite and opens it`)
    return
  }
  // The diff reviews of the group end first, so a holds finding of theirs takes the lane before the ship.
  shipped[g] = Promise.all(diffReviews[g] || []).then(() => serial(g, () => ship(g)))
}
async function ship(g) {
  const parent = parentOf(g)
  const own = ids.filter((id) => tasks[id].group === g)
  if (heldGroup[g]) {
    ships.push({ group: g, parent, sha: heads[g], suite: { command: SUITE, line: 'not run: the group is held', passed: false }, pr: '', auto_merge: false })
    log(`${g}: no PR: the group is held by ${heldGroup[g].kind} red; ${heldGroup[g].next}`)
    return
  }
  const p = await call(own, `Ship the group branch ${g} of ${repo}: every task of parent issue #${parent} has landed on it. Push nothing to ${base.ref}.
${makeWave(g)}
2. Open sub-issues: gh api repos/${repo}/issues/${parent}/sub_issues --jq '.[] | select(.state == "open") | .number'. Report each as #N in open. When open is not empty, stop here: push nothing, open no PR; report sha (git rev-parse HEAD), suite {command "${SUITE}", line "not run: open sub-issues", passed false}, pr "", auto_merge false, and escalation "open sub-issues: <them>".
3. Merge the default branch in, by a merge commit, never a rebase: git merge --no-ff --no-edit origin/${base.ref}. On a conflict: git merge --abort, push nothing, open no PR, and report suite passed false with line and escalation "merge conflict with ${base.ref}: <files>".
4. ${resetup(dirOf(g))}Run the full suite once on that head: ${SUITE}. Do not run it again to hope for a pass.${EXIT_CODE} Report sha (git rev-parse HEAD) and suite: command, its last output line, passed.
5. Red: push nothing and open no PR. Run git reset -q --hard origin/${g}. Report pr "", auto_merge false, and in escalation the last output line, then each failing test with its file path.
6. Green: git push -q origin ${g}. If gh pr list --repo ${repo} --head ${g} --state open --json url -q '.[0].url' prints a URL, that is the PR. Else open it: gh pr create --repo ${repo} --base ${base.ref} --head ${g} --title "<the title of issue #${parent}>" --body "Closes #${parent}

Tasks, each closed when it landed: ${own.map((id) => `#${tasks[id].task.issue}`).join(' ')}.
Full suite: ${SUITE}: <its last output line> at <the SHA>."
   Then: gh pr merge <the PR> --repo ${repo} --auto --merge. Report pr (the URL) and auto_merge true when that exits 0.
Keep ${remote ? `your checkout of ${g}` : `the worktree ${root}/${g}`}. Never push to ${base.ref}, never merge into it yourself. ${TIMES}
When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`,
  { label: `ship ${g}`, phase: 'Ship', schema: groupPrSchema, ...spawn('integrator', ROLE_TIER.integrator) })
  if (p) know(p.at)
  const green = Boolean(p && p.suite && p.suite.passed && (p.open || []).length === 0)
  const row = { group: g, parent, sha: p && !badSha(p.sha) ? p.sha : heads[g], suite: p ? p.suite : { command: SUITE, line: 'the integrator returned nothing', passed: false }, pr: green ? p.pr || '' : '', auto_merge: Boolean(green && p.pr && p.auto_merge) }
  ships.push(row)
  if (green && row.pr) {
    heads[g] = row.sha
    log(`${g}: full suite green at ${row.sha}; PR ${row.pr}${row.auto_merge ? ', set to merge itself on green' : '; auto-merge did not set: the lead sets it'}`)
    return
  }
  if (p && (p.open || []).length > 0) {
    row.reason = `parent #${parent} has open sub-issues: ${p.open.join(', ')}`
    log(`${g}: no PR: ${row.reason}`)
    return
  }
  if (green) {
    row.reason = 'the full suite is green, but no PR was opened'
    log(`${g}: ${row.reason}; the lead opens it`)
    return
  }
  row.reason = `the full suite is red on ${g}: ${(p && p.escalation) || row.suite.line}`
  log(`${g}: no PR: ${row.reason}; the group stays open`)
  const f = await fileFinding({ kind: 'bug', severity: 'holds', title: `holds: ${SUITE} is red on ${g}`, evidence: `${SUITE}: ${(p && p.escalation) || row.suite.line} at ${row.sha}`, minutes: 0 },
    `the ship of ${g}`, `finding ${g}`, `the full suite is red on the group branch ${g} of parent #${parent}, so the group opens no PR and main does not take it.`, g)
  if (fixOnce(g, f)) row.fix = (await runFix(g, f, `the ship of ${g}`, SUITE)) ? `fixed at ${heads[g]}; the next flow run ships ${g}` : 'the fix agent did not fix it'
}

// ---- Reviews: they run beside the landings, each in its own lane, so no landing waits on one.
const REVIEW_EVERY = args.review_every || 6
const REVIEW_ASK = `Read only: edit, commit and push nothing, file no issue, and open no pull request. Report landings: the task ids above. Report each problem in findings: task, the landing it is in; kind, 1 of the kinds the review shape lists; severity holds only when main would break (a red gate, a crash, data loss, a broken save, a shipped feature that stops working), else major or minor; title; evidence a second reader can check (the file and line, or the command and its last output line); minutes, the minutes it cost you (0 when none). Report [] when you find none. The flow searches the open findings and votes on a match.`
const landings = []
const diffReviews = {}
const reviews = []
let batchCount = 0
function reviewLanding(l) {
  landings.push(l)
  const p = serial(`#review ${l.id}`, () => review(`review ${l.id}`, [l], `the diff review of task ${l.id}`, `Review the landing of task ${l.id} on the group branch ${l.group} of ${repo}: git fetch -q origin, then read git diff ${l.from} ${l.to}. Look for a bug, a second path for 1 behaviour, a missing test, a slow path or a wrong doc in that diff.`, l.id, spawn('diff_reviewer', ROLE_TIER.diff_reviewer)))
  ;(diffReviews[l.group] = diffReviews[l.group] || []).push(p)
  if (landings.length % REVIEW_EVERY === 0) batchReview(landings.slice(-REVIEW_EVERY))
}
// batchReview: 1 blind review of the landings together, at the reviewer tier. It sees the diffs only.
function batchReview(list) {
  const n = ++batchCount
  return serial('#batch', () => review(`review batch ${n}`, list, `the batched review ${n}`, `Review blind the last ${list.length} landing${list.length === 1 ? '' : 's'} of this flow on ${repo}, together. Read only the code and these diffs, after git fetch -q origin. Do not read the task issues, the worker reports, the pull requests or the findings already filed, and do not ask who built what.
${list.map((l) => `- ${l.id} on ${l.group}: git diff ${l.from} ${l.to}`).join('\n')}
Look for what 1 diff hides: 2 paths for 1 behaviour, 1 contract changed 2 ways, a test gap across the landings, a slow path, a wrong doc.`, [], spawn('reviewer', ROLE_TIER.reviewer)))
}
// review: 1 reviewer; each finding goes to the finding lane. A holds finding takes the landing lane of its
// group at once, so its 1 fix agent runs before the next landing of that group.
async function review(label, list, who, ask, owners, how) {
  const a = await call(owners, `${ask}\n${REVIEW_ASK}${rules}`, { label, phase: 'Review', schema: landingReviewSchema, ...how })
  const row = { review: label, landings: list.map((l) => l.id), findings: 0 }
  reviews.push(row)
  if (!a) {
    row.reason = 'the reviewer returned nothing'
    log(`${label}: ${row.reason}`)
    return
  }
  for (const [i, f] of (a.findings || []).entries()) {
    const l = list.find((x) => x.id === f.task)
    const g = l ? l.group : ''
    row.findings++
    const filed = fileFinding(f, who, `finding ${label} ${i + 1}`, `found by ${who} in the landing of task ${f.task}${g ? ` on ${g}` : ''}.`, g)
    if (f.severity !== 'holds') continue
    if (!l) {
      log(`${label}: the holds finding ${f.title} names ${f.task}, not a landing it read; it gets no fix agent`)
      continue
    }
    serial(g, async () => {
      const h = await filed
      return fixOnce(g, h) && runFix(g, h, who, `the command of the evidence (${h.evidence})`)
    })
  }
  log(`${label}: ${row.findings} finding${row.findings === 1 ? '' : 's'} on ${row.landings.join(' ')}`)
}

// ---- 1 task: brief, build, land. It holds its lease until it returns.
const running = new Map()
let startCount = 0
async function runTask(id) {
  const s = tasks[id]
  const plan = await writeBrief(id)
  if (!plan) return
  // A brief that widens the files into a task that started earlier waits until that task lands.
  const widened = [...new Set([...s.task.files, ...plan.files])]
  leases.set(id, widened)
  for (let x = leasedBy(id, widened); x && tasks[x].startNo < s.startNo; x = leasedBy(id, widened)) {
    s.notes.push(`waited for ${x}: both lease ${overlap(widened, leases.get(x)).join(', ')}`)
    log(`${id}: the brief widens into the lease of ${x}; it waits until ${x} lands`)
    await running.get(x)
  }
  move(id, 'briefed')
  move(id, 'claimed', { reason: claimOf(id) })
  move(id, 'building')
  const r = await build(id, plan)
  const refused = verify(r, id, s.branch)
  if (refused) return stop(id, 'escalated', refused)
  know(r.at)
  if (r.notes) s.notes.push(r.notes)
  s.reports.push(r)
  move(id, 'built')
  // A major or minor finding files in the background: it never delays the landing. A holds finding files
  // first, then its 1 fix agent takes the landing lane of the group ahead of this landing.
  for (const [i, f] of (r.findings || []).entries()) {
    const filed = fileFinding(f, `task ${id}`, `finding ${id} ${i + 1}`, `found by task ${id} (${issueOf(s.task)}) on ${s.group}.`, s.group)
    // The lane slot is taken now, before the filing answers, so no landing of the group slips in ahead.
    if (f.severity === 'holds') serial(s.group, async () => {
      const h = await filed
      return fixOnce(s.group, h) && runFix(s.group, h, `task ${id}`, `the command of the evidence (${h.evidence})`)
    })
  }
  const m = await integrate(id, r)
  if (!m.ok) return m.base ? hold(id, m.base.holds ? m.base : holdOf(s.group, m.base)) : stop(id, 'escalated', m.reason)
  move(id, 'integrated')
  log(`${id}: landed on ${s.group} at ${heads[s.group]}`)
  reviewLanding({ id, group: s.group, from: m.from, to: m.to })
  shipWhenDone(s.group)
}

// ---- Check: 1 agent makes each group branch that is not on the remote, at the base, and reads what an
// earlier flow left there: a task whose merge commit is on its group branch is skipped; a task whose
// branch is on the remote resumes from its head.
const canStart = (id) => Boolean(claimOf(id))
const MERGE_SUBJECT = /^Merge (\S+) into \S+$/
for (const g of groups) heads[g] = base.sha
if (ids.some(canStart)) {
  phase('Check')
  const named = [...groups, ...ids.map((id) => tasks[id].branch)]
  const rm = await call([], `Read what an earlier flow left on the remote of ${repo}, and make the group branches. Edit and commit nothing, open no pull request, and push nothing but step 2.
1. git fetch -q origin
2. Make each of these group branches that is not on the remote, at the base: git push -q origin ${base.sha}:refs/heads/<branch>. Then git fetch -q origin.
   ${groups.join(' ')}
3. For each of these branches that is on the remote, report its head (git rev-parse origin/<branch>). Leave out a branch that is not there:
   ${named.join(' ')}
4. For each group branch, report the subject of each merge commit on it since the base, verbatim: git log --merges --format=%s ${base.sha}..origin/<branch>
Report heads (branch and full SHA) and merges (the subjects).${rules}`,
    { label: 'remote check', phase: 'Check', schema: remoteSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  if (!rm) log('remote check: the agent returned nothing; the flow starts each group branch at the base')
  const done = new Set((rm ? rm.merges : []).map((m) => (MERGE_SUBJECT.exec(m) || [])[1]).filter(Boolean))
  const head = Object.fromEntries((rm ? rm.heads : []).filter((h) => !badSha(h.sha)).map((h) => [h.branch, h.sha]))
  for (const g of groups) if (head[g]) heads[g] = head[g]
  for (const id of ids) {
    const s = tasks[id]
    if (done.has(s.branch)) {
      s.before = true
      log(`${id}: landed on ${s.group} by an earlier flow; skipped`)
    } else if (head[s.branch]) {
      s.resume = head[s.branch]
      log(`${id}: resumes from its branch head ${s.resume}`)
    }
  }
}

// ---- Load: with args.max_load, 1 first-try agent reads the load before each new task starts. Above it,
// the next read waits LOAD_WAIT_S first; after LOAD_TRIES reads above it, no new task starts.
const LOAD_WAIT_S = 60
const LOAD_TRIES = 30
let loadTries = 0
let loadStuck = ''
async function loadOk() {
  const again = loadTries > 0
  const l = await call([], `Read the load of this machine. Edit, commit and push nothing, open no pull request.${again ? ` The load was above ${args.max_load} per core: wait first with sleep ${LOAD_WAIT_S}.` : ''}
Run uptime and report load: its 1-minute load average, the first of the 3 numbers after "load average". Report cpus: the count of online CPUs (getconf _NPROCESSORS_ONLN; when it fails, sysctl -n hw.ncpu).`,
  { label: 'load', phase: 'Build', schema: loadSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  const perCore = l && l.cpus > 0 ? l.load / l.cpus : null
  if (perCore !== null && perCore <= args.max_load) {
    loadTries = 0
    return true
  }
  loadTries++
  log(`load: ${perCore === null ? 'unknown' : `${Math.round(perCore * 100) / 100} per core`}, above ${args.max_load}: no new task starts (read ${loadTries} of ${LOAD_TRIES})`)
  if (loadTries >= LOAD_TRIES) loadStuck = `the load stayed above ${args.max_load} per core for ${LOAD_TRIES} reads`
  return false
}

// ---- The loop: start the next task in queue order whose files no running task leases, when a slot is
// free and the load allows; else wait until a running task lands or stops.
phase('Build')
const pending = ids.filter((id) => !tasks[id].before)
for (const id of pending.filter((x) => !canStart(x))) stop(id, null, 'no claim: the lead posts 1 claim comment per issue and passes its URL in args.claims')
for (let i = pending.length - 1; i >= 0; i--) if (!canStart(pending[i])) pending.splice(i, 1)
while (pending.length > 0 || running.size > 0) {
  const next = running.size < slots && !loadStuck ? pending.find((id) => !heldGroup[tasks[id].group] && !leasedBy(id, filesOf(id))) : undefined
  if (next !== undefined) {
    if (args.max_load && !remote && !(await loadOk())) continue
    pending.splice(pending.indexOf(next), 1)
    tasks[next].startNo = ++startCount
    leases.set(next, filesOf(next))
    const p = runTask(next)
      .catch((e) => stop(next, null, `the flow failed on the task: ${e.message}`))
      .then(() => {
        leases.delete(next)
        running.delete(next)
      })
    running.set(next, p)
    continue
  }
  if (running.size === 0) break
  await Promise.race(running.values())
}
for (const id of pending) {
  const h = heldGroup[tasks[id].group]
  if (h) hold(id, h, 'its group branch is held')
  else stop(id, null, loadStuck || 'did not start')
}
// A group whose tasks all landed in an earlier flow ships now, once.
for (const g of groups) shipWhenDone(g)
// The landings no batched review read yet get 1 more.
if (landings.length % REVIEW_EVERY > 0) batchReview(landings.slice(-(landings.length % REVIEW_EVERY)))
// Wait until every lane is idle: a finding, a fix or a ship may queue more work while the others run.
for (let lanes = []; ;) {
  const now = [...Object.values(queues), ...Object.values(shipped)]
  if (now.length === lanes.length && now.every((x, i) => x === lanes[i])) break
  lanes = now
  await Promise.all(lanes)
}

// ---- Report: 1 metrics row per task that started an agent. This runtime reports no usage.
phase('Report')
const UNAVAILABLE = 'unavailable'
const secs = (xs, k) => xs.filter(Boolean).reduce((n, x) => n + (Number(x[k]) || 0), 0)
const result = (s) => (s.state === 'integrated' ? 'merged' : s.state === 'escalated' ? 'escalated' : 'failed')
const metrics = ids
  .filter((id) => tasks[id].agents > 0)
  .map((id) => {
    const s = tasks[id]
    const sp = runtime.tiers[s.tier]
    return {
      task: id, provider: runtime.provider, tier: s.tier, model: sp.model, ...(sp.effort && { effort: sp.effort }),
      agents: s.agents, elapsed_s: Math.max(0, isoSeconds(s.integratedAt || newest) - isoSeconds(claimedAt[id] || args.started_at)),
      rework_rounds: 0, browser_s: secs([...s.reports, ...s.merges], 'browser_s'), lock_wait_s: secs([...s.reports, ...s.merges], 'lock_wait_s'), ...(s.order > 0 && { reproved: s.merges.some((m) => merged(m) && m.reproved !== false) }),
      findings: { critical: 0, major: 0, minor: 0 }, result: result(s), tokens: UNAVAILABLE, cost_usd: UNAVAILABLE,
      ...(s.closedAt && { closed_at: s.closedAt }), ...(s.pruned && s.closedAt && { pruned: true }),
    }
  })
const browser = { browser_s: secs(metrics, 'browser_s'), lock_wait_s: secs(metrics, 'lock_wait_s') }
const earlier = ids.filter((id) => tasks[id].before)
const landed = ids.filter((id) => tasks[id].state === 'integrated')
const open = ids.filter((id) => !tasks[id].before && tasks[id].state !== 'integrated')
const baseReds = Object.values(holds)
log(`${landed.length} of ${ids.length} tasks landed${earlier.length > 0 ? ` (${earlier.length} by an earlier flow)` : ''}; ${groups.map((g) => `${g} at ${heads[g]}`).join(', ')}; ${open.length} need the lead${baseReds.length > 0 ? ` (${baseReds.length} base red)` : ''}; ${ships.filter((x) => x.pr).length} group PR${ships.filter((x) => x.pr).length === 1 ? '' : 's'} open; ${findings.filter((f) => !f.voted).length} finding${findings.filter((f) => !f.voted).length === 1 ? '' : 's'} filed, ${findings.filter((f) => f.voted).length} vote${findings.filter((f) => f.voted).length === 1 ? '' : 's'}, ${fixes.length} fix agent${fixes.length === 1 ? '' : 's'}; ${reviews.length} review${reviews.length === 1 ? '' : 's'}.`)

return {
  groups: Object.fromEntries(groups.map((g) => [g, heads[g]])),
  landed,
  ...(earlier.length > 0 && { merged_before: earlier }),
  ...browser,
  ...(baseReds.length > 0 && { base_red: baseReds }),
  ships,
  findings: [...findings].sort((a, b) => b.priority - a.priority),
  fixes,
  reviews,
  ...(heldByFinding.length > 0 && { held: heldByFinding }),
  escalations: [...heldByFinding.map((h) => ({ task: h.target, state: 'fix', reason: h.next })), ...open.filter((id) => !tasks[id].held).map((id) => ({ task: id, state: tasks[id].state, reason: tasks[id].reason })), ...ships.filter((x) => x.reason).map((x) => ({ task: x.group, state: 'ship', reason: x.reason }))],
  tasks: ids.map((id) => {
    const s = tasks[id]
    return { task: id, issue: s.task.issue, group: s.group, state: s.state, tier: s.tier, branch: s.branch, notes: s.notes, reports: s.reports, merges: s.merges, ...(s.closedAt && { closed_at: s.closedAt }), ...(s.pruned && { pruned: true }), ...(s.held && { held: s.reason }) }
  }),
  metrics,
  transitions,
}
