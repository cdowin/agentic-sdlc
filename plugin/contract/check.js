#!/usr/bin/env node
// check.js - validate 1 value of the SDLC contract: its shape (sdlc.schema.json), then its meaning.
// Node 18 or later, no packages. Any lead (Claude, Codex or other) runs it on a worker's output
// before it accepts the output.
//
// usage: node check.js <def> <file.json | -> [options]
//   <def>            a key of $defs in sdlc.schema.json: graph, report, merge, review, claim, ...
//   --repo <dir>     check each SHA against the remote branch head (git fetch in <dir>; needs git).
//                    For a claim that takes over, also the last commit time of the branch.
//   --graph <file>   the graph of the task: its rework_limit bounds report and transition rounds
//   --ids <a,b,...>  the result ids of a review batch: each must be scored, and no other
//   --runtime <file> the runtime profile of the agent that claims: a claim of a graph task (see
//                    --graph) is refused when the runtime lacks a capability in the task's needs
//   --claims <file>  the claim comments of the issue (claim_comment shapes): a takeover needs a
//                    stale claim
//   --now <time>     the time to judge against (default: the clock); for tests
// Exit 0: valid; a runtime lists its unverified entries. Exit 1: invalid, 1 line per problem
// on stdout. Exit 2: usage.
'use strict'
const fs = require('fs')
const path = require('path')
const { execFileSync } = require('child_process')

const contract = JSON.parse(fs.readFileSync(path.join(__dirname, 'sdlc.schema.json'), 'utf8'))
// A workflow cannot import. `node tests/workflows.js --write` copies the shared blocks of this file
// into each workflow, after the x- keys of the contract; tests/workflows.js fails when a copy drifts.
// Shared code reads only `contract` and uses no require.
// ---- shared: begin
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
// ---- shared: end
const ROLES = Object.keys(ROLE_TIER)
const OPTIONAL_CAPABILITIES = contract['x-optional-capabilities'] || []
const MINUTE_MS = 60 * 1000
const STALE_MS = LIMITS.stale_claim_minutes * MINUTE_MS
const SKEW_MS = LIMITS.clock_skew_minutes * MINUTE_MS
const TIE = 'tie'

// shape(schema, value, at) -> problems. The subset of JSON Schema that sdlc.schema.json uses.
function typeOf(v) {
  if (v === null) return 'null'
  if (Array.isArray(v)) return 'array'
  if (Number.isInteger(v)) return 'integer'
  return typeof v
}
function typeOk(want, v) {
  const got = typeOf(v)
  return [].concat(want).some((t) => t === got || (t === 'number' && got === 'integer'))
}
function shape(s, v, at = '$') {
  if (s.$ref) return shape(contract.$defs[s.$ref.replace('#/$defs/', '')], v, at)
  if (s.anyOf) {
    return s.anyOf.some((alt) => shape(alt, v, at).length === 0) ? [] : [`${at}: matches no allowed form`]
  }
  if (s.type && !typeOk(s.type, v)) return [`${at}: want ${[].concat(s.type).join(' or ')}, got ${typeOf(v)}`]
  const out = []
  if ('const' in s && v !== s.const) out.push(`${at}: want ${JSON.stringify(s.const)}`)
  if (s.enum && !s.enum.includes(v)) out.push(`${at}: ${JSON.stringify(v)} is not one of ${s.enum.join(', ')}`)
  if (typeof v === 'string') {
    if (s.minLength && v.length < s.minLength) out.push(`${at}: empty`)
    if (s.pattern && !new RegExp(s.pattern).test(v)) out.push(`${at}: ${JSON.stringify(v)} does not match ${s.pattern}`)
  }
  if (typeof v === 'number') {
    if ('minimum' in s && v < s.minimum) out.push(`${at}: ${v} is below ${s.minimum}`)
    if ('maximum' in s && v > s.maximum) out.push(`${at}: ${v} is above ${s.maximum}`)
  }
  if (Array.isArray(v)) {
    if (s.minItems && v.length < s.minItems) out.push(`${at}: fewer than ${s.minItems} items`)
    if (s.items) v.forEach((x, i) => out.push(...shape(s.items, x, `${at}[${i}]`)))
  }
  if (typeOf(v) === 'object') {
    for (const k of s.required || []) if (!(k in v)) out.push(`${at}.${k}: missing`)
    for (const [k, sub] of Object.entries(s.properties || {})) if (k in v) out.push(...shape(sub, v[k], `${at}.${k}`))
  }
  return out
}

// meaning[def](value, opts) -> problems. The rules a JSON shape cannot say.
// The graph checks. The plan and wave workflows run them too.
// ---- shared meaning: begin
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
// ---- shared meaning: end

// chainMeaning: the graph checks, where 2 tasks in 2 chains may edit the same file: they build on 2
// branches, and the converge step of wave merges them. A chain task waits only on tasks of its chain,
// and a chain branch is no task branch. plugin/workflows/wave.js holds the same function.
function chainMeaning(g) {
  const chain = Object.fromEntries(g.tasks.map((t) => [t.id, t.chain || '']))
  const apart = g.tasks.flatMap((a, i) => g.tasks.slice(i + 1).filter((b) => chain[a.id] !== chain[b.id]).map((b) => `tasks ${a.id} and ${b.id} run in parallel and both edit `))
  const out = graphMeaning(g).filter((p) => !apart.some((x) => p.startsWith(x)))
  const branches = g.tasks.map((t) => t.branch || `${g.branch}-${t.id}`)
  for (const t of g.tasks.filter((x) => x.chain)) {
    for (const b of t.blockers) if (b in chain && chain[b] !== t.chain) out.push(`task ${t.id}: chain ${t.chain} waits on ${b}, which is not in it`)
    if (branches.includes(`${g.branch}-${t.chain}`)) out.push(`chain ${t.chain}: its branch ${g.branch}-${t.chain} is a task branch`)
  }
  return [...new Set(out)]
}

function reportMeaning(r, opts) {
  const out = []
  if (r.status === 'done' && !r.test.passed) out.push('status done, but the focused test did not pass')
  if (r.status === 'done' && r.escalation) out.push('status done, but escalation is set')
  if (r.status === 'escalated' && !r.escalation) out.push('status escalated needs the question in escalation')
  if ((r.round || 0) > opts.limit) out.push(`round ${r.round} is over the rework limit ${opts.limit}`)
  if (opts.repo) out.push(...atHead(opts.repo, r.branch, r.sha))
  return out
}

function mergeMeaning(m, opts) {
  const out = []
  if (!m.oracle_passed && !m.escalation) out.push('oracle_passed is false, but escalation is empty')
  if (m.oracle_passed && m.merged.length === 0) out.push('oracle_passed is true, but nothing was merged')
  if (opts.repo) out.push(...atHead(opts.repo, m.branch, m.sha))
  return out
}

function splitMeaning(p) {
  const out = []
  if (p.escalation) {
    if (p.briefs.length > 0) out.push('escalation is set, so briefs must be empty')
    return out
  }
  if (p.briefs.length < LIMITS.split_parts_min) out.push(`fewer than ${LIMITS.split_parts_min} parts`)
  for (const d of new Set(dupes(p.briefs.map((b) => b.part)))) out.push(`part ${d} is not unique`)
  for (let i = 0; i < p.briefs.length; i++) {
    for (let j = i + 1; j < p.briefs.length; j++) {
      const both = overlap(p.briefs[i].files, p.briefs[j].files)
      if (both.length > 0) out.push(`parts ${p.briefs[i].part} and ${p.briefs[j].part} both edit ${both.join(', ')}`)
    }
  }
  return out
}

function reviewMeaning(rv, opts) {
  const out = []
  const ids = rv.scores.map((s) => s.id)
  for (const d of new Set(dupes(ids))) out.push(`scores: ${d} is scored 2 times`)
  if (opts.ids) {
    for (const id of opts.ids) if (!ids.includes(id)) out.push(`scores: result ${id} is not scored`)
    for (const id of ids) if (!opts.ids.includes(id)) out.push(`scores: ${id} is not a result of the batch`)
  }
  const known = (id, at) => (ids.includes(id) ? [] : [`${at}: ${id} is not a scored result`])
  for (const p of rv.pairs || []) {
    out.push(...known(p.a, 'pairs'), ...known(p.b, 'pairs'))
    if (p.a === p.b) out.push(`pairs: ${p.a} is paired with itself`)
    if (![p.a, p.b, TIE].includes(p.better)) out.push(`pairs: better is ${p.better}, not ${p.a}, ${p.b} or ${TIE}`)
  }
  for (const d of new Set(dupes(rv.findings.map((f) => f.id)))) out.push(`findings: id ${d} is not unique`)
  for (const f of rv.findings) {
    if (f.ids.length === 0) out.push(`finding ${f.id}: names no result`)
    f.ids.forEach((id) => out.push(...known(id, `finding ${f.id}`)))
    if (f.cross_issue !== f.ids.length >= 2) out.push(`finding ${f.id}: cross_issue must be true exactly when it names 2 or more results`)
  }
  return out
}

function claimMeaning(c, opts) {
  const out = []
  if (opts.runtime && !opts.tasks) out.push('--runtime needs --graph: the task\'s needs come from the graph')
  if (opts.runtime && opts.tasks) {
    const task = opts.tasks.find((t) => t.id === c.task)
    if (!task) out.push(`task ${c.task} is not in the graph`)
    for (const n of task ? task.needs || [] : []) {
      if (!hasCapability(opts.runtime, n)) out.push(`task ${c.task} needs ${n}, but runtime ${opts.runtime.provider} does not have it`)
    }
  }
  const at = Date.parse(c.at)
  if (Number.isNaN(at)) out.push(`at: ${c.at} is not a time`)
  else if (at > opts.now + SKEW_MS) out.push(`at: ${c.at} is in the future`)
  if (!c.supersedes) return out
  if (c.state !== 'claimed') out.push('a claim that supersedes another must have state claimed')
  if (!c.resume_sha) out.push('a claim that supersedes another needs resume_sha, the remote branch head')
  let head = null
  if (opts.repo) {
    head = remoteHead(opts.repo, c.branch)
    // A lead that died before its first push left no branch. The new lead resumes from base_sha.
    if (!head) {
      if (c.resume_sha && c.resume_sha !== c.base_sha) out.push(`branch ${c.branch} is not on the remote, so resume_sha must be base_sha`)
    } else if (c.resume_sha && head.sha !== c.resume_sha) out.push(`resume_sha is not the head ${head.sha} of ${c.branch}`)
    else if (opts.now - head.time < STALE_MS) out.push(`the claim is not stale: ${c.branch} has a commit from ${new Date(head.time).toISOString()}`)
  }
  if (opts.claims) {
    const old = opts.claims.find((x) => x.url === c.supersedes)
    if (!old) out.push(`supersedes ${c.supersedes}, which is not a claim comment of the issue`)
    else {
      if (old.claim.task !== c.task) out.push(`supersedes a claim of task ${old.claim.task}, not ${c.task}`)
      if (opts.now - Date.parse(old.created_at) < STALE_MS) out.push(`the claim ${c.supersedes} is not stale: created_at ${old.created_at}`)
    }
  }
  return out
}

function transitionMeaning(t, opts) {
  const out = []
  if (!(TRANSITIONS[t.from] || []).includes(t.to)) out.push(`${t.from} -> ${t.to} is not an allowed transition`)
  if (t.to === 'rework') {
    if (!t.round) out.push('a change to rework needs round')
    else if (t.round > opts.limit) out.push(`round ${t.round} is over the rework limit ${opts.limit}; escalate`)
  }
  return out
}

function runtimeMeaning(r) {
  const out = []
  for (const k of Object.keys(r)) if (!(k in contract.$defs.runtime.properties)) out.push(`${k}: not a runtime field; put a fact in an evidence string`)
  for (const role of ROLES) if (typeof r.agent_types[role] !== 'string') out.push(`agent_types.${role}: missing`)
  for (const name of CAPABILITIES) {
    if (!(name in r.capabilities)) {
      if (!OPTIONAL_CAPABILITIES.includes(name)) out.push(`capabilities.${name}: missing`)
    } else out.push(...shape({ $ref: '#/$defs/capability' }, r.capabilities[name], `$.capabilities.${name}`))
  }
  for (const name of Object.keys(r.capabilities)) if (!CAPABILITIES.includes(name)) out.push(`capabilities.${name}: not in x-capabilities`)
  for (const t of Object.keys(r.tiers)) if (!TIERS.includes(t)) out.push(`tiers.${t}: not a tier`)
  return out
}

// blastMeaning: proven needs a run (level 4 or 5) and the proof that shows it.
function blastMeaning(b) {
  const out = []
  if (b.proven && b.level < 4) out.push(`proven is true, but level ${b.level} is below 4`)
  if (b.proven && !b.proof.trim()) out.push('proven is true, but proof is empty')
  return out
}

// unverified: the entries of a valid runtime profile that are guesses.
function unverified(r) {
  return [
    ...Object.entries(r.tiers).filter(([, s]) => !s.verified).map(([t, s]) => `tiers.${t}: ${s.model}${s.effort ? ` ${s.effort}` : ''}: ${s.evidence}`),
    ...Object.entries(r.capabilities).filter(([, c]) => c.status === 'unverified').map(([n, c]) => `capabilities.${n}: ${c.evidence}`),
  ]
}

const meaning = {
  graph: chainMeaning,
  brief: (b) => tierMeaning('brief', b),
  critique: (c) => (c.complete === (c.missing.length === 0) ? [] : [c.complete ? 'complete is true, but missing is not empty' : 'complete is false, but missing is empty']),
  split: splitMeaning,
  report: reportMeaning,
  merge: mergeMeaning,
  review: reviewMeaning,
  claim: claimMeaning,
  transition: transitionMeaning,
  runtime: runtimeMeaning,
  spec: (s) => specMeaning(s),
  blast: blastMeaning,
}

// remoteHead: the SHA and commit time of the remote branch head, or null when it has none.
function remoteHead(repo, branch) {
  const git = (...a) => execFileSync('git', ['-C', repo, ...a], { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()
  try {
    git('fetch', '-q', 'origin', `refs/heads/${branch}`)
    const [sha, time] = git('log', '-1', '--format=%H %cI', 'FETCH_HEAD').split(' ')
    return { sha, time: Date.parse(time) }
  } catch {
    return null
  }
}

// atHead: the SHA is the head of the remote branch, not an older commit on it.
function atHead(repo, branch, sha) {
  const head = remoteHead(repo, branch)
  if (!head) return [`branch ${branch} is not on the remote`]
  return head.sha === sha ? [] : [`${sha} is not the head ${head.sha} of the remote branch ${branch}`]
}

function check(def, value, opts = {}) {
  const schema = contract.$defs[def]
  if (!schema) throw new Error(`no contract shape named ${def}`)
  const o = { limit: LIMITS.rework_rounds, now: Date.now(), ...opts }
  const out = shape(schema, value)
  if (out.length > 0 || !meaning[def]) return out
  return meaning[def](value, o)
}

module.exports = { contract, check, unverified, higherTier }

if (require.main === module) {
  const argv = process.argv.slice(2)
  const opt = (name) => {
    const i = argv.indexOf(name)
    return i < 0 ? undefined : argv.splice(i, 2)[1]
  }
  const usage = (why) => {
    process.stderr.write(`${why}\nusage: node check.js <${Object.keys(contract.$defs).join('|')}> <file.json|-> [--repo <dir>] [--graph <file>] [--ids <a,b>] [--runtime <file>] [--claims <file>] [--now <time>]\n`)
    process.exit(2)
  }
  const readJson = (file) => JSON.parse(fs.readFileSync(file === '-' ? 0 : file, 'utf8'))
  const opts = { repo: opt('--repo') }
  const graph = opt('--graph')
  const ids = opt('--ids')
  const claims = opt('--claims')
  const runtime = opt('--runtime')
  const now = opt('--now')
  const [def, file] = argv
  if (!def || !file || !contract.$defs[def]) usage('need a contract shape and a file')
  try {
    if (graph) {
      const g = readJson(graph)
      const bad = check('graph', g)
      if (bad.length > 0) usage(`--graph ${graph} is not a valid graph: ${bad[0]}`)
      opts.limit = g.rework_limit
      opts.tasks = g.tasks
    }
    if (runtime) {
      opts.runtime = readJson(runtime)
      const bad = check('runtime', opts.runtime)
      if (bad.length > 0) usage(`--runtime ${runtime} is not a valid runtime: ${bad[0]}`)
    }
    if (ids) opts.ids = ids.split(',')
    if (claims) {
      opts.claims = readJson(claims)
      const bad = shape({ type: 'array', items: { $ref: '#/$defs/claim_comment' } }, opts.claims)
      if (bad.length > 0) usage(`--claims ${claims}: ${bad[0]}`)
    }
  } catch (e) {
    usage(`cannot read an option file: ${e.message}`)
  }
  if (now !== undefined) {
    opts.now = Date.parse(now)
    if (Number.isNaN(opts.now)) usage(`--now ${now} is not a time`)
  }
  let value
  try {
    value = readJson(file)
  } catch (e) {
    process.stdout.write(`${file}: not JSON: ${e.message}\n`)
    process.exit(1)
  }
  const problems = check(def, value, opts)
  for (const p of problems) process.stdout.write(`${def}: ${p}\n`)
  if (problems.length === 0 && def === 'runtime') for (const u of unverified(value)) process.stdout.write(`unverified: ${u}\n`)
  process.exit(problems.length > 0 ? 1 : 0)
}
