export const meta = {
  name: 'wave',
  description: 'Run one wave of a contract graph: check each oracle, take each ready issue as its brief, build each task when its blockers are integrated, merge each green task into the wave branch 1 at a time, 1 blind review of the wave head at the end, 1 rework round, 1 metrics row per task. Opens no PR.',
  phases: ['Check', 'Brief', 'Build', 'Integrate', 'Converge', 'Review', 'Rework', 'Report'],
}

log(`wave ${args.graph ? `${args.graph.repo} ${args.graph.branch}: ${(args.graph.tasks || []).map((t) => `#${t.issue || t.id}`).join(' ')}` : 'with no args.graph'}`)

// Defaults: the issue is the brief, and 1 review runs at the end. Workers fan out; judgment runs once.
// First 1 agent reads what an earlier run left on the remote. Then, before any build, 1 agent runs each oracle in list mode: an oracle that selects 0 tests refuses
// the graph, unless the task or a task it waits on writes the oracle file. The same agent runs each oracle
// once on the base and lists the tests red there: such a test is no task's, so it stops no worker and no
// merge. A clean merge whose tree is the tree the worker proved runs only the gate. A brief that widens a task's files into a task beside it serializes the 2 tasks (logged in
// the task notes); it escalates nothing. A worker picks a how-to choice itself and names it in notes; an
// escalation with no quote from the issue goes back to the worker once. The run logs the concurrency
// cap, the CPU count and the chains at start; parallel chains run in 1 workflow (graph task field chain).
// Each metrics row has browser_s and lock_wait_s, and the run summary sums them. A red gate that is red on
// the pre-merge tip too, or could not run there with the same error, is base red: it escalates no task,
// holds only the merges it blocks and the tasks that wait on them, and the result lists it once under
// base_red. A red oracle is always the task's. A red in a rework round, or at the converge, is no hold for a
// task: the rework escalates; the converge holds as 1 base_red entry.
// args: { graph, started_at, claimed_at, claims, gate, converge_gate, regression, setup, issues, answers, review, cpus, rules,
//         lens, decisions, runtime }
//   graph     a contract graph ($defs graph in plugin/contract/sdlc.schema.json). Check it first:
//             node plugin/contract/check.js graph <file>. graph.branch is the wave branch. It must be
//             on the remote at graph.base.sha before the run: every task branch starts on it.
//             A task with spec_sha (plan pushed its spec to spec/<task id>) starts on that SHA and
//             merges the wave branch into it, so the wave branch gets the red spec tests only with the
//             task. This holds for a build and for a split. A task with no spec_sha starts on the wave
//             branch: a spec/<task id> branch on the remote is never used by name.
//             A task with resume_from (a full SHA, or a remote branch) starts on it instead, merges the
//             wave branch into it, and its worker continues that work: a re-run needs no new branch name.
//             A task with chain builds on the branch <graph.branch>-<chain> (the remote check makes it at
//             the base) and waits only on tasks of its chain; 2 chains may edit the same file. A chain task
//             may also wait on a task with no chain; a chain with such a task is cut at the wave head after
//             that task merges, not at graph.base.sha. A task with no chain that a chain waits on may not
//             wait on a chain task. When every
//             chain task has ended, 1 integrator merges the chain branches into graph.branch in the order
//             each chain first appears in graph.tasks, resolves the conflicts and runs the gate once. A
//             task with no chain builds on graph.branch; when it waits on a chain task, it starts after
//             the converge. The end review reads the converged head.
//             A task's scaffold lists its spec tests that are not keep. When the task's oracle passes on
//             the merged tree, the same integrator deletes the scaffold files that git shows as added
//             since graph.base.sha, minus the keep files of every task, in 1 commit of that merge step.
//             Then it runs the oracle over the files that stay and the gate. A red check, or no check
//             to run, keeps the files. The result reports scaffold.deleted and scaffold.kept.
//             The brief of a task: its issue body as written (args.issues) when it is ready, else the
//             graph brief. Only a task with neither, or an issue that lacks a part, gets a brief-writer,
//             and then it writes the missing parts only. A task with split runs as a split.
//             Stale briefs: a Files path missing where the task starts (and made by no task it waits on), a path a merge deleted or
//             renamed (merge gone), or a task its notes say it absorbed sends a brief back to a brief-writer once; still stale, no worker.
//             graph.fix_lane: optional; default false. When true, 1 lead-tier fix agent runs on the
//             branch <graph.branch>-fix, cut from the wave head, for a CRITICAL end-review finding, a
//             major tagged guard (a second path, duplicate store or forwarder, second mount path), or a
//             red converge gate that its rework round did not clear or that has no round left. It gets
//             the brief, reports and diff of each involved task and the finding. Its branch merges into
//             the wave branch, then the converge gate runs again. It does not count against
//             rework_limit, runs at most once per wave, and the end review does not run again after it.
//   started_at  required; ISO UTC time (the lead runs date -u +%Y-%m-%dT%H:%M:%SZ). The runtime forbids
//             Date, so the workflow reads no clock: this is its first known time.
//   claimed_at optional; task id -> ISO UTC time of the lead's claim comment. Default: started_at.
//   claims    task id -> the URL of the lead's claim comment on the task's issue (the contract
//             claim shape). The lead posts 1 claim per task before the run. A task with no claim
//             does not start, and neither does a task it blocks. 'solo': 1 lead and no claim lock
//             (no GitHub issues, or 1 person). Every task starts with no claim; the run logs it.
//   gate      optional; the per-merge fast check (keep it quick). The integrator runs it after each merge,
//             after the oracle of the task.
//   converge_gate optional; the full check (the whole unit suite, integration). It runs once on the
//             converged head: after the last merge, or after the chain converge, before the end review.
//             Red: 1 rework round on the task the failure names (the task whose files the failing test
//             covers, else the last merged), then the gate runs again; still red, or no round left, it
//             goes under escalations for the lead. The result holds converge_gate: {command, passed, line}.
//   regression optional; a command that runs the one load-bearing scenario. At the end of the wave,
//             1 agent runs it on graph.base.sha and 1 on the final wave head (2 agents, no retry).
//             Exit 0 means the scenario passes. A pass on the base and a fail on the head escalates
//             the wave. With no merge the lane is skipped. With no value nothing changes.
//   setup     optional; a command every agent runs once in a fresh worktree before any oracle, gate or
//             regression command (for example an engine import cache). The integrator also runs it again
//             in its wave worktree after each merge, before the gate, because a merge can move files and
//             leave a stale cache. The run logs the command once. With no value nothing changes.
//   issues    optional; task id -> the issue body, verbatim (gh issue view N --json body -q .body). The
//             body is ready when it has the headings Outcome, Done when, Files, Proof (or Oracle) and
//             Decisions; a ready body is the worker's brief and no brief-writer runs.
//   answers   optional; task id -> the lead's answers to the task's questions. They count as its
//             decisions, come last in every brief, and win over every other line. Answer and continue:
//             run the same graph again with the answers. A task merged by an earlier run (its merge
//             commit is on the wave branch) is skipped; a task whose branch is on the remote resumes
//             from its head, as if resume_from were set.
//   review    optional; 'end' (default): after the last merge, 1 lead-tier reviewer reads the whole
//             wave head blind and across issues. A CRITICAL or major finding opens at most 1 rework
//             round on the task merged last among its ids; minor findings return as 1 follow-up issue
//             draft (follow_up). No skeptic; a blast-radius check only for a risky task. 'batch': a
//             blind review of each REVIEW_BATCH merged results beside the build, 2 skeptics per finding
//             above minor, rework to graph.rework_limit.
//   cpus      optional; the CPU count of the machine. Claude Code runs min(16, cpus - 2) agents of 1
//             workflow at once; the run logs that cap. A runtime with its own concurrency wins. On fewer
//             than 8 CPUs with more than 3 chains, the run warns that browser runs will queue.
//   rules     optional; the repo's code rules as text, passed to every agent
//   lens      optional; paths of the repo's convention lens. Default: CONSTITUTION.md and .claude/review-lens.md.
//             Every reviewer and blast-radius prompt names them; the agent reads those that exist. [] turns it off.
//   decisions optional; the design decisions the reviewer must not report as findings
//   runtime   optional; a provider profile from plugin/contract/runtimes.json. Default: Claude.
// Close and prune: when a task merge is validated (green and pushed), the same integrator closes the task
// issue with the merge SHA and the oracle and gate lines, deletes the task branch on the remote (only an
// ancestor of the target, named by no other open claim) and removes the task worktree. After a validated
// converge it deletes each chain branch merged into the wave branch. The parent issue stays open.
// The workflow opens no pull request, merges nothing into main and deletes no other branch: never the
// wave branch or main. The lead owns the wave PR, CI and the merge, then closes the parent issues.
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
// STUB (spec 310): not implemented; the build returns `${LEAD_REQUEST}\n${prompt}`.
const asLead = (prompt) => prompt
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
          guard: { type: 'boolean', description: 'true on a major that breaks a convergence guard: a second path, duplicate store or forwarder, or a second mount path' },
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

const oracleListSchema = {
  type: 'object',
  description: 'The oracle check before a wave starts: the oracle of each task run in list mode on the commit its branch starts from, then once on the wave base. An oracle that lists and selects 0 tests refuses the graph. A test red on the base is not a task\'s.',
  required: ['tasks'],
  properties: {
    browser_s: { type: 'number', minimum: 0, description: 'Seconds the browser test runs of this agent took; 0 when none' },
    lock_wait_s: { type: 'number', minimum: 0, description: 'Seconds this agent waited for a machine-wide browser lock before them; 0 when none' },
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['task', 'command', 'listed', 'selected', 'line'],
        properties: {
          task: { type: 'string' },
          command: { type: 'string', description: 'The list-mode command that ran' },
          listed: { type: 'boolean', description: 'False when the runner has no list mode; then selected means nothing' },
          selected: { type: 'integer', minimum: 0, description: 'The count of tests the command selects' },
          line: { type: 'string', description: 'The last output line' },
          red: { type: 'array', items: { type: 'string' }, description: 'The tests that fail when the oracle runs on the wave base, by name as the runner prints it; empty when all pass' },
        },
      },
    },
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

// ---- Setup
const graph = args.graph
if (!graph || !graph.repo || !graph.branch || !graph.base || !graph.base.sha || !(graph.tasks || []).length) {
  throw new Error('wave needs args.graph: a contract graph with repo, branch, base.sha and at least 1 task')
}
const shapeProblems = taskShape(graph)
if (shapeProblems.length > 0) throw new Error(`args.graph does not match the contract task shape: ${shapeProblems.join('; ')}`)
if (isoSeconds(args.started_at) === null) {
  throw new Error('wave needs args.started_at: the ISO UTC time now (date -u +%Y-%m-%dT%H:%M:%SZ). The workflow cannot read the clock.')
}
if (args.cpus !== undefined && !(Number.isInteger(args.cpus) && args.cpus > 0)) throw new Error('args.cpus must be the CPU count of the machine, a positive integer')
const REVIEW_MODES = ['end', 'batch']
const reviewMode = args.review === undefined ? 'end' : args.review
if (!REVIEW_MODES.includes(reviewMode)) throw new Error(`args.review must be ${REVIEW_MODES.join(' or ')}, not ${args.review}`)
if (args.regression !== undefined && (typeof args.regression !== 'string' || args.regression.trim() === '')) {
  throw new Error('args.regression must be a command string: the one load-bearing scenario, run on the base SHA and on the wave head')
}
if (args.setup !== undefined && (typeof args.setup !== 'string' || args.setup.trim() === '')) {
  throw new Error('args.setup must be a command string: it runs once in each fresh worktree, before any oracle, gate or regression command')
}
if (args.converge_gate !== undefined && (typeof args.converge_gate !== 'string' || args.converge_gate.trim() === '')) {
  throw new Error('args.converge_gate must be a command string: it runs once on the converged head, before the end review')
}
if (args.setup) log(`setup: ${args.setup}; each agent runs it once in each fresh worktree before any oracle, gate or regression command`)
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
const solo = args.claims === 'solo'
const SOLO = 'solo: 1 lead, no claim lock'
const claims = solo ? {} : args.claims || {}
const claimOf = (id) => (solo ? SOLO : claims[id])
const root = runtime.worktree_root
const wave = graph.branch
const limit = graph.rework_limit
const fixLaneOn = graph.fix_lane === true
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const LENS_PATHS = args.lens === undefined ? ['CONSTITUTION.md', '.claude/review-lens.md'] : args.lens
const lens = LENS_PATHS.length > 0 ? `\nConvention lens: read ${LENS_PATHS.join(', ')} in the repo root of the checkout (skip a path that does not exist). A new mechanism that duplicates a pattern the lens catalogs is a MAJOR finding; name the existing pattern it should use.` : ''
const issues = args.issues || {}
const answers = args.answers || {}
const gate = args.gate ? ` Then run the gate: ${args.gate}.` : ''
// setupText: the setup sentence for a prompt that makes the fresh worktree where; '' with no args.setup.
// setupLine: the same sentence on a line of its own after the line that makes the worktree; '' with no args.setup.
const setupText = (where) => (args.setup ? ` Run the setup command once in ${where}, before any test, oracle, gate or regression command: ${args.setup}. If it fails, report that error in escalation and stop.` : '')
const setupLine = (where, indent = '') => (args.setup ? `\n${indent}${setupText(where).trim()}` : '')
// resetup(where): the setup sentence for a step after a merge. It runs even when the worktree exists already.
const resetup = (where) => (args.setup ? `Run the setup command again in ${where}, even though the worktree exists: the merge can move files and leave a stale cache (skip it when you aborted the merge). Run it before any oracle or gate command: ${args.setup}. If it fails, report that error in escalation and stop. ` : '')
const issueOf = (t) => (t.issue ? `issue #${t.issue} of ${graph.repo}` : `task ${t.id} of ${graph.repo}`)
// baseRed: the tests the oracle check found red on graph.base.sha. They are no task's: a worker or a
// merge may report them red and pass. notBase: the red tests of a report that are not on that list.
const baseRed = new Set()
const notBase = (red) => (red || []).filter((x) => !baseRed.has(x))
// A reach run that is red is red for the merge too, whatever oracle_passed says.
const merged = (m) => Boolean(m && m.oracle_passed && !m.escalation && notBase(m.red).length === 0 && !(m.reach || []).some((x) => !x.passed))
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
  if (own.length > 0) return `the focused test is red: ${own.join(', ')} not red on the base`
  if (args.gate) {
    if (!r.gate) return `the gate was not run: report gate for ${args.gate}`
    if (!r.gate.passed) return `the gate is red: ${r.gate.line}`
    const gateOwn = notBase(r.gate.red)
    if (gateOwn.length > 0) return `the gate is red: ${gateOwn.join(', ')} not red on the base`
  }
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
      task: t, state: 'planned', tier: t.tier, branch: t.branch || `${wave}-${t.id}`, plan: null, agents: 0, rounds: 0, answerRound: 0,
      findings: { critical: 0, major: 0, minor: 0 }, reports: [], merges: [], notes: [], reason: '',
      integratedAt: null, order: 0, blasted: false, scaffold: null, building: deferred(), integrated: deferred(), after: [],
    },
  ]),
)
// Chains: the tasks of 1 chain build on the branch <wave>-<chain>; a task with no chain builds on the wave
// branch. After the converge, every merge (a rework round, a task that waited on a chain) goes to the wave branch.
const chainOf = (id) => tasks[id].task.chain || ''
const chains = [...new Set(graph.tasks.map((t) => t.chain).filter(Boolean))]
const chainBranch = (c) => `${wave}-${c}`
let convergedOk = false
const targetOf = (id) => (chainOf(id) && !convergedOk ? chainBranch(chainOf(id)) : wave)
// gateOf(c): the no-chain tasks that tasks of chain c wait on. Direct blockers are enough: a no-chain task's
// own blockers are integrated before it starts. A chain with such a task is gated: openChain cuts its branch.
const gateOf = (c) => [...new Set(ids.filter((id) => chainOf(id) === c).flatMap((id) => tasks[id].task.blockers).filter((b) => !chainOf(b)))]
// The concurrency cap: the runtime's concurrency, else (Claude Code) min(16, CPUs - 2) agents of 1 workflow
// at once. The workflow cannot read the CPU count: the lead passes args.cpus. Agents mostly wait on the API.
const CLAUDE_CAP_MAX = 16
const CLAUDE_CAP_SPARE = 2
const cap = runtime.concurrency || (runtime.provider === 'claude' && args.cpus ? Math.max(1, Math.min(CLAUDE_CAP_MAX, args.cpus - CLAUDE_CAP_SPARE)) : null)
const roots = graph.tasks.filter((t) => t.blockers.length === 0).length
log(cap
  ? `concurrency cap: ${cap} agent${cap === 1 ? '' : 's'} at once; ${roots} tasks have no blocker${cap < roots ? '. The cap is small: agents queue' : ''}`
  : `concurrency cap: unknown; ${runtime.provider === 'claude' ? `Claude Code runs min(${CLAUDE_CAP_MAX}, CPUs - ${CLAUDE_CAP_SPARE}) agents at once: pass args.cpus` : 'the harness decides'}`)

// Browser runs share the machine: on fewer than BROWSER_CPUS CPUs, more than BROWSER_CHAINS chains queue.
const BROWSER_CPUS = 8
const BROWSER_CHAINS = 3
if (solo) log(SOLO)
log(`machine: ${args.cpus ? `${args.cpus} CPUs` : 'CPUs unknown (pass args.cpus)'}; ${chains.length} chain${chains.length === 1 ? '' : 's'}`)
if (args.cpus < BROWSER_CPUS && chains.length > BROWSER_CHAINS) log(`warning: ${chains.length} chains on ${args.cpus} CPUs: browser runs will queue`)

// A blocker that is no task, or a blocker cycle, would wait forever: refuse a graph that fails a check.
const graphProblems = chainMeaning(graph)
if (graphProblems.length > 0) throw new Error(`the graph fails the contract checks: ${graphProblems.join('; ')}`)

// blockersOf(id): the blockers of the graph, then the tasks id was serialized after at run time.
const blockersOf = (id) => [...tasks[id].task.blockers, ...tasks[id].after]
// before[id]: every task that must be integrated before id starts. The graph check refused a cycle.
const before = {}
const reachOf = (id) => before[id] || (before[id] = new Set(blockersOf(id).flatMap((b) => [b, ...reachOf(b)])))
// serialize: a brief widened the files of id into tasks beside it. id waits until each has ended
// (integrated or stopped), and is no longer beside it. A task beside id does not reach id, so no cycle.
function serialize(id, files) {
  const hits = beside(id).map((x) => [x, overlap(files, filesOf(x))]).filter(([, both]) => both.length > 0)
  for (const [x, both] of hits) {
    tasks[id].after.push(x)
    tasks[id].notes.push(`serialized after ${x}: both edit ${both.join(', ')}`)
    log(`${id}: serialized after ${x}: both edit ${both.join(', ')}`)
  }
  if (hits.length > 0) for (const k of Object.keys(before)) delete before[k]
}
// beside(id): the tasks that can run at the same time as id: no blocker path either way.
// Tasks in 2 chains build on 2 branches: they are never beside each other. A task an earlier run merged
// (before) is on the target already: it owns no file in this run.
const beside = (id) => ids.filter((x) => x !== id && !tasks[x].before && chainOf(x) === chainOf(id) && !reachOf(id).has(x) && !reachOf(x).has(id))
// filesOf: the files of a task, from its brief once written.
const filesOf = (x) => (tasks[x].plan || tasks[x].task).files
// doNotTouch(id): the files of the tasks beside id. A worker may edit any other file its outcome needs.
const doNotTouch = (id) => [...new Set(beside(id).flatMap(filesOf))]
// clashStep: the integrator checks the changed files against the tasks beside id that are not merged yet.
// Only such a task owning a changed file is a clash; any other file outside the list is fine.
function clashStep(id, report) {
  const open = beside(id).filter((x) => tasks[x].order === 0)
  if (open.length === 0) return ''
  return `
   The worker reports these files outside its list: ${(report.extra_files || []).join(', ') || 'none'}. Check them, and every other file in git diff --cached --name-only, against these tasks, which run beside it and are not merged yet:
${open.map((x) => `   - ${x}: ${filesOf(x).join(', ')}`).join('\n')}
   A changed file in one of those lists is a clash: run git merge --abort and set escalation to "clash: <file> is owned by task <id>". Any other file outside the list is fine.`
}

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
// The parts of a ready issue (the Definition of Ready), each found as a heading of the body: a
// Markdown heading, a bold line or a "Label:" line. A lead answer counts as the decisions.
const READY_PARTS = { outcome: /^outcome/i, 'done when': /^done[ -]when/i, files: /^files/i, proof: /^(proof|oracle)/i, decisions: /^decisions?\b/i }
const headingsOf = (body) => body.split('\n').map((l) => (/^\s*(?:#{1,6}\s+(.+)|\*\*([^*]+)\*\*|([A-Za-z][\w -]{0,30}):)/.exec(l) || []).slice(1).find(Boolean)).filter(Boolean).map((h) => h.trim())
const missingParts = (id) => Object.keys(READY_PARTS).filter((p) => !(p === 'decisions' && answers[id]) && !headingsOf(issues[id]).some((h) => READY_PARTS[p].test(h)))
// answersText: the lead's answers on the task. They come last in every brief and win over it.
const answersText = (id) => (answers[id] ? `\nThe lead's answers. They win over every other line of this brief:\n${answers[id]}` : '')
const answersRule = (id) => (answers[id] ? `\nThe lead answered these questions. Your text may not contradict or narrow them:\n${answers[id]}` : '')
const NO_WIDEN = 'Keep the files of the issue. A file you add that a task beside this one owns makes the wave run the 2 tasks one after the other.'

// brief: the issue as written when it is ready (no agent); else the graph brief; else a brief-writer
// for the missing parts of the issue only, or for the whole brief when the lead passed no issue body.
// stale: the paths or tasks the brief names that are gone (the path check, or a merge). Then a brief-writer
// always writes the whole brief again for the code as it is now, and its files and oracle win.
async function brief(id, stale) {
  const s = tasks[id]
  const t = s.task
  const own = { files: t.files, oracle: t.oracle, tier: t.tier }
  const body = issues[id]
  const missing = body ? missingParts(id) : []
  if (!stale && body && (missing.length === 0 || t.brief)) {
    log(`${id}: the brief is the issue body as written${missing.length > 0 ? `, then the graph brief for ${missing.join(', ')}` : ''}`)
    return { ...own, removes: t.removes, brief: `${body}${missing.length > 0 ? `\n\n${t.brief}` : ''}${answersText(id)}` }
  }
  if (!stale && t.brief) return { ...own, removes: t.removes, brief: `${t.brief}${answersText(id)}` }
  const ask = stale
    ? `The brief is stale: ${stale.join('; ')}. Write the whole brief again for the code on origin/${targetOf(id)} now: name only paths that exist there (git ls-tree -r --name-only origin/${targetOf(id)}), or that the task or a blocker creates (mark each such path "creates"). Keep the outcome. The brief as written:\n${(s.plan && s.plan.brief) || body || t.brief || '(none)'}`
    : body
    ? `The issue lacks these parts of a ready issue: ${missing.join(', ')}. Write only those parts. Do not restate or change the rest of the issue. The issue as written:\n${body}`
    : 'Write what a worker needs to finish with no judgment call: the files, each signature exactly, each trap quoted from the source, the oracle and its focused command.'
  const b = await call(
    id,
    `Write the brief for ${issueOf(t)}, task ${id}. Read only: edit, commit and push nothing.
The code of its blockers (${t.blockers.join(', ') || 'none'}) lands on ${targetOf(id)}: read origin/${targetOf(id)} after git fetch -q origin.
The plan says: tier ${t.tier}; files ${t.files.join(', ')}; oracle ${t.oracle.command} (files: ${t.oracle.files.join(', ') || 'none'}; uncovered: ${t.oracle.uncovered.join('; ') || 'none'}).
${ask}
Inventory the oracle files and list each behaviour they do not cover. Tier it: bounded only when the oracle covers every behaviour; judgment when 1 or more is uncovered; lead when the step-up rule in AGENTS-AND-MODELS.md applies. ${NO_WIDEN}${answersRule(id)}${rules}`,
    { label: `brief ${id}`, phase: 'Brief', schema: briefSchema, ...spawn('brief_writer', ROLE_TIER.brief_writer) },
  )
  if (!b) return null
  // The contract tier rule: the brief may raise the planned tier, never lower it. With an issue body,
  // the files and oracle stay the issue's unless they are a missing part.
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

// ---- Build
// start: the line that makes the worktree. With at (startOf the task), it starts on that commit, then
// merges origin/<from>, so the worker gets the spec tests or the earlier work, and the blockers' code.
// There is no fallback: a missing commit fails the line. A resumed branch may exist from the earlier
// run, so it is reset (-B) to the resume point.
const start = (branch, from, at, resumed) =>
  at
    ? `git fetch -q origin && git worktree add ${resumed ? '-B' : '-b'} ${branch} ${root}/${branch} ${at} && git -C ${root}/${branch} merge -q --no-edit origin/${from}`
    : `git fetch -q origin && git worktree add -b ${branch} ${root}/${branch} origin/${from}`
// startOf: where a task branch starts: resume_from (a full SHA, or a remote branch), else spec_sha, else
// nowhere (the wave branch).
const startOf = (t) => (t.resume_from ? (FULL_SHA.test(t.resume_from) ? t.resume_from : `origin/${t.resume_from}`) : t.spec_sha)
const startTask = (id) => start(tasks[id].branch, targetOf(id), startOf(tasks[id].task), Boolean(tasks[id].task.resume_from))
const resumeText = (id) => {
  const t = tasks[id].task
  return t.resume_from ? `\nThis branch resumes earlier work on the task from ${t.resume_from}. Read git log origin/${targetOf(id)}..HEAD first and continue that work; do not redo it.` : ''
}
// TIMES: each agent that runs a test reports its browser time and its wait for a machine-wide browser lock.
const TIMES = 'When a test run drives a browser, time it: report browser_s, the seconds the browser runs took, and lock_wait_s, the seconds you waited for a machine-wide browser lock first (0 when none).'
// redText: the tests red on the base, for a worker or an integrator. A red test on the list is not theirs.
// workerGate: the worker runs args.gate once after its focused test (the integrator's text is const gate).
const workerGate = args.gate ? ` Then run the gate once: ${args.gate}. Fix what it reports in your files, or escalate. Report the gate in gate: command, passed, last output line.` : ''
const redText = (who) => (baseRed.size > 0 ? `\nThese tests are red on the base ${graph.base.sha} before any change: ${[...baseRed].join('; ')}. They are not ${who}: when every red test is on this list, count the run green and list those tests in ${who === 'yours' ? 'test.red' : 'red'}. Do not fix them unless the brief says so.` : '')
// startLog: 1 log line that says where a task branch starts.
const startLog = (id, t) => log(`${id}: starts from ${t.resume_from ? `resume ${t.resume_from}` : t.spec_sha ? `spec ${t.spec_sha}` : `${targetOf(id)}, no spec`}`)
// workerPrompt: the file list is intent, not a fence (rule: "File lists" in AGENTS-AND-MODELS.md). avoid is
// the files of the tasks that can run at the same time. An oracle file in the list is the worker's to edit.
function workerPrompt({ id, what, text, branch, makeLine, files, avoid, test, oracleFiles, round }) {
  const locked = oracleFiles.filter((f) => overlap([f], files).length === 0)
  return `${what}
${text}
Work in your own worktree ${root}/${branch}. Make it first with this exact line:
${makeLine}${setupLine(`${root}/${branch}`)}
Your files: ${files.join(', ')}. You may also edit any other file your outcome needs; list each one in extra_files.
Do not touch these files, because tasks that run at the same time own them: ${avoid.join(', ') || 'none'}.
Your test files are yours to edit, oracle files in your list included; do not weaken an existing assertion unless the brief says so.${locked.length > 0 ? ` Do not edit these oracle files, which you do not own: ${locked.join(', ')}.` : ''}
Run only the focused test: ${test}.${workerGate}${redText('yours')} ${TIMES} Commit small and push after every commit: git push -q -u origin ${branch}. Open no pull request. Merge nothing.
For a how-to question under a decided design (which file, which mechanism, which token), pick the option that keeps the issue's decisions and the repo rules, build it, and name the choice in notes. Escalate only a question the issue does not answer about what the user sees, hears or reads, or when the test cannot pass without a file you must not touch. Quote where in the issue you looked. To escalate, push what you have and set status to escalated.
Report task ${id}, round ${round}, branch ${branch}, the full 40-character SHA of your last push (run git rev-parse HEAD after it; never a placeholder such as zeros), the test command with its last output line, and extra_files. When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`
}

// QUOTED: an escalation that quotes the issue: a "..." span or a > line.
const QUOTED = /["\u201c][^"\u201d\n]{3,}["\u201d]|^\s*>/m
// work: 1 worker call. An escalation with no quote from the issue goes back to the same worker once,
// before it reaches the lead.
async function work(owners, prompt, opts, branch) {
  let r = await call(owners, prompt, opts)
  if (r && r.status === 'done' && badSha(r.sha)) {
    log(`${opts.label}: the report SHA ${r.sha} is no commit; it goes back to the worker once`)
    r = (await call(owners, `${prompt}

You reported the SHA ${r.sha}, which is no commit. Your worktree ${root}/${branch} exists: continue there. Push the branch if it is not pushed, run git rev-parse HEAD, and report that full 40-character SHA. Never report a placeholder.`, { ...opts, label: `${opts.label} sha` })) || r
  }
  if (!r || r.status !== 'escalated' || QUOTED.test(r.escalation || '')) return r
  log(`${opts.label}: the escalation quotes no line of the issue; it goes back to the worker once`)
  return call(owners, `${prompt}

You escalated once already, with no quote from the issue: ${r.escalation || 'no question given'}
Your worktree ${root}/${branch} exists: continue there and do not make it again (if it is gone: git fetch -q origin && git worktree add ${root}/${branch} origin/${branch}). If the issue answers the question, or it is a how-to question, build it and name the choice in notes. Else escalate again and quote the line of the issue where you looked.`, { ...opts, label: `${opts.label} again` })
}

function build(id, plan) {
  const s = tasks[id]
  startLog(id, s.task)
  return work(
    id,
    workerPrompt({ id, what: `Build ${issueOf(s.task)}.`, text: `${plan.brief}${resumeText(id)}`, branch: s.branch, makeLine: startTask(id), files: plan.files, avoid: doNotTouch(id), test: plan.oracle.command, oracleFiles: plan.oracle.files, round: 0 }),
    { label: `build ${id}`, phase: 'Build', schema: reportSchema, ...spawn('worker', plan.tier) },
    s.branch,
  )
}

// buildSplit: the split workflow as a plain function (a wave may not nest a workflow). It returns a
// report of the task branch, or null with s.reason set. The sub-lead and each part run at least at the
// task's tier: a lead-tier task splits and builds on the lead tier.
async function buildSplit(id, plan) {
  const s = tasks[id]
  startLog(id, s.task)
  const sp = await call(
    id,
    `Split ${issueOf(s.task)} into these parts: ${s.task.split.join(', ')}. Brief:
${plan.brief}
1. Cut branch ${s.branch}: ${startTask(id)}${resumeText(id)}${setupLine(`${root}/${s.branch}`)}
2. The oracle of the whole task is: ${plan.oracle.command}. Add a focused filter of it for each part.
3. Write stubs for the seams between parts, so each part builds alone. Commit the stubs and push ${s.branch}.
4. Write 1 brief per part: its files (2 parts never edit the same file, and only files in ${plan.files.join(', ')}), its focused test, the oracle cases it must pass, what it must not touch.
5. Tier each part: bounded when the oracle covers it, judgment when it does not, lead when the step-up rule in AGENTS-AND-MODELS.md applies.
If the task does not split cleanly, set escalation and write no briefs.${rules}`,
    { label: `split ${id}`, phase: 'Build', schema: splitSchema, ...spawn('sub_lead', higherTier(ROLE_TIER.sub_lead, plan.tier)) },
  )
  if (!sp || sp.escalation || sp.briefs.length < LIMITS.split_parts_min) {
    s.reason = sp ? sp.escalation || `the split has fewer than ${LIMITS.split_parts_min} parts` : 'the sub-lead returned nothing'
    return null
  }
  const parts = await parallel(
    sp.briefs.map((b) => () =>
      work(
        id,
        workerPrompt({ id: b.part, what: `Build part ${b.part} of ${issueOf(s.task)}.`, text: b.brief, branch: `${s.branch}-${b.part}`, makeLine: start(`${s.branch}-${b.part}`, s.branch), files: b.files, avoid: [...new Set([...doNotTouch(id), ...sp.briefs.filter((o) => o !== b).flatMap((o) => o.files)])], test: b.test, oracleFiles: plan.oracle.files, round: 0 }),
        { label: `build ${id} ${b.part}`, phase: 'Build', schema: reportSchema, ...spawn('worker', higherTier(b.tier, plan.tier)) },
        `${s.branch}-${b.part}`,
      ),
    ),
  )
  const refused = sp.briefs.map((b, i) => verify(parts[i], b.part, `${s.branch}-${b.part}`)).map((why, i) => why && `${sp.briefs[i].part}: ${why}`).filter(Boolean)
  if (refused.length > 0) {
    s.reason = `${refused.length} of ${parts.length} parts refused: ${refused.join('; ')}`
    return null
  }
  s.parts = sp.briefs.map((b) => b.part)
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
  return { task: id, branch: s.branch, sha: m.sha, status: 'done', round: 0, test: { command: plan.oracle.command, line: 'the oracle passed after the part merge', passed: true }, ...(args.gate && { gate: { command: args.gate, line: 'each part passed the gate', passed: true } }) }
}

// mergedHead: before a task escalates on a report SHA that is no commit, 1 agent reads the remote. It
// returns the remote head of the task branch when that head is already in the target (an earlier merge
// attempt merged it), else ''. A branch a validated merge deleted counts as merged by its merge subject
// on the target alone. It also moves heads[target] to the remote head of the target.
async function mergedHead(id, branch) {
  const target = targetOf(id)
  const rm = await call(id, `Read the remote of ${graph.repo}. Edit and commit nothing, push nothing, open no pull request.
1. git fetch -q origin
2. Report in heads the head of each of these branches that is on the remote (git ls-remote origin <branch>): ${branch} ${target}
3. If ${branch} is on the remote and its head is an ancestor of origin/${target} (git merge-base --is-ancestor <head> origin/${target}), report in merges the one subject "Merge ${branch} into ${target}".
   If ${branch} is not on the remote (a validated merge deletes it), look for its merge commit on the target: git log --merges --format='%H %s' ${graph.base.sha}..origin/${target}. When one has the subject "Merge ${branch} into ${target}", report that subject in merges, and in heads the branch ${branch} with the SHA of the merged head (git rev-parse <that commit>^2).
   Else report merges [].${rules}`,
    { label: `remote check ${id}`, phase: 'Integrate', schema: remoteSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  const head = (rm ? rm.heads : []).filter((h) => !badSha(h.sha))
  // A pruned branch is no head on the remote: its merge subject on the target is enough, at the head the agent read from it.
  const own = head.find((h) => h.branch === branch)
  if (!rm || !rm.merges.includes(`Merge ${branch} into ${target}`)) return ''
  const tip = head.find((h) => h.branch === target)
  if (!own && !tip) return ''
  if (tip) heads[target] = tip.sha
  return own ? own.sha : tip.sha
}

// ---- Integrate: 1 branch at a time, the first try on its x-first-try tier, the step-up on its x-roles tier.
// heads: the head of each branch the run merges into: the wave branch and each chain branch.
const heads = { [wave]: graph.base.sha }
// serial: 1 merge at a time on each branch; 2 chains merge at the same time.
const queues = {}
function serial(target, run) {
  const p = (queues[target] || Promise.resolve()).then(run)
  queues[target] = p.catch(() => null)
  return p
}
const drained = () => Promise.all(Object.values(queues))
let mergeCount = 0
// keepOf: the oracle files of a task that are not its scaffold. No scaffold step deletes one.
const keepOf = (x) => (tasks[x].plan || tasks[x].task).oracle.files.filter((f) => !(tasks[x].task.scaffold || []).includes(f))
const NOT_RUN = { command: 'none', line: 'not run', passed: false }
// scaffoldOf: the scaffold of task id still on the wave branch, the oracle files that stay without
// it, and whether any check can run then. A check that cannot run keeps the files.
function scaffoldOf(id) {
  const s = tasks[id]
  const keepAll = new Set(ids.flatMap(keepOf))
  const files = (s.scaffold ? s.scaffold.kept : s.task.scaffold || []).filter((f) => !keepAll.has(f))
  const rest = keepOf(id)
  return { files, rest, runnable: rest.length > 0 || Boolean(args.gate) }
}
// scaffoldStep: step 6 of a merge. It deletes only files the spec added, and checks the tree without them.
function scaffoldStep(id) {
  const { files, rest, runnable } = scaffoldOf(id)
  if (files.length === 0 || !runnable) return ''
  const list = files.join(' ')
  const oracle = rest.length > 0 ? `Run the oracle of the task over the oracle files that stay (${rest.join(', ')}), not over the deleted files: ${tasks[id].plan.oracle.command}.` : 'The task has no oracle file left to run.'
  return `
6. Scaffold: these spec tests were an oracle for the build only: ${list}. Delete only those added since the base, in 1 follow-up commit:
   git rm -q --ignore-unmatch -- $(git diff --name-only --diff-filter=A ${graph.base.sha}..HEAD -- ${list})
   When git diff lists no file, delete nothing: report scaffold.deleted [], scaffold.kept [${files.join(', ')}] and scaffold.test with line "not run" and passed false.
   ${oracle}${gate}
   Green: git commit -q -m "Delete scaffold tests of task ${id}" -m "No caller relies on them: they were spec scaffolding for the build." Report scaffold.deleted (the files removed), scaffold.kept [] and the check you ran with its last output line as scaffold.test.
   Red: git restore --staged --worktree -- ${list}. Report scaffold.deleted [], scaffold.kept [${files.join(', ')}] and the red check as scaffold.test with passed false.
   Never set scaffold.test.passed true when no check ran.`
}
// proofStep: step 4 of a merge. A clean merge whose tree is the tree the worker proved keeps the
// worker's proof and runs only the gate; after a conflict or a fix, the oracle runs again. A check is
// green by its exit code, never by its last line.
const EXIT_CODE = ' A check is green only when it exits 0: read its exit code, not its last output line.'
const proofStep = (id, report, target) => `4. ${resetup(`${root}/${target}`)}If step 2 had no conflict and git write-tree prints the tree of ${report.sha} (git rev-parse ${report.sha}^{tree}), the merged tree is the tree the worker proved: do not run the oracle again; keep the worker's proof (${report.test.line}) and set reproved false. Otherwise run the oracle of the task: ${tasks[id].plan.oracle.command}, and set reproved true.${gate}${reachStep(id)}${EXIT_CODE}`
// reachStep: with oracle.reach, the merge also runs the test folders outside the focused oracle that use
// the change, even when the worker's proof is kept. '' without reach, so other prompts do not change.
const reachStep = (id) => {
  const reach = tasks[id].plan.oracle.reach
  return reach ? ` Then, in every case, run reach: list the test folders that reference a changed file (git diff --name-only HEAD) or a changed class name, drop the folders of the oracle files (${tasks[id].plan.oracle.files.join(', ') || 'none'}), and run ${reach} for each remaining folder with {dir} replaced by it. Report each run in reach: dir, command, passed (true when it exits 0, or when every red test of it is on the base red list). Step 5 decides on it.` : ''
}
// ---- Close and prune: a task issue closes, and its branch and worktree go, when its own merge is
// validated: green and pushed. The guard: the merge is validated, the branch is an ancestor of the
// target, and no other open claim names it. A parent issue closes only after the wave PR merges into main.
// keepBranch: a branch the workflow never deletes: the wave branch, a chain branch, the base, main.
const keepBranch = (b) => [wave, 'main', graph.base.ref, ...chains.map(chainBranch)].includes(b)
// pruneBranches: the task branches a merge of report deletes: the branch, and its split parts in round 0.
const pruneBranches = (id, report) => [report.branch, ...(report.branch === tasks[id].branch ? (tasks[id].parts || []).map((p) => `${tasks[id].branch}-${p}`) : [])]
// claimGuard: guard 3 of the close step. A solo run has no claims.
function claimGuard(id, branches) {
  if (solo) return 'This is a solo run: there is no other claim to check.'
  const issue = tasks[id].task.issue
  const other = ids.filter((x) => x !== id && claims[x]).map((x) => claims[x])
  return `No other open claim may name ${branches.join(' or ')}: ${issue ? `read gh issue view ${issue} --repo ${graph.repo} --json comments -q '.comments[].body', ` : ''}and the claim comments of the other tasks of this wave (${other.join(' ') || 'none'}). When an open claim for a task other than ${id} names one of these branches, close nothing and delete nothing: add "<branch>: named by the open claim <url>" to kept.`
}
// pruneStep: step n of a merge, after the push of step n - 1. It runs only when the merge is validated.
// A failed close or delete never fails the merge: the integrator sets closed or pruned false and says why in kept.
function pruneStep(id, report, target, n) {
  const s = tasks[id]
  const issue = s.task.issue
  const branches = pruneBranches(id, report)
  const kept = branches.filter(keepBranch)
  if (kept.length > 0) {
    log(`${id}: ${kept.join(' ')} is a wave, chain or base branch: the merge closes and deletes nothing`)
    return `\n${n}. Close nothing and delete nothing: ${kept.join(' ')} is a branch the workflow keeps. Report closed false, pruned false, pruned_branch "" and kept ["${kept.join(' ')}: kept branch"].`
  }
  const proof = `Oracle: ${s.plan.oracle.command}: <its last output line in step 4, or the worker's proof "${report.test.line}" when you kept it>.${args.gate ? ` Gate: ${args.gate}: <its last output line>.` : ''}`
  const close = !issue
    ? `(a) Task ${id} has no issue: close nothing, and add "${id}: no issue to close" to kept. Report closed false.`
    : s.closedAt
      ? `(a) Issue #${issue} closed at an earlier merge of this task: do not close it again. Comment on it: gh issue comment ${issue} --repo ${graph.repo} --body "Rework ${report.branch} merged into ${target} at <the full SHA of the push>. ${proof}" Report closed false.`
      : `(a) gh issue close ${issue} --repo ${graph.repo} --comment "Merged ${report.branch} into ${target} at <the full SHA of the push>. ${proof}" Report closed true when it exits 0.`
  return `
${n}. Close and prune, only when the merge is validated: step 5 was green and the push of step ${n - 1} printed no error. When the merge is red, aborted or not pushed, close nothing and delete nothing: report closed false and pruned false. ${claimGuard(id, branches)}
   ${close}
   (b) git fetch -q origin. For each of these branches: ${branches.join(' ')}. When it is on the remote and git merge-base --is-ancestor origin/<branch> origin/${target} exits 0, delete it: git push -q origin --delete <branch>. Name the exact branch; never a pattern. Else keep it: add "<branch>: not merged into ${target}" to kept. Never delete ${target === wave ? wave : `${target}, ${wave}`}, a chain branch or main.
   (c) For each of those branches: git worktree remove --force ${root}/<branch> and git branch -D <branch>, each only when present. Keep the worktree ${root}/${target}.
   Report pruned true only when (b) and (c) ran for every branch, and pruned_branch: the branches deleted, space-separated. A failed close or delete does not fail the merge: keep oracle_passed true, set closed or pruned false and say why in kept.`
}
// makeWave: step 1 of a merge into target: its worktree, made once, then fast-forwarded to the remote.
const makeWave = (target) => `1. If the worktree ${root}/${target} is missing, make it: git fetch -q origin && git worktree add -B ${target} ${root}/${target} origin/${target}${setupLine(`${root}/${target}, only when you make it here`, '   ')}
   Otherwise, in it: git fetch -q origin && git merge -q --ff-only origin/${target}`
// ---- Base red: a red merge with evidence that it is not the task's (the gate red on the pre-merge tip
// too, or the gate could not run there with the same error) escalates no task. Only the gate can be base red:
// the task oracle is red on the pre-merge tip by design. The evidence must name the tip the run holds. It holds that merge and the tasks that wait on it;
// the other tasks and chains keep merging. The result lists each base red once (target and check), with
// the tasks it holds. The run does not poll for a fix: the lead fixes the target, then runs the same graph
// again; a held task resumes from its pushed branch.
const holds = {}
const notTask = (m, before) => {
  const b = m && m.base_red
  if (!b || !args.gate || b.check !== args.gate || badSha(b.tip) || b.tip !== before) return false
  return b.kind === 'base' || (b.kind === 'infra' && m.escalation === b.line)
}
function holdOf(target, b) {
  const key = `${target}\n${b.check}`
  if (!holds[key]) {
    const fix = b.kind === 'base' ? `fix ${b.check} on ${target} (red at ${b.tip} before the merge)` : `fix the harness or machine error of ${b.check}`
    holds[key] = { kind: b.kind, target, check: b.check, line: b.line, tip: b.tip, owner: 'lead', next: `${fix}, then run the same graph again`, holds: [] }
    log(`base red on ${target}: ${b.kind}: ${b.check}: ${b.line}; the merges into ${target} that hit it wait for the lead`)
  }
  return holds[key]
}
// hold: task id waits on base red h. It is no escalation: its state stays, and it is listed under h.
function hold(id, h, why) {
  h.holds.push(id)
  tasks[id].held = h
  stop(id, null, `held by ${h.kind} red on ${h.target}: ${h.check}: ${h.line}${why ? `; ${why}` : ''}`)
}
// baseRedStep: the red branch of a merge step. Only a red gate can be base red; a red oracle is the task's.
const baseRedStep = args.gate ? `When the oracle is red, the red is the task's: leave base_red out. When only the gate (${args.gate}) is red, find whose red it is: note the pre-merge tip (git rev-parse HEAD), run git merge --abort, then run the gate once on that tip. When it is red there too, set base_red: kind base, check ${args.gate}, its last output line on the tip, and the tip SHA. When the gate could not run at all on the merged tree (a harness, tool or machine error, not a test result) and could not run on the tip either, with the same error, set base_red: kind infra, check ${args.gate}, that error as line (the same text as escalation), and the tip SHA. When the gate ran green on the tip, the red is the task's: leave base_red out. ` : 'The red is the task\'s: leave base_red out. '
function integrate(id, report) {
  const s = tasks[id]
  const scaffold = scaffoldStep(id)
  const target = targetOf(id)
  const prompt = (resolve, tip) => `You integrate task ${id} into the ${target === wave ? 'wave' : 'chain'} branch ${target} of ${graph.repo}. Merge 1 branch: ${report.branch} at ${report.sha}.
${makeWave(target)}
2. In it: git merge --no-ff --no-commit ${report.sha}${clashStep(id, report)}
3. On a conflict: ${resolve ? 'resolve it when both sides are clear; keep the behaviour of both. When the 2 sides change the same contract in 2 ways, run git merge --abort and set escalation to the files.' : 'run git merge --abort and set escalation to the conflicting files. Do not resolve it.'}
${proofStep(id, report, target)}
5. Green (the gate passed, the oracle when it ran${tasks[id].plan.oracle.reach ? ', and every reach run passed' : ''}): git commit -q -m "Merge ${report.branch} into ${target}". Report branch ${target}, merged [${report.branch}] and oracle_passed true.
   Red${tasks[id].plan.oracle.reach ? ' (a reach red counts: name its folder and last output line in escalation)' : ''}: report oracle_passed false and the last output line in escalation. ${baseRedStep}Then run git merge --abort when the merge is still in progress. Stop: commit nothing, push nothing, close nothing and delete nothing.${redText("this task's")}${scaffold}
${scaffold ? 7 : 6}. git push -q origin ${target}. Report the full 40-character SHA of the push. Then report in gone each path the merge deleted or renamed away: git diff --name-status -M ${tip} <the merge commit of step 5>: the path of each D line and the old path of each R line, nothing else; [] when none.${pruneStep(id, report, target, scaffold ? 8 : 7)}
Keep the worktree ${root}/${target} for the next merge. Open no pull request. Never touch main. ${TIMES}
When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`
  const run = async () => {
    const before = heads[target] || graph.base.sha
    let m = await call(id, prompt(false, before), { label: `merge ${id}`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', FIRST_TRY.integrator) })
    // The stronger integrator must confirm a base-red claim before it holds the merge.
    if (!merged(m)) {
      m = await call(id, prompt(true, before), { label: `merge ${id} step-up`, phase: 'Integrate', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) })
    }
    s.merges.push(m)
    if (!merged(m) && notTask(m, before)) return { ok: false, base: m.base_red, reason: `${m.base_red.kind} red on ${target}: ${m.base_red.check}: ${m.base_red.line}` }
    if (!merged(m)) return { ok: false, reason: m ? m.escalation || 'the merge is red' : 'the integrator returned nothing' }
    heads[target] = m.sha
    s.order = ++mergeCount
    s.diff = `${before}...${report.sha}`
    if (m.reproved === false) log(`${id}: the merged tree is the tree the worker proved; only the gate ran`)
    // The scaffold step: a deletion counts only over a check that ran and passed; else the files stay.
    const sc = scaffoldOf(id)
    if (sc.files.length > 0) {
      const r = scaffold && m.scaffold ? m.scaffold : { deleted: [], kept: sc.files, test: NOT_RUN }
      const deleted = r.test.passed ? r.deleted : []
      s.scaffold = { deleted: [...((s.scaffold && s.scaffold.deleted) || []), ...deleted], kept: sc.files.filter((f) => !deleted.includes(f)), test: r.test }
      log(`${id}: scaffold deleted ${deleted.join(' ') || 'none'}; kept ${s.scaffold.kept.join(' ') || 'none'} (${r.test.line})`)
    }
    know(m.at)
    s.integratedAt = isoSeconds(m.at) === null ? newest : m.at
    staleAfter(id, m.gone || [], `${report.notes || ''}\n${m.notes || ''}`)
    // Close and prune: read back only over a validated, pushed merge. closed_at is the integrator's at.
    if (!badSha(m.sha)) {
      if (m.closed && !s.closedAt) s.closedAt = s.integratedAt
      if (m.pruned) s.pruned = true
      if (m.closed || m.pruned || (m.kept || []).length > 0) log(`${id}: ${m.closed ? `issue #${s.task.issue} closed; ` : ''}${m.pruned ? `deleted ${m.pruned_branch}` : 'no branch deleted'}${(m.kept || []).length > 0 ? `; kept ${m.kept.join('; ')}` : ''}`)
    }
    return { ok: true, diff: `${before}...${report.sha}` }
  }
  return serial(target, run)
}

// regress: run the regression command once on a commit. Returns { sha, passed, line } or null when the agent returned nothing.
async function regress(side, sha, command) {
  const v = await call([], `Run 1 scenario of ${graph.repo} on commit ${sha}. Read only: edit nothing, commit nothing, push nothing, open no pull request.
1. git fetch -q origin && git worktree add --detach ${root}/regression-${side} ${sha}${setupLine(`${root}/regression-${side}`)}
2. In that worktree, run exactly: ${command}
3. Set agree to true when the command exits 0, and to false when it does not. Set reason to its last output line.
4. Remove the worktree: git worktree remove --force ${root}/regression-${side}${rules}`,
    { label: `regression ${side}`, phase: 'Report', schema: verdictSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  return v ? { sha, passed: v.agree, line: v.reason } : null
}

// ---- Review. With review 'batch': batches of REVIEW_BATCH integrated results beside the build, flushed
// when the build ends. With review 'end' (the default): the queue waits for reviewEnd.
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
  if (reviewMode === 'batch' && queue.length >= REVIEW_BATCH) track(review(queue.splice(0, REVIEW_BATCH)))
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
${evidence}${rules}${lens}`,
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
${args.decisions || '(none given)'}${rules}${lens}
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

// left: the oracle files of the task that the scaffold step did not delete. reworkTest: the oracle command
// the rework worker runs, over those files only (a deleted scaffold file would turn the run red).
const left = (s) => s.plan.oracle.files.filter((f) => !((s.scaffold && s.scaffold.deleted) || []).includes(f))
const reworkTest = (s) => {
  const gone = s.plan.oracle.files.filter((f) => !left(s).includes(f))
  return gone.length > 0 ? `${s.plan.oracle.command}, over the oracle files that remain (${left(s).join(', ') || 'none'}), not over the deleted scaffold files (${gone.join(', ')})` : s.plan.oracle.command
}
// ---- Rework: 1 round per finding set on a new branch from the wave branch; it merges and is reviewed again.
async function rework(id, findings, early = false) {
  const s = tasks[id]
  s.rounds++
  move(id, 'rework', { round: s.rounds, reason: findings.map((f) => f.id).join(', ') })
  const r = await work(
    id,
    workerPrompt({
      id,
      what: `Rework ${issueOf(s.task)}, round ${s.rounds}. Its code is already on ${targetOf(id)}. Fix exactly these review findings, nothing else:`,
      text: `${findings.map((f) => `- ${f.id} ${f.severity}: ${f.claim} Evidence: ${f.evidence}`).join('\n')}${answersText(id)}`,
      branch: `${s.branch}-r${s.rounds}`, makeLine: start(`${s.branch}-r${s.rounds}`, targetOf(id)), files: s.plan.files, avoid: doNotTouch(id), test: reworkTest(s), oracleFiles: left(s), round: s.rounds,
    }),
    { label: `rework ${id} ${s.rounds}`, phase: 'Rework', schema: reportSchema, ...spawn('worker', higherTier(s.tier, REWORK_MIN_TIER)) },
    `${s.branch}-r${s.rounds}`,
  )
  const refused = verify(r, id, `${s.branch}-r${s.rounds}`)
  if (refused) return stop(id, 'escalated', `rework round ${s.rounds}: ${refused}`)
  know(r.at)
  s.reports.push(r)
  move(id, 'built')
  const m = await integrate(id, r)
  // A base red here escalates, not holds: the round-0 merge is on the target, so a re-run would skip the task.
  if (!m.ok) return stop(id, 'escalated', m.base ? `rework round ${s.rounds}: ${m.reason}; the first merge is on ${targetOf(id)}, so a re-run skips this task: merge ${s.branch}-r${s.rounds} by hand after the fix` : m.reason)
  move(id, 'integrated')
  if (reviewMode === 'batch') return enqueue({ id, diff: m.diff, test: s.plan.oracle.command })
  // An early round (the converge gate) comes before the end review, which still reads the task.
  if (early) return s.notes.push(`rework round ${s.rounds} merged for the converge gate; the end review reads it`)
  // The end review runs once: a merged rework round is not reviewed again.
  s.notes.push(`rework round ${s.rounds} merged; the end review does not run again`)
  move(id, 'reviewed')
  move(id, 'done')
}

// ---- Fix lane (graph.fix_lane): at most 1 lead-tier agent per wave, on the branch <wave>-fix cut from the wave
// head, for a CRITICAL end-review finding, a major tagged guard, or a red converge gate with no rework left.
// It gets the brief, last report and diff of each involved task, and the findings. Its branch merges through
// the merge step of the task merged last among them. It counts no rework round. It returns true when it merged.
let fixDone = false
let fixFail = ''
async function fixLane(trigger, involvedIds, findings) {
  if (fixDone || !fixLaneOn) return false
  fixDone = true
  const involved = involvedIds.filter((x) => tasks[x] && tasks[x].order > 0)
  if (involved.length === 0) {
    fixFail = 'no involved task is merged'
    return false
  }
  const id = involved.reduce((a, b) => (tasks[b].order > tasks[a].order ? b : a))
  const s = tasks[id]
  const branch = `${wave}-fix`
  const what = trigger === 'review' ? 'the end review' : 'the converge gate'
  log(`fix lane: ${what} on ${wave} at ${heads[wave]}: 1 lead-tier agent on ${branch} for ${findings.map((f) => f.id).join(', ')} (tasks ${involved.join(', ')})`)
  const context = involved.map((x) => {
    const t = tasks[x]
    const r = t.reports[t.reports.length - 1]
    const brief = (t.plan ? t.plan.brief : t.task.brief || '') || '(none)'
    return `- ${x} (${issueOf(t.task)}): diff ${t.diff || `${graph.base.sha}...${heads[wave]}`}; last report: ${r ? `branch ${r.branch} at ${r.sha}, test ${r.test.line}${r.notes ? `, notes: ${r.notes}` : ''}` : 'none'}
  Brief:
${brief.split('\n').map((l) => `    ${l}`).join('\n')}`
  }).join('\n')
  const r = await work(
    involved,
    workerPrompt({
      id,
      what: `Fix lane of the wave branch ${wave} of ${graph.repo} at ${heads[wave]}. The code of every involved task is already merged there. ${what === 'the end review' ? 'The end review' : 'The converge gate'} found what follows. Fix exactly this, nothing else, across the involved tasks. Keep 1 path for each behaviour: add no second path, duplicate store, forwarder or second mount path.`,
      text: `${findings.map((f) => `- ${f.id} ${f.severity}: ${f.claim} Evidence: ${f.evidence}`).join('\n')}
The involved tasks, with the brief, the last report and the diff of each:
${context}${involved.map(answersText).join('')}`,
      branch, makeLine: start(branch, wave), files: [...new Set(involved.flatMap(filesOf))], avoid: [],
      test: `${reworkTest(s)}${args.converge_gate ? `, then the converge gate: ${args.converge_gate}` : ''}`,
      oracleFiles: [...new Set(involved.flatMap((x) => left(tasks[x])))], round: s.rounds,
    }),
    { label: 'fix lane', phase: 'Rework', schema: reportSchema, ...spawn('worker', 'lead') },
    branch,
  )
  const refused = verify(r, id, branch)
  if (refused) {
    fixFail = refused
    log(`fix lane: ${refused}`)
    return false
  }
  know(r.at)
  s.reports.push(r)
  const m = await integrate(id, r)
  if (!m.ok) {
    fixFail = m.reason
    log(`fix lane: the merge of ${branch} failed: ${m.reason}`)
    return false
  }
  for (const x of involved) tasks[x].notes.push(`fix lane for ${what} merged ${branch} into ${wave} at ${heads[wave]}; it counts no rework round, and the end review does not run again`)
  return true
}
// gateAgain: the converge gate once more after the fix lane merged.
async function gateAgain() {
  const again = await gateRun(true, 'the fix lane')
  log(`converge gate after the fix lane: ${again.passed ? 'passed' : 'red'}: ${again.line}`)
  convergeGate = { ...again, fix: true }
  if (!again.passed) convergeGate.reason = `the converge gate "${args.converge_gate}" is still red on ${wave} after the fix lane: ${again.line}`
}
// gateFix: a red converge gate that its rework round did not clear, or with no round left, gets the fix lane.
async function gateFix() {
  if (!fixLaneOn || fixDone) return
  const fixed = await fixLane('gate', ids.filter((x) => tasks[x].order > 0), [{ id: 'converge_gate', severity: 'major', claim: `The converge gate (${args.converge_gate}) is red on the converged wave head ${heads[wave]}. Fix the failure.`, evidence: convergeGate.line }])
  if (fixed) return gateAgain()
  convergeGate.fix = true
  convergeGate.reason = `${convergeGate.reason}; the fix lane ran and did not merge: ${fixFail}`
}

// ---- Review at the end (the default): after the last merge, 1 lead-tier reviewer reads the whole wave
// head blind and across issues, with the decisions. No skeptic runs; a blast-radius check runs only for
// a risky task. A CRITICAL or major finding opens at most 1 rework round on the task that caused it (the
// one merged last); the minor findings become 1 follow-up issue draft.
let followUp = null
async function reviewEnd(entries) {
  const endIds = entries.map((e) => e.id)
  const riskyIds = endIds.filter((id) => tasks[id].task.risky && takeBlast())
  for (const id of riskyIds) tasks[id].blasted = true
  const byId = Object.fromEntries(entries.map((e) => [e.id, e]))
  const proofs = (await parallel(riskyIds.map((id) => () => blast(id, id, `task ${id}`, `diff ${byId[id].diff}; test: ${byId[id].test}`)))).filter(Boolean)
  const proofText = proofs.length > 0 ? `\nBlast-radius proofs (input to weigh, not a verdict; run your own checks and keep every finding you would have made):\n${proofs.map(renderBlast).join('\n')}` : ''
  const answered = endIds.filter((id) => answers[id]).map((id) => `- ${id}: ${answers[id]}`).join('\n')
  let rv = null
  for (let i = 0; i < REVIEW_TRIES && !rv; i++) {
    rv = await call(
      endIds,
      `Review the whole wave branch ${wave} of ${graph.repo} at ${heads[wave]}: ${entries.length} results, merged 1 at a time on ${graph.base.sha} (diff ${graph.base.sha}...${heads[wave]}). You do not know who wrote them. Judge the merged code and the tests across the issues: 2 results that solve alike, clash or break each other are findings too. Read only: edit, commit and push nothing. Run git fetch -q origin first.
Results:
${entries.map((e) => `- ${e.id} (${issueOf(tasks[e.id].task)}): diff ${e.diff}; test: ${e.test}`).join('\n')}${proofText}
Design decisions the results must follow (they are not findings):
${args.decisions || '(none given)'}${answered ? `\nThe lead's answers per task (they are not findings):\n${answered}` : ''}${rules}${lens}
1. Run each test. Score each result 1 to 5 on correctness, code rules, tests and scope.
2. For each pair that solves alike or clashes, say which is better and why.
3. List findings. Mark a finding cross_issue when it spans 2 or more results.
4. Give each finding a severity of ${SEVERITIES.join(', ')} and evidence a second reader can check.${fixLaneOn ? '\n5. Set guard true on a major that breaks a convergence guard: a second path, a duplicate store or forwarder, or a second mount path.' : ''}`,
      { label: 'review wave', phase: 'Review', schema: reviewSchema, ...spawn('reviewer', ROLE_TIER.reviewer) },
    )
  }
  if (!rv) {
    for (const id of endIds) {
      move(id, 'reviewed')
      stop(id, 'escalated', 'the review returned nothing')
    }
    return
  }
  const inEnd = (f) => f.ids.filter((x) => endIds.includes(x))
  const named = rv.findings.filter((f) => inEnd(f).length > 0)
  for (const f of named) for (const id of inEnd(f)) tasks[id].findings[f.severity]++
  reviews.push({ ids: endIds, scores: rv.scores, pairs: rv.pairs || [], findings: named, dropped: [], blast: proofs, blast_skipped: [] })
  const minor = named.filter((f) => f.severity === 'minor')
  if (minor.length > 0) {
    followUp = {
      title: `Minor review findings of wave ${wave}`,
      body: [`The end review of ${wave} at ${heads[wave]} found ${minor.length} minor finding${minor.length === 1 ? '' : 's'}:`, '', ...minor.map((f) => `- [ ] ${f.id} (${inEnd(f).join(', ')}): ${f.claim} Evidence: ${f.evidence}`)].join('\n'),
    }
  }
  const owner = (f) => inEnd(f).reduce((a, b) => (tasks[b].order > tasks[a].order ? b : a))
  // The fix lane runs before the rework loop: a finding it fixed opens no rework round and escalates no task.
  const fixable = fixLaneOn && !fixDone ? named.filter((f) => f.severity === 'critical' || (f.severity === 'major' && f.guard === true)) : []
  let handled = []
  let fixWhy = ''
  if (fixable.length > 0) {
    if (await fixLane('review', [...new Set(fixable.flatMap(inEnd))], fixable)) {
      handled = fixable
      if (args.converge_gate && (chains.length === 0 || convergedOk)) await gateAgain()
    } else fixWhy = `; the fix lane ran and did not merge: ${fixFail}`
  }
  const rounds = Math.min(1, limit)
  for (const id of endIds) {
    move(id, 'reviewed')
    const own = named.filter((f) => f.severity !== 'minor' && owner(f) === id && !handled.includes(f))
    if (own.length === 0) move(id, 'done')
    else if (tasks[id].rounds < rounds) track(rework(id, own))
    else stop(id, 'escalated', `findings ${own.map((f) => f.id).join(', ')} stand after ${tasks[id].rounds} rework rounds${own.some((f) => fixable.includes(f)) ? fixWhy : ''}`)
  }
}

// prReady: converge early. Once the converged head (or, with no chain, the head after the last build merge)
// passed the gate, the lead opens the wave PR, so CI runs while the other tasks and the end review finish.
const prReady = () => log(`${wave} at ${heads[wave]} passed the gate: open the wave PR now; CI runs while the rest finishes. Merge only with no open CRITICAL.`)

// ---- Converge gate: args.converge_gate runs once on the converged head, before the end review. Red:
// 1 rework round on the task the failure names, then it runs again; else the lead gets it under escalations.
let convergeGate = null
const gateOwner = (text) => {
  const done = ids.filter((id) => tasks[id].order > 0)
  const covers = done.filter((id) => [...(tasks[id].task.files || []), ...(tasks[id].task.oracle.files || [])].some((f) => text.includes(f)))
  const last = (xs) => xs.reduce((a, b) => (tasks[b].order > tasks[a].order ? b : a), xs[0])
  return covers.length > 0 ? last(covers) : done.length > 0 ? last(done) : null
}
const gateRun = (again, after = 'a rework round') => serial(wave, async () => {
  phase('Converge')
  const m = await call([], `Run the converge gate on the head of the wave branch ${wave} of ${graph.repo}${again ? ` once more, after ${after}` : ''}. Edit, commit and push nothing, and open no pull request.
${makeWave(wave)}
2. ${resetup(`${root}/${wave}`)}Run the converge gate once: ${args.converge_gate}.${EXIT_CODE}${redText("the wave's")}
3. Report branch ${wave}, sha (git rev-parse HEAD), merged [], reworked [] and the last output line of the converge gate in notes. Green: oracle_passed true. Red: oracle_passed false, and in escalation the last output line, then each failing test with its file path. When the gate could not run, say the error in escalation.
Keep the worktree. Never touch main. ${TIMES}
When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`,
  { label: again ? 'converge gate 2' : 'converge gate', phase: 'Converge', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) })
  if (m) know(m.at)
  return { command: args.converge_gate, passed: merged(m), line: m ? (merged(m) ? m.notes : m.escalation) || (merged(m) ? 'passed' : 'red') : 'the integrator returned nothing' }
})
async function runConvergeGate() {
  if (!args.converge_gate || mergeCount === 0 || (chains.length > 0 && !convergedOk)) return
  convergeGate = await gateRun(false)
  log(`converge gate on ${wave} at ${heads[wave]}: ${convergeGate.passed ? 'passed' : 'red'}: ${convergeGate.line}`)
  if (convergeGate.passed) return
  const id = gateOwner(convergeGate.line)
  const s = id && tasks[id]
  if (!s || s.state !== 'integrated' || s.rounds >= Math.min(1, limit)) {
    convergeGate.reason = `the converge gate "${args.converge_gate}" is red on ${wave} at ${heads[wave]}: ${convergeGate.line}${id ? `; task ${id} has no rework round left` : ''}`
    return gateFix()
  }
  move(id, 'reviewed')
  await rework(id, [{ id: 'converge_gate', severity: 'major', claim: `The converge gate (${args.converge_gate}) is red on the converged wave head ${heads[wave]}. Fix the failure that touches this task.`, evidence: convergeGate.line }], true)
  if (s.state === 'escalated') {
    convergeGate.reason = `the converge gate "${args.converge_gate}" is red on ${wave}: ${convergeGate.line}; the rework of task ${id} stopped`
    return
  }
  const again = await gateRun(true)
  log(`converge gate after the rework of ${id}: ${again.passed ? 'passed' : 'red'}: ${again.line}`)
  convergeGate = { ...again, rework: id }
  if (!again.passed) {
    convergeGate.reason = `the converge gate "${args.converge_gate}" is still red on ${wave} after the rework of task ${id}: ${again.line}`
    await gateFix()
  }
}

// ---- Converge: when every chain task has ended, 1 integrator merges the chain branches into the wave
// branch in the order each chain first appears in the graph, resolves the conflicts, and runs the gate
// once, after the last merge. Then the end review reads the converged head.
const converged = deferred()
let convergence = null
function converge() {
  const ready = chains.filter((c) => ids.some((id) => chainOf(id) === c && (tasks[id].order > 0 || tasks[id].before)))
  if (ready.length === 0) return converged.resolve(true)
  const branches = ready.map(chainBranch)
  const check = args.gate || [...new Set(ids.filter(chainOf).map((id) => (tasks[id].plan || tasks[id].task).oracle.command))].join(' && ')
  return serial(wave, async () => {
    phase('Converge')
    const m = await call([], `Converge the chains of the wave into the wave branch ${wave} of ${graph.repo}. Merge these chain branches in this order: ${branches.join(', ')}.
${makeWave(wave)}
2. For each chain branch in order: git merge --no-ff -m "Merge <branch> into ${wave}" origin/<branch>. On a conflict, resolve it when both sides are clear; keep the behaviour of both. When the 2 sides change the same contract in 2 ways, run git merge --abort and set escalation to the branch and the files. Fix a small integration break yourself (10 lines or fewer) and name each fix in reworked.
3. ${resetup(`${root}/${wave}`)}After the last merge, run the gate once: ${check}. Do not run it after each merge.${redText('the wave\'s')}
4. Green: git push -q origin ${wave}. Report branch ${wave}, merged (the chain branches in order), oracle_passed true, reproved true and the full 40-character SHA of the push.
   Then, only when the push printed no error, prune the chain branches: git fetch -q origin. For each of ${branches.join(' ')}: when git merge-base --is-ancestor origin/<branch> origin/${wave} exits 0, delete it: git push -q origin --delete <branch>, then git worktree remove --force ${root}/<branch> and git branch -D <branch>, each only when present. Name the exact branch; never a pattern. Else keep it and add "<branch>: not merged into ${wave}" to kept. Never delete ${wave} or main: the wave PR merge deletes ${wave}. Report pruned true only when every chain branch is deleted, and pruned_branch: the branches deleted, space-separated. A failed delete does not fail the converge: keep oracle_passed true, set pruned false and say why in kept.
   Red: report oracle_passed false and the last output line in escalation. ${args.gate ? `Find whose red it is: run git reset -q --hard origin/${wave}, then run the gate once on that pre-merge tip. When it is red there too, set base_red: kind base, check ${args.gate}, its last output line on the tip, and the tip SHA (git rev-parse HEAD). When the gate could not run at all after the merges and could not run on the tip either, with the same error, set base_red: kind infra, check ${args.gate}, that error as line (the same text as escalation), and the tip SHA. When the gate ran green on the tip, leave base_red out. ` : ''}Push nothing, and remove the worktree: git worktree remove --force ${root}/${wave}.
Open no pull request. Never touch main. ${TIMES}
When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.${rules}`,
    { label: 'converge', phase: 'Converge', schema: mergeSchema, ...spawn('integrator', ROLE_TIER.integrator) })
    convergence = { branches, merge: m }
    // A base red at the converge holds it as 1 base_red entry, with the chain tasks it holds.
    if (!merged(m) && notTask(m, heads[wave] || graph.base.sha)) {
      const h = holdOf(wave, m.base_red)
      for (const id of ids.filter(chainOf)) if (tasks[id].state === 'integrated') { h.holds.push(id); tasks[id].held = h; tasks[id].reason = `held by ${h.kind} red on ${wave} at the converge: ${h.check}: ${h.line}` }
      convergence.held = true
      return converged.resolve(false)
    }
    if (!merged(m)) {
      const reason = `the converge of ${branches.join(', ')} failed: ${m ? m.escalation || 'the gate is red' : 'the integrator returned nothing'}`
      for (const id of ids.filter(chainOf)) if (tasks[id].state === 'integrated') tasks[id].reason = reason
      convergence.reason = reason
      log(reason)
      return converged.resolve(false)
    }
    know(m.at)
    heads[wave] = m.sha
    convergedOk = true
    log(`converge: ${m.pruned ? `deleted ${m.pruned_branch}` : 'no chain branch deleted'}${(m.kept || []).length > 0 ? `; kept ${m.kept.join('; ')}` : ''}`)
    log(`converge: ${branches.join(', ')} merged into ${wave} at ${m.sha}; the gate ran once and passed`)
    prReady()
    converged.resolve(true)
  })
}

// openChain(c): the branch of gated chain c, cut from the wave branch after every task of gateOf(c) merged.
// 1 promise per chain. A branch the remote check found (an earlier run cut it) opens with no agent. On a
// re-run, git log --merges of that branch also lists the gate task's merge into the wave branch; that is
// correct: MERGE_SUBJECT only reads the task branch name.
const opened = new Map()
function openChain(c) {
  if (!opened.has(c)) opened.set(c, (async () => {
    if (heads[chainBranch(c)]) return true
    const gate = gateOf(c)
    const ok = await Promise.all(gate.map((g) => tasks[g].integrated.promise))
    if (!ok.every(Boolean)) {
      log(`chain ${c}: not opened, ${gate.filter((g, i) => !ok[i]).join(', ')} not integrated`)
      return false
    }
    return serial(wave, async () => {
      const rm = await call([], `Open the chain branch ${chainBranch(c)} of ${graph.repo} at the head of the wave branch ${wave}. Read-only except 1 push. Edit and commit nothing, open no pull request.
1. git fetch -q origin
2. git push -q origin origin/${wave}:refs/heads/${chainBranch(c)}
3. git fetch -q origin
Report heads: branch ${chainBranch(c)} and its full SHA (git rev-parse origin/${chainBranch(c)}). Report merges [].${rules}`,
      { label: `open chain ${c}`, phase: 'Build', schema: remoteSchema, ...spawn('integrator', FIRST_TRY.integrator) })
      const tip = ((rm && rm.heads) || []).find((h) => h.branch === chainBranch(c) && FULL_SHA.test(h.sha))
      if (!tip) {
        log(`chain ${c}: not opened, ${rm ? `no valid head of ${chainBranch(c)} in the answer` : 'the agent returned nothing'}`)
        return false
      }
      heads[chainBranch(c)] = tip.sha
      log(`chain ${c}: branch ${chainBranch(c)} cut from ${wave} at ${tip.sha} after ${gate.join(', ')} merged`)
      return true
    })
  })())
  return opened.get(c)
}

// writeBrief: the brief of id, checked. A stale brief (s.stale) goes to a brief-writer once, and its new
// files must exist; a second stale brief stops the task with no worker. Returns null when the task stopped.
async function writeBrief(id) {
  const s = tasks[id]
  const fail = (reason) => { stop(id, s.state === 'planned' ? 'escalated' : null, reason); return null }
  const stale = s.stale
  s.stale = null
  if (stale && s.rebriefed) return fail(`the brief is stale again after 1 new brief: ${stale.join('; ')}`)
  if (stale) s.rebriefed = true
  const plan = await brief(id, stale)
  if (!plan) return fail('the brief-writer returned nothing')
  const badBrief = tierMeaning(`brief ${id}`, plan)
  if (badBrief.length > 0) return fail(badBrief.join('; '))
  // 1 check agent: the paths of a new brief after a stale one, and the callers of each symbol or path the
  // brief removes with no alias. When no brief-writer listed removes (a ready issue, a graph brief), the
  // agent reads them from the brief text. No answer escalates: no worker starts on an unchecked brief.
  const removes = plan.removes === undefined ? null : plan.removes
  const paths = stale ? toFind(id, plan.files, plan.brief) : []
  if (paths.length > 0 || removes === null || removes.length > 0) {
    const got = await briefCheck([{ id, paths, removes, brief: plan.brief }], `check ${id}`, 'Brief')
    if (!got) return fail(`the brief check returned nothing: ${paths.length > 0 ? 'its paths and ' : ''}the callers of what it removes are unchecked, so no worker starts`)
    const { missing, hits } = got.get(id) || { missing: [], hits: [] }
    if (missing.length > 0) return fail(`the new brief still names paths that do not exist: ${missing.join(', ')}`)
    const gone = hits.map((h) => h.symbol)
    // A symbol or path the brief removes: a caller outside the task's files, or in an oracle file it
    // does not own, goes to the lead before a worker starts.
    const outside = hits.map((h) => ({ ...h, files: h.files.filter((f) => !gone.includes(f) && overlap([f], plan.files).length === 0) })).filter((h) => h.files.length > 0)
    const locked = [...new Set(outside.flatMap((h) => h.files))].filter((f) => overlap([f], plan.oracle.files || []).length > 0)
    if (outside.length > 0) return fail(`removes ${outside.map((h) => h.symbol).join(', ')}: callers outside the files of ${id}: ${outside.map((h) => `${h.symbol} in ${h.files.join(', ')}`).join('; ')}${locked.length > 0 ? `; locked oracle files: ${locked.join(', ')}` : ''}. Widen the files, serialize, or re-split.`)
  }
  // A brief's files and oracle replace the plan's. Files that widen into a task beside it serialize the
  // 2 tasks; then the graph check runs again on the updated graph.
  serialize(id, plan.files)
  const widened = chainMeaning({ ...graph, tasks: graph.tasks.map((x) => ({ ...x, ...(x.id === id ? plan : tasks[x.id].plan), blockers: blockersOf(x.id) })) })
  if (widened.length > 0) return fail(widened.join('; '))
  // A brief that leaves out the graph's oracle.reach keeps it: the reach is the planner's decision.
  const reach = s.task.oracle.reach
  s.plan = reach && !plan.oracle.reach ? { ...plan, oracle: { ...plan.oracle, reach } } : plan
  s.tier = plan.tier
  return s.plan
}

// ---- The graph: every task runs at once and waits on its blockers.
async function runTask(id) {
  const s = tasks[id]
  if (s.before) return
  const t = s.task
  const lacks = (t.needs || []).filter((n) => !hasCapability(runtime, n))
  if (lacks.length > 0) return stop(id, 'escalated', `needs ${lacks.join(', ')}; runtime ${runtime.provider} lacks it, so a peer that has it takes the task`)
  if (!claimOf(id)) return stop(id, null, 'no claim: the lead posts 1 claim comment per task and passes its URL in args.claims')
  const building = await Promise.all(t.blockers.map((b) => tasks[b].building.promise))
  if (!building.every(Boolean)) return stop(id, null, `blocker ${t.blockers.filter((b, i) => !building[i]).join(', ')} did not start`)
  let plan = await writeBrief(id)
  if (!plan) return
  move(id, 'briefed')
  // A task with no chain that waits on a chain task starts after the converge: then the code is on the wave branch.
  // A chain task that waits on a no-chain task waits only on its merge: the converge waits on the chain task.
  const integrated = await Promise.all(t.blockers.map((b) => (chainOf(b) === chainOf(id) || !chainOf(b) ? tasks[b].integrated.promise : Promise.all([tasks[b].integrated.promise, converged.promise]).then((xs) => xs.every(Boolean)))))
  const notIn = t.blockers.filter((b, i) => !integrated[i])
  const heldBy = notIn.find((b) => tasks[b].held)
  if (heldBy && notIn.every((b) => tasks[b].held)) return hold(id, tasks[heldBy].held, `waits on ${heldBy}`)
  if (notIn.length > 0) return stop(id, null, `blocker ${notIn.join(', ')} was not integrated`)
  // Every task of a gated chain waits on its branch: it does not exist before then.
  if (chainOf(id) && gateOf(chainOf(id)).length > 0 && !(await openChain(chainOf(id)))) return stop(id, null, `chain ${chainOf(id)} did not open: ${gateOf(chainOf(id)).join(', ')} not integrated`)
  // A serialized task waits for the other task to end, merged or not: they share files, not code.
  await Promise.all(s.after.map((x) => tasks[x].integrated.promise))
  // A merge since the brief deleted or renamed a path it names, or did its work: no worker on that brief.
  while (s.stale) {
    plan = await writeBrief(id)
    if (!plan) return
    await Promise.all(s.after.map((x) => tasks[x].integrated.promise))
  }
  move(id, 'claimed', { reason: claimOf(id) })
  move(id, 'building')
  s.building.resolve(true)
  let r = t.split ? await buildSplit(id, plan) : await build(id, plan)
  let refused = t.split && !r ? s.reason : verify(r, id, s.branch)
  // A report SHA that is no commit, with the branch already in the target: an earlier merge attempt merged it.
  let m = null
  if (refused && r && r.status === 'done' && badSha(r.sha)) {
    const head = await mergedHead(id, s.branch)
    if (head) {
      r = { ...r, sha: head }
      refused = verify(r, id, s.branch)
      if (!refused) {
        log(`${id}: the report SHA was no commit, but ${s.branch} at ${head} is already merged into ${targetOf(id)}`)
        s.order = ++mergeCount
        m = { ok: true, diff: `${heads[targetOf(id)]}...${head}` }
      }
    }
  }
  if (refused) return stop(id, 'escalated', refused)
  know(r.at)
  if (r.notes) s.notes.push(r.notes)
  s.reports.push(r)
  move(id, 'built')
  m = m || await integrate(id, r)
  if (!m.ok) return m.base ? hold(id, holdOf(targetOf(id), m.base)) : stop(id, 'escalated', m.reason)
  move(id, 'integrated')
  s.integrated.resolve(true)
  enqueue({ id, diff: m.diff, test: plan.oracle.command })
}

// canStart: the task has a claim, and the runtime has each capability it needs.
const canStart = (id) => Boolean(claimOf(id)) && (tasks[id].task.needs || []).every((n) => hasCapability(runtime, n))

// ---- Answer and continue: before the oracle check, 1 agent reads what an earlier run of the same graph
// left on the remote. A task whose merge commit ("Merge <task branch or its rework branch> into ...") is
// there is skipped. A task whose branch is there resumes from its head, as if resume_from were set; the
// lead's answer is already last in its brief. The lead changes no graph by hand.
const MERGE_SUBJECT = /^Merge (\S+) into \S+$/
// reworkRound: the round N of a rework branch `<task branch>-r<N>` of task s, else 0.
const reworkRound = (b, s) => (b.startsWith(`${s.branch}-r`) && /^\d+$/.test(b.slice(s.branch.length + 2)) ? Number(b.slice(s.branch.length + 2)) : 0)
const isTaskBranch = (b, s) => b === s.branch || (b.startsWith(`${s.branch}-r`) && /^\d+$/.test(b.slice(s.branch.length + 2)))
if (ids.some(canStart)) {
  phase('Check')
  const targets = [wave, ...chains.map(chainBranch)]
  const named = [...targets, ...ids.map((id) => tasks[id].branch)]
  // A gated chain is not made at the base: openChain cuts it after its gate tasks merge.
  const ungated = chains.filter((c) => gateOf(c).length === 0)
  const rm = await call([], `Read what an earlier run of this wave left on the remote of ${graph.repo}. Edit and commit nothing, open no pull request${ungated.length > 0 ? ', and push nothing but step 2' : ': push nothing'}.
1. git fetch -q origin${ungated.length > 0 ? `
2. Make each of these chain branches that is not on the remote, at the base: git push -q origin ${graph.base.sha}:refs/heads/<branch>. Then git fetch -q origin.
   ${ungated.map(chainBranch).join(' ')}` : ''}
${ungated.length > 0 ? 3 : 2}. For each of these branches that is on the remote, report its head (git rev-parse origin/<branch>). Leave out a branch that is not there:
   ${named.join(' ')}
${ungated.length > 0 ? 4 : 3}. For each of these branches that is on the remote, report the subject of each merge commit on it since the base, verbatim: git log --merges --format=%s ${graph.base.sha}..origin/<branch>
   ${targets.join(' ')}
Report heads (branch and full SHA) and merges (the subjects).${rules}`,
    { label: 'remote check', phase: 'Check', schema: remoteSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  if (!rm) log('remote check: the agent returned nothing; the run starts as a first run')
  const done = new Set((rm ? rm.merges : []).map((m) => (MERGE_SUBJECT.exec(m) || [])[1]).filter(Boolean))
  const head = Object.fromEntries((rm ? rm.heads : []).filter((h) => FULL_SHA.test(h.sha)).map((h) => [h.branch, h.sha]))
  for (const b of [wave, ...chains.map(chainBranch)]) if (head[b]) heads[b] = head[b]
  for (const id of ids) {
    const s = tasks[id]
    if ([...done].some((b) => isTaskBranch(b, s))) {
      s.before = true
      s.building.resolve(true)
      s.integrated.resolve(true)
      // A new answer: no rework branch of the task is merged yet. No state is kept between runs; the answer
      // round leaves its own merge commit, so the same args on the next run skip the task. A task the end
      // review already reworked counts as having seen its answer.
      const n = Math.max(0, ...[...done].map((b) => reworkRound(b, s)))
      if (answers[id] && n === 0) {
        if (n + 1 > limit) {
          s.notes.push(`answer not applied: round ${n + 1} is over the rework limit ${limit}`)
          log(`${id}: merged by an earlier run; the answer is not applied: round ${n + 1} is over the rework limit ${limit}`)
        } else {
          s.answerRound = n + 1
          log(`${id}: merged by an earlier run; the new answer gets rework round ${s.answerRound} from ${wave}`)
        }
      } else {
        log(`${id}: merged into ${targetOf(id)} by an earlier run; skipped`)
      }
    } else if (head[s.branch] && !s.task.resume_from) {
      s.task = { ...s.task, resume_from: head[s.branch] }
      log(`${id}: resumes from its branch head ${head[s.branch]}${answers[id] ? ', with the lead answer last in its brief' : ''}`)
    }
  }
}
// ---- Check: after the remote check and before any other agent, 1 agent runs the oracle of each task that can start in list mode,
// on the commit its branch starts from. An oracle that selects 0 tests refuses the graph: every task of
// its chain would fail on it. A task whose oracle files the wave itself writes is skipped. No answer, or a runner with no list mode, refuses nothing.
const checkAt = (t) => startOf(t) || graph.base.sha
// An oracle whose files all sit in the task's own files, or in the files of a task it waits on, is
// written by the wave: it selects 0 tests on the base by design, so it is not checked.
const writtenByWave = (id) => {
  const of = tasks[id].task.oracle.files
  const made = [id, ...reachOf(id)].flatMap(filesOf)
  return of.length > 0 && of.every((f) => overlap([f], made).length > 0)
}
let checkTimes = null
// briefText: the brief of a task: the written one, else the graph brief, else its issue body.
const briefText = (id) => (tasks[id].plan ? tasks[id].plan.brief : tasks[id].task.brief || issues[id] || '')
// toFind: the paths of files that must exist already: not a file of a task id waits on, not an oracle
// file the wave writes for id, and not a path the brief marks "creates" in its sentence.
const CREATES = /\b(creates?|new file)\b/i
function toFind(id, files, text) {
  const made = [...[...reachOf(id)].flatMap(filesOf), ...(writtenByWave(id) ? tasks[id].task.oracle.files : [])]
  const marked = (f) => text.split(/\n|\.\s/).some((l) => l.includes(f) && CREATES.test(l))
  return files.filter((f) => overlap([f], made).length === 0 && !marked(f))
}
// briefCheck: 1 read-only agent over entries {id, paths, removes, brief}. paths: the Files paths to find.
// removes: the symbols or paths to grep, or null when no brief-writer listed them: then the agent reads them
// from the brief. Returns id -> {missing, hits}: the asked paths it reports missing, the symbols with a
// caller. Returns null when the agent returned nothing.
async function briefCheck(list, label, at) {
  const ask = (e) => [
    e.paths.length > 0 ? ` at ${checkAt(tasks[e.id].task)} and origin/${targetOf(e.id)}: ${e.paths.join(' ')}` : '',
    e.removes === null
      ? `\n  removes: read them from the brief: each symbol or path its Done when or the lead's answers rename or delete with no alias left. Grep each on origin/${targetOf(e.id)}.\n  Brief:\n${e.brief.split('\n').map((l) => `    ${l}`).join('\n')}`
      : e.removes.length > 0 ? `\n  removes, grep on origin/${targetOf(e.id)}: ${e.removes.join(' ')}` : '',
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
// ---- Stale after a merge: the paths a task merge deleted or renamed away, and the tasks its notes say it
// absorbed, against the brief of each task that has not started. A hit sends that task back to a
// brief-writer before it gets a worker (writeBrief).
const ABSORBED = /\babsorb|\balready (did|done|built|covered|covers)|nothing left/i
const esc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const names = (text, x) => new RegExp(`(^|[^\\w-])${esc(x)}(?![\\w-])`).test(text)
function staleAfter(id, gone, notes) {
  const absorbed = ids.filter((x) => x !== id && notes.split('\n').some((l) => ABSORBED.test(l) && names(l, x)))
  if (gone.length === 0 && absorbed.length === 0) return
  for (const x of ids) {
    const s = tasks[x]
    if (x === id || s.before || s.reason || !['planned', 'briefed'].includes(s.state) || (chainOf(x) && chainOf(x) !== chainOf(id))) continue
    const text = briefText(x)
    const paths = gone.filter((f) => overlap([f], filesOf(x)).length > 0 || text.includes(f))
    const done = absorbed.filter((y) => y === x || names(text, y))
    const why = [...(paths.length > 0 ? [`the merge of ${id} deleted or renamed ${paths.join(', ')}`] : []), ...(done.length > 0 ? [`the notes of ${id} say it absorbed ${done.join(', ')}`] : [])]
    if (why.length === 0) continue
    s.stale = [...(s.stale || []), ...why]
    log(`${x}: ${why.join('; ')}; its brief goes back to a brief-writer before any worker`)
  }
}
const toCheck = ids.filter((id) => canStart(id) && !tasks[id].before && !writtenByWave(id))
if (toCheck.length > 0) {
  phase('Check')
  const ol = await call([], `Check the oracle of each task of ${graph.repo} before the wave starts. Read only: edit, commit and push nothing, open no pull request.
For each task below:
1. git fetch -q origin && git worktree add --detach ${root}/oracle-<task> <commit>${setupLine(`each worktree you make (${root}/oracle-<task>, ${root}/oracle-base)`)}
2. In that worktree, run the oracle command in list mode: it lists the tests it selects and runs none (Playwright: add --list; other runners: their list or collect-only flag). Count the tests it selects.
3. When the runner has no list mode, run nothing: set listed false and selected 0.
4. git worktree remove --force ${root}/oracle-<task>
Then run each oracle command once, not in list mode, on the wave base ${graph.base.sha} (git worktree add --detach ${root}/oracle-base ${graph.base.sha}; remove it after). When 2 tasks share a command, run it once. List in red each test that fails there, by name as the runner prints it; [] when all pass. A test file that is not on the base is not red.
Report 1 entry per task: task, the command you ran, listed, selected, the last output line and red. ${TIMES}
Tasks:
${toCheck.map((id) => `- ${id} at ${checkAt(tasks[id].task)}: ${tasks[id].task.oracle.command}`).join('\n')}${rules}`,
    { label: 'oracle check', phase: 'Check', schema: oracleListSchema, ...spawn('integrator', FIRST_TRY.integrator) })
  if (!ol) log('oracle check: the agent returned nothing; no task is refused')
  checkTimes = ol
  for (const e of ol ? ol.tasks : []) for (const x of e.red || []) baseRed.add(x)
  if (baseRed.size > 0) log(`red on the base ${graph.base.sha}, so no task's: ${[...baseRed].join('; ')}`)
  const empty = (ol ? ol.tasks : []).filter((e) => toCheck.includes(e.task) && e.listed && e.selected === 0)
  if (empty.length > 0) throw new Error(`the graph fails the oracle check: ${empty.map((e) => `task ${e.task}: its oracle "${e.command}" selects 0 tests on ${checkAt(tasks[e.task].task)} (${e.line})`).join('; ')}`)
}

// ---- Path check: after the oracle check, 1 agent confirms each path of the Files list of each task that
// can start exists at the commit it starts from, or on its target. A path the task or a task it waits on
// creates is not checked. A task with a missing path goes back to a brief-writer, not to a worker.
const pathTasks = ids.filter((id) => canStart(id) && !tasks[id].before).map((id) => [id, toFind(id, filesOf(id), briefText(id))]).filter(([, f]) => f.length > 0)
if (pathTasks.length > 0) {
  phase('Check')
  const found = await briefCheck(pathTasks.map(([id, paths]) => ({ id, paths, removes: [] })), 'path check', 'Check')
  // No answer marks the tasks unchecked and goes on: 1 failed agent does not stop every task of the wave,
  // the worker still stops on a missing path, and the result names each unchecked task for the lead.
  if (!found) for (const [id] of pathTasks) {
    tasks[id].unchecked = 'paths'
    log(`${id}: unchecked: the path check returned nothing, so its Files paths are not checked`)
  }
  for (const [id, { missing }] of found || []) {
    if (missing.length === 0) continue
    tasks[id].stale = [`these paths of its Files list do not exist at ${checkAt(tasks[id].task)}: ${missing.join(', ')}`]
    log(`${id}: ${tasks[id].stale[0]}; it goes back to a brief-writer`)
  }
}

phase('Build')
const runs = ids.map(runTask)
if (chains.length > 0) {
  await Promise.all(runs.filter((_, i) => chainOf(ids[i])))
  await converge()
}
await Promise.all(runs)
if (chains.length === 0 && mergeCount > 0) prReady()
await runConvergeGate()
// A chain task is reviewed only on the converged head; a failed converge leaves it integrated on its chain.
const reviewable = (e) => convergedOk || !chainOf(e.id)
if (reviewMode === 'end' && queue.some(reviewable)) {
  await drained()
  phase('Review')
  await reviewEnd(queue.splice(0).filter(reviewable))
}
// ---- Answer rework: a task merged by an earlier run with a new answer gets 1 rework round. This runs
// after the build, the converge and the end review, so the wave branch holds every merge and the round
// starts from the final wave head. A batch review reviews the round in the loop below. One at a time: the tasks may edit the same files.
for (const id of ids.filter((x) => tasks[x].answerRound > 0)) {
  const s = tasks[id]
  if (chainOf(id) && !convergedOk) {
    s.notes.push('answer not applied: the chains did not converge')
    log(`${id}: answer not applied: the chains did not converge`)
    continue
  }
  // The earlier run merged and reviewed the task: it enters the rework round from there.
  s.state = 'reviewed'
  s.plan = { files: s.task.files, oracle: s.task.oracle, tier: s.tier, brief: '' }
  s.rounds = s.answerRound - 1
  await rework(id, [{ id: 'answer', severity: 'major', claim: 'The lead answered this task after it merged. Apply the answer.', evidence: 'The answer is in the lead answers below.' }])
}

for (;;) {
  if (inflight.size > 0) await Promise.all([...inflight])
  else if (queue.length > 0) track(review(queue.splice(0, REVIEW_BATCH)))
  else break
}
await drained()

// ---- Reopen: a task issue closed at a validated merge reopens when the task does not end merged: a review
// finding with no round left, a red rework merge, a fix lane that did not merge, a failed converge.
const toReopen = ids.filter((id) => tasks[id].closedAt && tasks[id].state !== 'done')
if (toReopen.length > 0) {
  phase('Report')
  await parallel(toReopen.map((id) => async () => {
    const s = tasks[id]
    const why = s.reason || `the task ends ${s.state}, not merged`
    const v = await call(id, `Reopen issue #${s.task.issue} of ${graph.repo}. It closed when task ${id} merged, but the task did not end merged. Edit, commit and push nothing.
1. gh issue reopen ${s.task.issue} --repo ${graph.repo} --comment <the text below, quoted for the shell>
   Reopened by wave ${wave}: task ${id} ${s.state}: ${why}
2. Set agree to true when the command exits 0 (an issue that is already open counts), and to false when it does not. Set reason to its last output line.${rules}`,
      { label: `reopen ${id}`, phase: 'Report', schema: verdictSchema, ...spawn('integrator', FIRST_TRY.integrator) })
    if (v && v.agree) {
      s.closedAt = null
      s.reopened = true
      log(`${id}: issue #${s.task.issue} reopened: ${why}`)
    } else {
      s.reason = `${why}; issue #${s.task.issue} is still closed: the reopen failed: ${v ? v.reason : 'the agent returned nothing'}`
      log(`${id}: ${s.reason}`)
    }
  }))
}

// ---- Report: 1 metrics row per task that started an agent. This runtime reports no usage.
phase('Report')
// Regression lane: base first, then head, 2 agents at most. red on both and fixed are records, not escalations.
let regression
if (args.regression) {
  if (mergeCount === 0 && heads[wave] === graph.base.sha) {
    regression = { command: args.regression, skipped: 'nothing merged on the wave branch, so the head is the base' }
  } else {
    const base = await regress('base', graph.base.sha, args.regression)
    const head = await regress('head', heads[wave], args.regression)
    const verdict = !base || !head ? 'unknown' : base.passed && !head.passed ? 'regressed' : base.passed ? 'ok' : head.passed ? 'fixed' : 'red on both'
    regression = { command: args.regression, base, head, verdict }
  }
}
const convergeGateEscalation = convergeGate && convergeGate.reason ? [{ task: 'converge_gate', state: 'escalated', reason: convergeGate.reason }] : []
const regressionEscalation = !regression || !['regressed', 'unknown'].includes(regression.verdict) ? [] : [{
  task: 'regression', state: 'escalated',
  reason: regression.verdict === 'regressed'
    ? `the scenario "${regression.command}" passes on base ${regression.base.sha} and fails on head ${regression.head.sha}: ${regression.head.line}`
    : `the scenario "${regression.command}" has no result for ${[!regression.base && 'the base', !regression.head && 'the head'].filter(Boolean).join(' and ')}`,
}]
// secs: the sum of a time field over agent reports; a report with none counts 0.
const secs = (xs, k) => xs.filter(Boolean).reduce((n, x) => n + (Number(x[k]) || 0), 0)
const result = (s) => (s.state === 'done' ? 'merged' : s.state === 'escalated' ? 'escalated' : 'failed')
const metrics = ids
  .filter((id) => tasks[id].agents > 0)
  .map((id) => {
    const s = tasks[id]
    const sp = runtime.tiers[s.tier]
    return {
      task: id, provider: runtime.provider, tier: s.tier, model: sp.model, ...(sp.effort && { effort: sp.effort }),
      agents: s.agents, elapsed_s: Math.max(0, isoSeconds(s.integratedAt || newest) - isoSeconds(claimedAt[id] || args.started_at)),
      rework_rounds: s.rounds, browser_s: secs([...s.reports, ...s.merges], 'browser_s'), lock_wait_s: secs([...s.reports, ...s.merges], 'lock_wait_s'), ...(s.order > 0 && { reproved: s.merges.some((m) => merged(m) && m.reproved !== false) }), findings: s.findings, result: result(s), tokens: UNAVAILABLE, cost_usd: UNAVAILABLE,
      ...(s.closedAt && { closed_at: s.closedAt }), ...(s.pruned && (s.closedAt || s.reopened) && { pruned: true }), ...(s.reopened && { reopened: true }),
    }
  })
// The run summary: browser time and lock wait over every row, the oracle check and the converge.
const runOnly = [checkTimes, convergence && convergence.merge]
const browser = { browser_s: secs([...metrics, ...runOnly], 'browser_s'), lock_wait_s: secs([...metrics, ...runOnly], 'lock_wait_s') }
const earlier = ids.filter((id) => tasks[id].before)
const open = ids.filter((id) => tasks[id].state !== 'done' && (!tasks[id].before || tasks[id].state === 'escalated'))
const baseReds = Object.values(holds)
const scaffolds = ids.map((id) => tasks[id].scaffold).filter(Boolean)
const convergeEscalation = convergence && !convergedOk && !convergence.held ? [{ task: 'converge', state: 'escalated', reason: convergence.reason }] : []
log(`${ids.length - open.length} of ${ids.length} tasks done${earlier.length > 0 ? ` (${earlier.length} by an earlier run)` : ''} on ${wave} at ${heads[wave]}; ${open.length} need the lead${baseReds.length > 0 ? ` (${baseReds.length} base red)` : ''}${regression ? `; regression: ${regression.verdict || 'skipped'}` : ''}; browser ${browser.browser_s} s, lock wait ${browser.lock_wait_s} s`)

return {
  branch: wave,
  sha: heads[wave],
  done: ids.filter((id) => tasks[id].state === 'done'),
  ...(earlier.length > 0 && { merged_before: earlier }),
  ...browser,
  ...(regression && { regression }),
  ...(followUp && { follow_up: followUp }),
  ...(scaffolds.length > 0 && { scaffold: { deleted: scaffolds.flatMap((s) => s.deleted), kept: scaffolds.flatMap((s) => s.kept) } }),
  ...(convergence && { converge: convergence }),
  ...(convergeGate && { converge_gate: { command: convergeGate.command, passed: convergeGate.passed, line: convergeGate.line } }),
  ...(baseReds.length > 0 && { base_red: baseReds }),
  escalations: [...open.filter((id) => !tasks[id].held).map((id) => ({ task: id, state: tasks[id].state, reason: tasks[id].reason })), ...convergeEscalation, ...convergeGateEscalation, ...regressionEscalation],
  tasks: ids.map((id) => {
    const s = tasks[id]
    return { task: id, issue: s.task.issue, state: s.state, tier: s.tier, branch: s.branch, rounds: s.rounds, notes: s.notes, reports: s.reports, merges: s.merges, ...(s.scaffold && { scaffold: s.scaffold }), ...(s.closedAt && { closed_at: s.closedAt }), ...(s.pruned && { pruned: true }), ...(s.reopened && { reopened: true }), ...(s.unchecked && { unchecked: s.unchecked }), ...(s.held && { held: s.reason }) }
  }),
  reviews,
  metrics,
  transitions,
}
