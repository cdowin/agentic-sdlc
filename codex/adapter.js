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
  constructor(backend, claim) { this.backend = backend; this.claim = claim; this.skipped = []; this.record = null; this.lastPush = null; this.stopped = false }
  async acquire() {
    const b = this.backend, comments = await b.comments(), previous = owner(comments, this.claim.task, this.skipped)
    const head = await b.head(this.claim.branch)
    if (previous) {
      if (previous.claim.branch !== this.claim.branch || previous.claim.base_sha !== this.claim.base_sha) throw new Error('owner branch/base mismatch')
      const now = b.now()
      if (head && !await b.ancestor(previous.claim.resume_sha || previous.claim.base_sha, head.sha)) throw new Error('remote branch force-pushed; stop and escalate')
      // No branch: the old lead died before its first push. Only the claim age decides, and the
      // new lead resumes from base_sha.
      if (now - Date.parse(previous.created_at) < staleMs || (head && now - head.time < staleMs)) throw new Error('task already claimed; not stale')
      this.claim = { ...this.claim, supersedes: previous.url, resume_sha: head ? head.sha : this.claim.base_sha }
      validate('claim', this.claim, { claims: comments, now })
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
    if (!this.record || this.released) return
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
    if (this.runtime.provider !== 'codex') throw new Error('Codex runtime required')
    this.repo = path.resolve(this.repo)
    this.concurrency = Math.min(this.concurrency || this.runtime.concurrency || 1, this.runtime.concurrency || Infinity)
    if (!Number.isInteger(this.concurrency) || this.concurrency < 1) throw new Error('positive concurrency required')
    if (!this.lead) throw new Error('stable lead id required')
    this.active = new Set(); this.claims = []; this.worktrees = []; this.sequence = 0; this.job = randomBytes(6).toString('hex'); this.cancelled = false
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
      return this.worktrees.length ? { ...result, worktrees: this.worktrees } : result
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
  cancel() { this.cancelled = true; return Promise.all([...this.active].map((a) => this.host.interrupt(a))) }
  async run(role, tier, message, def, opts = {}) {
    if (this.cancelled) throw new Error('adapter cancelled')
    const setting = this.runtime.tiers[tier]
    if (!setting?.model || !setting.effort) throw new Error(`explicit model/effort required for ${tier}`)
    if (!['none', 'minimal', 'low', 'medium', 'high'].includes(setting.effort)) throw new Error('effort exceeds high')
    const handle = await this.host.spawn({ role, model: setting.model, effort: setting.effort,
      message: `Role: ${role} (${this.runtime.agent_types[role]}). ${message}\nReturn only JSON matching this contract:\n${JSON.stringify(contract.$defs[def])}\nPR, CI and merge to main belong to the lead. Open no PR.\n${this.rules || ''}` })
    this.active.add(handle)
    if (this.cancelled) { await this.host.interrupt(handle); this.active.delete(handle); throw new Error('adapter cancelled') }
    const value = validate(def, json(await this.host.wait(handle)), opts)
    this.active.delete(handle)
    return { handle, value }
  }
  async claim(task, branch, base) {
    if (this.cancelled) throw new Error('adapter cancelled')
    if (!this.backend) throw new Error('split needs repository and numeric issue for claims')
    const c = new ClaimSession(this.backend, { task, lead: `${this.lead}:${this.job}:${++this.sequence}`, provider: 'codex', branch, base_sha: base,
      at: new Date(this.backend.now()).toISOString(), state: 'claimed' })
    this.claims.push(c)
    await c.acquire()
    if (this.cancelled) { await c.release(); throw new Error('adapter cancelled') }
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
    return `Work only in worktree ${dir}, branch ${c.claim.branch}. The claim is ${c.record.url}.\nCommit by path. Push after every commit through this guard; open no PR:\nnode ${path.join(__dirname, 'adapter.js')}\nIts first stdin JSON line: ${JSON.stringify({ method: 'push', options: { repo: dir, repository: this.repository, issue: this.issue }, args: { claim_url: c.record.url } })}\nAfter the first push, include args.last_push_sha from the prior guard result. A lost claim or rewritten branch means stop and escalate.\n`
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
  async split(args) { return this.finish(async () => {
    const { branch, base, test } = args, parts = (args.parts || []).map((p) => typeof p === 'string' ? p : p.name)
    name(branch); parts.forEach(name)
    if (!args.issue || !base || !test || parts.length < limits.split_parts_min || parts.length > limits.review_batch || new Set(parts).size !== parts.length) throw new Error('split needs issue, branch, base, test and unique parts')
    const baseSha = git(this.repo, 'rev-parse', `${base}^{commit}`)
    const leadClaim = await this.claim(String(args.issue), branch, baseSha)
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
      const claim = await this.claim(`${args.issue}/${b.part}`, `${branch}-${b.part}`, prepared.sha)
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
      const heavy = review.findings.filter((f) => f.severity !== 'minor')
      if (!heavy.length) break
      if (round === limits.rework_rounds) return { status: 'escalated', escalation: '2 rework rounds exhausted', builds, review }
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
  }) }
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
        if (input.method === 'claim') result = await new ClaimSession(backend, args).acquire()
        else {
          const record = (await backend.comments()).find((c) => c.url === args.claim_url)
          if (!record || record.claim.state !== 'claimed') throw new Error('claim_url must identify a claimed comment')
          const c = new ClaimSession(backend, record.claim); c.record = record
          if (input.method === 'release') { await c.release(); result = { released: true } }
          else {
          const ref = `refs/agentic-sdlc/claims/${record.url.split('-').pop()}`
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
