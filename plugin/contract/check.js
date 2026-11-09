#!/usr/bin/env node
// check.js - validate 1 value of the SDLC contract: its shape (sdlc.schema.json), then its meaning.
// Node 18 or later, no packages. Any lead (Claude, Codex or other) runs it on a worker's output
// before it accepts the output.
//
// usage: node check.js <def> <file.json | -> [options]
//   <def>            a key of $defs in sdlc.schema.json: report, landing, review, claim, ...
//   --repo <dir>     check each SHA against the remote branch head (git fetch in <dir>; needs git).
//                    For a claim that takes over, also the last commit time of the branch.
//   --ids <a,b,...>  the result ids of a review batch: each must be scored, and no other
//   --needs <a,b>    the capabilities the claimed issue needs (its needs: labels, by x-need-labels)
//   --runtime <file> the runtime profile of the agent that claims: a claim is refused when the
//                    runtime lacks a capability in --needs
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
const dupes = (xs) => xs.filter((x, i) => xs.indexOf(x) !== i)

function reportMeaning(r, opts) {
  const out = []
  if (r.status === 'done' && !r.test.passed) out.push('status done, but the focused test did not pass')
  if (r.status === 'done' && r.gate && !r.gate.passed) out.push('status done, but the gate did not pass')
  if (r.status === 'done' && r.escalation) out.push('status done, but escalation is set')
  if (r.status === 'escalated' && !r.escalation) out.push('status escalated needs the question in escalation')
  if ((r.round || 0) > opts.limit) out.push(`round ${r.round} is over the rework limit ${opts.limit}`)
  if (opts.repo) out.push(...atHead(opts.repo, r.branch, r.sha))
  return out
}

// landingMeaning: a landing that merged nothing says why; a merged landing has a green fast check.
function landingMeaning(l) {
  const out = []
  if (!l.merged && !l.escalation) out.push('merged is false, but escalation is empty')
  if (l.merged && l.check && !l.check.passed) out.push('merged is true, but the fast check is red')
  return out
}

// prMeaning: ready needs a PR, auto-merge needs ready, and no PR says why.
function prMeaning(p) {
  const out = []
  if (p.ready && !p.pr) out.push('ready is true, but no PR was opened')
  if (p.auto_merge && !p.ready) out.push('auto_merge is true, but the PR is not ready')
  if (!p.pr && !p.escalation) out.push('pr is empty, but escalation is empty')
  return out
}

// findingMeaning: a vote names the open finding it voted on, and adds to the vote of its filing.
function findingMeaning(f) {
  const out = []
  if (f.voted && !f.url) out.push('voted is true, but url does not name the open finding')
  if (f.voted && f.votes < 2) out.push(`voted is true, but votes is ${f.votes}; a vote adds 1 to the filing`)
  if (!f.voted && f.votes !== 1 && f.url) out.push(`voted is false, but votes is ${f.votes}; a new filing has 1 vote`)
  return out
}

// landingReviewMeaning: a review names each landing once, and each finding is in a landing it read.
function landingReviewMeaning(r) {
  const out = [...new Set(dupes(r.landings))].map((d) => `landings: ${d} is not unique`)
  for (const f of r.findings) if (!r.landings.includes(f.task)) out.push(`finding ${JSON.stringify(f.title)}: task ${f.task} is not a landing the review read`)
  return out
}

// metricsMeaning: a row is pruned only when its task issue closed (closed_at) or closed and reopened.
function metricsMeaning(m) {
  const out = m.pruned && !m.closed_at && !m.reopened ? ['pruned is true, but closed_at is not set'] : []
  if (m.reopened && m.closed_at) out.push('reopened is true, but closed_at is set')
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
  for (const n of opts.runtime ? opts.needs || [] : []) {
    if (!CAPABILITIES.includes(n)) out.push(`--needs ${n} is not in x-capabilities`)
    else if (!hasCapability(opts.runtime, n)) out.push(`task ${c.task} needs ${n}, but runtime ${opts.runtime.provider} does not have it`)
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
  for (const k of Object.keys(r.agent_types)) if (!ROLES.includes(k)) out.push(`agent_types.${k}: not a role (roles: ${ROLES.join(', ')})`)
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
  report: reportMeaning,
  landing: landingMeaning,
  pr: prMeaning,
  finding: findingMeaning,
  landing_review: landingReviewMeaning,
  metrics: metricsMeaning,
  review: reviewMeaning,
  claim: claimMeaning,
  transition: transitionMeaning,
  runtime: runtimeMeaning,
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
    process.stderr.write(`${why}\nusage: node check.js <${Object.keys(contract.$defs).join('|')}> <file.json|-> [--repo <dir>] [--ids <a,b>] [--needs <a,b>] [--runtime <file>] [--claims <file>] [--now <time>]\n`)
    process.exit(2)
  }
  const readJson = (file) => JSON.parse(fs.readFileSync(file === '-' ? 0 : file, 'utf8'))
  const opts = { repo: opt('--repo') }
  const needs = opt('--needs')
  const ids = opt('--ids')
  const claims = opt('--claims')
  const runtime = opt('--runtime')
  const now = opt('--now')
  const [def, file] = argv
  if (!def || !file || !contract.$defs[def]) usage('need a contract shape and a file')
  try {
    if (runtime) {
      opts.runtime = readJson(runtime)
      const bad = check('runtime', opts.runtime)
      if (bad.length > 0) usage(`--runtime ${runtime} is not a valid runtime: ${bad[0]}`)
    }
    if (ids) opts.ids = ids.split(',')
    if (needs) opts.needs = needs.split(',')
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
