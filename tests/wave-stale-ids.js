// tests/wave-stale-ids.js - spec checks of the absorbed-task match (#299). Node, no packages.
// wave.js: a task counts as absorbed only when the notes name it as a task. A short or plain-word id
// ('a', 'ui') in ordinary prose marks nothing; 'task a', '`a`', '"a"' and '#a' do; an id with a digit or
// a hyphen still matches as a bare word. Stub harness of tests/workflows.js.
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
const oracle = (id) => ({ command: `t ${id}`, files: [], uncovered: ['layout'] })
const task = (id, files, blockers = []) => ({ id, tier: 'judgment', blockers, files, brief: `Edit ${files.join(', ')}.`, oracle: oracle(id) })
// z builds first; a, ui and x-1 wait on it. The notes of z say what it absorbed.
const GRAPH = { ...H.ARGS.wave.graph, rework_limit: 0, tasks: [task('z', ['src/z.ts']), task('a', ['src/a.ts'], ['z']), task('ui', ['src/ui.ts'], ['z']), task('x-1', ['src/x.ts'], ['z'])] }
const notesOf = (notes) => H.run(file, { ...H.ARGS.wave, graph: GRAPH, claims: 'solo', regression: undefined }, H.answerWith('wave', { report: (n, a, label) => (label === 'build z' ? { ...a, notes } : a) }))
const rebriefed = (r, id) => labels(r).includes(`brief ${id}`)

async function main() {
  const prose = await notesOf('Absorbed a helper from the old module. Absorbed the ui work too.')
  expect(!rebriefed(prose, 'a') && !rebriefed(prose, 'ui') && labels(prose).includes('build a') && labels(prose).includes('build ui'), `prose ids: a plain word marked a task stale: ${labels(prose)}`)
  for (const [phrase, id] of [['Absorbed the work of `a`.', 'a'], ['It already did task a.', 'a'], ['It already did task #ui.', 'ui'], ['Absorbed "ui" fully.', 'ui'], ['Absorbed #a.', 'a'], ['Absorbed x-1 in full.', 'x-1']]) {
    const hit = await notesOf(phrase)
    expect(rebriefed(hit, id), `task reference: "${phrase}" did not re-brief ${id}: ${labels(hit)}`)
  }

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`wave-stale-ids: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('wave-stale-ids: 0 passed, 1 failed')
  process.exit(1)
})
