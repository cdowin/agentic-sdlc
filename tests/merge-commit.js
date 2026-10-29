// tests/merge-commit.js - the integrator runs the gate on a committed merge (#349). Node, no packages.
// It runs plugin/workflows/wave.js and flow.js under the stub harness of tests/workflows.js. The stub
// integrator does what the merge prompt says, in a real fixture repo: the merge of step 2, a commit the
// prompt asks for before step 4, the gate, then the commit or the reset of step 5. A gate that reads
// git status sees a staged merge as drift, so it is green only on a committed merge.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, waveOne, flowTask, claimUrl, problems }`)(require, __dirname)
const wf = (n) => path.join(__dirname, '..', 'plugin', 'workflows', `${n}.js`)

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'merge-commit-'))
const DRIFT = 'test -z "$(git status --porcelain)"'
const ENV = { ...process.env, GIT_AUTHOR_NAME: 't', GIT_AUTHOR_EMAIL: 't@t', GIT_COMMITTER_NAME: 't', GIT_COMMITTER_EMAIL: 't@t' }
const sh = (dir, c) => spawnSync('sh', ['-c', c], { cwd: dir, encoding: 'utf8', env: ENV })
const out = (dir, c) => sh(dir, c).stdout.trim()

// repo(name, base, task): a repo with the files of base on main, and a task commit that writes task.
function repo(name, base, task) {
  const dir = path.join(tmp, name)
  fs.mkdirSync(dir)
  sh(dir, 'git init -q -b main')
  for (const [f, v] of Object.entries(base)) fs.writeFileSync(path.join(dir, f), v)
  sh(dir, 'git add -A && git commit -q -m base && git checkout -q -b task')
  for (const [f, v] of Object.entries(task)) fs.writeFileSync(path.join(dir, f), v)
  sh(dir, 'git add -A && git commit -q -m task && git checkout -q main')
  return { dir, base: out(dir, 'git rev-parse main'), task: out(dir, 'git rev-parse task') }
}

const stepOf = (p, n) => {
  const i = p.indexOf(`\n${n}. `)
  const j = p.indexOf(`\n${n + 1}. `, i + 1)
  return i < 0 ? '' : p.slice(i, j < 0 ? undefined : j)
}
const COMMIT = /git commit -q (?:--no-edit )?-m "[^"]+"/
// integrator: run the merge prompt in dir, as an integrator that follows it to the letter.
function integrator(r, gate, prompt, a) {
  const s2 = stepOf(prompt, 2)
  const s5 = stepOf(prompt, 5)
  const [green, red] = s5.split(/\n\s*Red/)
  const tip = out(r.dir, 'git rev-parse HEAD')
  const merge = (s2.match(/git merge --no-ff[^\n]*?[0-9a-f]{40}/) || [''])[0]
  sh(r.dir, merge)
  const early = (s2 + stepOf(prompt, 3)).match(COMMIT)
  if (early) sh(r.dir, early[0])
  if (sh(r.dir, gate).status === 0) {
    const late = !early && (green || '').match(COMMIT)
    if (late) sh(r.dir, late[0])
    return { ...a, sha: out(r.dir, 'git rev-parse HEAD'), oracle_passed: true }
  }
  const m = { ...a, oracle_passed: false, merged: [], escalation: 'drift', closed: false, pruned: false }
  if (/git reset (-q )?--hard HEAD\^1/.test(red)) sh(r.dir, 'git reset -q --hard HEAD^1')
  else if (/run git merge --abort, then run the gate/.test(red)) sh(r.dir, 'git merge --abort')
  if (sh(r.dir, gate).status !== 0) m.base_red = { kind: 'base', check: gate, line: 'drift', tip: out(r.dir, 'git rev-parse HEAD') }
  if (/git reset (-q )?--hard <the pre-merge tip>/.test(red)) sh(r.dir, `git reset -q --hard ${tip}`)
  else if (fs.existsSync(path.join(r.dir, '.git', 'MERGE_HEAD'))) sh(r.dir, 'git merge --abort')
  return m
}

// The answers: round 0 of the task reports the fixture task commit; its merges run in the repo.
const answers = (r, gate, first) => ({
  report: (n, a) => (a.round === 0 ? { ...a, sha: r.task } : a),
  merge: (n, a, label, prompt) => (label.startsWith(first) && prompt.includes(`at ${r.task}.`) ? integrator(r, gate, prompt, a) : a),
})
const wave = (r, gate) => H.run(wf('wave'), { ...H.ARGS.wave, ...H.waveOne, gate, regression: undefined, graph: { ...H.waveOne.graph, base: { ref: 'main', sha: r.base } } }, H.answerWith('wave', answers(r, gate, 'merge read')))
const flow = (r, gate) => H.run(wf('flow'), { ...H.ARGS.flow, max_load: undefined, gate, base: { ref: 'main', sha: r.base }, queue: [H.flowTask(21, 20, '20-save', 'src/save.ts')], claims: { 21: H.claimUrl('21') } }, H.answerWith('flow', answers(r, gate, 'merge 21')))
const stateOf = (res, id) => ((res.result.tasks || []).find((t) => String(t.task) === id) || {}).state
const clean = (r, at) => out(r.dir, 'git rev-parse HEAD') === at && out(r.dir, 'git status --porcelain') === '' && !fs.existsSync(path.join(r.dir, '.git', 'MERGE_HEAD'))

async function main() {
  for (const [name, run, id] of [['wave', wave, 'read'], ['flow', flow, '21']]) {
    // (a) A gate that fails on drift is green on a clean merge of a generated file: the merge is committed first.
    const g = repo(`${name}-green`, { 'gen.txt': 'v1\n' }, { 'gen.txt': 'v2\n' })
    const green = await run(g, DRIFT)
    const merge = out(g.dir, 'git rev-parse HEAD')
    expect(merge !== g.base && out(g.dir, 'git rev-parse HEAD^2') === g.task && out(g.dir, 'git status --porcelain') === '', `${name}: the merge of a generated file is not committed and clean: HEAD ${merge}`)
    expect(stateOf(green, id) !== 'escalated', `${name}: a drift gate is red on the staged merge: task ${id} ${stateOf(green, id)}`)

    // (b) A red gate on the merge: the branch is reset to the pre-merge tip, nothing is left staged.
    const t = repo(`${name}-red`, { 'gen.txt': 'v1\n' }, { 'gen.txt': 'bad\n' })
    const taskGate = `${DRIFT} && ! grep -q bad gen.txt`
    const red = await run(t, taskGate)
    expect(clean(t, t.base), `${name}: a task red does not reset the branch to the pre-merge tip ${t.base}: HEAD ${out(t.dir, 'git rev-parse HEAD')}, status "${out(t.dir, 'git status --porcelain')}"`)
    expect(stateOf(red, id) === 'escalated', `${name}: a task red ends ${stateOf(red, id)}, not escalated`)

    // (c) The gate is red on the pre-merge tip too: base red. The branch ends at the first-parent tip.
    const b = repo(`${name}-base`, { 'gen.txt': 'bad\n', 'x.txt': '1\n' }, { 'x.txt': '2\n' })
    const base = await run(b, taskGate)
    expect(clean(b, b.base), `${name}: a base red does not reset the branch to the first-parent tip ${b.base}: HEAD ${out(b.dir, 'git rev-parse HEAD')}`)
    const holds = base.result.base_red || base.result.holds || []
    expect(stateOf(base, id) !== 'done' && JSON.stringify(holds).includes(b.base), `${name}: a base red is not held at the tip ${b.base}: ${stateOf(base, id)} ${JSON.stringify(holds)}`)
  }
  for (const p of H.problems) expect(false, `harness: ${p}`)
  fs.rmSync(tmp, { recursive: true, force: true })
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`${checks - problems.length}/${checks} checks pass`)
  process.exit(problems.length > 0 ? 1 : 0)
}
main().catch((e) => { console.log(`FAIL ${e.stack}`); process.exit(1) })
