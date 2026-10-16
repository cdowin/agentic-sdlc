// tests/spec-299-behaviour.js - mutation spec of tests/wave-prune.js and tests/wave-reach.js (#299). Node, no packages.
// Each mutation breaks 1 behaviour of a scratch copy of plugin/workflows/wave.js (a wrong call order, a row
// that records what a failed merge claims). The 2 test files, run against the copy, must exit 1: a check that
// observes the result rows or the order of agent calls catches it. The unmutated copy must pass. A mutation
// no test file catches is printed as a FAIL line. The scratch copy is removed at the end; the real wave.js is never edited.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')

const root = path.join(__dirname, '..')
const TESTS = ['tests/wave-prune.js', 'tests/wave-reach.js']
// [name, the text in wave.js, its replacement]: the numbers are the checks of the brief that must catch it.
const MUTATIONS = [
  ['3: a failed close fails the merge', "if (m.pruned) s.pruned = true", "if (m.pruned) s.pruned = true\n      if (!m.closed) return { ok: false, reason: 'the close failed' }"],
  ['3: a prune is recorded only with a close', 'if (m.pruned) s.pruned = true', 'if (m.pruned && m.closed) s.pruned = true'],
  ['2: a red merge records its lie', 's.merges.push(m)\n    if (!merged(m) && notTask', "s.merges.push(m)\n    if (m && !merged(m) && m.closed) { s.closedAt = m.at; s.pruned = Boolean(m.pruned) }\n    if (!merged(m) && notTask"],
  ['4: a rework merge moves closed_at', 'if (m.closed && !s.closedAt) s.closedAt = s.integratedAt', "if (m.closed) s.closedAt = '2026-01-01T00:00:00Z'"],
  ['5: no reopen of a closed task that is not merged', '.filter((id) => tasks[id].closedAt && tasks[id].state !== \'done\')', '.filter((id) => false)'],
  ['5: no reopen for a task with a rework round', "const toReopen = ids.filter((id) => tasks[id].closedAt && tasks[id].state !== 'done')", "const toReopen = ids.filter((id) => tasks[id].closedAt && tasks[id].state !== 'done' && tasks[id].rounds < 0)"],
  ['6: no step-up after a red first merge', 'if (!merged(m)) {\n      m = await call(id, prompt(true', 'if (false) {\n      m = await call(id, prompt(true'],
  ['7: a green merge steps up', 'if (!merged(m)) {\n      m = await call(id, prompt(true', 'if (true) {\n      m = await call(id, prompt(true'],
  ['8: a reach red is merged', ' && !(m.reach || []).some((x) => !x.passed))', ')'],
]

const run = (dir, file) => spawnSync('node', [path.join(dir, file)], { encoding: 'utf8', timeout: 120000 })
const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'spec-299-'))
try {
  for (const d of ['tests', 'plugin']) fs.cpSync(path.join(root, d), path.join(dir, d), { recursive: true })
  const wave = path.join(dir, 'plugin', 'workflows', 'wave.js')
  const original = fs.readFileSync(wave, 'utf8')
  for (const f of TESTS) {
    const r = run(dir, f)
    expect(r.status === 0, `${f}: fails on the unmutated wave.js: ${(r.stdout || '').trim().split('\n').pop()}`)
  }
  for (const [name, from, to] of MUTATIONS) {
    expect(original.includes(from), `mutation ${name}: the text to break is not in wave.js: wave.js changed, update this spec`)
    if (!original.includes(from)) continue
    fs.writeFileSync(wave, original.replace(from, () => to))
    const caught = TESTS.filter((f) => run(dir, f).status !== 0)
    expect(caught.length > 0, `mutation ${name}: no behaviour check of ${TESTS.join(' or ')} fails on it`)
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true })
}
for (const p of problems) console.log(`FAIL ${p}`)
console.log(`spec-299-behaviour: ${checks - problems.length} passed, ${problems.length} failed`)
process.exit(problems.length > 0 ? 1 : 0)
