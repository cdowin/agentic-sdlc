#!/usr/bin/env node
'use strict'
// Node 18+, no packages. This is a host boundary, not a standalone Codex runtime.
// new Adapter({host: new CodexHost(call, readResult), runtime, repo, repository, issue,
//   lead, concurrency}).split(args) / .reviewBatch(args).
// call dispatches the exact collaboration tool names below. readResult(target) returns
// {status:'running'} or {status:'completed',output:<final JSON string/object>} from the
// host's mailbox/list_agents. Native wait_agent supplies wakeups, not report values.
// The current wrapper cannot select agent_type or enforce a schema/worktree/tool list.
// Role and schema are in the brief; git creates worktrees and check.js gates every output.
// CLI: first stdin JSON line is {method:'split'|'review-batch'|'claim'|'push'|'release',options,args}.
// stdout {id,tool,args} requests need stdin {id,result} or {id,error} replies from a host.
// read_result is a host mailbox operation, not a native tool. Final: {result} or {error}.
// split works under the lead's claim: args.claims maps the task id to the URL of the claim comment
// the lead posted. Neither the adapter nor its workers post or release a claim. A worker pushes its
// child branch (the claim branch plus -part) under the same comment: push args carry branch.
// args.needs lists the capabilities the task needs; the runtime must have each of them.
// claim/push/release use GitHub and git directly and need no host. push args include claim_url
// and last_push_sha after the first push. Never push around this guard. The worker must
// remember the returned SHA between commits. Worktree isolation is not a sandbox.
const fs = require('fs')
const path = require('path')
const readline = require('readline')
const { randomBytes } = require('crypto')
const { execFileSync } = require('child_process')
const { contract, check } = require('../plugin/contract/check.js')
const limits = contract['x-limits']
const staleMs = limits.stale_claim_minutes * 60000
const validate = (def, value, opts) => {
  const errors = check(def, value, opts)
  if (errors.length) throw new Error(`${def}: ${errors.join('; ')}`)
  return value
}
const json = (value) => typeof value === 'string' ? JSON.parse(value) : value
const name = (s) => {
  if (typeof s !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(s)) throw new Error(`unsafe branch/part name: ${s}`)
  return s
}
const filePath = (p) => {
  if (typeof p !== 'string' || !p || path.posix.isAbsolute(p) || p.split('/').includes('..')) throw new Error('files must be relative repo paths')
  return path.posix.normalize(p).replace(/\/+$/, '')
}
const ownsFile = (files, f) => files.some((p) => f === p || f.startsWith(`${p}/`))
const git = (repo, ...args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
const ancestor = (repo, a, b) => {
  try { git(repo, 'merge-base', '--is-ancestor', a, b); return true } catch { return false }
}
const encodeClaim = (c) => `agentic-sdlc:claim\n\`\`\`json\n${JSON.stringify(c, null, 2)}\n\`\`\`\n`
// A marked comment that cannot be read fails closed (throws) unless the reader passes a skipped
// list. Then it goes in the list as {url, reason} and every other comment stays readable.
function parseComments(comments, skipped) {
  const out = []
  for (const c of comments.filter((x) => x.body.split('\n')[0].trim() === 'agentic-sdlc:claim')) {
    try {
      const match = c.body.match(/^agentic-sdlc:claim\s*\n```json\n([\s\S]*?)\n```\s*$/)
      if (!match) throw new Error(`malformed claim comment ${c.html_url}`)
      const record = { url: c.html_url, created_at: c.created_at, claim: JSON.parse(match[1]) }
      validate('claim_comment', record)
      if (!Number.isFinite(Date.parse(record.created_at))) throw new Error('invalid server created_at')
      out.push(record)
    } catch (error) {
      if (!skipped) throw error
      skipped.push({ url: c.html_url, reason: error.message })
    }
  }
  return out
}
// Server time decides. Numeric comment id breaks same-second ties in creation order.
// A historical claim that is malformed, fails the contract or breaks a takeover rule is skipped and
// pushed to the optional skipped list as {url, reason}. It never blocks the readers of the task.
function owner(comments, task, skipped = []) {
  const skip = (c, error) => skipped.push({ url: c?.url, reason: error.message })
  const readable = comments.filter((c) => {
    const bad = check('claim_comment', c)
    if (bad.length) skip(c, new Error(bad[0]))
    return !bad.length
  })
  const sorted = readable.filter((c) => c.claim.task === task).sort((a, b) => {
    const order = Date.parse(a.created_at) - Date.parse(b.created_at)
    if (order) return order
    const x = BigInt(a.url.split('-').pop()), y = BigInt(b.url.split('-').pop())
    return x < y ? -1 : x > y ? 1 : 0
  })
  const active = []
  for (const c of sorted) {
    try {
      validate('claim', c.claim, { now: Date.parse(c.created_at), claims: sorted })
      if (c.claim.state === 'released') {
        for (let i = active.length - 1; i >= 0; i--) if (active[i].claim.lead === c.claim.lead) active.splice(i, 1)
      } else if (c.claim.supersedes) {
        const old = sorted.find((x) => x.url === c.claim.supersedes)
        if (old.claim.state !== 'claimed' || old.claim.branch !== c.claim.branch || old.claim.base_sha !== c.claim.base_sha) throw new Error('takeover changed branch/base or targets release')
        // A concurrent takeover may have read the same stale owner. The earlier
        // server comment won; the losing historical comment must not poison reads.
        if (active[0]?.url !== c.claim.supersedes) continue
        active.shift()
        // The takeover replaces the first owner ahead of outstanding losing claims.
        active.unshift(c)
      } else active.push(c)
    } catch (error) { skip(c, error) }
  }
  return active[0] || null
}
class GitHubClaims {
  constructor({ repo, repository, issue, now = () => Date.now() }) {
    if (!/^[\w.-]+\/[\w.-]+$/.test(repository) || !/^\d+$/.test(String(issue))) throw new Error('repository and numeric issue required')
    this.repo = path.resolve(repo); this.repository = repository; this.issue = issue; this.now = now
  }
  async comments() {
    const pages = JSON.parse(execFileSync('gh', ['api', '--paginate', '--slurp', `repos/${this.repository}/issues/${this.issue}/comments`], { encoding: 'utf8' }))
    this.skipped = []
    return parseComments(pages.flat(), this.skipped)
  }
  async post(claim) {
    validate('claim', claim, { now: this.now() })
    const c = JSON.parse(execFileSync('gh', ['api', `repos/${this.repository}/issues/${this.issue}/comments`, '--method', 'POST', '--input', '-'], {
      input: JSON.stringify({ body: encodeClaim(claim) }), encoding: 'utf8',
    }))
    return parseComments([c])[0]
  }
  async head(branch) {
    name(branch)
    // Missing branches are expected before a first push; network failures must stop.
    const listed = git(this.repo, 'ls-remote', '--heads', 'origin', `refs/heads/${branch}`)
    if (!listed) return null
    git(this.repo, 'fetch', '-q', 'origin', `refs/heads/${branch}`)
    const [sha, time] = git(this.repo, 'log', '-1', '--format=%H %cI', 'FETCH_HEAD').split(' ')
    return { sha, time: Date.parse(time) }
  }
  async ancestor(a, b) {
    if (git(this.repo, 'rev-parse', '--is-shallow-repository') === 'true') git(this.repo, 'fetch', '--unshallow', 'origin')
    return ancestor(this.repo, a, b)
  }
  async push(repo, branch) { git(repo, 'push', 'origin', `HEAD:refs/heads/${name(branch)}`); return git(repo, 'rev-parse', 'HEAD') }
}
class ClaimSession {
  // gate: {runtime, tasks} for the contract claim check. A claim of a graph task is refused when
// the runtime lacks a capability in the task's needs (check.js --runtime --graph).
constructor(backend, claim, gate = {}) { this.backend = backend; this.claim = claim; this.gate = gate; this.skipped = []; this.record = null; this.lastPush = null; this.stopped = false }
  async acquire() {
    const b = this.backend, comments = await b.comments()
    validate('claim', this.claim, { now: b.now(), ...this.gate })
    const previous = owner(comments, this.claim.task, this.skipped)
    const head = await b.head(this.claim.branch)
    if (previous) {
      if (previous.claim.branch !== this.claim.branch || previous.claim.base_sha !== this.claim.base_sha) throw new Error('owner branch/base mismatch')
      const now = b.now()
      if (head && !await b.ancestor(previous.claim.resume_sha || previous.claim.base_sha, head.sha)) throw new Error('remote branch force-pushed; stop and escalate')
      // No branch: the old lead died before its first push. Only the claim age decides, and the
      // new lead resumes from base_sha.
      if (now - Date.parse(previous.created_at) < staleMs || (head && now - head.time < staleMs)) throw new Error('task already claimed; not stale')
      this.claim = { ...this.claim, supersedes: previous.url, resume_sha: head ? head.sha : this.claim.base_sha }
      validate('claim', this.claim, { claims: comments, now, ...this.gate })
    } else if (head) {
      if (!await b.ancestor(this.claim.base_sha, head.sha)) throw new Error('remote branch rewrote base')
      this.claim = { ...this.claim, resume_sha: head.sha }
    }
    this.record = await b.post(this.claim)
    await this.beforePush()
    return this.record
  }
  async beforePush() {
    if (this.stopped || !this.record) throw new Error('claim session stopped or unclaimed')
    const b = this.backend, head = await b.head(this.claim.branch), current = owner(await b.comments(), this.claim.task, this.skipped)
    if (current?.url !== this.record.url) {
      await this.release()
      this.stopped = true
      throw new Error('claim lost; stopped')
    }
    const anchor = this.lastPush || this.claim.resume_sha || this.claim.base_sha
    // A resume_sha equal to base_sha means the old lead never pushed: no branch is expected.
    const resumed = this.claim.resume_sha && this.claim.resume_sha !== this.claim.base_sha
    if ((!head && (this.lastPush || resumed)) || (head && !await b.ancestor(anchor, head.sha))) {
      this.stopped = true
      throw new Error('remote branch force-pushed/deleted; stop and escalate')
    }
    return head
  }
  async push(repo) {
    const head = await this.beforePush()
    const local = git(repo, 'rev-parse', 'HEAD')
    if (!await this.backend.ancestor(head?.sha || this.claim.base_sha, local)) throw new Error('local branch does not resume remote head')
    this.lastPush = await this.backend.push(repo, this.claim.branch)
    return this.lastPush
  }
  async release() {
    // An adopted claim belongs to the lead that posted it. The adapter never releases it.
    if (!this.record || this.released || this.adopted) return
    const released = { ...this.claim, state: 'released', at: new Date(this.backend.now()).toISOString() }
    delete released.supersedes; delete released.resume_sha
    await this.backend.post(released)
    this.released = true; this.stopped = true
  }
}
class CodexHost {
  constructor(call, readResult) { this.call = call; this.readResult = readResult; this.sequence = 0; this.session = randomBytes(6).toString('hex') }
  async spawn({ message, model, effort, role }) {
    const r = await this.call('spawn_agent', { task_name: `sdlc_${this.session}_${role}_${++this.sequence}`, message, model, reasoning_effort: effort, fork_turns: 'none' })
    const handle = r.task_name || r.agent_id
    if (!handle) throw new Error('spawn response needs task_name or agent_id')
    return handle
  }
  async wait(target) {
    while (true) {
      const r = await this.readResult(target)
      if (r.status === 'completed') return r.output
      if (r.status !== 'running') throw new Error(`worker ${target}: ${r.status}`)
      await this.call('wait_agent', { timeout_ms: 10000 })
    }
  }
  message(target, message) { return this.call('send_message', { target, message }) }
  followUp(target, message) { return this.call('followup_task', { target, message }) }
  interrupt(target) { return this.call('interrupt_agent', { target }) }
}
class Adapter {
  constructor(options) {
    Object.assign(this, options)
    validate('runtime', this.runtime)
    this.repo = path.resolve(this.repo)
    this.concurrency = Math.min(this.concurrency || this.runtime.concurrency || 1, this.runtime.concurrency || Infinity)
    if (!Number.isInteger(this.concurrency) || this.concurrency < 1) throw new Error('positive concurrency required')
    if (!this.lead) throw new Error('stable lead id required')
    this.clock = options.clock || Date.now; this.spawns = []; this.rounds = 0; this.lastReview = null
    this.active = new Set(); this.claims = []; this.skipped = []; this.worktrees = []; this.job = randomBytes(6).toString('hex'); this.cancelled = false
    this.backend = options.backend || (this.repository && this.issue ? new GitHubClaims(options) : null)
  }
  async batch(items, fn) {
    const results = []
    // Bound starts as well as waits; a rejected item cancels all peers in finish().
    for (let i = 0; i < items.length; i += this.concurrency) {
      const settled = await Promise.allSettled(items.slice(i, i + this.concurrency).map(async (item) => {
        try { return await fn(item) } catch (error) { await this.cancel(); throw error }
      }))
      const failed = settled.find((r) => r.status === 'rejected')
      if (failed) throw failed.reason
      results.push(...settled.map((r) => r.value))
    }
    return results
  }
  async finish(fn) {
    try {
      const result = await fn()
      if (result.status === 'done') {
        for (const wt of [...this.worktrees]) {
          const head = await this.backend.head(wt.branch)
          const local = git(wt.path, 'rev-parse', 'HEAD')
          if (head && await this.backend.ancestor(local, head.sha) && !git(wt.path, 'status', '--porcelain', '--ignored')) {
            git(this.repo, 'worktree', 'remove', wt.path)
            this.worktrees.splice(this.worktrees.indexOf(wt), 1)
          }
        }
      }
      const skipped = this.skippedClaims()
      const extra = { ...(this.worktrees.length ? { worktrees: this.worktrees } : {}), ...(skipped.length ? { skipped_claims: skipped } : {}) }
      return { ...result, ...extra }
    } catch (error) {
      if (this.worktrees.length) error.message += `; recovery worktrees: ${this.worktrees.map((w) => w.path).join(', ')}`
      throw error
    } finally {
      this.cancelled = true
      const errors = await Promise.allSettled([...this.active].map((a) => this.host.interrupt(a)))
      this.active.clear()
      const releases = await Promise.allSettled(this.claims.map((c) => c.release()))
      const failed = [...errors, ...releases].find((r) => r.status === 'rejected')
      if (failed) throw new Error(`cleanup failed: ${failed.reason.message}`)
    }
  }
  // Every historical claim comment that was skipped as malformed, once each.
  skippedClaims() {
    const all = [...this.skipped, ...(this.backend?.skipped || []), ...this.claims.flatMap((c) => c.skipped)]
    return all.filter((x, i) => all.findIndex((y) => y.url === x.url && y.reason === x.reason) === i)
  }
  cancel() { this.cancelled = true; return Promise.all([...this.active].map((a) => this.host.interrupt(a))) }
  async run(role, tier, message, def, opts = {}) {
    if (this.cancelled) throw new Error('adapter cancelled')
    const setting = this.runtime.tiers[tier]
    if (!setting?.model || !setting.effort) throw new Error(`explicit model/effort required for ${tier}`)
    if (!['none', 'minimal', 'low', 'medium', 'high'].includes(setting.effort)) throw new Error('effort exceeds high')
    const handle = await this.host.spawn({ role, model: setting.model, effort: setting.effort,
      message: `Role: ${role} (${this.runtime.agent_types[role]}). ${message}\nReturn only JSON matching this contract:\n${JSON.stringify(contract.$defs[def])}\nPR, CI and merge to main belong to the lead. Open no PR.\n${this.rules || ''}` })
    this.spawns.push({ role, tier, model: setting.model, effort: setting.effort, handle })
    this.active.add(handle)
    if (this.cancelled) { await this.host.interrupt(handle); this.active.delete(handle); throw new Error('adapter cancelled') }
    const value = validate(def, json(await this.host.wait(handle)), opts)
    this.active.delete(handle)
    return { handle, value }
  }
  // The lead posts one claim per task before the run and passes its comment URL in args.claims
  // (task id -> URL). The adapter works under that claim: it posts none and releases none.
  async adopt(task, claimUrl, branch, base, needs = []) {
    if (this.cancelled) throw new Error('adapter cancelled')
    if (!this.backend) throw new Error('split needs repository and numeric issue for claims')
    if (!claimUrl) throw new Error(`split needs args.claims[${task}]: the URL of the lead's claim comment`)
    const comments = await this.backend.comments()
    const record = comments.find((c) => c.url === claimUrl)
    if (!record || record.claim.state !== 'claimed' || record.claim.task !== task) throw new Error(`args.claims[${task}] must identify a claimed comment of task ${task}`)
    if (record.claim.branch !== branch || record.claim.base_sha !== base) throw new Error('lead claim branch/base differ from the split')
    const current = owner(comments, task, this.skipped)
    if (current?.url !== claimUrl) throw new Error('the lead claim is not the owner of the task')
    validate('claim', record.claim, { now: this.backend.now(), runtime: this.runtime, tasks: [{ id: task, needs }] })
    const c = new ClaimSession(this.backend, record.claim)
    c.record = record; c.adopted = true
    this.claims.push(c)
    return c
  }
  // A worker branch is a child of the lead branch. It pushes under the same claim comment.
  child(lead, branch, base) {
    const claim = { ...lead.claim, branch, base_sha: base }
    delete claim.supersedes; delete claim.resume_sha
    const c = new ClaimSession(this.backend, claim)
    c.record = lead.record; c.adopted = true
    this.claims.push(c)
    return c
  }
  worktree(branch, base) {
    name(branch)
    const root = path.resolve(this.repo, this.runtime.worktree_root)
    if (root === this.repo || !root.startsWith(`${this.repo}${path.sep}`)) throw new Error('worktree root must be inside repo')
    const dir = path.join(root, `${branch}-${this.job}`)
    fs.mkdirSync(root, { recursive: true })
    if (!fs.realpathSync(root).startsWith(`${fs.realpathSync(this.repo)}${path.sep}`)) throw new Error('worktree root escapes repo through symlink')
    let exists = false
    try { git(this.repo, 'show-ref', '--verify', `refs/heads/${branch}`); exists = true } catch {}
    git(this.repo, 'worktree', 'add', ...(exists ? ['--detach'] : ['-b', branch]), dir, base)
    this.worktrees.push({ branch, path: dir })
    return dir
  }
  pushBrief(c, dir) {
    return `Work only in worktree ${dir}, branch ${c.claim.branch}. The claim is ${c.record.url}.\nCommit by path. Push after every commit through this guard; open no PR:\nnode ${path.join(__dirname, 'adapter.js')}\nIts first stdin JSON line: ${JSON.stringify({ method: 'push', options: { repo: dir, repository: this.repository, issue: this.issue }, args: { claim_url: c.record.url, branch: c.claim.branch } })}\nAfter the first push, include args.last_push_sha from the prior guard result. A lost claim or rewritten branch means stop and escalate.\n`
  }
  async report(value, b, c, base, round) {
    if (value.task !== b.part || value.branch !== c.claim.branch || (value.round || 0) !== round) throw new Error('report task/branch/round mismatch')
    if (value.test.command !== b.test) throw new Error('report focused test mismatch')
    await c.beforePush()
    const head = await this.backend.head(value.branch)
    if (!head || head.sha !== value.sha || !await this.backend.ancestor(base, value.sha)) throw new Error('report SHA/base mismatch')
    const allowed = b.files.map(filePath)
    const edited = git(this.repo, 'diff', '--name-only', base, value.sha).split('\n').filter(Boolean)
    if (edited.some((f) => !ownsFile(allowed, f))) throw new Error('worker edited outside its files')
    c.lastPush = value.sha
    return value
  }
  async reviewBatch(args) { return this.finish(() => this.review(args)) }
  async review(args) {
    const results = args.results || [], ids = results.map((r) => r.id)
    if (!results.length || results.length > limits.review_batch || new Set(ids).size !== ids.length || results.some((r) => !r.id || !r.diff || !r.test)) throw new Error('review needs unique ids, diff/test, within batch limit')
    const brief = `Blind review these diffs and tests as one batch; no author/model/cost. Run tests.\n${JSON.stringify(results.map(({ id, diff, test }) => ({ id, diff, test })))}\nDesign decisions: ${args.decisions || '(none)'}\nScore all ids. Give severity and reproducible evidence for each finding.`
    const { value: review } = await this.run('reviewer', 'lead', brief, 'review', { ids })
    const heavy = review.findings.filter((f) => f.severity !== 'minor')
    const checked = []
    for (const f of heavy) {
      const verdicts = await this.batch([1, 2], async () => (await this.run('skeptic', 'judgment', `Try to disprove finding ${JSON.stringify(f)}. Reproduce evidence before agreeing.\n${JSON.stringify(results.filter((r) => f.ids.includes(r.id)).map(({ id, diff, test }) => ({ id, diff, test })))}`, 'verdict')).value)
      checked.push({ ...f, verdicts, stands: verdicts.every((v) => v.agree) })
    }
    return { scores: review.scores, pairs: review.pairs || [], findings: [...review.findings.filter((f) => f.severity === 'minor'), ...checked.filter((f) => f.stands)], dropped: checked.filter((f) => !f.stands) }
  }
  // One contract metrics row per task, after the task ran. Codex reports no usage, so tokens and
  // cost are unavailable (never 0). No spawn, no row: the task started no agent.
  metricsRow(args, result, started) {
    if (!this.spawns.length) return []
    const tier = args.tier || 'judgment', setting = this.runtime.tiers[tier]
    const count = (severity) => (this.lastReview?.findings || []).filter((f) => f.severity === severity).length
    return [validate('metrics', { task: String(args.issue), provider: this.runtime.provider, tier, model: setting.model, effort: setting.effort,
      agents: this.spawns.length, elapsed_s: Math.max(0, (this.clock() - started) / 1000), rework_rounds: this.rounds,
      findings: { critical: count('critical'), major: count('major'), minor: count('minor') }, result,
      tokens: 'unavailable', cost_usd: 'unavailable' })]
  }
  async split(args) {
    const started = this.clock()
    try {
      const result = await this.finish(() => this.splitTask(args))
      return { ...result, spawns: this.spawns, metrics: this.metricsRow(args, result.status === 'done' ? 'merged' : 'escalated', started) }
    } catch (error) {
      error.metrics = this.metricsRow(args, 'failed', started)
      throw error
    }
  }
  async splitTask(args) {
    const { branch, base, test } = args, parts = (args.parts || []).map((p) => typeof p === 'string' ? p : p.name)
    name(branch); parts.forEach(name)
    if (!args.issue || !base || !test || parts.length < limits.split_parts_min || parts.length > limits.review_batch || new Set(parts).size !== parts.length) throw new Error('split needs issue, branch, base, test and unique parts')
    const baseSha = git(this.repo, 'rev-parse', `${base}^{commit}`)
    const task = String(args.issue)
    const leadClaim = await this.adopt(task, (args.claims || {})[task], branch, baseSha, args.needs || [])
    const dir = this.worktree(branch, leadClaim.claim.resume_sha || baseSha)
    const { value: plan } = await this.run('sub_lead', 'judgment', `${this.pushBrief(leadClaim, dir)}\nRead issue ${args.issue}. Write whole-issue oracle first (${test}) and stubs. Commit/push them. Split into ${parts.join(', ')} with disjoint files and focused tests. Escalate with no briefs if unclear.`, 'split')
    if (plan.escalation) return { status: 'escalated', escalation: plan.escalation, builds: [] }
    if (plan.briefs.some((b) => !parts.includes(b.part)) || plan.briefs.length !== parts.length) throw new Error('split part ids mismatch')
    await leadClaim.beforePush()
    const prepared = await this.backend.head(branch)
    if (!prepared || !await this.backend.ancestor(baseSha, prepared.sha)) throw new Error('split oracle/stubs not pushed from declared base')
    const oracle = filePath(plan.oracle)
    git(this.repo, 'cat-file', '-e', `${prepared.sha}:${oracle}`)
    for (const stub of plan.stubs || []) git(this.repo, 'cat-file', '-e', `${prepared.sha}:${filePath(stub)}`)
    for (const b of plan.briefs) {
      if (!b.brief || !b.test || !b.files.length) throw new Error('part needs brief, focused test and files')
      if (ownsFile(b.files.map(filePath), oracle)) throw new Error('worker may not edit the oracle')
    }
    leadClaim.lastPush = prepared.sha
    const workers = await this.batch(plan.briefs, async (b) => {
      const claim = this.child(leadClaim, `${branch}-${b.part}`, prepared.sha)
      const worktree = this.worktree(claim.claim.branch, claim.claim.resume_sha || prepared.sha)
      const { handle, value } = await this.run('worker', b.tier, `${this.pushBrief(claim, worktree)}\n${b.brief}\nEdit only ${b.files.join(', ')}. Do not edit oracle ${plan.oracle}. Focused test: ${b.test}. Report task ${b.part}, round 0. Stop and escalate if unclear.`, 'report')
      return { b, claim, handle, value: await this.report(value, b, claim, prepared.sha, 0) }
    })
    let builds = workers.map((w) => w.value)
    const stuck = () => builds.filter((r) => r.status === 'escalated')
    if (stuck().length) return { status: 'escalated', escalation: stuck().map((r) => r.escalation).join('\n'), builds }
    const integrate = async () => {
      const { value: merged } = await this.run('integrator', 'judgment', `${this.pushBrief(leadClaim, dir)}\nMerge only these verified branches and SHAs into ${branch}: ${JSON.stringify(builds)}. Run whole oracle ${test}. Push and return merge shape. Escalate if red.`, 'merge')
      await leadClaim.beforePush()
      const head = await this.backend.head(branch)
      if (merged.merged.length !== builds.length || new Set(merged.merged).size !== builds.length || merged.branch !== branch || head?.sha !== merged.sha || !await this.backend.ancestor(prepared.sha, merged.sha) || builds.some((b) => !merged.merged.includes(b.branch) || !ancestor(this.repo, b.sha, merged.sha))) throw new Error('merge branch/SHA/parents mismatch')
      leadClaim.lastPush = merged.sha
      return merged
    }
    let review, merged
    for (let round = 0; round <= limits.rework_rounds; round++) {
      merged = await integrate()
      if (!merged.oracle_passed || merged.escalation) return { ...merged, status: 'escalated', builds }
      review = await this.review({ results: builds.map((r) => ({ id: r.task, diff: `${prepared.sha}...${r.sha}`, test: r.test.command })), decisions: args.decisions })
      this.lastReview = review
      const heavy = review.findings.filter((f) => f.severity !== 'minor')
      if (!heavy.length) break
      if (round === limits.rework_rounds) return { status: 'escalated', escalation: '2 rework rounds exhausted', builds, review }
      this.rounds = round + 1
      await this.batch(workers.filter((w) => heavy.some((f) => f.ids.includes(w.b.part))), async (w) => {
        const nextRound = (w.value.round || 0) + 1
        const message = `Rework round ${nextRound}. Fix only these findings: ${JSON.stringify(heavy.filter((f) => f.ids.includes(w.b.part)))}. Keep the same branch, worktree, focused test and guard. Return report JSON.`
        this.active.add(w.handle)
        // One instruction: followup_task also triggers the turn, so send_message would double it.
        await this.host.followUp(w.handle, message)
        if (this.cancelled) { await this.host.interrupt(w.handle); throw new Error('adapter cancelled') }
        w.value = await this.report(validate('report', json(await this.host.wait(w.handle))), w.b, w.claim, prepared.sha, nextRound)
        this.active.delete(w.handle)
      })
      builds = workers.map((w) => w.value)
      if (stuck().length) return { status: 'escalated', escalation: stuck().map((r) => r.escalation).join('\n'), builds, review }
    }
    return { ...merged, status: merged.oracle_passed && !merged.escalation ? 'done' : 'escalated', builds, review }
  }
}
module.exports = { Adapter, CodexHost, ClaimSession, GitHubClaims, owner, parseComments, encodeClaim }
if (require.main === module) {
  const pending = new Map(); let seq = 0, started = false, closed = false
  const out = (v) => process.stdout.write(`${JSON.stringify(v)}\n`)
  const rpc = (tool, args) => new Promise((resolve, reject) => { if (closed) { reject(new Error('host input closed')); return } const id = ++seq; pending.set(id, { resolve, reject }); out({ id, tool, args }) })
  const lines = readline.createInterface({ input: process.stdin })
  lines.on('close', () => { closed = true; for (const p of pending.values()) p.reject(new Error('host input closed')); pending.clear() })
  lines.on('line', async (line) => {
    try {
      const input = JSON.parse(line)
      if (started) {
        const p = pending.get(input.id)
        if (!p) throw new Error('unknown response id')
        pending.delete(input.id); input.error ? p.reject(new Error(input.error)) : p.resolve(input.result)
        return
      }
      started = true
      const options = input.options || {}, args = input.args || {}
      let result
      if (['claim', 'push', 'release'].includes(input.method)) {
        const backend = new GitHubClaims(options)
        if (input.method === 'claim') {
          // args.needs is the capability list of the task; it is not part of the claim comment.
          const { needs, ...fields } = args
          result = await new ClaimSession(backend, { provider: options.runtime?.provider, ...fields }, { runtime: options.runtime, tasks: options.tasks || [{ id: fields.task, needs: needs || [] }] }).acquire()
        }
        else {
          const record = (await backend.comments()).find((c) => c.url === args.claim_url)
          if (!record || record.claim.state !== 'claimed') throw new Error('claim_url must identify a claimed comment')
          // A worker pushes its own branch under the lead's claim: the lead branch plus a suffix.
          const branch = args.branch || record.claim.branch
          if (branch !== record.claim.branch && !branch.startsWith(`${record.claim.branch}-`)) throw new Error('branch must be the claim branch or a child of it')
          const own = { ...record.claim, branch: name(branch) }
          if (branch !== record.claim.branch) { delete own.supersedes; delete own.resume_sha }
          const c = new ClaimSession(backend, own); c.record = record
          if (input.method === 'release') { await c.release(); result = { released: true } }
          else {
          c.adopted = true // the lead owns the claim comment; a push never posts or releases one
          const ref = `refs/agentic-sdlc/claims/${record.url.split('-').pop()}/${branch}`
          let prior = null
          try { prior = git(options.repo, 'show-ref', '--hash', ref) || null } catch {}
          if (prior && args.last_push_sha && prior !== args.last_push_sha) throw new Error('last_push_sha differs from saved last push')
          c.lastPush = prior || args.last_push_sha || null
          if (c.lastPush && !/^[0-9a-f]{40}$/.test(c.lastPush)) throw new Error('last_push_sha must be full SHA')
          result = { sha: await c.push(options.repo) }
          git(options.repo, 'update-ref', ref, result.sha)
          }
        }
      } else {
        const adapter = new Adapter({ ...options, host: new CodexHost(rpc, (target) => rpc('read_result', { target })) })
        if (input.method === 'split') result = await adapter.split(args)
        else if (input.method === 'review-batch') result = await adapter.reviewBatch(args)
        else throw new Error('unknown method')
      }
      out({ result }); lines.close()
    } catch (e) { out({ error: e.message }); process.exitCode = 1; lines.close() }
  })
}
