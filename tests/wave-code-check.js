// tests/wave-code-check.js - spec checks of the code check before dispatch (#341). Node, no packages.
// wave.js: before any worker starts, 1 bounded-tier agent spot-checks each net-new task against the code.
// A ready issue that renames a symbol and leaves its caller file out of Files gets that file added to its
// files, and a false claim about the code goes into its brief as a decision. The result lists the
// corrections per task. args.code_check false turns it off; no answer marks the task unchecked, and the
// per-task caller check runs as before. Stub harness of tests/workflows.js.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, problems }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'wave.js')

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const before = (r, a, b) => labels(r).indexOf(a) >= 0 && labels(r).indexOf(a) < labels(r).indexOf(b)
const GRAPH = { ...H.ARGS.wave.graph, rework_limit: 0, tasks: [{ id: 'a', tier: 'judgment', blockers: [], files: ['src/a.ts'], oracle: { command: 't a', files: [], uncovered: ['layout'] } }] }
const READY = '## Outcome\nB replaces A.\n## Done when\nA is renamed to B, with no alias. The save has a version field.\n## Files\nsrc/a.ts\n## Proof\nt a\n## Decisions\nnone'
const CLAIM = { claim: 'The save has a version field', fact: 'src/save.ts:12 writes no version field' }
const FOUND = { tasks: [{ task: 'a', files: ['src/a.ts', 'src/other.ts'], claims: [CLAIM] }] }
const wave = (extra, codeCheck) => H.run(file, { ...H.ARGS.wave, graph: GRAPH, claims: 'solo', regression: undefined, issues: { a: READY }, ...extra }, H.answerWith('wave', { code_check: codeCheck }))
const rowOf = (r) => (r.result.tasks || []).find((t) => t.task === 'a') || {}

async function main() {
  // 1. The issue names src/a.ts only; src/other.ts calls A. The check runs before any worker and widens the files.
  const r = await wave({}, FOUND)
  const cc = promptOf(r, 'code check')
  expect(before(r, 'code check', 'build a') && cc.includes('A is renamed to B') && cc.includes('files: src/a.ts'), `on: the code check did not run before the worker with the task text: ${labels(r)}`)
  const call = r.calls.find((c) => c.label === 'code check') || {}
  const bounded = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'plugin', 'contract', 'runtimes.json'), 'utf8')).claude.tiers.bounded.model
  expect(call.model === bounded, `on: the code check is not on the bounded tier: ${call.model}`)
  const build = promptOf(r, 'build a')
  expect(build.includes('Your files: src/a.ts, src/other.ts.'), 'on: the worker did not get the caller file in its files')
  expect(build.includes(`False: ${CLAIM.claim}. The code: ${CLAIM.fact}`), 'on: the false claim is not a decision in the brief')
  expect(!labels(r).includes('check a'), `on: the per-task caller check ran after the code check: ${labels(r)}`)
  const c = (r.result.corrections || {}).a
  expect(c && c.files.join() === 'src/other.ts' && c.claims.length === 1 && rowOf(r).state === 'done', `on: the result does not list the corrections of a: ${JSON.stringify(r.result.corrections)}`)

  // 2. Opt out: no code check, and the per-task caller check runs as before.
  const off = await wave({ code_check: false }, FOUND)
  expect(!labels(off).includes('code check') && labels(off).includes('check a') && !off.result.corrections, `off: ${labels(off)}`)

  // 3. No answer: the task is unchecked, and the per-task caller check runs.
  const none = await wave({}, null)
  expect(rowOf(none).unchecked === 'code' && labels(none).includes('check a') && labels(none).includes('build a'), `null: ${JSON.stringify(rowOf(none).unchecked)} ${labels(none)}`)

  // 4. A bad value throws before any agent.
  let msg = ''
  try { await wave({ code_check: 'no' }, FOUND) } catch (e) { msg = e.message }
  expect(/args\.code_check must be true or false/.test(msg), `bad arg: ${msg || 'it did not throw'}`)

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`wave-code-check: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('wave-code-check: 0 passed, 1 failed')
  process.exit(1)
})
