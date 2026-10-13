// tests/answer-merged.js - the spec of a re-run that gives a merged task a new answer 1 rework round.
// A stub harness like tests/workflows.js (the stub answers each agent() call with
// tests/fixtures/contract/<shape>.ok.json). Node, no packages. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')
const { contract } = require('../plugin/contract/check.js')

const fixtures = path.join(__dirname, 'fixtures', 'contract')
const wavePath = path.join(__dirname, '..', 'plugin', 'workflows', 'wave.js')
const SHA = '0123456789abcdef0123456789abcdef01234567'
const ANSWER = 'Use the system font.'
const claimUrl = (id) => `https://github.com/example/game/issues/1#issuecomment-${id.length}${id.charCodeAt(0)}`
const graph = {
  repo: 'example/game', parent: 10, branch: '10-wave-1', base: { ref: 'main', sha: SHA }, rework_limit: 2,
  tasks: [
    { id: 'read', issue: 11, tier: 'bounded', blockers: [], files: ['src/read.ts'], oracle: { command: 't read', files: ['test/read.test.ts'], uncovered: [] } },
    { id: 'hud', issue: 15, tier: 'judgment', blockers: [], files: ['src/hud.ts'], oracle: { command: 't hud', files: ['test/hud.test.ts'], uncovered: ['layout'] } },
  ],
}
const MERGED = ['Merge 10-wave-1-read into 10-wave-1', 'Merge 10-wave-1-hud into 10-wave-1']
const inline = (v) =>
  Array.isArray(v) ? v.map(inline) : v && typeof v === 'object'
    ? v.$ref ? inline(contract.$defs[v.$ref.replace('#/$defs/', '')]) : Object.fromEntries(Object.entries(v).map(([k, x]) => [k, inline(x)]))
    : v
const shapeOf = (schema) => Object.keys(contract.$defs).find((d) => JSON.stringify(inline(contract.$defs[d])) === JSON.stringify(schema))
const fixture = (def) => JSON.parse(fs.readFileSync(path.join(fixtures, `${def}.ok.json`), 'utf8'))

async function runWave(merges) {
  const src = fs.readFileSync(wavePath, 'utf8').replace(/^export /m, '')
  const AsyncFunction = (async () => {}).constructor
  const calls = []
  const agent = async (prompt, opts) => {
    const def = shapeOf(opts.schema)
    let a = fixture(def)
    const m = def === 'report' && prompt.match(/Report task (\S+), round (\d+), branch (\S+?),/)
    if (m) a = { ...a, task: m[1], round: Number(m[2]), branch: m[3] }
    if (def === 'remote') a = { merges, heads: [] }
    if (def === 'brief') { const t = graph.tasks.find((x) => opts.label === `brief ${x.id}`); if (t) a = { ...a, files: t.files, oracle: t.oracle } }
    calls.push({ prompt, label: opts.label })
    return a
  }
  const NoClock = function () { throw new Error('no clock') }
  for (const k of ['now', 'parse', 'UTC']) NoClock[k] = NoClock
  const args = { graph, claims: { read: claimUrl('read'), hud: claimUrl('hud') }, answers: { read: ANSWER }, cpus: 4, started_at: '2026-10-08T12:00:00Z' }
  const result = await new AsyncFunction('args', 'phase', 'agent', 'parallel', 'log', 'Date', src)(args, () => {}, agent, (ts) => Promise.all(ts.map((t) => t())), () => {}, NoClock)
  return { calls, result }
}

const problems = []
const expect = (ok, msg) => { if (!ok) problems.push(msg) }

async function main() {
  // A new answer: the remote shows no merged rework branch of read.
  const a = await runWave(MERGED)
  const ls = a.calls.map((c) => c.label)
  expect(ls.includes('rework read 1'), `a merged task with a new answer got no rework round: ${ls}`)
  expect(!ls.some((l) => l.startsWith('build read') || l.startsWith('rework hud') || l.startsWith('build hud')), `a task ran that should be skipped: ${ls}`)
  const p = (a.calls.find((c) => c.label === 'rework read 1') || { prompt: '' }).prompt
  expect(p.includes(ANSWER) && p.includes('10-wave-1-read-r1') && p.includes('origin/10-wave-1'), 'the answer rework lacks the answer, the r1 branch or the wave head')
  expect(JSON.stringify([...(a.result.merged_before || [])].sort()) === '["hud","read"]', `merged_before is ${a.result.merged_before}`)
  const t = (a.result.tasks || []).find((x) => x.task === 'read')
  expect(t && t.state === 'done', `read ends ${t && t.state}, not done`)
  // The answer round already merged: the answer was seen, no rework.
  const b = await runWave([...MERGED, 'Merge 10-wave-1-read-r1 into 10-wave-1'])
  const lb = b.calls.map((c) => c.label)
  expect(!lb.some((l) => /^(rework|build) read/.test(l)), `a seen answer ran again: ${lb}`)
  // The next round after r1 and r2 merged is over the limit (rework_limit 2): no rework, a note.
  const c = await runWave([...MERGED, 'Merge 10-wave-1-read-r1 into 10-wave-1', 'Merge 10-wave-1-read-r2 into 10-wave-1'])
  expect(!c.calls.some((x) => /^rework read/.test(x.label)), 'a task past the rework limit was reworked')
  for (const x of problems) console.log(`FAIL ${x}`)
  console.log(`answer-merged: ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}
main().catch((e) => { console.log(`FAIL ${e.message}`); process.exit(1) })
