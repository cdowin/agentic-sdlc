// tests/wave-reach.js - spec checks of oracle.reach in wave (#296). Node, no packages.
// It runs plugin/workflows/wave.js under the stub harness of tests/workflows.js, loaded without its
// main(). A task with oracle.reach gets a reach step in its merge, and a reach red is red for step 5: no
// commit, push, close or prune, and the workflow does not count the merge. A worker report with unverified
// suites goes to the merge, which runs them. A task without reach keeps its prompts and checks.
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
const rowOf = (r, id) => (r.result.metrics || []).find((m) => m.task === id) || {}
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

  // (c) A report with unverified suites goes to the merge, with or without reach: the merge runs reach.
  for (const args of [REACH, H.waveOne]) {
    const r = await wave(args, UNVERIFIED)
    expect(r.calls.some((c) => c.label === 'merge read') && taskOf(r, 'read').state !== 'escalated', `unverified B was refused before the merge: ${whyOf(r, 'read')}`)
  }

  // (d) A reach red decides step 5: the green condition names reach, the red branch commits, pushes, closes
  // and deletes nothing, and the push (step 7) and the close (step 8) come after that decision.
  const step5 = mr.indexOf('5. Green (the gate passed, the oracle when it ran, and every reach run passed)')
  const redLine = mr.indexOf('Red (a reach red counts', step5)
  const stopLine = mr.indexOf('Stop: commit nothing, push nothing, close nothing and delete nothing.', redLine)
  const push = mr.indexOf('git push -q origin', stopLine)
  const close = mr.indexOf('Close and prune, only when the merge is validated: step 5 was green', push)
  expect(mr.indexOf('Then, in every case, run reach:') < step5 && step5 > 0 && redLine > step5 && stopLine > redLine && push > stopLine && close > push, `merge read: reach is not decided in step 5 before the push and the close: ${[step5, redLine, stopLine, push, close]}`)
  expect(!/A reach red is the task's[^.]*oracle_passed false/.test(mr), 'merge read: step 4 still decides the reach red apart from step 5')
  // An integrator that breaks the rule (oracle_passed true, reach red, closed and pruned): no merge counted,
  // nothing recorded as closed or pruned, and the task is not merged.
  const liar = await wave(REACH, { merge: (n, a) => ({ ...a, reach: [{ dir: 'B', command: 't unit B', passed: false }], closed: true, pruned: true, pruned_branch: '10-wave-1-read' }) })
  const t = taskOf(liar, 'read')
  expect(t.state === 'escalated' && !(liar.result.done || []).includes('read') && rowOf(liar, 'read').result !== 'merged', `a reach-red merge with oracle_passed true counted as merged: ${t.state}`)
  expect(t.closed_at === undefined && t.pruned === undefined && rowOf(liar, 'read').closed_at === undefined && rowOf(liar, 'read').pruned === undefined && !liar.calls.some((c) => c.label.startsWith('reopen')), 'a reach-red merge is recorded as closed or pruned')
  expect(liar.calls.filter((c) => c.label.startsWith('merge read')).length === 2, `a reach-red merge did not step up once: ${liar.calls.map((c) => c.label)}`)

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
