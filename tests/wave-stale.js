// tests/wave-stale.js - spec checks of the stale-brief guard (#295). Node, no packages.
// wave.js: a path a merge deleted (merge gone), a task a merge's notes absorbed, or a Files path missing
// at the start commit sends the brief back to a brief-writer, never to a worker on the stale brief.
// plan.js: a brief line "needs X merged" with X not a blocker is a problem. Stub harness of tests/workflows.js.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, problems }`)(require, __dirname)
const root = path.join(__dirname, '..')
const file = path.join(root, 'plugin', 'workflows', 'wave.js')

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const before = (r, a, b) => labels(r).indexOf(a) >= 0 && labels(r).indexOf(a) < labels(r).indexOf(b)
const oracle = (id) => ({ command: `t ${id}`, files: [], uncovered: ['layout'] })
const task = (id, files, blockers = [], brief = `Edit ${files.join(', ')}.`) => ({ id, tier: 'judgment', blockers, files, brief, oracle: oracle(id) })
const GRAPH = { ...H.ARGS.wave.graph, rework_limit: 0, tasks: [task('a', ['src/a.ts']), task('b', ['src/f.ts'], ['a']), task('c', ['src/a.ts', 'src/c.ts', 'src/new.ts'], ['a'], 'Edit src/c.ts. It creates src/new.ts.')] }
const wave = (over, graph = GRAPH) => H.run(file, { ...H.ARGS.wave, graph, claims: 'solo', regression: undefined }, H.answerWith('wave', over))
const merged = (extra) => ({ merge: (n, a, label) => (label === 'merge a' ? { ...a, ...extra } : a) })
const rebriefB = (files) => ({ brief: (n, a, label) => (label === 'brief b' ? { ...a, task: 'b', files, oracle: oracle('b') } : a) })

async function main() {
  // 1. The issue's Done when: a merges and deletes src/f.ts; b names it. b re-briefs, then builds on the new brief.
  const gone = await wave({ ...merged({ gone: ['src/f.ts'] }), ...rebriefB(['src/g.ts']) })
  expect(before(gone, 'merge a', 'brief b') && before(gone, 'brief b', 'build b') && promptOf(gone, 'brief b').includes('src/f.ts'), `gone: b was not re-briefed with src/f.ts before its build: ${labels(gone)}`)
  expect(promptOf(gone, 'build b').includes('Your files: src/g.ts.'), 'gone: the worker of b got the stale file list')
  expect(!labels(gone).includes('brief c'), 'gone: c names no gone path, but it was re-briefed')
  // The new brief still names a missing path: b stops with no worker.
  const still = await wave({ ...merged({ gone: ['src/f.ts'] }), ...rebriefB(['src/f.ts']), path_check: (n, a, label) => (label === 'path check b' ? { tasks: [{ task: 'b', missing: ['src/f.ts'] }] } : a) })
  expect(labels(still).includes('brief b') && !labels(still).some((l) => l.startsWith('build b')), `still stale: b got a worker: ${labels(still)}`)
  // 2. The notes of a say it absorbed b: b re-briefs before any worker.
  const absorbed = await wave({ ...rebriefB(['src/g.ts']), report: (n, a, label) => (label === 'build a' ? { ...a, notes: 'Absorbed the work of task b.' } : a) })
  expect(before(absorbed, 'merge a', 'brief b') && before(absorbed, 'brief b', 'build b'), `absorbed: b was not re-briefed before its build: ${labels(absorbed)}`)

  // 3. The path check: a blocker's file and a path the brief creates are not asked; a missing path re-briefs a.
  const fresh = await wave({})
  const pc = promptOf(fresh, 'path check')
  expect(pc.includes('- a at ') && pc.includes('- c at ') && /- c at [^\n]*src\/c\.ts($|\n)/.test(pc) && !/- c at [^\n]*src\/(a|new)\.ts/.test(pc), `path check: wrong paths asked:\n${pc}`)
  expect(!labels(fresh).some((l) => l.startsWith('brief ')), `path check: a task with all its paths got a brief-writer: ${labels(fresh)}`)
  const missing = await wave({ path_check: (n, a, label) => (label === 'path check' ? { tasks: [{ task: 'a', missing: ['src/a.ts'] }] } : a) })
  expect(before(missing, 'brief a', 'build a') && promptOf(missing, 'brief a').includes('src/a.ts'), `path check: a missing path did not re-brief a first: ${labels(missing)}`)

  // 4. plan.js problems: "needs 1 merged" with 1 not a blocker is a problem line; with 1 a blocker it is none.
  const src = fs.readFileSync(path.join(root, 'plugin', 'workflows', 'plan.js'), 'utf8')
  const block = src.slice(src.indexOf('// ---- contract: begin'), src.indexOf('// ---- contract: end'))
  const problemsOf = new Function('args', 'NEED_LABELS', `${block}\n${src.slice(src.indexOf('const problemsOf = '), src.indexOf('const escalate = '))}\nreturn problemsOf`)({}, {})
  const plan = (blockers) => ({ repo: 'x/y', branch: 'b', base: GRAPH.base, rework_limit: 0, tasks: [{ ...task('1', ['src/a.ts']), brief: 'Write it. 3 lines.' }, { ...task('2', ['src/b.ts'], blockers), brief: 'Build the menu.\nIt needs 1 merged first.' }] })
  const lines = (g) => problemsOf(g).filter((p) => /brief says/.test(p))
  expect(lines(plan([])).join() === 'task 2: brief says it needs 1 merged, but 1 is not a blocker', `plan: an unlisted wait gives ${lines(plan([]))}`)
  expect(lines(plan(['1'])).length === 0, 'plan: a listed wait is flagged')

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`wave-stale: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('wave-stale: 0 passed, 1 failed')
  process.exit(1)
})
