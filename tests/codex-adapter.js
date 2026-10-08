'use strict'
// Real scratch git remotes, fixture host only. Live host proof is separate from this suite.
const assert = require('assert/strict')
const fs = require('fs')
const os = require('os')
const path = require('path')
const { execFileSync, spawn } = require('child_process')
const { Adapter, CodexHost, ClaimSession, GitHubClaims, owner, parseComments, encodeClaim } = require('../codex/adapter.js')
const { check } = require('../plugin/contract/check.js')
const runtime = JSON.parse(JSON.stringify(require('../plugin/contract/runtimes.json').codex))
runtime.concurrency = 2
const git = (repo, ...args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sdlc-adapter-'))
let passed = 0
const now = Date.parse('2026-10-09T00:00:00Z')
const sha = 'a'.repeat(40)
const url = (i) => `https://github.com/example/kit/issues/1#issuecomment-${i}`
const claim = (lead, state = 'claimed', extra = {}) => ({ task: '1', lead, provider: 'codex', branch: 'task', base_sha: sha, at: '2026-10-08T00:00:00Z', state, ...extra })
const comment = (i, c, time = '2026-10-08T00:00:00Z') => ({ url: url(i), created_at: time, claim: c })
const test = async (label, fn) => { await fn(); passed++; console.log(`ok ${label}`) }
class MemoryClaims extends GitHubClaims {
  constructor(repo) { super({ repo, repository: 'example/kit', issue: 1, now: () => now }); this.records = []; this.id = 0; this.reads = 0; this.headReads = 0 }
  async comments() { this.reads++; return this.records }
  async post(c) { assert.deepEqual(check('claim', c, { now }), []); const r = comment(++this.id, JSON.parse(JSON.stringify(c)), new Date(now).toISOString()); this.records.push(r); return r }
  async head(branch) { this.headReads++; return super.head(branch) }
}
function scratch(label) {
  const repo = path.join(tmp, label), remote = `${repo}.git`
  execFileSync('git', ['init', '-q', '--bare', remote])
  execFileSync('git', ['init', '-q', repo])
  git(repo, 'config', 'user.name', 'fixture'); git(repo, 'config', 'user.email', 'fixture@example.invalid')
  fs.writeFileSync(path.join(repo, 'seed'), 'base\n'); git(repo, 'add', 'seed'); git(repo, 'commit', '-qm', 'base')
  git(repo, 'remote', 'add', 'origin', remote); git(repo, 'push', '-q', 'origin', 'HEAD:refs/heads/main')
  return { repo, remote, base: git(repo, 'rev-parse', 'HEAD'), backend: new MemoryClaims(repo) }
}
function session(s, extra = {}) {
  return new ClaimSession(s.backend, claim('lead', 'claimed', { base_sha: s.base, at: new Date(now).toISOString(), ...extra }))
}
function commit(repo, file, text) { fs.writeFileSync(path.join(repo, file), text); git(repo, 'add', file); git(repo, 'commit', '-qm', file); return git(repo, 'rev-parse', 'HEAD') }
async function suite() {
  await test('server order, tie ids, release, and superseded claims do not resurrect', () => {
    const a = comment(2, claim('a', 'claimed', { at: '2026-10-08T00:04:00Z' })), b = comment(1, claim('b'))
    assert.equal(owner([a, b], '1').url, b.url)
    const c = comment(3, claim('c', 'claimed', { supersedes: b.url, resume_sha: sha, at: new Date(now).toISOString() }), new Date(now).toISOString())
    const release = comment(4, claim('c', 'released', { at: new Date(now).toISOString() }), new Date(now).toISOString())
    assert.equal(owner([b, c, release], '1'), null)
    assert.equal(owner([a, b, c, release], '1').url, a.url)
    assert.equal(owner([a, b, { ...c, claim: { ...c.claim, supersedes: a.url } }], '1').url, b.url)
    const contender = comment(5, claim('loser', 'claimed', { supersedes: b.url, resume_sha: sha, at: new Date(now).toISOString() }), new Date(now).toISOString())
    assert.equal(owner([b, c, contender], '1').url, c.url)
    assert.equal(owner([b, c, contender, release], '1'), null)
    const skipped = []
    assert.equal(owner([b, { ...c, claim: { ...c.claim, branch: 'other' } }], '1', skipped).url, b.url)
    assert.match(skipped[0].reason, /branch\/base/); assert.equal(skipped[0].url, c.url)
  })
  await test('marked comment JSON fails closed; unmarked comments are data', () => {
    assert.deepEqual(parseComments([{ body: 'hello' }]), [])
    assert.throws(() => parseComments([{ body: 'agentic-sdlc:claim\nno json', html_url: url(1) }]), /malformed/)
    const c = claim('lead'); assert.equal(parseComments([{ body: encodeClaim(c), html_url: url(1), created_at: c.at }])[0].claim.lead, 'lead')
  })
  await test('a malformed historical claim is skipped and reported, not thrown for every reader', async () => {
    const good = comment(1, claim('good')), skipped = []
    const noShape = { url: url(2), created_at: '2026-10-08T00:01:00Z', claim: { task: '1' } }
    const badUrl = { url: 'not-a-url', created_at: '2026-10-08T00:02:00Z', claim: claim('x') }
    const orphan = comment(4, claim('orphan', 'claimed', { supersedes: url(77), resume_sha: sha }), '2026-10-08T00:03:00Z')
    assert.equal(owner([noShape, badUrl, orphan, good], '1', skipped).url, good.url)
    assert.equal(skipped.length, 3)
    assert.equal(owner([noShape], '1'), null)
    const bodies = [{ body: 'agentic-sdlc:claim\nno json', html_url: url(5) }, { body: encodeClaim(claim('lead')), html_url: url(6), created_at: '2026-10-08T00:00:00Z' }]
    const list = []
    assert.equal(parseComments(bodies, list).length, 1); assert.match(list[0].reason, /malformed/); assert.equal(list[0].url, url(5))
  })
  await test('fresh duplicate loses; every guard re-reads comments and remote', async () => {
    const s = scratch('duplicate'), a = session(s); await a.acquire()
    await assert.rejects(session(s, { lead: 'second' }).acquire(), /not stale/)
    const before = s.backend.reads; await a.beforePush(); assert.ok(s.backend.reads > before)
    assert.ok(s.backend.headReads >= 3)
    const c = comment(99, claim('winner', 'claimed', { base_sha: s.base, at: new Date(now + 3 * 3600000).toISOString(), supersedes: a.record.url, resume_sha: s.base }), new Date(now + 3 * 3600000).toISOString())
    s.backend.records.push(c)
    await assert.rejects(a.beforePush(), /lost/)
    assert.equal(a.released, true)
  })
  await test('stale takeover starts at remote head; fresh branch commit blocks takeover', async () => {
    const s = scratch('stale'); git(s.repo, 'push', '-q', 'origin', 'HEAD:refs/heads/task')
    s.backend.records.push(comment(1, claim('old', 'claimed', { base_sha: s.base }))); s.backend.id = 1
    const real = s.backend.head.bind(s.backend); s.backend.head = async (b) => ({ ...await real(b), time: now - 1000 })
    await assert.rejects(session(s).acquire(), /not stale/)
    s.backend.head = async (b) => ({ ...await real(b), time: now - 3 * 3600000 })
    const c = session(s); await c.acquire(); assert.equal(c.claim.resume_sha, s.base); assert.equal(c.claim.supersedes, url(1))
  })
  await test('stale claim with no branch is taken over from base_sha; a fresh one is not', async () => {
    const s = scratch('nobranch')
    s.backend.records.push(comment(1, claim('old', 'claimed', { base_sha: s.base }), '2026-10-08T23:00:00Z')); s.backend.id = 1
    await assert.rejects(session(s).acquire(), /not stale/)
    s.backend.records[0].created_at = '2026-10-08T00:00:00Z'
    const c = session(s); await c.acquire()
    assert.equal(c.claim.resume_sha, s.base); assert.equal(c.claim.supersedes, url(1))
    commit(s.repo, 'first', 'first'); await c.push(s.repo)
    assert.equal(c.lastPush, git(s.repo, 'rev-parse', 'HEAD'))
  })
  await test('force push and branch deletion stop after own push', async () => {
    const s = scratch('force'), c = session(s); await c.acquire()
    commit(s.repo, 'change', 'one'); await c.push(s.repo)
    git(s.repo, 'push', '-q', '--force', 'origin', `${s.base}:refs/heads/task`)
    await assert.rejects(c.beforePush(), /force-pushed/)
    const t = scratch('delete'), d = session(t); await d.acquire(); await d.push(t.repo)
    git(t.repo, 'push', '-q', 'origin', '--delete', 'task')
    await assert.rejects(d.beforePush(), /deleted/)
  })
  await test('GitHub comment read failure never permits a push', async () => {
    const s = scratch('network'), c = session(s); await c.acquire()
    s.backend.comments = async () => { throw new Error('network unavailable') }
    await assert.rejects(c.push(s.repo), /network unavailable/)
    assert.equal(await s.backend.head('task'), null)
  })
  await test('Codex boundary uses native task_name, wait wakeups, message, followup, interrupt', async () => {
    const calls = []; let reads = 0
    const host = new CodexHost(async (tool, args) => { calls.push({ tool, args }); return { task_name: '/root/fixture' } }, async () => ++reads === 1 ? { status: 'running' } : { status: 'completed', output: { ok: true } })
    const h = await host.spawn({ role: 'worker', model: 'model', effort: 'low', message: 'brief' })
    assert.equal(h, '/root/fixture'); assert.deepEqual(await host.wait(h), { ok: true })
    await host.message(h, 'finding'); await host.followUp(h, 'rework'); await host.interrupt(h)
    assert.deepEqual(calls.map((r) => r.tool), ['spawn_agent', 'wait_agent', 'send_message', 'followup_task', 'interrupt_agent'])
    assert.deepEqual(Object.keys(calls[0].args).sort(), ['fork_turns', 'message', 'model', 'reasoning_effort', 'task_name'].sort())
    const other = new CodexHost(host.call, host.readResult)
    await other.spawn({ role: 'worker', model: 'model', effort: 'low', message: 'brief' })
    assert.notEqual(calls[0].args.task_name, calls.at(-1).args.task_name)
  })
  await test('batched review validates scores and both skeptic verdicts; strips authors', async () => {
    const s = scratch('review'), prompts = [], outputs = [{ scores: [{ id: 'a', correctness: 4, code_rules: 4, tests: 4, scope: 4 }], findings: [{ id: 'f', ids: ['a'], severity: 'major', claim: 'defect', evidence: 'file:1', cross_issue: false }] }, { agree: true, reason: 'reproduced' }, { agree: false, reason: 'disproved' }]
    const host = { spawn: async (p) => { prompts.push(p.message); return String(prompts.length) }, wait: async () => outputs.shift(), interrupt: async () => {} }
    const a = new Adapter({ host, runtime, repo: s.repo, backend: s.backend, lead: 'lead' })
    const r = await a.reviewBatch({ results: [{ id: 'a', diff: 'patch', test: 'test', author: 'hidden' }] })
    assert.equal(r.findings.length, 0); assert.equal(r.dropped.length, 1); assert.ok(prompts.every((p) => !p.includes('hidden')))
    const invalid = new Adapter({ host: { ...host, wait: async () => ({ scores: [], findings: [] }) }, runtime, repo: s.repo, backend: s.backend, lead: 'lead' })
    await assert.rejects(invalid.reviewBatch({ results: [{ id: 'a', diff: 'patch', test: 'test' }] }), /not scored/)
  })
  await test('inflight late spawn is interrupted when sibling fails', async () => {
    const s = scratch('race'), interrupted = []; let release
    const late = new Promise((r) => { release = r })
    const host = { spawn: async (p) => { if (p.message.includes('slow')) { await late; return 'slow' } return 'bad' }, wait: async () => { release(); return {} }, interrupt: async (h) => interrupted.push(h) }
    const a = new Adapter({ host, runtime, repo: s.repo, backend: s.backend, lead: 'lead', concurrency: 2 })
    await assert.rejects(a.finish(() => a.batch(['bad', 'slow'], (p) => a.run('worker', 'judgment', p, 'report'))), /report|cancelled/)
    assert.ok(interrupted.includes('slow')); assert.ok(interrupted.includes('bad')); assert.equal(a.active.size, 0)
  })

  await test('GitHub pagination flags and CLI push persist last SHA across processes', async () => {
    const s = scratch('cli'), bin = path.join(tmp, 'bin'), state = path.join(tmp, 'comments.json'), log = path.join(tmp, 'gh.log')
    fs.mkdirSync(bin)
    fs.writeFileSync(state, '[]')
    const fake = "#!/usr/bin/env node\nconst fs=require('fs');const a=process.argv.slice(2);fs.appendFileSync(process.env.CLAIM_LOG,JSON.stringify(a)+'\\n');let c=JSON.parse(fs.readFileSync(process.env.CLAIM_STATE));if(a.includes('POST')){const input=JSON.parse(fs.readFileSync(0,'utf8'));const r={body:input.body,html_url:'https://github.com/example/kit/issues/1#issuecomment-'+(c.length+1),created_at:new Date().toISOString()};c.push(r);fs.writeFileSync(process.env.CLAIM_STATE,JSON.stringify(c));process.stdout.write(JSON.stringify(r))}else{if(!a.includes('--paginate')||!a.includes('--slurp'))process.exit(2);process.stdout.write(JSON.stringify(c.map(x=>[x])))}\n"
    fs.writeFileSync(path.join(bin, 'gh'), fake, { mode: 0o755 })
    const env = { ...process.env, PATH: bin + path.delimiter + process.env.PATH, CLAIM_STATE: state, CLAIM_LOG: log }
    const options = { repo: s.repo, repository: 'example/kit', issue: 1 }
    const cli = (method, args) => JSON.parse(execFileSync(process.execPath, [path.join(__dirname, '../codex/adapter.js')], { env, input: JSON.stringify({ method, options, args }) + '\n', encoding: 'utf8' }).trim())
    const r = cli('claim', claim('cli', 'claimed', { base_sha: s.base, at: new Date().toISOString() })).result
    assert.equal(r.claim.base_sha, s.base)
    commit(s.repo, 'first', 'first'); const first = cli('push', { claim_url: r.url }).result.sha
    commit(s.repo, 'second', 'second'); const second = cli('push', { claim_url: r.url }).result.sha
    assert.notEqual(first, second)
    git(s.repo, 'push', '-q', '--force', 'origin', first + ':refs/heads/task')
    let failure
    try { cli('push', { claim_url: r.url }) } catch (e) { failure = JSON.parse(e.stdout.toString()).error }
    assert.match(failure, /force-pushed/)
    assert.equal(cli('release', { claim_url: r.url }).result.released, true)
    assert.equal(parseComments(JSON.parse(fs.readFileSync(state, 'utf8'))).at(-1).claim.state, 'released')
    const reads = fs.readFileSync(log, 'utf8').trim().split('\n').map(JSON.parse)
    assert.ok(reads.filter((a) => a.includes('--paginate')).length >= 7)
  })
  await test('normal Git push race fails without force', async () => {
    const s = scratch('push-race'), c = session(s); await c.acquire(); await c.push(s.repo)
    const rival = path.join(tmp, 'rival'); execFileSync('git', ['clone', '-q', '--branch', 'task', s.remote, rival])
    git(rival, 'config', 'user.name', 'fixture'); git(rival, 'config', 'user.email', 'fixture@example.invalid')
    commit(s.repo, 'local', 'local')
    const realPush = s.backend.push.bind(s.backend)
    s.backend.push = async (repo, branch) => { commit(rival, 'rival', 'rival'); git(rival, 'push', '-q', 'origin', 'HEAD:refs/heads/task'); return realPush(repo, branch) }
    await assert.rejects(c.push(s.repo), /rejected|failed to push/)
    assert.equal((await s.backend.head('task')).sha, git(rival, 'rev-parse', 'HEAD'))
  })
  await test('executable JSONL rejects malformed worker output and interrupts before exit', async () => {
    const s = scratch('bridge'), operations = [], frames = []
    const proc = spawn(process.execPath, [path.join(__dirname, '../codex/adapter.js')], { stdio: ['pipe', 'pipe', 'pipe'] })
    let buffered = '', stderr = ''
    proc.stderr.on('data', (d) => { stderr += d })
    proc.stdout.on('data', (d) => {
      buffered += d
      while (buffered.includes('\n')) {
        const at = buffered.indexOf('\n'), frame = JSON.parse(buffered.slice(0, at)); buffered = buffered.slice(at + 1); frames.push(frame)
        if (!frame.tool) continue
        operations.push(frame.tool)
        const result = frame.tool === 'spawn_agent' ? { task_name: '/root/bridge' } : frame.tool === 'read_result' ? { status: 'completed', output: '{}' } : {}
        proc.stdin.write(JSON.stringify({ id: frame.id, result }) + '\n')
      }
    })
    proc.stdin.write(JSON.stringify({ method: 'review-batch', options: { repo: s.repo, repository: 'example/kit', issue: 1, lead: 'bridge', runtime }, args: { results: [{ id: 'a', diff: 'diff', test: 'test' }] } }) + '\n')
    const code = await new Promise((resolve) => proc.on('exit', resolve)); proc.stdin.end()
    assert.equal(code, 1, stderr); assert.match(frames.at(-1).error, /review:/)
    assert.deepEqual(operations, ['spawn_agent', 'read_result', 'interrupt_agent'])
  })
  await test('executable EOF during worker read exits and interrupt failure still releases claims', async () => {
    const s = scratch('eof'), frames = []
    const proc = spawn(process.execPath, [path.join(__dirname, '../codex/adapter.js')], { stdio: ['pipe', 'pipe', 'pipe'] })
    let buffered = ''
    proc.stdout.on('data', (d) => {
      buffered += d
      while (buffered.includes('\n')) {
        const at = buffered.indexOf('\n'), frame = JSON.parse(buffered.slice(0, at)); buffered = buffered.slice(at + 1); frames.push(frame)
        if (frame.tool === 'spawn_agent') proc.stdin.write(JSON.stringify({ id: frame.id, result: { task_name: '/root/eof' } }) + '\n')
        if (frame.tool === 'read_result') proc.stdin.end()
      }
    })
    proc.stdin.write(JSON.stringify({ method: 'review-batch', options: { repo: s.repo, lead: 'eof', runtime }, args: { results: [{ id: 'a', diff: 'diff', test: 'test' }] } }) + '\n')
    const timeout = setTimeout(() => proc.kill(), 5000)
    const code = await new Promise((resolve) => proc.on('exit', resolve)); clearTimeout(timeout)
    assert.equal(code, 1); assert.match(frames.at(-1).error, /host input closed/)
    const c = session(s); await c.acquire()
    const a = new Adapter({ host: { interrupt: async () => { throw new Error('interrupt unavailable') } }, runtime, repo: s.repo, backend: s.backend, lead: 'eof' })
    a.claims.push(c); a.active.add('failed-worker')
    await assert.rejects(a.finish(async () => { throw new Error('bad report') }), /cleanup failed/)
    assert.equal(c.released, true)
  })
  for (const mode of ['success', 'wrong-task', 'wrong-sha', 'rework', 'exhaust', 'cancel-rework']) await test(`split real git ${mode}`, async () => {
    const s = scratch(mode), outputs = new Map(), workers = new Map(), events = []; let count = 0, reviews = 0, releaseRework
    const host = {
      spawn: async (p) => {
        const h = String(++count); events.push(p.role)
        const worktree = p.message.match(/Work only in worktree ([^,]+), branch ([^.]+)\./)
        const dir = worktree?.[1], branch = worktree?.[2]
        if (p.role === 'sub_lead') {
          commit(dir, 'oracle', 'oracle'); git(dir, 'push', '-q', 'origin', `HEAD:refs/heads/${branch}`)
          outputs.set(h, { oracle: 'oracle', escalation: '', briefs: ['a', 'b'].map((part) => ({ part, files: [part], brief: `write ${part}`, tier: 'judgment', test: `test-${part}` })) })
        } else if (p.role === 'worker') {
          const part = branch.endsWith('-a') ? 'a' : 'b'; commit(dir, part, `${part}0`); git(dir, 'push', '-q', 'origin', `HEAD:refs/heads/${branch}`)
          const r = { task: part, branch, sha: git(dir, 'rev-parse', 'HEAD'), status: 'done', round: 0, test: { command: `test-${part}`, line: 'pass', passed: true } }
          workers.set(h, { dir, part, r }); outputs.set(h, mode === 'wrong-task' ? { ...r, task: 'wrong' } : mode === 'wrong-sha' ? { ...r, sha: s.base } : r)
        } else if (p.role === 'integrator') {
          const reports = [...workers.values()].map((w) => w.r)
          for (const r of reports) { git(dir, 'fetch', '-q', 'origin', `refs/heads/${r.branch}`); git(dir, 'merge', '--no-edit', 'FETCH_HEAD') }
          git(dir, 'push', '-q', 'origin', `HEAD:refs/heads/${branch}`)
          outputs.set(h, { branch, sha: git(dir, 'rev-parse', 'HEAD'), merged: reports.map((r) => r.branch), oracle_passed: true, reworked: [] })
        } else if (p.role === 'reviewer') {
          reviews++; const finding = mode === 'cancel-rework' || mode === 'exhaust' || mode === 'rework' && reviews === 1
          outputs.set(h, { scores: ['a', 'b'].map((id) => ({ id, correctness: 4, code_rules: 4, tests: 4, scope: 4 })), findings: finding ? [{ id: 'f', ids: mode === 'cancel-rework' ? ['a', 'b'] : ['a'], severity: 'major', claim: 'fix a', evidence: 'a:1', cross_issue: mode === 'cancel-rework' }] : [] })
        } else outputs.set(h, { agree: true, reason: 'reproduced' })
        return h
      },
      wait: async (h) => outputs.get(h), message: async (h) => { events.push(`message:${h}`) },
      followUp: async (h) => { if (mode === 'cancel-rework') { if (workers.get(h).part === 'a') await new Promise((r) => { releaseRework = r }); else throw new Error('follow-up failed'); return } const w = workers.get(h); w.r = { ...w.r, round: w.r.round + 1 }; commit(w.dir, w.part, `${w.part}${w.r.round}`); git(w.dir, 'push', '-q', 'origin', `HEAD:refs/heads/${w.r.branch}`); w.r.sha = git(w.dir, 'rev-parse', 'HEAD'); outputs.set(h, w.r); events.push(`follow:${h}`) },
      interrupt: async (h) => { events.push(`interrupt:${h}`); if (releaseRework) releaseRework() },
    }
    const a = new Adapter({ host, runtime, repo: s.repo, repository: 'example/kit', issue: 1, backend: s.backend, lead: 'lead', concurrency: 2 })
    const run = () => a.split({ issue: 1, branch: 'task', base: s.base, parts: ['a', 'b'], test: 'whole-test' })
    if (mode.startsWith('wrong')) await assert.rejects(run(), /mismatch/)
    else if (mode === 'cancel-rework') { await assert.rejects(run(), /cancelled|follow-up failed/); assert.equal(events.filter((e) => e.startsWith('follow:')).length, 0) }
    else {
      const r = await run(); assert.equal(r.status, mode === 'exhaust' ? 'escalated' : 'done')
      assert.ok(events.indexOf('integrator') < events.indexOf('reviewer'))
      if (mode === 'exhaust') assert.equal(r.worktrees.length, 3)
      else assert.equal(git(s.repo, 'worktree', 'list', '--porcelain').split('worktree ').length - 1, 1)
      assert.equal(events.filter((e) => e.startsWith('follow:')).length, mode === 'rework' ? 1 : mode === 'exhaust' ? 2 : 0)
      assert.equal(events.filter((e) => e === 'worker').length, 2)
      assert.equal(events.filter((e) => e.startsWith('message:')).length, 0, 'rework is sent once, by follow-up only')
    }
    assert.equal(a.active.size, 0)
    for (const c of a.claims) assert.ok(c.released)
  })
}
suite().then(() => console.log(`${passed} adapter tests passed`)).catch((e) => { console.error(e); process.exitCode = 1 }).finally(() => fs.rmSync(tmp, { recursive: true, force: true }))
