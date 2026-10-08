#!/usr/bin/env node
// check.js - validate 1 value of the SDLC contract: its shape (sdlc.schema.json), then its meaning.
// Node 18 or later, no packages. Any lead (Claude, Codex or other) runs it on a worker's output
// before it accepts the output.
//
// usage: node check.js <def> <file.json | -> [--repo <dir>] [--limit <n>]
//   <def>    a key of $defs in sdlc.schema.json: graph, report, merge, review, claim, ...
//   --repo   also check each SHA against the remote branch (git fetch in <dir>; needs git)
//   --limit  the rework limit of the graph (default: x-limits.rework_rounds)
// Exit 0: valid. Exit 1: invalid, 1 line per problem on stdout. Exit 2: usage.
'use strict'
const fs = require('fs')
const path = require('path')
const { execFileSync } = require('child_process')

const contract = JSON.parse(fs.readFileSync(path.join(__dirname, 'sdlc.schema.json'), 'utf8'))
const LIMITS = contract['x-limits']
const TIERS = Object.keys(contract['x-tiers'])
const ROLES = Object.keys(contract['x-roles'])
const CAPABILITIES = contract['x-capabilities']
const TRANSITIONS = contract['x-transitions']
const ESCALATED = 'escalated'

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
const overlap = (a, b) => a.filter((f) => b.includes(f))

function graphMeaning(g) {
  const out = []
  const ids = g.tasks.map((t) => t.id)
  for (const d of new Set(dupes(ids))) out.push(`tasks: id ${d} is not unique`)
  const byId = Object.fromEntries(g.tasks.map((t) => [t.id, t]))
  for (const t of g.tasks) {
    for (const b of t.blockers) if (!byId[b]) out.push(`task ${t.id}: blocker ${b} is not a task`)
    out.push(...tierMeaning(`task ${t.id}`, t.tier, t.oracle))
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
    for (const b of (byId[id] && byId[id].blockers) || []) {
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

function tierMeaning(at, tier, oracle) {
  if (tier !== 'bounded') return []
  const out = []
  if (oracle.uncovered.length > 0) out.push(`${at}: tier bounded, but the oracle does not cover ${oracle.uncovered.join('; ')}`)
  if (oracle.files.length === 0) out.push(`${at}: tier bounded needs the oracle files inventoried`)
  return out
}

function reportMeaning(r, opts) {
  const out = []
  if (r.status === 'done' && !r.test.passed) out.push('status done, but the focused test did not pass')
  if (r.status === ESCALATED && !r.escalation) out.push('status escalated needs the question in escalation')
  if ((r.round || 0) > opts.limit) out.push(`round ${r.round} is over the rework limit ${opts.limit}`)
  if (opts.repo) out.push(...onRemote(opts.repo, r.branch, r.sha))
  return out
}

function mergeMeaning(m, opts) {
  const out = []
  if (!m.oracle_passed && !m.escalation) out.push('oracle_passed is false, but escalation is empty')
  if (opts.repo) out.push(...onRemote(opts.repo, m.branch, m.sha))
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

function reviewMeaning(rv) {
  const out = []
  const ids = rv.scores.map((s) => s.id)
  for (const d of new Set(dupes(ids))) out.push(`scores: ${d} is scored 2 times`)
  const known = (id, at) => (ids.includes(id) ? [] : [`${at}: ${id} is not a scored result`])
  for (const p of rv.pairs || []) {
    out.push(...known(p.a, 'pairs'), ...known(p.b, 'pairs'))
    if (p.a === p.b) out.push(`pairs: ${p.a} is paired with itself`)
    if (![p.a, p.b, 'tie'].includes(p.better)) out.push(`pairs: better is ${p.better}, not ${p.a}, ${p.b} or tie`)
  }
  for (const d of new Set(dupes(rv.findings.map((f) => f.id)))) out.push(`findings: id ${d} is not unique`)
  for (const f of rv.findings) {
    if (f.ids.length === 0) out.push(`finding ${f.id}: names no result`)
    f.ids.forEach((id) => out.push(...known(id, `finding ${f.id}`)))
    if (f.cross_issue !== f.ids.length >= 2) out.push(`finding ${f.id}: cross_issue must be true exactly when it names 2 or more results`)
  }
  return out
}

function judgeMeaning(j) {
  const out = []
  if (!j.ranking.includes(j.winner)) out.push(`winner ${j.winner} is not in the ranking`)
  else if (j.ranking[0] !== j.winner) out.push('the winner must rank first')
  for (const d of new Set(dupes(j.ranking))) out.push(`ranking: ${d} is listed 2 times`)
  return out
}

function claimMeaning(c, opts) {
  const out = []
  if (Number.isNaN(Date.parse(c.at))) out.push(`at: ${c.at} is not a time`)
  if (c.supersedes && !c.resume_sha) out.push('a claim that supersedes another needs resume_sha, the remote branch head')
  if (opts.repo && c.resume_sha) out.push(...onRemote(opts.repo, c.branch, c.resume_sha))
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
  for (const role of ROLES) if (typeof r.agent_types[role] !== 'string') out.push(`agent_types.${role}: missing`)
  for (const name of CAPABILITIES) {
    if (!(name in r.capabilities)) out.push(`capabilities.${name}: missing`)
    else out.push(...shape({ $ref: '#/$defs/capability' }, r.capabilities[name], `$.capabilities.${name}`))
  }
  for (const name of Object.keys(r.capabilities)) if (!CAPABILITIES.includes(name)) out.push(`capabilities.${name}: not in x-capabilities`)
  for (const t of Object.keys(r.tiers)) if (!TIERS.includes(t)) out.push(`tiers.${t}: not a tier`)
  return out
}

const meaning = {
  graph: graphMeaning,
  brief: (b) => tierMeaning('brief', b.tier, b.oracle),
  split: splitMeaning,
  report: reportMeaning,
  merge: mergeMeaning,
  review: reviewMeaning,
  judge: judgeMeaning,
  claim: claimMeaning,
  transition: transitionMeaning,
  runtime: runtimeMeaning,
}

// onRemote: the SHA is a commit on the remote branch (the branch head or before it).
function onRemote(repo, branch, sha) {
  const git = (...a) => execFileSync('git', ['-C', repo, ...a], { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()
  try {
    git('fetch', '-q', 'origin', `refs/heads/${branch}`)
  } catch {
    return [`branch ${branch} is not on the remote`]
  }
  try {
    git('merge-base', '--is-ancestor', sha, 'FETCH_HEAD')
    return []
  } catch {
    return [`${sha} is not on the remote branch ${branch}`]
  }
}

function check(def, value, opts = {}) {
  const schema = contract.$defs[def]
  if (!schema) throw new Error(`no contract shape named ${def}`)
  const o = { limit: LIMITS.rework_rounds, ...opts }
  const out = shape(schema, value)
  if (out.length > 0 || !meaning[def]) return out
  return meaning[def](value, o)
}

module.exports = { contract, check }

if (require.main === module) {
  const argv = process.argv.slice(2)
  const opt = (name) => {
    const i = argv.indexOf(name)
    return i < 0 ? undefined : argv.splice(i, 2)[1]
  }
  const repo = opt('--repo')
  const limit = opt('--limit')
  const [def, file] = argv
  if (!def || !file || !contract.$defs[def] || (limit !== undefined && !/^\d+$/.test(limit))) {
    process.stderr.write(`usage: node check.js <${Object.keys(contract.$defs).join('|')}> <file.json|-> [--repo <dir>] [--limit <n>]\n`)
    process.exit(2)
  }
  let value
  try {
    value = JSON.parse(fs.readFileSync(file === '-' ? 0 : file, 'utf8'))
  } catch (e) {
    process.stdout.write(`${file}: not JSON: ${e.message}\n`)
    process.exit(1)
  }
  const problems = check(def, value, { repo, ...(limit !== undefined && { limit: Number(limit) }) })
  for (const p of problems) process.stdout.write(`${def}: ${p}\n`)
  process.exit(problems.length > 0 ? 1 : 0)
}
