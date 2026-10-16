// tests/wave-stale.js - spec checks of the stale-brief guard (#295). Node, no packages.
// wave.js: a path a merge deleted (merge gone), a task a merge's notes absorbed, or a Files path missing
// at the start commit sends the brief back to a brief-writer, never to a worker on the stale brief.
// A brief that removes a symbol with callers outside its files escalates with no worker (#297), for a
// brief-writer's removes, a graph task's removes, or removes the check agent reads from a ready issue.
// A check agent that returns nothing: the brief check escalates; the path check marks the task unchecked.
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
  const still = await wave({ ...merged({ gone: ['src/f.ts'] }), ...rebriefB(['src/f.ts']), brief_check: (n, a, label) => (label === 'check b' ? { tasks: [{ task: 'b', missing: ['src/f.ts'], hits: [] }] } : a) })
  expect(labels(still).includes('brief b') && !labels(still).some((l) => l.startsWith('build b')), `still stale: b got a worker: ${labels(still)}`)
  // 2. The notes of a say it absorbed b: b re-briefs before any worker.
  const absorbed = await wave({ ...rebriefB(['src/g.ts']), report: (n, a, label) => (label === 'build a' ? { ...a, notes: 'Absorbed the work of task b.' } : a) })
  expect(before(absorbed, 'merge a', 'brief b') && before(absorbed, 'brief b', 'build b'), `absorbed: b was not re-briefed before its build: ${labels(absorbed)}`)

  // 2b. An id counts as absorbed only when the notes name it as a task (#299). z is built first; a, ui and x-1 wait on it.
  const six = { ...GRAPH, tasks: [task('z', ['src/z.ts']), task('a', ['src/a.ts'], ['z']), task('ui', ['src/ui.ts'], ['z']), task('x-1', ['src/x.ts'], ['z'])] }
  const notesOf = (notes) => wave({ report: (n, a, label) => (label === 'build z' ? { ...a, notes } : a) }, six)
  const rebriefed = (r, id) => labels(r).includes(`brief ${id}`)
  const prose = await notesOf('Absorbed a helper from the old module. Absorbed the ui work too.')
  expect(!rebriefed(prose, 'a') && !rebriefed(prose, 'ui') && labels(prose).includes('build a') && labels(prose).includes('build ui'), `prose ids: a plain word marked a task stale: ${labels(prose)}`)
  for (const [phrase, id] of [['Absorbed the work of `a`.', 'a'], ['It already did task a.', 'a'], ['It already did task #ui.', 'ui'], ['Absorbed "ui" fully.', 'ui'], ['Absorbed #a.', 'a'], ['Absorbed x-1 in full.', 'x-1']]) {
    const hit = await notesOf(phrase)
    expect(rebriefed(hit, id), `task reference: "${phrase}" did not re-brief ${id}: ${labels(hit)}`)
  }

  // 3. The path check: a blocker's file and a path the brief creates are not asked; a missing path re-briefs a.
  const fresh = await wave({})
  const pc = promptOf(fresh, 'path check')
  expect(pc.includes('- a at ') && pc.includes('- c at ') && /- c at [^\n]*src\/c\.ts($|\n)/.test(pc) && !/- c at [^\n]*src\/(a|new)\.ts/.test(pc), `path check: wrong paths asked:\n${pc}`)
  expect(!labels(fresh).some((l) => l.startsWith('brief ')), `path check: a task with all its paths got a brief-writer: ${labels(fresh)}`)
  const missing = await wave({ brief_check: (n, a, label) => (label === 'path check' ? { tasks: [{ task: 'a', missing: ['src/a.ts'], hits: [] }] } : a) })
  expect(before(missing, 'brief a', 'build a') && promptOf(missing, 'brief a').includes('src/a.ts'), `path check: a missing path did not re-brief a first: ${labels(missing)}`)

  // 4. plan.js problems: "needs 1 merged" with 1 not a blocker is a problem line; with 1 a blocker it is none.
  const src = fs.readFileSync(path.join(root, 'plugin', 'workflows', 'plan.js'), 'utf8')
  const block = src.slice(src.indexOf('// ---- contract: begin'), src.indexOf('// ---- contract: end'))
  const problemsOf = new Function('args', 'NEED_LABELS', `${block}\n${src.slice(src.indexOf('const problemsOf = '), src.indexOf('const escalate = '))}\nreturn problemsOf`)({}, {})
  const plan = (blockers) => ({ repo: 'x/y', branch: 'b', base: GRAPH.base, rework_limit: 0, tasks: [{ ...task('1', ['src/a.ts']), brief: 'Write it. 3 lines.' }, { ...task('2', ['src/b.ts'], blockers), brief: 'Build the menu.\nIt needs 1 merged first.' }] })
  const lines = (g) => problemsOf(g).filter((p) => /brief says/.test(p))
  expect(lines(plan([])).join() === 'task 2: brief says it needs 1 merged, but 1 is not a blocker', `plan: an unlisted wait gives ${lines(plan([]))}`)
  expect(lines(plan(['1'])).length === 0, 'plan: a listed wait is flagged')

  // 5. The caller check: a has no graph brief, so a brief-writer writes it; it renames A to B with no alias.
  const { brief: _, ...bare } = task('a', ['src/a.ts'])
  const lone = { ...GRAPH, tasks: [bare] }
  const renamed = (files, locked = []) => wave({
    brief: (n, a, label) => (label === 'brief a' ? { ...a, task: 'a', brief: 'Rename A to B.', files: ['src/a.ts'], oracle: { ...oracle('a'), files: locked }, removes: ['A'] } : a),
    brief_check: (n, a, label) => (label === 'check a' ? { tasks: [{ task: 'a', missing: [], hits: [{ symbol: 'A', files }] }] } : a),
  }, lone)
  const reasonOf = (r) => ((r.result.escalations || []).find((e) => e.task === 'a') || {}).reason || ''
  const outside = await renamed(['src/a.ts', 'src/other.ts'])
  expect(labels(outside).includes('check a') && !labels(outside).some((l) => l.startsWith('build a')), `callers: a caller outside the files got a worker: ${labels(outside)}`)
  expect(reasonOf(outside).includes('src/other.ts') && !reasonOf(outside).includes('locked'), `callers: the escalation does not name src/other.ts: ${reasonOf(outside)}`)
  const inside = await renamed(['src/a.ts'])
  expect(labels(inside).includes('build a') && !reasonOf(inside), `callers: a caller inside the files did not build: ${labels(inside)} ${reasonOf(inside)}`)
  const locked = await renamed(['test/a.test.ts'], ['test/a.test.ts'])
  expect(!labels(locked).some((l) => l.startsWith('build a')) && /locked oracle files: test\/a\.test\.ts/.test(reasonOf(locked)), `callers: a caller in a locked oracle file did not escalate: ${reasonOf(locked)}`)

  // 6. A ready issue body: no brief-writer runs, so the check agent reads what it removes from the brief.
  const READY = '## Outcome\nB replaces A.\n## Done when\nA is renamed to B, with no alias.\n## Files\nsrc/a.ts\n## Proof\nt a\n## Decisions\nnone'
  const readyHit = (hits) => H.run(file, { ...H.ARGS.wave, graph: lone, claims: 'solo', regression: undefined, issues: { a: READY } }, H.answerWith('wave', {
    brief_check: (n, a, label) => (label === 'check a' ? { tasks: [{ task: 'a', missing: [], hits }] } : a),
  }))
  const ready = await readyHit([{ symbol: 'A', files: ['src/a.ts', 'src/other.ts'] }])
  const ca = promptOf(ready, 'check a')
  expect(!labels(ready).includes('brief a') && ca.includes('removes: read them from the brief') && ca.includes('A is renamed to B, with no alias.'), `ready issue: the check agent did not get the brief to read removes from: ${labels(ready)}`)
  expect(!labels(ready).some((l) => l.startsWith('build a')) && reasonOf(ready).includes('src/other.ts'), `ready issue: a caller outside the files got a worker: ${labels(ready)} ${reasonOf(ready)}`)
  const readyClean = await readyHit([])
  expect(labels(readyClean).includes('build a'), `ready issue: no caller, but no worker: ${labels(readyClean)} ${reasonOf(readyClean)}`)
  // A graph brief with removes listed greps those, and does not ask the agent to read the brief.
  const listed = await wave({}, { ...GRAPH, tasks: [{ ...task('a', ['src/a.ts']), removes: ['A'] }] })
  expect(promptOf(listed, 'check a').includes('removes, grep on origin/') && !promptOf(listed, 'check a').includes('read them from the brief'), 'graph removes: the check agent was asked to read the brief')

  // 7. No answer from the check agents. The brief check escalates the task with no worker; the path check
  // of the Check phase marks the tasks unchecked and the wave goes on.
  const silent = await wave({ brief_check: (n, a, label) => (label === 'check a' ? null : a) }, lone)
  expect(!labels(silent).some((l) => l.startsWith('build a')) && reasonOf(silent).includes('the brief check returned nothing'), `null brief check: a got a worker: ${labels(silent)} ${reasonOf(silent)}`)
  const blind = await wave({ brief_check: (n, a, label) => (label === 'path check' ? null : a) })
  const row = (blind.result.tasks || []).find((t) => t.task === 'a') || {}
  expect(row.unchecked === 'paths' && labels(blind).includes('build a') && blind.logs.some((l) => /^a: unchecked: the path check returned nothing/.test(l)) && !blind.logs.some((l) => /no path is missing/.test(l)), `null path check: a is not marked unchecked: ${JSON.stringify(row.unchecked)} ${labels(blind)}`)

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
