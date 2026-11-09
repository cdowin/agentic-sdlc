// tests/merge-commit.js - the lander runs the fast check on a committed merge (#349). Node, no packages.
// It runs plugin/workflows/flow.js under the stub harness of tests/workflows.js. The stub
// lander does what the landing prompt says, in a real fixture repo: the merge of step 2, a commit the
// prompt asks for before step 4, the gate, then the commit or the reset of step 5. A gate that reads
// git status sees a staged merge as drift, so it is green only on a committed merge.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, problems }`)(require, __dirname)
const wf = (n) => path.join(__dirname, '..', 'plugin', 'workflows', `${n}.js`)

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'merge-commit-'))
const DRIFT = 'test -z "$(git status --porcelain)"'
const ENV = { ...process.env, GIT_AUTHOR_NAME: 't', GIT_AUTHOR_EMAIL: 't@t', GIT_COMMITTER_NAME: 't', GIT_COMMITTER_EMAIL: 't@t' }
const sh = (dir, c) => spawnSync('sh', ['-c', c], { cwd: dir, encoding: 'utf8', env: ENV })
const HOOK = path.join(__dirname, '..', 'plugin', 'hooks', 'git-denylist.sh')
// shGuarded: run c as the lander's Bash with the git-denylist hook active; a refused command is a problem and does not run.
function shGuarded(dir, c) {
  const h = spawnSync('sh', [HOOK], { cwd: dir, encoding: 'utf8', input: JSON.stringify({ tool_input: { command: c } }) })
  expect(h.status === 0, `the git-denylist hook refuses the red path command: ${c}: ${h.stderr.trim()}`)
  return h.status === 0 ? sh(dir, c) : h
}
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
const COMMIT = /git commit -q (?:--no-edit )?-m (["'])[^"']+\1/
// lander: run the landing prompt in dir, as a lander that follows it to the letter.
function lander(r, gate, prompt, a) {
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
    return { ...a, sha: out(r.dir, 'git rev-parse HEAD'), merged: true, check: { command: gate, line: 'ok', passed: true } }
  }
  const m = { ...a, merged: false, check: { command: gate, line: 'drift', passed: false }, escalation: 'drift' }
  if (/git checkout -q -f -B "\$\(git branch --show-current\)" <the pre-merge tip>/.test(red)) shGuarded(r.dir, `git checkout -q -f -B "$(git branch --show-current)" ${tip}`)
  else if (fs.existsSync(path.join(r.dir, '.git', 'MERGE_HEAD'))) sh(r.dir, 'git merge --abort')
  m.sha = out(r.dir, 'git rev-parse HEAD')
  return m
}

// The answers: the builder of issue 21 reports the fixture task commit; its landing runs in the repo.
const ISSUE = { issue: 21, state: 'open', parent: 20, group: '20-save', branch: '21-save', tier: 'judgment', blocked_by: [] }
const answers = (r, gate) => ({
  tracker: () => ({ at: '2026-10-08T12:00:00Z', issues: [ISSUE], groups: [] }),
  report: (n, a) => ({ ...a, sha: r.task }),
  landing: (n, a, label, prompt) => (label === 'land 21' && prompt.includes(`at ${r.task}, by that SHA`) ? lander(r, gate, prompt, a) : a),
})
const flow = (r, gate) => H.run(wf('flow'), { ...H.ARGS.flow, gate, base: { ref: 'main', sha: r.base }, queue: [21] }, H.answerWith('flow', answers(r, gate)))
const stateOf = (res, id) => ((res.result.issues || []).find((t) => String(t.issue) === id) || {}).state
const clean = (r, at) => out(r.dir, 'git rev-parse HEAD') === at && out(r.dir, 'git status --porcelain') === '' && !fs.existsSync(path.join(r.dir, '.git', 'MERGE_HEAD'))

async function main() {
  for (const [name, run, id] of [['flow', flow, '21']]) {
    // (a) A gate that fails on drift is green on a clean merge of a generated file: the merge is committed first.
    const g = repo(`${name}-green`, { 'gen.txt': 'v1\n' }, { 'gen.txt': 'v2\n' })
    const green = await run(g, DRIFT)
    const merge = out(g.dir, 'git rev-parse HEAD')
    expect(merge !== g.base && out(g.dir, 'git rev-parse HEAD^2') === g.task && out(g.dir, 'git status --porcelain') === '', `${name}: the merge of a generated file is not committed and clean: HEAD ${merge}`)
    expect(stateOf(green, id) === 'landed', `${name}: a drift gate is red on the staged merge: issue ${id} ${stateOf(green, id)}`)

    // (b) A red gate on the merge: the branch is reset to the pre-merge tip, nothing is left staged.
    const t = repo(`${name}-red`, { 'gen.txt': 'v1\n' }, { 'gen.txt': 'bad\n' })
    const taskGate = `${DRIFT} && ! grep -q bad gen.txt`
    const red = await run(t, taskGate)
    expect(clean(t, t.base), `${name}: a task red does not reset the branch to the pre-merge tip ${t.base}: HEAD ${out(t.dir, 'git rev-parse HEAD')}, status "${out(t.dir, 'git status --porcelain')}"`)
    expect(stateOf(red, id) === 'escalated', `${name}: a task red ends ${stateOf(red, id)}, not escalated`)

  }
  for (const p of H.problems) expect(false, `harness: ${p}`)
  fs.rmSync(tmp, { recursive: true, force: true })
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`${checks - problems.length}/${checks} checks pass`)
  process.exit(problems.length > 0 ? 1 : 0)
}
main().catch((e) => { console.log(`FAIL ${e.stack}`); process.exit(1) })
