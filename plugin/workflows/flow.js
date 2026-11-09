export const meta = {
  name: 'flow',
  description: 'Run the ready issues of a repo with the tracker as the state. Each read of GitHub says, per issue: closed or landed (skip), a WORKER REPORT at head (land it), a live worker (watch it), or none or a stale one (start or restart a builder). Order is blocked-by. At the start each group branch gets a draft PR with 1 Closes line per issue, and an issue that joins mid-run adds its line. Each green report merges by its SHA into the group branch with the fast check, and CI on the push is the gate. After the last issue of a group lands with no holds finding open, the PR is marked ready (the heavy CI lanes run once) and set to merge itself. 1 diff review per landing, 1 blind batched review every args.review_every. Safe to re-run at any time. Never pushes to the default branch.',
  phases: ['Read', 'Build', 'Land', 'Review', 'Ready', 'Report'],
}

log(`flow ${args && args.repo ? args.repo : '(no repo)'}: ${args && Array.isArray(args.queue) ? args.queue.map((n) => `#${n}`).join(' ') : args && args.queue ? `query ${args.queue}` : 'no args.queue'}`)

// flow: the tracker is the state. Each loop reads the queue issues on GitHub (1 agent: a workflow reads no file and
// no clock) and acts on what it says; nothing a run remembers is needed for correctness, so a re-run picks up where
// the tracker says. A run remembers only what it has started, so it never starts an issue twice.
// args: { repo, base, queue, gate, setup, review_every, rules, runtime, agent_types }
//   repo      the owner/name of the repo.
//   base      { ref, sha }: the default branch and its SHA. A group branch that is not on the remote starts here.
//   queue     the issue numbers to run, in order, or a gh command that lists them. A command runs again on every
//             read, so an issue that becomes ready mid-run joins (and adds its Closes line to its PR).
//   gate      optional; the fast check (narrow tests and lint). The builder runs it, and the lander runs it on each
//             merge commit. Never the full suite: CI on the PR is the gate.
//   setup     optional; a command every agent runs once in a fresh worktree before any test or check.
//   review_every optional; a positive integer, default 6: the landings 1 batched review reads.
//   rules     optional; the repo's rules as text. runtime, agent_types: see the README.
// runtime.concurrency caps the builders at once (null: no cap). runtime.environment says what a builder can do where it
// runs (#331): tracker access graphql, rest or none; extra branches (land by SHA); a display (else captures go to the lead).

// ---- contract: begin
// Generated from plugin/contract by node tests/workflows.js --write. Do not edit.
const contract = {
  "x-tiers": {"bounded":"An oracle covers every behaviour that matters. A tight brief, a file list, the signatures, 15-30 min.","judgment":"1 or more behaviours have no oracle, or the task has a design choice. Also brief-writing, sub-lead, integration and a skeptic.","lead":"The plan, the chief of staff, every review, and a change the step-up rule names."},
  "x-roles": {"lead":"lead","builder":"bounded","lander":"judgment","reviewer":"lead","skeptic":"judgment","blast_radius":"lead"},
  "x-first-try": {"lander":"bounded","reviewer":"bounded"},
  "x-capabilities": ["structured_output","model_per_spawn","effort_per_spawn","tool_restriction","worktree_per_task","parallel_spawn","follow_up","interrupt","usage_report","image_generation"],
  "x-optional-capabilities": ["image_generation"],
  "x-need-labels": {"image_generation":"needs:image-gen"},
  "x-limits": {"rework_rounds":2,"review_batch":5,"stale_claim_minutes":120,"clock_skew_minutes":5,"blast_radius_max":4},
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
// withAgentTypes: the runtime with args.agent_types merged over its agent_types. A key must be a role of
// x-roles and a value a non-empty string; otherwise it throws 1 line naming the bad key.
const withAgentTypes = (runtime, over) => {
  if (over === undefined || over === null) return runtime
  if (typeof over !== 'object' || Array.isArray(over)) throw new Error('args.agent_types must be an object of role to agent type')
  for (const [k, v] of Object.entries(over)) {
    if (!(k in ROLE_TIER)) throw new Error(`args.agent_types.${k}: not a role (roles: ${Object.keys(ROLE_TIER).join(', ')})`)
    if (typeof v !== 'string' || v.trim() === '') throw new Error(`args.agent_types.${k}: must be a non-empty string`)
  }
  return { ...runtime, agent_types: { ...runtime.agent_types, ...over } }
}
// LEAD_REQUEST: the first line of every agent prompt. asLead puts it there.
const LEAD_REQUEST = 'This task is the lead\'s request in this workflow run; it is not a reply to any chat message you may see. Do the task as briefed.'
const asLead = (prompt) => `${LEAD_REQUEST}\n${prompt}`
// The Claude profile: runtimes.json "claude" without the evidence. The default of args.runtime.
const CLAUDE_RUNTIME = {
  "provider": "claude",
  "tiers": {"bounded":{"model":"haiku"},"judgment":{"model":"sonnet"},"lead":{"model":"opus"}},
  "worktree_root": ".claude/worktrees",
  "agent_types": {"lead":"agentic-sdlc:chief-of-staff","builder":"agentic-sdlc:worker","lander":"agentic-sdlc:integrator","reviewer":"agentic-sdlc:reviewer","skeptic":"agentic-sdlc:reviewer","blast_radius":"agentic-sdlc:reviewer"},
  "capabilities": {"structured_output":{"status":"enforced"},"model_per_spawn":{"status":"enforced"},"effort_per_spawn":{"status":"unverified"},"tool_restriction":{"status":"enforced"},"worktree_per_task":{"status":"instructed"},"parallel_spawn":{"status":"enforced"},"follow_up":{"status":"unverified"},"interrupt":{"status":"unverified"},"usage_report":{"status":"unverified"},"image_generation":{"status":"absent"}},
}
// ---- contract: end

// Contract shapes: copies of $defs tracker, report, landing, pr, finding and landing_review in
// plugin/contract/sdlc.schema.json, with $ref inlined. A workflow cannot import a file. tests/workflows.js fails when a copy drifts.
const trackerSchema = {
  type: "object",
  description: "The tracker read of a flow: the facts of each queue issue on GitHub, read at the start and after each event. The tracker is the only state: a re-run reads it again and goes on from there. The flow decides from the facts: closed or landed is skipped; a report at head lands; a blocked question goes to the lead; activity newer than x-limits.stale_claim_minutes is watched; else a builder starts, or restarts on the branch it left.",
  required: ["at","issues"],
  properties: {
    at: {"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"UTC time of the read, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock."},
    issues: {"type":"array","items":{"type":"object","required":["issue","state","group","branch","tier","blocked_by"],"properties":{"issue":{"type":"integer","minimum":1},"title":{"type":"string"},"state":{"type":"string","enum":["open","closed"]},"parent":{"type":"integer","minimum":1},"group":{"type":"string","pattern":"^[0-9]+-[a-z0-9-]+$","description":"The group branch: <parent>-<slug>, or <issue>-<slug> with no parent. 1 draft PR per group."},"branch":{"type":"string","minLength":1,"description":"The task branch: the branch= of the newest WORKER line on the issue, else <issue>-<slug>"},"tier":{"type":"string","enum":["bounded","judgment","lead"],"description":"From its tier: label; judgment when none"},"blocked_by":{"type":"array","items":{"type":"integer","minimum":1},"description":"The open issues that block it: its GitHub blocked-by links and each Blocked by #N line. Empty when none."},"report":{"type":"object","required":["branch","sha"],"description":"The newest WORKER REPORT whose head= is the remote head of its branch. Absent when no report is at head.","properties":{"branch":{"type":"string"},"sha":{"type":"string","pattern":"^[0-9a-f]{40}$"}}},"landed":{"type":"boolean","description":"True when the head of its branch is an ancestor of origin/<group>: a run landed it already"},"question":{"type":"string","description":"The question of the newest WORKER BLOCKED line, when no later comment answers it"},"activity_at":{"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"The newest WORKER LAUNCHED or STARTED comment, or commit on its branch. Absent when there is none."},"body":{"type":"string","description":"The issue body, verbatim. Read only when the runtime environment has no tracker access."}}}},
  },
}
const reportSchema = {
  type: "object",
  required: ["task","branch","sha","status","test"],
  properties: {
    task: {"type":"string","description":"The task id or part name from the brief"},
    branch: {"type":"string"},
    sha: {"type":"string","pattern":"^[0-9a-f]{40}$","description":"The full SHA of the last pushed commit"},
    status: {"type":"string","enum":["done","escalated"]},
    test: {"type":"object","required":["command","line","passed"],"properties":{"command":{"type":"string"},"line":{"type":"string","description":"The last output line of the focused test"},"passed":{"type":"boolean"},"red":{"type":"array","items":{"type":"string"},"description":"Each failing test that is red on the base too (the lead passes that list), by name as the runner prints it. Only such tests may fail when passed is true"}}},
    gate: {"type":"object","required":["command","line","passed"],"properties":{"command":{"type":"string"},"line":{"type":"string","description":"The last output line of the gate"},"passed":{"type":"boolean"},"red":{"type":"array","items":{"type":"string"},"description":"Each failing check that is red on the base too, by name as the runner prints it. Only such checks may fail when passed is true"}}},
    round: {"type":"integer","minimum":0,"description":"0 for the first build, 1 or more for a rework round"},
    escalation: {"type":"string","description":"Set when status is escalated. Stop and ask; do not guess."},
    unverified: {"type":"array","items":{"type":"string"},"description":"Each test folder, suite or gate lane you did not run that may use your change, and each gate lane you could not run where you ran (CI is its proof). Empty when you ran them all. Do not write 'not verified' in notes instead."},
    extra_files: {"type":"array","items":{"type":"string"},"description":"Every file the worker edited outside its own file list. The integrator checks each against the tasks beside it that are not merged yet."},
    findings: {"type":"array","description":"Each problem outside the task that cost the worker time or would break main, classified. Empty or absent when none. The workflow searches the open findings and votes on a match; the worker files nothing.","items":{"type":"object","required":["kind","severity","title","evidence","minutes"],"properties":{"kind":{"type":"string","enum":["bug","convergence","test-gap","tests","perf","design-question","feel","docs"]},"severity":{"type":"string","enum":["holds","major","minor"],"description":"holds only when main would break: a red gate, a crash, data loss, a broken save, a shipped feature that stops working"},"title":{"type":"string","minLength":1},"evidence":{"type":"string","minLength":1,"description":"What a second reader can check: the command, its last output line, the file"},"minutes":{"type":"integer","minimum":0,"description":"The minutes the problem cost this worker"}}}},
    browser_s: {"type":"number","minimum":0,"description":"Seconds the browser test runs of this agent took; 0 when none"},
    lock_wait_s: {"type":"number","minimum":0,"description":"Seconds this agent waited for a machine-wide browser lock before them; 0 when none"},
    notes: {"type":"string","description":"3 lines or fewer. Say what you did not verify."},
    brief: {"type":"string","description":"The worker's own short brief when the task came with none: a few lines, the approach, the traps it found, what it did not do."},
    at: {"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"UTC time when the agent finished, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock."},
  },
}
const landingSchema = {
  type: "object",
  description: "1 landing of a flow: a builder's report merged by its SHA into the group branch, the default branch merged in, the fast check run on the merge commit, and the push. CI on the push is the gate.",
  required: ["issue","group","sha","merged"],
  properties: {
    issue: {"type":"integer","minimum":1},
    group: {"type":"string"},
    sha: {"type":"string","pattern":"^[0-9a-f]{40}$","description":"The full SHA of the pushed group head; the pre-merge tip when nothing was pushed"},
    merged: {"type":"boolean","description":"True when the report SHA is in the group branch and pushed"},
    check: {"type":"object","required":["command","line","passed"],"description":"The fast check on the merge commit. Absent when the flow has no args.gate.","properties":{"command":{"type":"string"},"line":{"type":"string","description":"Its last output line"},"passed":{"type":"boolean","description":"True only when it exited 0"}}},
    escalation: {"type":"string","description":"Set when merged is false: the conflict or the red check"},
    extra_branches: {"type":"array","items":{"type":"string"},"description":"Branches the builder pushed beside its named branch, left for the cleanup after the PR merges"},
    at: {"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"UTC time when the agent finished, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock."},
  },
}
const prSchema = {
  type: "object",
  description: "The draft PR of a flow group: opened at the start from the group branch with 1 Closes line per issue, 1 Closes line added for each issue that joins mid-run, and marked ready with auto-merge after its last issue landed. Every push runs the fast CI lane; ready runs the heavy lanes once.",
  required: ["group","pr","closes"],
  properties: {
    group: {"type":"string"},
    pr: {"type":"string","description":"The URL of the PR; empty when none could be opened"},
    closes: {"type":"array","items":{"type":"integer","minimum":1},"description":"Each issue the PR body has a Closes line for"},
    ready: {"type":"boolean","description":"True when gh pr ready exited 0"},
    auto_merge: {"type":"boolean","description":"True when gh pr merge --auto --merge exited 0"},
    escalation: {"type":"string","description":"Set when the PR could not be opened or made ready"},
    at: {"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"UTC time when the agent finished, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock."},
  },
}
const findingSchema = {
  type: "object",
  description: "1 classified finding, filed once as an issue with the labels kind:<kind> and sev:<severity>. Before filing, the agent searches the open findings; on a match it votes instead of filing. Priority = x-severity-weights[severity] x votes x minutes (at least 1). Severity holds: main would break (a red gate, a crash, data loss, a broken save, a shipped feature that stops working); only holds keeps its group's PR a draft.",
  required: ["kind","severity","title","evidence","url","minutes","voted","votes"],
  properties: {
    kind: {"type":"string","enum":["bug","convergence","test-gap","tests","perf","design-question","feel","docs"]},
    severity: {"type":"string","enum":["holds","major","minor"]},
    title: {"type":"string","minLength":1},
    evidence: {"type":"string","minLength":1,"description":"What a second reader can check: the command, its last output line, the SHA"},
    url: {"type":"string","description":"The URL of the finding issue, or of the open finding it voted on; empty when the filing failed"},
    minutes: {"type":"integer","minimum":0,"description":"The minutes lost to the problem: the filing and every vote, summed"},
    voted: {"type":"boolean","description":"True when an open finding matched and the agent voted on it (1 comment naming its task and the minutes lost, and a +1 reaction) instead of filing a new issue"},
    votes: {"type":"integer","minimum":1,"description":"The votes on the finding now: 1 for the filing plus 1 per vote comment"},
  },
}
const landingReviewSchema = {
  type: "object",
  description: "A review of flow landings: a diff review of 1 landing (the reviewer's first-try tier), or a blind batched review of the last args.review_every landings (the reviewer tier). The review files nothing and holds nothing: the flow files or votes each finding, and only a holds finding keeps its group's PR a draft.",
  required: ["landings","findings"],
  properties: {
    landings: {"type":"array","minItems":1,"items":{"type":"string"},"description":"The task ids of the landings the review read"},
    findings: {"type":"array","description":"Each problem the review found in those landings, classified. Empty when none.","items":{"type":"object","required":["task","kind","severity","title","evidence","minutes"],"properties":{"task":{"type":"string","description":"The task id of the landing the problem is in; 1 of landings"},"kind":{"type":"string","enum":["bug","convergence","test-gap","tests","perf","design-question","feel","docs"]},"severity":{"type":"string","enum":["holds","major","minor"],"description":"holds only when main would break: a red gate, a crash, data loss, a broken save, a shipped feature that stops working"},"title":{"type":"string","minLength":1},"evidence":{"type":"string","minLength":1,"description":"What a second reader can check: the file and line, or the command and its last output line"},"minutes":{"type":"integer","minimum":0,"description":"The minutes the problem cost the reviewer; 0 when it cost none"}}}},
  },
}

// ---- Setup
// RETIRED: the v4 args, each with what replaced it. A call that passes one stops with that line.
const RETIRED = {
  converge_gate: 'CI is the gate: the heavy lanes run once when the PR is marked ready',
  claims: 'the tracker is the state: flow reads each claim and report on the issue',
  claimed_at: 'the tracker is the state: flow reads each claim and report on the issue',
  started_at: 'each tracker read reports its own time',
  answers: 'answer on the issue: the builder reads its comments',
  max_load: 'flow reads no load: runtime.concurrency caps the builders',
  cpus: 'flow reads no load: runtime.concurrency caps the builders',
  test_count: 'the test-budget CI check measures test lines',
  test_share_warn: 'the test-budget CI check measures test lines',
}
if (!args || !args.repo || !args.base || !args.base.ref || !args.base.sha) throw new Error('flow needs args.repo and args.base: { ref, sha } of the default branch')
for (const [k, why] of Object.entries(RETIRED)) if (args[k] !== undefined) throw new Error(`args.${k} is gone in v5: ${why}`)
const queueArg = args.queue
const queueList = Array.isArray(queueArg) && queueArg.length > 0 && queueArg.every((n) => Number.isInteger(n) && n > 0)
if (!queueList && !(typeof queueArg === 'string' && queueArg.trim() !== '')) {
  throw new Error('flow needs args.queue: the issue numbers to run, or a gh command that lists them')
}
for (const k of ['gate', 'setup']) {
  if (args[k] !== undefined && (typeof args[k] !== 'string' || args[k].trim() === '')) throw new Error(`args.${k} must be a command string`)
}
if (args.review_every !== undefined && !(Number.isInteger(args.review_every) && args.review_every > 0)) throw new Error('args.review_every must be a positive integer: the landings 1 batched review reads')

const repo = args.repo
const base = args.base
const runtime = withAgentTypes(args.runtime || CLAUDE_RUNTIME, args.agent_types)
const root = runtime.worktree_root
// remote: each agent may run anywhere, so a prompt names the work (branch, base, report), never a path under root.
const remote = runtime.remote === true
const rules = args.rules ? `\nRepo rules:\n${args.rules}\n` : ''
const setupText = (where) => (args.setup ? ` Run the setup command once in ${where}, before any test or check: ${args.setup}. If it fails, report that error and stop.` : '')
const spawn = (role, tier) => {
  const t = runtime.tiers[tier]
  return { model: t.model, ...(t.effort && { effort: t.effort }), agentType: runtime.agent_types[role] }
}
// The environment of a builder (#331). An entry left out means a local-like agent.
const env = runtime.environment || {}
const access = (env.tracker && env.tracker.access) || 'graphql'
const envHas = (name, dflt) => (env[name] ? HAS.includes(env[name].status) : dflt)
const display = envHas('display', true)
const extraBranches = envHas('extra_branches', false)
const readIssue = (n) => (access === 'rest' ? `gh api repos/${repo}/issues/${n} and gh api repos/${repo}/issues/${n}/comments` : `gh issue view ${n} --repo ${repo} --comments`)
const postLine = (n) => (access === 'rest' ? `gh api repos/${repo}/issues/${n}/comments -f body=<the comment>` : `gh issue comment ${n} --repo ${repo} --body <the comment>`)

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
  return (era * 146097 + doe - 719468) * 86400 + h * 3600 + mi * 60 + sec
}
const FULL_SHA = new RegExp(reportSchema.properties.sha.pattern)
const badSha = (sha) => !FULL_SHA.test(sha || '') || /^0+$/.test(sha)

const agentsOf = {}
// call: 1 agent, counted for its issue (if any). A failed spawn returns null.
async function call(issue, prompt, opts) {
  if (issue) agentsOf[issue] = (agentsOf[issue] || 0) + 1
  try {
    return await agent(asLead(prompt), opts)
  } catch (e) {
    log(`${opts.label}: ${e.message}`)
    return null
  }
}
// serial: 1 run at a time per lane (a group branch, the findings, the batched reviews).
const lanes = {}
function serial(lane, run) {
  const p = (lanes[lane] || Promise.resolve()).then(run)
  lanes[lane] = p.catch(() => null)
  return p
}
const checkout = (g) => (remote
  ? `Get branch ${g} at origin/${g} in your checkout: git fetch -q origin, create it from origin/${g} if you have none, then git merge -q --ff-only origin/${g}.`
  : `In the worktree ${root}/${g} (make it when missing: git fetch -q origin && git worktree add -B ${g} ${root}/${g} origin/${g}): git fetch -q origin && git merge -q --ff-only origin/${g}.`)
const where = (g) => (remote ? `your checkout of ${g}` : `${root}/${g}`)
const AT = 'When you finish, run date -u +%Y-%m-%dT%H:%M:%SZ and report the result as at.'

// ---- Read: 1 agent reads the facts of every queue issue; the flow decides from them (stateOf).
const STALE_S = LIMITS.stale_claim_minutes * 60
let reads = 0
const MAX_READS = 200
function readTracker(watch) {
  reads++
  const wait = watch.length > 0
    ? `0. First wait for news on the issues being built elsewhere: run the agentic-sdlc plugin's bin/wait-reports with WAIT_REPORTS_STALL=${LIMITS.stale_claim_minutes}: wait-reports ${watch.map((e) => `${repo}#${e.issue}@${e.branch}`).join(' ')}. It exits on the first report, block, stall or close. Then read.\n`
    : ''
  return call(0, `Read the state of the queue issues of ${repo} on GitHub. Read only: edit, commit, push and post nothing, open no pull request.
${wait}1. The issues: ${queueList ? queueArg.map((n) => `#${n}`).join(' ') : `each issue this command lists, in its order: ${queueArg}`}. git fetch -q origin.
2. For each, report: issue; title; state (open or closed); parent, its parent issue (sub-issue) or its "Parent: #N" line; group, the branch <parent>-<slug> with slug the parent title in lower case, at most 3 words joined by - (with no parent: <issue>-<slug> of its own title); tier, from its tier: label, else judgment; blocked_by, the open issues that block it (gh api repos/${repo}/issues/<n>/dependencies/blocked_by, and each "Blocked by #N" line of its body whose issue is open), [] when none.
3. From its comments: branch, the branch= of the newest comment whose first line starts with WORKER, else <issue>-<slug of its title>. report, the newest WORKER REPORT branch=<b> head=<sha> whose sha is the head of origin/<b> (git ls-remote origin refs/heads/<b>); leave it out when none is at head. landed, true when the head= of its newest WORKER REPORT is an ancestor of origin/<group> (git merge-base --is-ancestor <sha> origin/<group> exits 0). question, the text of the newest WORKER BLOCKED comment, only when no comment came after it. activity_at, the time of the newest WORKER LAUNCHED or WORKER STARTED comment or of the newest commit on origin/<branch>, whichever is newer; leave it out when there is none.${access === 'none' ? '\n4. body: the issue body, verbatim.' : ''}
Report at last: run date -u +%Y-%m-%dT%H:%M:%SZ.${rules}`,
  { label: `read ${reads}`, phase: 'Read', schema: trackerSchema, ...spawn('lander', FIRST_TRY.lander) })
}
// stateOf: what the flow does with an issue, from the facts of the last read and its time now (seconds).
function stateOf(e, now) {
  if (e.state === 'closed') return 'closed'
  if (e.landed) return 'landed'
  if (e.report && !badSha(e.report.sha)) return 'reported'
  if (e.question) return 'blocked'
  const at = isoSeconds(e.activity_at)
  if (at === null) return 'new'
  return now - at > STALE_S ? 'stale' : 'live'
}

// ---- PR: 1 draft PR per group branch from the start, with 1 Closes line per issue (#410).
const prs = {}
function openPr(g, list) {
  const parent = list.find((e) => e.parent) || {}
  const closes = list.map((e) => `Closes #${e.issue}`)
  return serial(g, async () => {
    const p = await call(0, `Open or update the draft PR of the group branch ${g} of ${repo}. Push nothing but step 1; never push to ${base.ref}.
1. git fetch -q origin. When origin/${g} is missing, make it at the base with 1 empty commit (a PR needs a commit): ${remote ? `in your checkout, git checkout -q -B ${g} ${base.sha}` : `git worktree add -B ${g} ${root}/${g} ${base.sha}, and in it`} git commit -q --allow-empty -m "Start ${g}" && git push -q origin ${g}.
2. gh pr list --repo ${repo} --head ${g} --state open --json url,body -q '.[0]'. With none, open it as a draft: gh pr create --repo ${repo} --draft --base ${base.ref} --head ${g} --title "<the title of ${parent.parent ? `#${parent.parent}` : `#${list[0].issue}`}>" --body "${parent.parent ? `Refs #${parent.parent}\n\n` : ''}${closes.join('\n')}". With one, add each of these lines its body lacks, and change nothing else: gh pr edit <url> --repo ${repo} --body "<the body with the lines added>": ${closes.join(', ')}.
3. Report group ${g}, pr (the URL; "" with escalation when it could not open), closes (each issue its body now has a Closes line for), ready false, auto_merge false. ${AT}${rules}`,
    { label: `pr ${g}`, phase: 'Read', schema: prSchema, ...spawn('lander', FIRST_TRY.lander) })
    prs[g] = { group: g, pr: (p && p.pr) || (prs[g] && prs[g].pr) || '', closes: [...new Set([...((prs[g] && prs[g].closes) || []), ...((p && p.closes) || [])])] }
    log(`${g}: ${prs[g].pr ? `draft PR ${prs[g].pr}` : 'no PR'}; ${closes.join(', ')}`)
  })
}

// ---- Build: 1 builder per issue; the issue is its brief.
const FINDINGS_ASK = 'Report each problem outside your issue that cost you time or would break main in findings: kind, 1 of the kinds the report shape lists; severity holds only when main would break (a red gate, a crash, data loss, a broken save, a shipped feature that stops working), else major or minor; title; evidence a second reader can check; and minutes, the minutes it cost you. File no issue: the flow searches the open findings and votes on a match.'
function builderPrompt(e, st) {
  const [b, g, n] = [e.branch, e.group, e.issue]
  const tracked = access !== 'none'
  const make = remote
    ? `git fetch -q origin; build on branch ${b}: from origin/${b} when it is on the remote (then merge origin/${g} into it), else made from origin/${g}.`
    : `Work in your own worktree ${root}/${b}: git fetch -q origin, then git worktree add -B ${b} ${root}/${b} origin/${b} when origin/${b} is on the remote (then merge origin/${g} into it), else git worktree add -b ${b} ${root}/${b} origin/${g}.`
  return `Build issue #${n} of ${repo}${e.title ? `: ${e.title}` : ''}. ${tracked ? `The issue and its comments are your brief (${readIssue(n)}); a later comment of the lead answers an earlier question and wins.` : `This runtime cannot reach the tracker: post nothing. The issue is your brief:\n${e.body || '(no body was read)'}\n`} Brief yourself: read the code the issue touches, then build it and its test.
${st === 'stale' ? `An earlier builder went quiet on ${b} (last sign ${e.activity_at}). Continue its work: read git log origin/${g}..HEAD first and do not redo it.\n` : ''}${make}${setupText(remote ? `your checkout of ${b}` : `${root}/${b}`)}
${tracked ? `Your first act: post 1 comment on issue #${n} whose first line is exactly WORKER STARTED branch=${b} session=<your session URL, or unknown> (${postLine(n)}).\n` : ''}Run only narrow tests: the issue's Proof command${args.gate ? `, then the fast check once: ${args.gate}. Report it in gate: command, passed, last output line` : ''}. Never run the full suite: CI on the PR is the gate. List in unverified each gate lane you could not run here.${display ? '' : ' This runtime has no display: take no capture and run no headed test; list each such check in unverified, and the lead runs it.'}
Commit small and push after every commit: git push -q -u origin ${b}. Open no pull request. Merge nothing into ${g} or ${base.ref}.
For a how-to question under a decided design, pick the option that keeps the issue's decisions and the repo rules, build it, and name the choice in notes. Escalate only a question the issue does not answer about what the user sees, hears or reads. To escalate, push what you have${tracked ? `, post 1 comment whose first line is exactly WORKER BLOCKED branch=${b} and then the question,` : ''} and set status escalated.
${FINDINGS_ASK}
${tracked ? `When done, post 1 comment whose first line is exactly WORKER REPORT branch=${b} head=<the SHA you pushed>, then the proof lines and what you did not verify.\n` : ''}Report task ${n}, round 0, branch ${b}, the full 40-character SHA of your last push (git rev-parse HEAD after it; never a placeholder), and the test command with its last output line. ${AT}${rules}`
}
// verify: why the flow refuses a builder report, or '' when it lands it.
function verify(r, e) {
  if (!r) return 'the builder returned nothing'
  if (r.status !== 'done') return `the builder escalated: ${r.escalation || 'no question given'}`
  if (r.task !== String(e.issue)) return `the report names task ${r.task}, not ${e.issue}`
  if (r.branch !== e.branch) return `the report names branch ${r.branch}, not ${e.branch}`
  if (badSha(r.sha)) return `the report SHA ${r.sha} is not a full SHA`
  if (!r.test.passed) return `the focused test is red: ${r.test.line}`
  if (args.gate && !(r.gate && r.gate.passed)) return r.gate ? `the fast check is red: ${r.gate.line}` : `the fast check was not run: report gate for ${args.gate}`
  return ''
}

// ---- Land: 1 landing at a time per group branch. The lander merges by SHA, runs the fast check, pushes.
function landPrompt(e, rep, resolve) {
  const g = e.group
  return `You land issue #${e.issue} of ${repo} in its group branch ${g}: merge ${rep.branch} at ${rep.sha}, by that SHA.
1. ${checkout(g)} Then merge the default branch in: git merge -q --no-edit origin/${base.ref} (on a conflict: git merge --abort and go on without it).${extraBranches ? ` The builder pushes a branch of its own beside ${rep.branch}: fetch the SHA itself (git fetch -q origin ${rep.sha}) and never merge by a branch name. Report in extra_branches each other remote branch whose head is ${rep.sha} (git ls-remote origin), for the cleanup after the PR merges.` : ''}
2. In it: note the pre-merge tip (git rev-parse HEAD), then git merge --no-ff --no-commit ${rep.sha}
3. On a conflict: ${resolve ? 'resolve it when both sides are clear; keep the behavior of both. When the 2 sides change one contract in 2 ways, run git merge --abort and set escalation to the files.' : 'run git merge --abort and set escalation to the conflicting files. Do not resolve it.'}
   When the merge was not aborted, commit it now, before the check: git commit -q -m "Merge ${rep.branch} into ${g}". The check of step 4 runs on this commit.
4. ${args.gate ? `${setupText(where(g)).trim()} Run the fast check once: ${args.gate}. It is green only when it exits 0. Report check: command, its last output line, passed. Run nothing wider: CI on the push is the gate.` : 'There is no fast check: CI on the push is the gate.'}
5. Green: keep the merge commit and report merged true.
   Red: report merged false and the last output line in escalation. Then reset the branch to the pre-merge tip of step 2: git checkout -q -f -B "$(git branch --show-current)" <the pre-merge tip> (git merge --abort when the merge is still in progress). Stop: commit nothing more, push nothing.
6. git push -q origin ${g}. Report issue ${e.issue}, group ${g}, and sha: the full SHA of the push (the pre-merge tip when nothing was pushed).
Keep ${where(g)} for the next landing. Open no pull request, delete no branch, and never touch ${base.ref}. ${AT}${rules}`
}
function land(e, rep) {
  return serial(e.group, async () => {
    const opts = (tier) => ({ label: `land ${e.issue}`, phase: 'Land', schema: landingSchema, ...spawn('lander', tier) })
    let l = await call(e.issue, landPrompt(e, rep, false), opts(FIRST_TRY.lander))
    const red = l && l.check && !l.check.passed
    // The first try merges a clean merge only; a conflict steps up to the lander tier, which may resolve it.
    if (!l || (!l.merged && !red)) l = await call(e.issue, landPrompt(e, rep, true), opts(ROLE_TIER.lander))
    if (!l || !l.merged || badSha(l.sha)) return done(e, 'escalated', l ? l.escalation || `the landing SHA ${l.sha} is not a full SHA` : 'the lander returned nothing')
    done(e, 'landed', `landed on ${e.group} at ${l.sha}`, l.at)
    if ((l.extra_branches || []).length > 0) extra.push(...l.extra_branches)
    reviewLanding({ issue: e.issue, group: e.group, sha: l.sha })
  })
}

// ---- Findings: 1 agent at a time searches the open findings of the kind; on a match it votes (1 comment and a +1
// reaction), else it files 1 issue labelled kind:<kind> and sev:<severity>. A holds finding keeps its group a draft.
const WEIGHTS = contract['x-severity-weights']
const priority = (f) => (WEIGHTS[f.severity] || 0) * Math.max(1, f.votes || 1) * Math.max(1, f.minutes || 0)
const findings = []
function fileFinding(f, who, label, g) {
  return serial('#findings', async () => {
    const minutes = f.minutes || 0
    const a = await call(0, `File or vote on 1 finding on ${repo}. Edit, commit and push nothing, and open no pull request.
The finding: kind ${f.kind}, severity ${f.severity}, title ${JSON.stringify(f.title)}. Evidence: ${f.evidence}. It cost ${who} ${minutes} minutes.
1. Search the open findings: gh issue list --repo ${repo} --state open --label kind:${f.kind} --limit 100 --json number,title,url,body. A match is an open finding of the same problem: the same failing check, file or symptom, in other words.
2. On a match, vote and file nothing: gh issue comment <n> --repo ${repo} --body "+1 from ${who}: cost ${minutes} minutes. Evidence: ${f.evidence}", then gh api repos/${repo}/issues/<n>/reactions -f content=+1. Report voted true; url, the URL of the match; votes, 1 plus the count of its comments that start with "+1 from" (yours included); minutes, the "Minutes lost: N" of its body plus the "cost N minutes" of each such comment.
3. No match: gh label create kind:${f.kind} --repo ${repo} --force and gh label create sev:${f.severity} --repo ${repo} --force, then gh issue create --repo ${repo} --label kind:${f.kind} --label sev:${f.severity} --title ${JSON.stringify(f.title)} --body "Severity ${f.severity}: found by ${who}${g ? ` on ${g}` : ''}.

Evidence: ${f.evidence}
Minutes lost: ${minutes}"
   Report voted false, votes 1, minutes ${minutes}, and url: the issue URL it printed ("" when it failed).
4. Report kind ${f.kind}, severity ${f.severity}, and the title and evidence as given.${rules}`,
    { label, phase: 'Review', schema: findingSchema, ...spawn('lander', FIRST_TRY.lander) })
    const row = { group: g, by: who, ...(a || { kind: f.kind, severity: f.severity, title: f.title, evidence: f.evidence, url: '', minutes, voted: false, votes: 1 }) }
    row.priority = priority(row)
    findings.push(row)
    log(`${label}: ${row.voted ? `voted on ${row.url} (${row.votes} votes)` : row.url ? `filed ${row.url}` : 'the filing failed'}: ${row.severity} ${row.kind}: ${row.title}`)
  })
}

// ---- Reviews: beside the landings, each in its own lane, so no landing waits on one.
const REVIEW_EVERY = args.review_every || 6
const REVIEW_ASK = 'Read only: edit, commit and push nothing, file no issue, and open no pull request. Report landings: the issue numbers above. Report each problem in findings: task, the landing it is in; kind, 1 of the kinds the review shape lists; severity holds only when main would break (a red gate, a crash, data loss, a broken save, a shipped feature that stops working), else major or minor; title; evidence a second reader can check (the file and line, or the command and its last output line); minutes, the minutes it cost you (0 when none). Report [] when you find none. The flow searches the open findings and votes on a match.'
const landings = []
const reviewRuns = []
const reviews = []
let batchCount = 0
const diffOf = (l) => `git diff ${l.sha}^1 ${l.sha}`
function reviewLanding(l) {
  landings.push(l)
  reviewRuns.push(review(`review ${l.issue}`, [l], `the diff review of #${l.issue}`, `Review the landing of issue #${l.issue} on the group branch ${l.group} of ${repo}: git fetch -q origin, then read ${diffOf(l)}. Look for a bug, a second path for 1 behavior, a missing test, a slow path or a wrong doc in that diff.`, spawn('reviewer', FIRST_TRY.reviewer)))
  if (landings.length % REVIEW_EVERY === 0) batchReview(landings.slice(-REVIEW_EVERY))
}
// batchReview: 1 blind review of the landings together, at the reviewer tier. It sees the diffs only.
function batchReview(list) {
  const n = ++batchCount
  reviewRuns.push(serial('#batch', () => review(`review batch ${n}`, list, `the batched review ${n}`, `Review blind the last ${list.length} landing${list.length === 1 ? '' : 's'} of this flow on ${repo}, together. Read only the code and these diffs, after git fetch -q origin. Do not read the issues, the reports, the pull requests or the findings already filed, and do not ask who built what.
${list.map((l) => `- #${l.issue} on ${l.group}: ${diffOf(l)}`).join('\n')}
Look for what 1 diff hides: 2 paths for 1 behavior, 1 contract changed 2 ways, a test gap across the landings, a slow path, a wrong doc.`, spawn('reviewer', ROLE_TIER.reviewer))))
}
async function review(label, list, who, ask, how) {
  const a = await call(0, `${ask}\n${REVIEW_ASK}${rules}`, { label, phase: 'Review', schema: landingReviewSchema, ...how })
  const row = { review: label, landings: list.map((l) => String(l.issue)), findings: 0 }
  reviews.push(row)
  if (!a) {
    row.reason = 'the reviewer returned nothing'
    return log(`${label}: ${row.reason}`)
  }
  for (const [i, f] of (a.findings || []).entries()) {
    const l = list.find((x) => String(x.issue) === f.task)
    row.findings++
    reviewRuns.push(fileFinding(f, who, `finding ${label} ${i + 1}`, l ? l.group : ''))
  }
  log(`${label}: ${row.findings} finding${row.findings === 1 ? '' : 's'}`)
}

// ---- The loop: read, act, wait for the next event, read again.
const issues = new Map()
const outcome = new Map()
const active = new Map()
const extra = []
const cap = runtime.concurrency || Infinity
let now = 0
let firstAt = null
function done(e, state, reason, at) {
  outcome.set(e.issue, { state, reason, at })
  log(`#${e.issue}: ${state}: ${reason}`)
}
// LANDED: the outcomes whose code is on its group branch; a blocker in one of them no longer blocks.
const LANDED = ['landed', 'skipped']
const waitsOn = (e) => (e.blocked_by || []).filter((b) => !LANDED.includes((outcome.get(b) || {}).state))
function dispatch(e) {
  const st = stateOf(e, now)
  if (st === 'closed') return done(e, 'skipped', 'closed')
  if (st === 'landed') return done(e, 'skipped', `landed on ${e.group} by an earlier run`)
  if (st === 'blocked') return done(e, 'escalated', `WORKER BLOCKED: ${e.question}`)
  if (st === 'live' || waitsOn(e).length > 0 || active.size >= cap) return
  log(`#${e.issue}: ${st === 'reported' ? `a report at ${e.report.sha} lands` : st === 'stale' ? `quiet since ${e.activity_at}: a builder restarts on ${e.branch}` : `a builder starts on ${e.branch}`}`)
  const run = st === 'reported'
    ? land(e, e.report)
    : call(e.issue, builderPrompt(e, st), { label: `build ${e.issue}`, phase: 'Build', schema: reportSchema, ...spawn('builder', e.tier) }).then((r) => {
      const refused = verify(r, e)
      if (refused) return done(e, 'escalated', refused)
      for (const [i, f] of (r.findings || []).entries()) reviewRuns.push(fileFinding(f, `#${e.issue}`, `finding ${e.issue} ${i + 1}`, e.group))
      return land(e, { branch: r.branch, sha: r.sha })
    })
  active.set(e.issue, run.catch((err) => done(e, 'escalated', `the flow failed on it: ${err.message}`)).then(() => active.delete(e.issue)))
}
phase('Read')
for (;;) {
  const live = [...issues.values()].filter((e) => !outcome.has(e.issue) && !active.has(e.issue) && stateOf(e, now) === 'live')
  if (reads >= MAX_READS) {
    log(`${MAX_READS} tracker reads: the flow stops; run it again to go on`)
    break
  }
  const t = await readTracker(active.size === 0 ? live : [])
  if (!t) {
    log('the tracker read returned nothing: the flow stops; run it again to go on')
    break
  }
  now = isoSeconds(t.at) || now
  firstAt = firstAt || t.at
  const joined = t.issues.filter((e) => e.state === 'open' && !issues.has(e.issue))
  for (const e of t.issues) issues.set(e.issue, e)
  await Promise.all([...new Set(joined.map((e) => e.group))].map((g) => openPr(g, joined.filter((e) => e.group === g))))
  phase('Build')
  for (const e of t.issues) if (!outcome.has(e.issue) && !active.has(e.issue)) dispatch(e)
  if (active.size > 0) await Promise.race(active.values())
  else if (![...issues.values()].some((e) => !outcome.has(e.issue) && stateOf(e, now) === 'live')) break
}
await Promise.all([...active.values()])
// The landings no batched review read yet get 1 more. Then wait for every review and finding, which may queue more.
if (landings.length % REVIEW_EVERY > 0) batchReview(landings.slice(-(landings.length % REVIEW_EVERY)))
for (let n = 0; n < reviewRuns.length;) {
  const m = reviewRuns.length
  await Promise.all(reviewRuns.slice(n, m))
  n = m
}

// ---- Ready: a group whose issues all landed, with no holds finding of this run, leaves draft and merges itself.
phase('Ready')
const groups = [...new Set([...issues.values()].map((e) => e.group))]
const ownOf = (g) => [...issues.values()].filter((e) => e.group === g)
for (const g of groups) {
  const own = ownOf(g)
  const open = own.filter((e) => !LANDED.includes((outcome.get(e.issue) || {}).state))
  const holds = findings.filter((f) => f.group === g && f.severity === 'holds')
  const row = prs[g] || { group: g, pr: '', closes: [] }
  prs[g] = row
  if (!own.some((e) => e.state === 'open')) continue
  if (open.length > 0 || holds.length > 0) {
    row.reason = open.length > 0 ? `stays a draft: ${open.map((e) => `#${e.issue}`).join(' ')} not landed` : `stays a draft: holds finding ${holds.map((f) => f.url || f.title).join(', ')}`
    log(`${g}: ${row.reason}`)
    continue
  }
  const p = await serial(g, () => call(0, `Make the draft PR of the group branch ${g} of ${repo} ready: every issue of it has landed. Never push to ${base.ref} or merge into it yourself.
1. ${checkout(g)} Merge the default branch in by a merge commit: git merge --no-ff --no-edit origin/${base.ref}. On a conflict: git merge --abort, push nothing, and report escalation "merge conflict with ${base.ref}: <files>". Else git push -q origin ${g}.
2. The PR: gh pr list --repo ${repo} --head ${g} --state open --json url -q '.[0].url'. Mark it ready, which runs the heavy CI lanes once: gh pr ready <url> --repo ${repo}. Report ready true when it exits 0.
3. gh pr merge <url> --repo ${repo} --auto --merge. Report auto_merge true when it exits 0.
Report group ${g}, pr (the URL), and closes (each issue its body has a Closes line for). ${AT}${rules}`,
  { label: `ready ${g}`, phase: 'Ready', schema: prSchema, ...spawn('lander', FIRST_TRY.lander) }))
  Object.assign(row, p ? { pr: p.pr || row.pr, ready: Boolean(p.ready), auto_merge: Boolean(p.ready && p.auto_merge) } : {})
  if (!row.auto_merge) row.reason = (p && p.escalation) || 'the PR is not ready with auto-merge: the lead sets it'
  log(`${g}: ${row.auto_merge ? `${row.pr} is ready and merges itself on green` : row.reason}`)
}

// ---- Report: 1 metrics row per issue that ran an agent. This runtime reports no usage.
phase('Report')
const UNAVAILABLE = 'unavailable'
const RESULT = { landed: 'merged', escalated: 'escalated' }
const stateIs = (s) => [...issues.keys()].filter((n) => (outcome.get(n) || {}).state === s)
const waiting = [...issues.values()].filter((e) => !outcome.has(e.issue))
const metrics = Object.keys(agentsOf).filter((n) => issues.has(Number(n))).map((n) => {
  const e = issues.get(Number(n))
  const o = outcome.get(e.issue) || {}
  const sp = runtime.tiers[e.tier]
  return {
    task: n, provider: runtime.provider, tier: e.tier, model: sp.model, ...(sp.effort && { effort: sp.effort }), agents: agentsOf[n],
    elapsed_s: Math.max(0, (isoSeconds(o.at) || now) - (isoSeconds(firstAt) || now)), rework_rounds: 0,
    findings: { critical: 0, major: 0, minor: 0 }, result: RESULT[o.state] || 'failed', tokens: UNAVAILABLE, cost_usd: UNAVAILABLE,
  }
})
const escalations = [
  ...stateIs('escalated').map((n) => ({ issue: n, reason: outcome.get(n).reason })),
  ...waiting.map((e) => ({ issue: e.issue, reason: waitsOn(e).length > 0 ? `waits on ${waitsOn(e).map((b) => `#${b}`).join(' ')}` : `${stateOf(e, now)}: not started` })),
]
log(`${stateIs('landed').length} landed, ${stateIs('skipped').length} skipped, ${escalations.length} for the lead; ${groups.map((g) => `${g}: ${prs[g].pr || 'no PR'}${prs[g].auto_merge ? ' (ready)' : ''}`).join(', ')}; ${findings.length} finding${findings.length === 1 ? '' : 's'}, ${reviews.length} review${reviews.length === 1 ? '' : 's'}, ${reads} tracker read${reads === 1 ? '' : 's'}.`)

return {
  prs: groups.map((g) => prs[g]),
  landed: stateIs('landed'),
  skipped: stateIs('skipped'),
  escalations,
  ...(extra.length > 0 && { extra_branches: extra }),
  findings: [...findings].sort((a, b) => b.priority - a.priority),
  reviews,
  issues: [...issues.values()].map((e) => ({ issue: e.issue, group: e.group, branch: e.branch, state: (outcome.get(e.issue) || {}).state || 'waiting', reason: (outcome.get(e.issue) || {}).reason || '' })),
  metrics,
}
