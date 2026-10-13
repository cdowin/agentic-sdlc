// tests/chain-gate.js - spec checks of a no-chain task that chain tasks wait on (#263). Node, no packages.
// It runs plugin/workflows/wave.js under the stub harness of tests/workflows.js (run, ARGS, answerWith),
// loaded without its main(), and the graph checks of plugin/contract/check.js.
// A chain task may wait on a task with no chain (a gate task). The chain branch is then cut from the wave
// branch after the gate task merges, by 1 'open chain <c>' agent. A gate task may not reach a chain task.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, chainTask, claimUrl, SHA, check, contract }`)(require, __dirname)
const root = path.join(__dirname, '..')
const waveFile = path.join(root, 'plugin', 'workflows', 'wave.js')
const checkFile = path.join(root, 'plugin', 'contract', 'check.js')
const { SHA, chainTask } = H

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const escalationOf = (r, id) => ((r.result.escalations || []).find((e) => e.task === id) || {}).reason || ''
const graphOf = (tasks) => ({ ...H.ARGS.wave.graph, tasks })
const claimsOf = (ids) => Object.fromEntries(ids.map((id) => [id, H.claimUrl(id)]))
// graphProblems: the problems check.js reports for the graph, or the error it throws.
function graphProblems(g) {
  try {
    return H.check('graph', g)
  } catch (e) {
    return [`threw: ${e.message}`]
  }
}
// runWave: the wave run, or { error } when it throws.
async function runWave(args, over = {}) {
  try {
    return await H.run(waveFile, { ...H.ARGS.wave, ...args }, H.answerWith('wave', over))
  } catch (e) {
    return { error: e.message, calls: e.calls || [], logs: [] }
  }
}
// fnText: the body of function name, from its function line up to the first line that is "}".
// The comment above each copy names the other file, so it is not compared.
function fnText(file, name) {
  const src = fs.readFileSync(file, 'utf8')
  const at = src.indexOf(`\nfunction ${name}(`)
  return at < 0 ? null : src.slice(at, src.indexOf('\n}\n', at) + 3)
}

// The gate graph: 1 no-chain task first, then 2 chains on top of it that edit 1 shared file.
const gated = graphOf([
  chainTask('gate', undefined, ['docs/contract.md']),
  chainTask('a', 'x', ['src/shared.ts'], ['gate']),
  chainTask('b', 'y', ['src/shared.ts'], ['gate']),
])
const GATED_IDS = ['gate', 'a', 'b']
const openAnswer = (heads) => (n, a, label) => {
  const c = label.startsWith('open chain ') && label.slice('open chain '.length)
  return c && heads[c] ? { merges: [], heads: [{ branch: `10-wave-1-${c}`, sha: heads[c] }] } : a
}
const DEADLOCK = 'task gate: chain y waits on it, but it waits on chain task a'

async function main() {
  // 1. The graph checks of check.js.
  const ok = graphProblems(gated)
  expect(ok.length === 0, `graph: a chain task that waits on a no-chain task is refused: ${ok.join('; ')}`)

  const deadlock = graphOf([chainTask('a', 'x', ['p']), chainTask('gate', undefined, ['q'], ['a']), chainTask('b', 'y', ['r'], ['gate'])])
  const dl = graphProblems(deadlock)
  expect(dl.includes(DEADLOCK), `graph: a gate task that waits on a chain task is not refused with "${DEADLOCK}": ${dl.join('; ')}`)
  expect(!dl.some((p) => p.startsWith('task b: chain y waits on gate')), `graph: the no-chain blocker gate is still refused as not in the chain: ${dl.join('; ')}`)

  const deep = graphOf([chainTask('a', 'x', ['p']), chainTask('mid', undefined, ['m'], ['a']), chainTask('gate', undefined, ['q'], ['mid']), chainTask('b', 'y', ['r'], ['gate'])])
  const dp = graphProblems(deep)
  expect(dp.includes(DEADLOCK), `graph: a gate task that reaches a chain task through a no-chain task is not refused: ${dp.join('; ')}`)

  const cross = graphProblems(graphOf([chainTask('a', 'x', ['p']), chainTask('b', 'y', ['r'], ['a'])]))
  expect(cross.includes('task b: chain y waits on a, which is not in it'), `graph: a chain task that waits on another chain is not refused with the old message: ${cross.join('; ')}`)

  const cycle = graphProblems(graphOf([chainTask('g1', undefined, ['q'], ['g2']), chainTask('g2', undefined, ['s'], ['g1']), chainTask('b', 'y', ['r'], ['g1'])]))
  expect(!cycle.some((p) => p.startsWith('threw')) && cycle.some((p) => /cycle/i.test(p)), `graph: a blocker cycle under a gate task throws or is not reported: ${cycle.join('; ')}`)
  const ghost = graphProblems(graphOf([chainTask('gate', undefined, ['q'], ['ghost']), chainTask('b', 'y', ['r'], ['gate'])]))
  expect(!ghost.some((p) => p.startsWith('threw')) && ghost.length > 0, `graph: a gate task that waits on no task throws or passes: ${ghost.join('; ')}`)

  // 2. The copies of chainMeaning in check.js and wave.js stay identical.
  const inCheck = fnText(checkFile, 'chainMeaning')
  const inWave = fnText(waveFile, 'chainMeaning')
  expect(inCheck && inCheck === inWave, 'chainMeaning: the copy in wave.js differs from the one in check.js')

  // 3. The schema text of task.chain names the gate task.
  const desc = (((H.contract.$defs.task || {}).properties || {}).chain || {}).description || ''
  expect(desc.endsWith(' A chain task may also wait on a task with no chain; the chain branch is then cut from the graph branch after that task merges, and that task may not wait on a chain task.'), 'schema: the description of task.chain does not name the gate task')

  // 4. The wave refuses the deadlock graph before any build.
  const wd = await runWave({ graph: deadlock, claims: claimsOf(['a', 'gate', 'b']) })
  expect(wd.error && wd.error.includes(DEADLOCK) && !labels(wd).some((l) => l.startsWith('build')), `wave: the deadlock graph is not refused before any build: ${wd.error || 'no error'}`)

  // 5. The gated chains open after the gate merges, then build on their own branches and converge once.
  const r = await runWave({ graph: gated, claims: claimsOf(GATED_IDS) }, { remote: openAnswer({ x: SHA, y: SHA }) })
  if (r.error) expect(false, `wave gated: it threw: ${r.error}`)
  else {
    const ls = labels(r)
    const at = (l) => ls.indexOf(l)
    expect(at('merge gate') >= 0 && at('merge gate') < at('open chain x') && at('merge gate') < at('open chain y'), `wave gated: the chains do not open after the gate merges: ${ls}`)
    expect(at('open chain x') >= 0 && at('open chain x') < at('build a') && at('open chain y') >= 0 && at('open chain y') < at('build b'), `wave gated: a chain task builds before its chain opens: ${ls}`)
    expect(ls.filter((l) => l === 'open chain x').length === 1 && ls.filter((l) => l === 'open chain y').length === 1, `wave gated: each chain does not open exactly once: ${ls}`)
    expect(!promptOf(r, 'remote check').includes(`git push -q origin ${SHA}:refs/heads/<branch>`), 'wave gated: the remote check cuts a gated chain branch at the base')
    expect(promptOf(r, 'open chain x').includes('git push -q origin origin/10-wave-1:refs/heads/10-wave-1-x'), 'wave gated: the open chain agent does not cut the chain branch from the wave branch')
    expect(r.logs.includes(`chain x: branch 10-wave-1-x cut from 10-wave-1 at ${SHA} after gate merged`), `wave gated: no log of the chain cut: ${r.logs.filter((l) => l.startsWith('chain')).join(' | ')}`)
    expect(promptOf(r, 'build a').includes('10-wave-1-a origin/10-wave-1-x\n') && promptOf(r, 'merge a').includes('into the chain branch 10-wave-1-x'), 'wave gated: task a does not build and merge on its chain branch')
    expect(JSON.stringify(r.result.done) === JSON.stringify(GATED_IDS), `wave gated: done is ${r.result.done}, not ${GATED_IDS}`)
    expect(ls.filter((l) => l === 'converge').length === 1, `wave gated: not exactly 1 converge: ${ls}`)
  }

  // 6. The gate task stops: no chain opens, and every chain task stops.
  const f = await runWave({ graph: gated, claims: claimsOf(GATED_IDS) }, {
    remote: openAnswer({ x: SHA, y: SHA }),
    report: (n, a, label) => (label.startsWith('build gate') ? { ...a, status: 'escalated', escalation: 'The issue says "keep the format"; which format?' } : a),
  })
  if (f.error) expect(false, `wave failed gate: it threw: ${f.error}`)
  else {
    const ls = labels(f)
    expect(!ls.some((l) => l.startsWith('open chain') || l === 'build a' || l === 'build b'), `wave failed gate: a chain opened or a chain task built: ${ls}`)
    for (const id of ['a', 'b']) expect(/did not open|was not integrated/.test(escalationOf(f, id)), `wave failed gate: task ${id} stops for "${escalationOf(f, id)}"`)
  }

  // 7. An open chain agent with no head: that chain does not open; the other chain still builds.
  const n = await runWave({ graph: gated, claims: claimsOf(GATED_IDS) }, { remote: openAnswer({ x: SHA }) })
  if (n.error) expect(false, `wave no head: it threw: ${n.error}`)
  else {
    expect(/did not open/.test(escalationOf(n, 'b')) && !labels(n).includes('build b'), `wave no head: task b stops for "${escalationOf(n, 'b')}", not a chain that did not open`)
    expect(n.result.done.includes('a'), `wave no head: chain x did not finish: done ${n.result.done}`)
  }

  // 8. A re-run: the gate merged and chain x was cut by the earlier run. Only chain y opens.
  const re = await runWave({ graph: gated, claims: claimsOf(GATED_IDS) }, {
    remote: (k, a, label) => (label === 'remote check'
      ? { merges: ['Merge 10-wave-1-gate into 10-wave-1'], heads: [{ branch: '10-wave-1', sha: SHA }, { branch: '10-wave-1-x', sha: SHA }] }
      : openAnswer({ y: SHA })(k, a, label)),
  })
  if (re.error) expect(false, `wave re-run: it threw: ${re.error}`)
  else {
    const ls = labels(re)
    expect(!ls.includes('open chain x') && ls.includes('open chain y') && !ls.includes('build gate'), `wave re-run: a chain branch on the remote opened again, or the merged gate built again: ${ls}`)
    expect(promptOf(re, 'build a').includes('10-wave-1-a origin/10-wave-1-x\n'), 'wave re-run: task a does not build on the chain branch the earlier run cut')
  }

  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`chain-gate: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main()
