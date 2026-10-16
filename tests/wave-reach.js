// tests/wave-reach.js - spec checks of oracle.reach in wave (#296). Node, no packages.
// It runs plugin/workflows/wave.js under the stub harness of tests/workflows.js, loaded without its
// main(). A task with oracle.reach gets a reach step in its merge, a reach red refuses the merge, and a
// worker report with unverified suites is refused. A task without reach keeps its prompts and checks.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, waveOne, problems }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'wave.js')

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const taskOf = (r, id) => (r.result.tasks || []).find((t) => t.task === id) || {}
const whyOf = (r, id) => ((r.result.escalations || []).find((e) => e.task === id) || {}).reason || ''
const read = H.waveOne.graph.tasks[0]
const REACH = { ...H.waveOne, graph: { ...H.waveOne.graph, tasks: [{ ...read, oracle: { ...read.oracle, reach: 't unit {dir}' } }] } }
const wave = (args, over = {}) => H.run(file, { ...H.ARGS.wave, ...args }, H.answerWith('wave', over))
const UNVERIFIED = { report: (n, a) => ({ ...a, unverified: ['B'] }) }

async function main() {
  // (a) The merge of a task with reach runs the template for each folder outside the oracle, even when
  // the worker's proof is kept; a task without reach has no reach step.
  const on = await wave(REACH)
  const mr = promptOf(on, 'merge read')
  expect(mr.includes('Then, in every case, run reach:') && mr.includes('and run t unit {dir} for each remaining folder') && mr.includes('drop the folders of the oracle files (test/read.test.ts, test/read.spec.ts)'), 'merge read: the prompt has no reach step with t unit {dir}')
  expect(!promptOf(await wave(H.waveOne), 'merge read').includes('reach'), 'merge read without reach: the prompt names reach')

  // (b) A reach red in folder B refuses the merge; the task carries the escalation.
  const red = await wave(REACH, { merge: (n, a) => ({ ...a, oracle_passed: false, merged: [], escalation: 't unit B: 2 failed', reach: [{ dir: 'B', command: 't unit B', passed: false }], closed: false, pruned: false }) })
  expect(taskOf(red, 'read').state === 'escalated' && whyOf(red, 'read').includes('t unit B: 2 failed'), `a reach red in B did not refuse the merge: ${taskOf(red, 'read').state}, ${whyOf(red, 'read')}`)

  // (c) A report with unverified suites is refused when the task has reach, accepted when it has none.
  const refused = await wave(REACH, UNVERIFIED)
  expect(taskOf(refused, 'read').state === 'escalated' && whyOf(refused, 'read').includes('unverified suites not run: B; run t unit {dir} for each') && !refused.calls.some((c) => c.label.startsWith('merge')), `unverified B with reach: ${taskOf(refused, 'read').state}, ${whyOf(refused, 'read')}`)
  const accepted = await wave(H.waveOne, UNVERIFIED)
  expect(accepted.calls.some((c) => c.label === 'merge read') && taskOf(accepted, 'read').state !== 'escalated', `unverified B without reach was refused: ${whyOf(accepted, 'read')}`)

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`wave-reach: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('wave-reach: 0 passed, 1 failed')
  process.exit(1)
})
