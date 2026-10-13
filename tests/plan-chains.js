// tests/plan-chains.js - the graph check of plan.js and wave.js gives one verdict on the same graph.
// Two tasks in two chains may edit one file (they build on two branches); two unchained tasks may not.
// It runs problemsOf of plan.js and the same meaning that wave.js holds. Node, no packages.
// Prints 1 line per problem and the count of checks. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')
const { check } = require('../plugin/contract/check.js')

const root = path.join(__dirname, '..')
const problems = []
const expect = (ok, msg) => { if (!ok) problems.push(msg) }
const SHA = '0123456789abcdef0123456789abcdef01234567'
const task = (id, chain) => ({ id, title: id, outcome: id, done_when: ['t'], area: 'a', tier: 'judgment', blockers: [], files: ['src/shared.ts'], ...(chain && { chain }), oracle: { command: 't', files: [`test/${id}.ts`], uncovered: ['layout'] } })
const graph = (a, b) => ({ repo: 'x/y', branch: 'b', base: { ref: 'main', sha: SHA }, rework_limit: 0, tasks: [task('one', a), task('two', b)] })
const PARALLEL = /run in parallel and both edit/

// problemsOf: cut from plan.js, so the test runs the function the workflow runs, over its own contract block.
function planProblems(g) {
  const src = fs.readFileSync(path.join(root, 'plugin', 'workflows', 'plan.js'), 'utf8')
  const block = src.slice(src.indexOf('// ---- contract: begin'), src.indexOf('// ---- contract: end'))
  const from = src.indexOf('const problemsOf = ')
  const to = src.indexOf('const escalate = ')
  expect(from > 0 && to > from, 'plan.js: problemsOf not found')
  const body = src.slice(from, to).replace(/^const problemsOf/, 'return ((problemsOf)')
  const fn = new Function('args', 'NEED_LABELS', `${block.replace(/^export /gm, '')}\n${src.slice(from, to)}\nreturn problemsOf`)
  return fn({}, {})(g)
}

const cases = [
  ['two chains, one file', graph('x', 'y'), false],
  ['one chain, one file', graph('x', 'x'), false],
  ['no chain, one file', graph(), true],
]
for (const [name, g, flagged] of cases) {
  let got
  try { got = planProblems(g) } catch (e) { got = [`threw: ${e.message}`] }
  expect(got.some((p) => PARALLEL.test(p)) === flagged, `plan problemsOf, ${name}: ${flagged ? 'must flag' : 'must not flag'} the parallel overlap; got ${JSON.stringify(got)}`)
  // wave and the contract check hold the same meaning.
  expect(check('graph', g).some((p) => PARALLEL.test(p)) === flagged, `check graph, ${name}: ${flagged ? 'must flag' : 'must not flag'} the parallel overlap`)
}
for (const p of problems) console.log(p)
console.log(`${cases.length * 2} checks, ${problems.length} problems`)
process.exit(problems.length ? 1 : 0)
