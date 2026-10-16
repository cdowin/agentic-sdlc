// tests/spec-escalate.js - plan.js Spec phase: a failed spec chain keeps the specs of the chains that passed (#311).
// Runs plan.js under a stub that answers by label. Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const SHA = '0123456789abcdef0123456789abcdef01234567'
const SPEC_SHA = 'fedcba9876543210fedcba9876543210fedcba98'
const ARGS = { goal: 10, repo: 'example/game', branch: '10-wave-1', base: { ref: 'main', sha: SHA } }
const fixture = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'contract', `${n}.json`), 'utf8'))
const task = (id) => ({ id, title: `Build ${id}`, outcome: 'It works.', done_when: [`t ${id} passes`], area: id, tier: 'judgment', blockers: [], files: [`src/${id}.ts`], oracle: { command: `t ${id}`, files: [`test/${id}.test.ts`], uncovered: ['x'] } })
const idOf = (label) => label.replace(/^spec-/, '').replace(/-\d+$/, '')
const answer = (id) => ({ ...fixture('spec.ok'), task: id, tests: [`test/${id}.spec.ts`], created: [`test/${id}.spec.ts`], keep: [], stubs: [`src/${id}.ts`], command: `t ${id}`, uncovered: [], sha: SPEC_SHA })
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)
function NoClock() { throw new Error('no clock in workflow scripts') }
for (const k of ['now', 'parse', 'UTC']) NoClock[k] = NoClock

async function main() {
  const src = fs.readFileSync(path.join(__dirname, '..', 'plugin', 'workflows', 'plan.js'), 'utf8').replace(/^export /m, '')
  const tasks = [task('a'), task('b'), task('c')]
  const agent = async (prompt, o) => {
    if (/^architect/.test(o.label)) return { repo: ARGS.repo, branch: ARGS.branch, base: ARGS.base, rework_limit: 0, tasks }
    const t = tasks.find((x) => o.label === `brief-${x.id}`)
    if (t) return { task: t.id, brief: `Build ${t.id}.`, files: t.files, why: 'stub', tier: t.tier, oracle: t.oracle }
    if (/^spec-/.test(o.label)) return idOf(o.label) === 'b' ? { ...answer('b'), red: { line: '0 failed', failed: false } } : answer(idOf(o.label))
    if (o.label === 'critic') return fixture('critique.ok')
    throw new Error(`no stub answer for ${o.label}`)
  }
  const AsyncFunction = (async () => {}).constructor
  const out = []
  let result
  try {
    result = await new AsyncFunction('args', 'phase', 'agent', 'parallel', 'log', 'Date', src)(ARGS, () => {}, agent, (ts) => Promise.all(ts.map((t) => t())), () => {}, NoClock)
  } catch (e) { out.push(`plan threw ${e}`) }
  if (result) {
    if (!(result.status === 'escalated' && result.problems.some((p) => /^task b: spec: /.test(p)))) out.push(`1 of 3 red: status ${result.status}, problems ${JSON.stringify(result.problems)}`)
    if (!(same(result.specs.map((x) => x.task), ['a', 'c']) && result.specs.every((x) => x.tier_before && x.tier_after))) out.push(`1 of 3 red: specs are ${JSON.stringify(result.specs.map((x) => x.task))}, not a and c with tier_before and tier_after`)
  }
  for (const p of out) console.log(`FAIL ${p}`)
  console.log(`spec-escalate: ${2 - out.length} passed, ${out.length} failed`)
  process.exit(out.length ? 1 : 0)
}
main()
