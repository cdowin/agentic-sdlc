export const meta = {
  name: 'flow',
  description: 'Run the ready issues of a repo with the tracker as the state. Each read (plugin/bin/queue-state, fixed rules) says, per issue: closed or landed (skip), a passed WORKER REPORT at head (land it), a live builder (watch it), a question (to the lead), or none or a stale one (start or restart a builder). Order is blocked-by. At the start each group branch gets a draft PR with 1 Closes line per issue, and an issue that joins mid-run adds its line. Each passed report merges by its SHA into the group branch over the fast check, and CI on the push is the gate. When every issue the PR Closes is landed and no holds finding is open, the PR is marked ready (the heavy CI lanes run once), and it merges only when each required check has a passed run since ready (a SKIPPED or pending one stops it; no auto-merge). 1 diff review per landing, 1 blind batched review every args.review_every. Safe to re-run at any time. Never pushes to the default branch.',
  phases: ['Read', 'Build', 'Land', 'Review', 'Ready', 'Report'],
}

log(`flow ${args && args.repo ? args.repo : '(no repo)'}: ${args && Array.isArray(args.queue) ? args.queue.map((n) => `#${n}`).join(' ') : args && args.queue ? `query ${args.queue}` : 'no args.queue'}`)

// flow: the tracker is the state. Each loop reads the queue issues on GitHub with plugin/bin/queue-state (1 agent
// runs it: a workflow reads no file and no clock) and acts on what it says; nothing a run remembers is needed for
// correctness, so a re-run picks up where the tracker says. A run remembers only what it has started.
// args: { repo, base, queue, gate, group_pr, setup, review_every, rules, runtime, agent_types }
//   repo      the owner/name of the repo.
//   base      { ref, sha }: the default branch and its SHA. A group branch that is not on the remote starts here.
//   queue     the issue numbers to run, in order, or a command that prints them 1 per line. A command runs again
//             on every read, so an issue that becomes ready mid-run joins (and adds its Closes line to its PR).
//   gate      required; the fast check (narrow tests and lint). The builder runs it, and the lander runs it on each
//             merge commit before the push. Never the full suite: CI on the PR is the gate.
//   group_pr  optional; a PR number: every issue lands in its head branch (1 PR for the whole queue).
//   setup     optional; a command every agent runs once in a fresh worktree before any test or check.
//   review_every optional; a positive integer, default x-limits.review_batch: the landings 1 batched review reads.
//   rules     optional; the repo's rules as text. runtime, agent_types: see the README.
// runtime.concurrency caps the builders at once (null: no cap). runtime.environment says what a builder can do where it
// runs (#331): tracker access graphql, rest or none; extra branches (land by SHA); a display (else captures go to the lead).
// Shell safety: a prompt puts no tracker or agent text inside a double-quoted shell argument. Such text goes in a
// quoted heredoc (DOC); a branch or group is checked against SAFE_REF first.

// ---- contract: begin
// Generated from plugin/contract by node tests/workflows.js --write. Do not edit.
const contract = {
  "x-tiers": {"bounded":"An oracle covers every behaviour that matters. A tight brief, a file list, the signatures, 15-30 min.","judgment":"1 or more behaviours have no oracle, or the task has a design choice. Also a brief, a landing that steps up and a skeptic.","lead":"The chief of staff, a blind batched review, a blast radius, and a change the step-up rule names."},
  "x-roles": {"lead":"lead","builder":"bounded","lander":"judgment","reviewer":"lead"},
  "x-tier-per-spawn": ["builder","reviewer"],
  "x-first-try": {"lander":"bounded","reviewer":"bounded"},
  "x-capabilities": ["structured_output","model_per_spawn","effort_per_spawn","tool_restriction","worktree_per_task","parallel_spawn","follow_up","interrupt","usage_report","image_generation"],
  "x-optional-capabilities": ["image_generation"],
  "x-need-labels": {"image_generation":"needs:image-gen"},
  "x-limits": {"review_batch":5,"stale_claim_minutes":60,"clock_skew_minutes":5,"blast_radius_max":4},
  "x-severity-weights": {"holds":9,"major":3,"minor":1},
}
const LIMITS = contract['x-limits']
const TIERS = Object.keys(contract['x-tiers'])
const ROLE_TIER = contract['x-roles']
const FIRST_TRY = contract['x-first-try']
const HAS = ['enforced', 'instructed']
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
  "agent_types": {"lead":"agentic-sdlc:chief-of-staff","builder":"agentic-sdlc:builder","lander":"agentic-sdlc:lander","reviewer":"agentic-sdlc:reviewer"},
  "capabilities": {"structured_output":{"status":"enforced"},"model_per_spawn":{"status":"enforced"},"effort_per_spawn":{"status":"unverified"},"tool_restriction":{"status":"enforced"},"worktree_per_task":{"status":"instructed"},"parallel_spawn":{"status":"enforced"},"follow_up":{"status":"unverified"},"interrupt":{"status":"unverified"},"usage_report":{"status":"unverified"},"image_generation":{"status":"absent"}},
}
// ---- contract: end

// Contract shapes: copies of $defs tracker, report, landing, pr, finding and landing_review in
// plugin/contract/sdlc.schema.json, with $ref inlined. A workflow cannot import a file. tests/workflows.js fails when a copy drifts.
const trackerSchema = {
  type: "object",
  description: "The tracker read of a flow: the output of plugin/bin/queue-state, which reads GitHub by fixed rules (no judgment), at the start and after each event. The tracker is the only state: a re-run reads it again and goes on from there. The flow decides from the facts: closed or landed is skipped; a passed report at head lands; a question goes to the lead; activity newer than x-limits.stale_claim_minutes is watched; else a builder starts, or restarts on the branch it left. A group is made ready only when every issue its PR Closes is landed and it has no open holds finding.",
  required: ["at","issues","groups"],
  properties: {
    at: {"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"UTC time of the read, from date -u +%Y-%m-%dT%H:%M:%SZ. A workflow cannot read the clock."},
    issues: {"type":"array","items":{"type":"object","required":["issue","state","group","branch","tier","blocked_by"],"properties":{"issue":{"type":"integer","minimum":1},"title":{"type":"string"},"state":{"type":"string","enum":["open","closed"]},"parent":{"type":"integer","minimum":1},"group":{"type":"string","pattern":"^(?!-)(?!.*\\.\\.)[A-Za-z0-9._/-]+$","description":"The group branch: the head of --group-pr, else <parent>-<slug> (an existing <parent>-* branch wins), or <issue>-<slug> with no parent. 1 draft PR per group."},"branch":{"type":"string","pattern":"^(?!-)(?!.*\\.\\.)[A-Za-z0-9._/-]+$","description":"The task branch: the branch= of the newest trusted WORKER line on the issue, else <issue>-<slug>"},"tier":{"type":"string","enum":["bounded","judgment","lead"],"description":"From its tier: label; judgment when none"},"blocked_by":{"type":"array","items":{"type":"integer","minimum":1},"description":"The open issues that block it: its GitHub blocked-by links and each Blocked by #N line. Empty when none."},"report":{"type":"object","required":["branch","sha","passed"],"description":"The newest trusted WORKER REPORT, when its first line holds passed and its head= is the remote head of its branch. Absent otherwise.","properties":{"branch":{"type":"string","pattern":"^(?!-)(?!.*\\.\\.)[A-Za-z0-9._/-]+$"},"sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"passed":{"const":true}}},"landed":{"type":"boolean","description":"True when the head= of the newest passed report is in origin/<group>: a run landed it already"},"question":{"type":"string","description":"The text of the newest trusted WORKER BLOCKED line (a question, or a landing the lander refused), or a note that the newest report lacks passed"},"activity_at":{"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"The newest WORKER LAUNCHED or STARTED comment, or commit on its branch. Absent when there is none."},"body":{"type":"string","description":"The issue body, verbatim. Read only when the runtime environment has no tracker access."}}}},
    groups: {"type":"array","items":{"type":"object","required":["group","pr","closes","holds"],"properties":{"group":{"type":"string"},"pr":{"type":"string","description":"The URL of its open PR; empty when none"},"closes":{"type":"array","items":{"type":"integer","minimum":1},"description":"Each issue the PR body Closes"},"holds":{"type":"array","items":{"type":"string"},"description":"The URL of each open sev:holds finding whose body has the line Group: <group>"}}}},
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
    extra_files: {"type":"array","items":{"type":"string"},"description":"Every file the builder edited outside its own file list. The lander checks each against the tasks beside it that are not merged yet."},
    findings: {"type":"array","description":"Each problem outside the task that cost the builder time or would break main, classified. Empty or absent when none. The workflow searches the open findings and votes on a match; the builder files nothing.","items":{"type":"object","required":["kind","severity","title","evidence","minutes"],"properties":{"kind":{"type":"string","enum":["bug","convergence","test-gap","tests","perf","design-question","feel","docs"]},"severity":{"type":"string","enum":["holds","major","minor"],"description":"holds only when main would break: a red gate, a crash, data loss, a broken save, a shipped feature that stops working"},"title":{"type":"string","minLength":1},"evidence":{"type":"string","minLength":1,"description":"What a second reader can check: the command, its last output line, the file"},"minutes":{"type":"integer","minimum":0,"description":"The minutes the problem cost this builder"}}}},
    browser_s: {"type":"number","minimum":0,"description":"Seconds the browser test runs of this agent took; 0 when none"},
    lock_wait_s: {"type":"number","minimum":0,"description":"Seconds this agent waited for a machine-wide browser lock before them; 0 when none"},
    notes: {"type":"string","description":"3 lines or fewer. Say what you did not verify."},
    brief: {"type":"string","description":"The builder's own short brief when the task came with none: a few lines, the approach, the traps it found, what it did not do."},
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
  description: "The draft PR of a flow group: opened at the start from the group branch with 1 Closes line per issue, 1 Closes line added for each issue that joins mid-run, and marked ready after its last issue landed. Every push runs the fast CI lane; ready runs the heavy lanes once. The ready step reports the newest run of each required check on the head; flow merges (pinned to head) only when each one started at or after ready_at, completed, and passed. A SKIPPED required check (GitHub counts it as passing, so a draft-only skip would merge at once) or a pending one stops the merge, so flow never turns on auto-merge.",
  required: ["group","pr","closes"],
  properties: {
    group: {"type":"string"},
    pr: {"type":"string","description":"The URL of the PR; empty when none could be opened"},
    closes: {"type":"array","items":{"type":"integer","minimum":1},"description":"Each issue the PR body has a Closes line for"},
    ready: {"type":"boolean","description":"True when gh pr ready exited 0"},
    head: {"type":"string","pattern":"^[0-9a-f]{40}$","description":"The ready step: the head SHA of the PR when it was marked ready"},
    ready_at: {"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$","description":"The ready step: UTC time just before gh pr ready"},
    required: {"type":"array","items":{"type":"string"},"description":"The ready step: the required check names of the base branch (rulesets and branch protection); empty when it requires none, and then every check on the head counts"},
    checks: {"type":"array","description":"The ready step: the newest run of each check on the head, after the wait","items":{"type":"object","required":["name","status","conclusion","started_at"],"properties":{"name":{"type":"string"},"status":{"type":"string","description":"queued, in_progress or completed"},"conclusion":{"type":"string","description":"success, neutral, skipped, failure, ...; empty while not completed"},"started_at":{"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$"}}}},
    merged: {"type":"boolean","description":"The merge step: true when gh pr merge --merge --match-head-commit exited 0"},
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
  throw new Error('flow needs args.queue: the issue numbers to run, or a command that prints them')
}
if (typeof args.gate !== 'string' || args.gate.trim() === '') throw new Error('flow needs args.gate: the fast check the lander runs on each merge before the push')
if (args.setup !== undefined && (typeof args.setup !== 'string' || args.setup.trim() === '')) throw new Error('args.setup must be a command string')
if (args.group_pr !== undefined && !(Number.isInteger(args.group_pr) && args.group_pr > 0)) throw new Error('args.group_pr must be a PR number')
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
// DOC: a command that reads text from a quoted heredoc, so the shell expands nothing in it.
const EOF = 'AGENTIC_SDLC_EOF'
const DOC = (cmd, text) => `${cmd} <<'${EOF}'\n${String(text).split(EOF).join('AGENTIC_SDLC-EOF')}\n${EOF}`
const oneLine = (s) => String(s).replace(/[\r\n]+/g, ' ')
const shq = (s) => `'${String(s).split("'").join("'\\''")}'`
// SAFE_REF: a ref a shell and git read as 1 plain name: no leading -, no "..".
const SAFE_REF = /^(?!-)(?!.*\.\.)[A-Za-z0-9._/-]+$/
const BIN = '"${CLAUDE_PLUGIN_ROOT}/bin'
const readIssue = (n) => (access === 'rest' ? `gh api repos/${repo}/issues/${n} and gh api repos/${repo}/issues/${n}/comments` : `gh issue view ${n} --repo ${repo} --comments`)
// postDoc: post 1 comment on issue n whose text is a quoted heredoc.
const postDoc = (n, text) => DOC(access === 'rest' ? `gh api repos/${repo}/issues/${n}/comments -F body=@-` : `gh issue comment ${n} --repo ${repo} --body-file -`, text)

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

// ---- Read: 1 agent runs queue-state and returns its stdout. The flow decides from the facts (stateOf).
const STALE_S = LIMITS.stale_claim_minutes * 60
let reads = 0
const MAX_READS = 200
let groupsRead = {}
function readTracker(watch) {
  reads++
  const wait = watch.length > 0
    ? `First wait for news on the issues being built elsewhere; it exits on the first report, block, stall or close:\nWAIT_REPORTS_STALL=${LIMITS.stale_claim_minutes} ${BIN}/wait-reports" ${watch.map((e) => shq(`${repo}#${e.issue}@${e.branch}`)).join(' ')}\nThen `
    : ''
  const q = queueList ? queueArg.join(' ') : queueArg
  return call(0, `Read the state of the queue issues of ${repo} on GitHub. Edit, commit, push and post nothing; open no pull request.
${wait}Run exactly this command and report its stdout as is, as your answer (it prints the tracker shape). Add, drop or change nothing; when it fails, report nothing:
${BIN}/queue-state"${access === 'none' ? ' --body' : ''}${args.group_pr ? ` --group-pr ${args.group_pr}` : ''} ${shq(repo)} ${shq(q)}${rules}`,
  { label: `read ${reads}`, phase: 'Read', schema: trackerSchema, ...spawn('lander', FIRST_TRY.lander) })
}
// stateOf: what the flow does with an issue, from the facts of the last read and its time now (seconds).
function stateOf(e, now) {
  if (e.state === 'closed') return 'closed'
  if (e.landed) return 'landed'
  if (!SAFE_REF.test(e.branch || '') || !SAFE_REF.test(e.group || '')) return 'unsafe'
  if (e.report) return e.report.passed === true && !badSha(e.report.sha) && SAFE_REF.test(e.report.branch || '') ? 'reported' : 'unpassed'
  if (e.question) return 'blocked'
  const at = isoSeconds(e.activity_at)
  if (at === null) return 'new'
  return now - at > STALE_S ? 'stale' : 'live'
}

// ---- PR: 1 draft PR per group branch from the start, with 1 Closes line per issue (#410).
const prs = {}
function openPr(g, list) {
  const parent = list.find((e) => e.parent) || {}
  const titleOf = parent.parent || list[0].issue
  const lines = list.map((e) => `Closes #${e.issue}`)
  return serial(g, async () => {
    const p = await call(0, `Open or update the draft PR of the group branch ${g} of ${repo}. Push nothing but step 1; never push to ${base.ref}.
1. git fetch -q origin. When origin/${g} is missing, make it at the base with 1 empty commit (a PR needs a commit): ${remote ? `in your checkout, git checkout -q -B ${g} ${base.sha}` : `git worktree add -B ${g} ${root}/${g} ${base.sha}, and in it`} git commit -q --allow-empty -m 'Start ${g}' && git push -q origin ${g}.
2. gh pr list --repo ${repo} --head ${g} --state open --json url -q '.[0].url'. With none, open it as a draft:
${DOC(`gh pr create --repo ${repo} --draft --base ${base.ref} --head ${g} --title "$(gh issue view ${titleOf} --repo ${repo} --json title -q .title)" --body-file -`, `${parent.parent ? `Refs #${parent.parent}\n\n` : ''}${lines.join('\n')}`)}
   With one, add each of these lines its body lacks and change nothing else: gh pr view <url> --repo ${repo} --json body -q .body > pr-body.txt, append each missing line to pr-body.txt, then gh pr edit <url> --repo ${repo} --body-file pr-body.txt. The lines: ${lines.join(', ')}.
3. Report group ${g}, pr (the URL; "" with escalation when it could not open), closes (each issue its body now has a Closes line for), ready false. ${AT}${rules}`,
    { label: `pr ${g}`, phase: 'Read', schema: prSchema, ...spawn('lander', FIRST_TRY.lander) })
    prs[g] = { group: g, pr: (p && p.pr) || (prs[g] && prs[g].pr) || '', closes: [...new Set([...((prs[g] && prs[g].closes) || []), ...((p && p.closes) || [])])] }
    log(`${g}: ${prs[g].pr ? `draft PR ${prs[g].pr}` : 'no PR'}; ${lines.join(', ')}`)
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
  const post = (first, rest) => `post 1 comment on issue #${n}, as a quoted heredoc (never inside double quotes):\n${postDoc(n, `${first}\n${rest}`)}`
  return `Build issue #${n} of ${repo}${e.title ? `: ${oneLine(e.title)}` : ''}. ${tracked ? `The issue and its comments are your brief (${readIssue(n)}); a later comment of the lead answers an earlier question and wins.` : `This runtime cannot reach the tracker: post nothing. The issue is your brief:\n${e.body || '(no body was read)'}\n`} Brief yourself: read the code the issue touches, then build it and its test.
${st === 'stale' ? `An earlier builder went quiet on ${b} (last sign ${e.activity_at}). Continue its work: read git log origin/${g}..HEAD first and do not redo it.\n` : ''}${make}${setupText(remote ? `your checkout of ${b}` : `${root}/${b}`)}
${tracked ? `Your first act: ${post(`WORKER STARTED branch=${b} session=<your session URL, or unknown>`, '')}\n` : ''}Run only narrow tests: the issue's Proof command, then the fast check once: ${args.gate}. Report it in gate: command, passed, last output line. Never run the full suite: CI on the PR is the gate. List in unverified each gate lane you could not run here.${display ? '' : ' This runtime has no display: take no capture and run no headed test; list each such check in unverified, and the lead runs it.'}
Commit small and push after every commit: git push -q -u origin ${b}. Open no pull request. Merge nothing into ${g} or ${base.ref}.
For a how-to question under a decided design, pick the option that keeps the issue's decisions and the repo rules, build it, and name the choice in notes. Escalate only a question the issue does not answer about what the user sees, hears or reads. To escalate, or when the test or the fast check stays red, push what you have${tracked ? `, ${post(`WORKER BLOCKED branch=${b}`, '<the question, or the red command and its last output line>')}\n,` : ''} and set status escalated.
${FINDINGS_ASK}
${tracked ? `When done, and only when the test and the fast check passed, ${post(`WORKER REPORT branch=${b} head=<the SHA you pushed> passed`, '<the proof lines and what you did not verify>')}\n` : ''}Report task ${n}, round 0, branch ${b}, the full 40-character SHA of your last push (git rev-parse HEAD after it; never a placeholder), and the test command with its last output line. ${AT}${rules}`
}
// verify: why the flow refuses a builder report, or '' when it lands it.
function verify(r, e) {
  if (!r) return 'the builder returned nothing'
  if (r.status !== 'done') return `the builder escalated: ${r.escalation || 'no question given'}`
  if (r.task !== String(e.issue)) return `the report names task ${r.task}, not ${e.issue}`
  if (r.branch !== e.branch) return `the report names branch ${r.branch}, not ${e.branch}`
  if (badSha(r.sha)) return `the report SHA ${r.sha} is not a full SHA`
  if (!r.test.passed) return `the focused test is red: ${r.test.line}`
  if (!(r.gate && r.gate.passed)) return r.gate ? `the fast check is red: ${r.gate.line}` : `the fast check was not run: report gate for ${args.gate}`
  return ''
}

// ---- Land: 1 landing at a time per group branch. The lander merges by SHA, runs the fast check, pushes.
// A refused landing posts WORKER BLOCKED on the issue, so a re-run reads a question, not a report to land.
function landPrompt(e, rep, resolve) {
  const g = e.group
  const refuse = DOC(`gh issue comment ${e.issue} --repo ${repo} --body-file -`, `WORKER BLOCKED branch=${rep.branch}\nlanding refused at ${rep.sha}: <the escalation line>`)
  return `You land issue #${e.issue} of ${repo} in its group branch ${g}: merge ${rep.branch} at ${rep.sha}, by that SHA.
1. ${checkout(g)} Then merge the default branch in: git merge -q --no-edit origin/${base.ref} (on a conflict: git merge --abort and go on without it).${extraBranches ? ` The builder pushes a branch of its own beside ${rep.branch}: fetch the SHA itself (git fetch -q origin ${rep.sha}) and never merge by a branch name. Report in extra_branches each other remote branch whose head is ${rep.sha} (git ls-remote origin), for the cleanup after the PR merges.` : ''}
2. In it: note the pre-merge tip (git rev-parse HEAD), then git merge --no-ff --no-commit ${rep.sha}
3. On a conflict: ${resolve ? 'resolve it when both sides are clear; keep the behavior of both. When the 2 sides change one contract in 2 ways, run git merge --abort and set escalation to the files.' : 'run git merge --abort and set escalation to the conflicting files. Do not resolve it.'}
   When the merge was not aborted, commit it now, before the check: git commit -q -m 'Merge ${rep.branch} into ${g}'. The check of step 4 runs on this commit.
4. ${setupText(where(g)).trim()} Run the fast check once: ${args.gate}. It is green only when it exits 0. Report check: command, its last output line, passed. Run nothing wider: CI on the push is the gate.
5. Green: keep the merge commit and report merged true.
   Red: report merged false and the last output line in escalation. Then reset the branch to the pre-merge tip of step 2: git checkout -q -f -B "$(git branch --show-current)" <the pre-merge tip> (git merge --abort when the merge is still in progress). Stop: commit nothing more, push nothing.
6. git push -q origin ${g}. Report issue ${e.issue}, group ${g}, and sha: the full SHA of the push (the pre-merge tip when nothing was pushed).${access === 'none' ? `\n   The builder could not post its report: after the push, post it for it:\n${DOC(`gh issue comment ${e.issue} --repo ${repo} --body-file -`, `WORKER REPORT branch=${rep.branch} head=${rep.sha} passed\nlanded on ${g}`)}` : ''}
7. When you report merged false ${resolve ? '' : 'because the check is red '}(not when you only stopped at a conflict you were told not to resolve), post the refusal on the issue, with the escalation line in place of <the escalation line>:
${refuse}
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
// reaction), else it files 1 issue labelled kind:<kind> and sev:<severity> with the line Group: <group>, which
// queue-state reads. An open holds finding keeps its group's PR a draft.
const WEIGHTS = contract['x-severity-weights']
const KINDS = findingSchema.properties.kind.enum
const priority = (f) => (WEIGHTS[f.severity] || 0) * Math.max(1, f.votes || 1) * Math.max(1, f.minutes || 0)
const findings = []
function fileFinding(f, who, label, g, issue) {
  if (!KINDS.includes(f.kind) || !(f.severity in WEIGHTS)) {
    log(`${label}: dropped: kind ${oneLine(f.kind)} or severity ${oneLine(f.severity)} is not in the contract`)
    return Promise.resolve()
  }
  return serial('#findings', async () => {
    const minutes = Number.isInteger(f.minutes) && f.minutes >= 0 ? f.minutes : 0
    const title = oneLine(f.title)
    const a = await call(0, `File or vote on 1 finding on ${repo}. Edit, commit and push nothing, and open no pull request. Put the finding's text only in the quoted heredocs below, never inside double quotes.
The finding: kind ${f.kind}, severity ${f.severity}. Its title and evidence are in step 3. It cost ${who} ${minutes} minutes.
1. Search the open findings: gh issue list --repo ${repo} --state open --label kind:${f.kind} --limit 100 --json number,title,url,body. A match is an open finding of the same problem: the same failing check, file or symptom, in other words.
2. On a match, vote and file nothing, with <n> its number:
${DOC(`gh issue comment <n> --repo ${repo} --body-file -`, `+1 from ${who}: cost ${minutes} minutes.\nEvidence: ${f.evidence}`)}
   then gh api repos/${repo}/issues/<n>/reactions -f content=+1. Report voted true; url, the URL of the match; votes, 1 plus the count of its comments that start with "+1 from" (yours included); minutes, the "Minutes lost: N" of its body plus the "cost N minutes" of each such comment.
3. No match: gh label create kind:${f.kind} --repo ${repo} --force and gh label create sev:${f.severity} --repo ${repo} --force, then:
${DOC(`gh issue create --repo ${repo} --label kind:${f.kind} --label sev:${f.severity} --title "$(head -n 1 <<'${EOF}T'\n${title.split(EOF).join('AGENTIC_SDLC-EOF')}\n${EOF}T\n)" --body-file -`, `Severity ${f.severity}: found by ${who}.\nGroup: ${g}\n\nEvidence: ${f.evidence}\nMinutes lost: ${minutes}`)}
   Report voted false, votes 1, minutes ${minutes}, and url: the issue URL it printed ("" when it failed).
4. Report kind ${f.kind}, severity ${f.severity}, title and evidence as above.${rules}`,
    { label, phase: 'Review', schema: findingSchema, ...spawn('lander', FIRST_TRY.lander) })
    const row = { group: g, by: who, ...(issue && { issue }), ...(a || { kind: f.kind, severity: f.severity, title, evidence: f.evidence, url: '', minutes, voted: false, votes: 1 }) }
    row.priority = priority(row)
    findings.push(row)
    log(`${label}: ${row.voted ? `voted on ${row.url} (${row.votes} votes)` : row.url ? `filed ${row.url}` : 'the filing failed'}: ${row.severity} ${row.kind}`)
  })
}

// ---- Reviews: beside the landings, each in its own lane, so no landing waits on one.
const REVIEW_EVERY = args.review_every || LIMITS.review_batch
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
    reviewRuns.push(fileFinding(f, who, `finding ${label} ${i + 1}`, l ? l.group : '', l && l.issue))
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
// waitsOn: the blockers of e that are not done for it. A closed blocker is not listed (queue-state lists open ones);
// an open blocker counts as done only once landed on the same group branch, where its code is (#418).
const landedHere = (b) => (outcome.get(b) || {}).state === 'landed' || Boolean((issues.get(b) || {}).landed)
const waitsOn = (e) => (e.blocked_by || []).filter((b) => !(landedHere(b) && (issues.get(b) || {}).group === e.group))
function dispatch(e) {
  const st = stateOf(e, now)
  if (st === 'closed') return done(e, 'skipped', 'closed')
  if (st === 'landed') return done(e, 'skipped', `landed on ${e.group} by an earlier run`)
  if (st === 'unsafe') return done(e, 'escalated', 'its branch or group has characters a shell would read')
  if (st === 'unpassed') return done(e, 'escalated', 'WORKER REPORT without passed: the test or the fast check failed')
  if (st === 'blocked') return done(e, 'escalated', `WORKER BLOCKED: ${oneLine(e.question)}`)
  if (st === 'live' || waitsOn(e).length > 0 || active.size >= cap) return
  log(`#${e.issue}: ${st === 'reported' ? `a passed report at ${e.report.sha} lands` : st === 'stale' ? `quiet since ${e.activity_at}: a builder restarts on ${e.branch}` : `a builder starts on ${e.branch}`}`)
  const run = st === 'reported'
    ? land(e, e.report)
    : call(e.issue, builderPrompt(e, st), { label: `build ${e.issue}`, phase: 'Build', schema: reportSchema, ...spawn('builder', e.tier) }).then((r) => {
      const refused = verify(r, e)
      if (refused) return done(e, 'escalated', refused)
      for (const [i, f] of (r.findings || []).entries()) reviewRuns.push(fileFinding(f, `#${e.issue}`, `finding ${e.issue} ${i + 1}`, e.group, e.issue))
      return land(e, { branch: r.branch, sha: r.sha })
    })
  active.set(e.issue, run.catch((err) => done(e, 'escalated', `the flow failed on it: ${err.message}`)).then(() => active.delete(e.issue)))
}
// absorb: take a tracker read in; returns the open issues it names for the first time.
function absorb(t) {
  now = isoSeconds(t.at) || now
  firstAt = firstAt || t.at
  const joined = t.issues.filter((e) => e.state === 'open' && !issues.has(e.issue))
  for (const e of t.issues) issues.set(e.issue, e)
  groupsRead = Object.fromEntries((t.groups || []).map((g) => [g.group, g]))
  return joined
}
phase('Read')
let lastRead = null
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
  lastRead = t
  const joined = absorb(t)
  await Promise.all([...new Set(joined.filter((e) => SAFE_REF.test(e.group)).map((e) => e.group))].map((g) => openPr(g, joined.filter((e) => e.group === g))))
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

// ---- Ready: decided on 1 fresh read, after every landing, review and finding. A group leaves draft only when every
// issue its PR Closes is landed per that read, and it has no open holds finding (read, or filed in this run).
phase('Ready')
const fresh = lastRead ? await readTracker([]) : null
if (fresh) absorb(fresh)
const shutOut = []
// held: the groups whose PR is ready but not merged, for the lead.
const held = []
const GREEN = ['success', 'neutral']
// checksNotGreen: why the ready-time checks of p do not allow a merge, or ''. Each required check (each check,
// when the base requires none) needs a newest run that started at or after ready_at, completed, and passed. A
// SKIPPED one stops the merge: GitHub counts it as passing, so a check skipped on a draft push would merge at once.
function checksNotGreen(p) {
  const at = isoSeconds(p.ready_at)
  if (at === null || badSha(p.head)) return 'the ready step reported no ready_at or head'
  const checks = p.checks || []
  const names = (p.required || []).length > 0 ? p.required : [...new Set(checks.map((c) => c.name))]
  if (names.length === 0) return 'no check ran on the head after ready'
  const bad = names.map((n) => {
    const c = checks.filter((x) => x.name === n).sort((x, y) => (isoSeconds(y.started_at) || 0) - (isoSeconds(x.started_at) || 0))[0]
    const conclusion = c ? String(c.conclusion || '').toLowerCase() : ''
    if (!c || (isoSeconds(c.started_at) || 0) < at) return `${n} has no run since ready`
    if (c.status !== 'completed') return `${n} is ${c.status}`
    if (conclusion === 'skipped') return `${n} was SKIPPED (a skip counts as passing on GitHub)`
    return GREEN.includes(conclusion) ? '' : `${n} is ${conclusion}`
  }).filter(Boolean)
  return bad.join('; ')
}
const groups = [...new Set([...issues.values()].map((e) => e.group))].filter((g) => SAFE_REF.test(g))
for (const g of groups) {
  const read = groupsRead[g] || { closes: [], holds: [] }
  const row = prs[g] || { group: g, pr: read.pr || '', closes: read.closes }
  prs[g] = row
  if (!fresh) {
    row.reason = 'stays a draft: no tracker read after the landings'
    continue
  }
  if (!read.pr || read.closes.length === 0) continue
  const notLanded = read.closes.filter((n) => !(issues.get(n) || {}).landed)
  // An issue closed with no landing never lands: the lead removes its Closes line or lands it.
  for (const n of notLanded.filter((x) => (issues.get(x) || {}).state === 'closed')) shutOut.push({ issue: n, reason: `closed without a landing, but ${read.pr} Closes it: remove its Closes line or land it` })
  const holds = [...read.holds, ...findings.filter((f) => f.group === g && f.severity === 'holds').map((f) => f.url || f.title)]
  if (notLanded.length > 0 || holds.length > 0) {
    row.reason = notLanded.length > 0 ? `stays a draft: ${notLanded.map((n) => `#${n}`).join(' ')} not landed` : `stays a draft: holds finding ${holds.join(', ')}`
    log(`${g}: ${row.reason}`)
    continue
  }
  const p = await serial(g, () => call(0, `Make the draft PR of the group branch ${g} of ${repo} ready, and wait for its ready-time checks: every issue it Closes has landed. Never push to ${base.ref}, never merge the PR, and never turn on auto-merge: flow merges after it reads your report.
1. ${checkout(g)} Merge the default branch in by a merge commit: git merge --no-ff --no-edit origin/${base.ref}. On a conflict: git merge --abort, push nothing, and report escalation "merge conflict with ${base.ref}: <files>". Else run the fast check once: ${args.gate}; red: push nothing and report its last line in escalation. Green: git push -q origin ${g}.
2. The PR: gh pr list --repo ${repo} --head ${g} --state open --json url,headRefOid. Report pr (its url) and head (its headRefOid).
3. Report ready_at: run date -u +%Y-%m-%dT%H:%M:%SZ. Then mark it ready, which runs the heavy CI lanes once: gh pr ready <url> --repo ${repo}. Report ready true when it exits 0.
4. Report required: the required check names of ${base.ref}: gh api repos/${repo}/rules/branches/${base.ref} --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context', and gh api repos/${repo}/branches/${base.ref}/protection/required_status_checks --jq '.contexts[]' (a 404 there means none); [] when both give none.
5. Wait, at most 90 minutes, polling every 60 seconds: gh api --paginate repos/${repo}/commits/<head>/check-runs --jq '.check_runs[] | [.name, .status, (.conclusion // ""), .started_at] | @tsv'. Keep the newest run of each name (the latest started_at). Stop when each required name (each name, when required is []) has a newest run that started at or after ready_at and is completed.
6. Report checks: the newest run of each name, as name, status, conclusion, started_at, exactly as the API gave them. Judge nothing: flow decides. ${AT}${rules}`,
  { label: `ready ${g}`, phase: 'Ready', schema: prSchema, ...spawn('lander', FIRST_TRY.lander) }))
  if (p) Object.assign(row, { pr: p.pr || row.pr, ready: Boolean(p.ready) })
  const why = !p ? 'the ready step returned nothing' : p.escalation || (!p.ready ? 'gh pr ready failed' : checksNotGreen(p))
  if (why) {
    row.reason = `not merged: ${why}`
    held.push({ group: g, reason: `${row.pr || g}: ${row.reason}` })
    log(`${g}: ${row.reason}`)
    continue
  }
  const m = await serial(g, () => call(0, `Merge the PR ${row.pr} of ${repo}, pinned to the head its checks ran on: gh pr merge ${row.pr} --repo ${repo} --merge --match-head-commit ${p.head}. Report group ${g}, pr, closes (each issue its body has a Closes line for), ready true, and merged true when it exits 0; else merged false and its last line in escalation. ${AT}${rules}`,
    { label: `merge ${g}`, phase: 'Ready', schema: prSchema, ...spawn('lander', FIRST_TRY.lander) }))
  row.merged = Boolean(m && m.merged)
  if (!row.merged) {
    row.reason = `not merged: ${(m && m.escalation) || 'the merge step returned nothing'}`
    held.push({ group: g, reason: `${row.pr}: ${row.reason}` })
  }
  log(`${g}: ${row.merged ? `${row.pr} merged after its ready-time checks passed` : row.reason}`)
}

// ---- Report: 1 metrics row per issue that ran an agent. This runtime reports no usage.
phase('Report')
const UNAVAILABLE = 'unavailable'
const RESULT = { landed: 'merged', escalated: 'escalated' }
const SEVERITY_ROW = { holds: 'critical', major: 'major', minor: 'minor' }
const stateIs = (s) => [...issues.keys()].filter((n) => (outcome.get(n) || {}).state === s)
const waiting = [...issues.values()].filter((e) => !outcome.has(e.issue))
const metrics = Object.keys(agentsOf).filter((n) => issues.has(Number(n))).map((n) => {
  const e = issues.get(Number(n))
  const o = outcome.get(e.issue) || {}
  const sp = runtime.tiers[e.tier]
  const counts = { critical: 0, major: 0, minor: 0 }
  for (const f of findings) if (f.issue === e.issue) counts[SEVERITY_ROW[f.severity]]++
  return {
    task: n, provider: runtime.provider, tier: e.tier, model: sp.model, ...(sp.effort && { effort: sp.effort }), agents: agentsOf[n],
    elapsed_s: Math.max(0, (isoSeconds(o.at) || now) - (isoSeconds(firstAt) || now)), rework_rounds: 0,
    findings: counts, result: RESULT[o.state] || 'failed', tokens: UNAVAILABLE, cost_usd: UNAVAILABLE,
  }
})
const escalations = [
  ...stateIs('escalated').map((n) => ({ issue: n, reason: outcome.get(n).reason })),
  ...shutOut,
  ...held.map((h) => ({ group: h.group, reason: h.reason })),
  ...waiting.map((e) => ({ issue: e.issue, reason: waitsOn(e).length > 0 ? `waits on ${waitsOn(e).map((b) => `#${b}`).join(' ')}` : `${stateOf(e, now)}: not started` })),
]
log(`${stateIs('landed').length} landed, ${stateIs('skipped').length} skipped, ${escalations.length} for the lead; ${groups.map((g) => `${g}: ${prs[g].pr || 'no PR'}${prs[g].merged ? ' (merged)' : ''}`).join(', ')}; ${findings.length} finding${findings.length === 1 ? '' : 's'}, ${reviews.length} review${reviews.length === 1 ? '' : 's'}, ${reads} tracker read${reads === 1 ? '' : 's'}.`)

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
