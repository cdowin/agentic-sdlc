// tests/wave-setup.js - spec checks of wave args.setup (#261). Node, no packages.
// It runs plugin/workflows/wave.js under the stub harness of tests/workflows.js (run, ARGS, ANSWERS),
// loaded without its main(). Each prompt that makes a fresh worktree carries 1 setup line of its own,
// after the line that makes the worktree and before the first test, oracle, gate or regression command.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, ANSWERS, answerWith, waveOne, twoChains, claimUrl, problems }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'wave.js')
const SETUP_CMD = 't setup'
const SETUP = 'Run the setup command once in'

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const has = (r, label) => r.calls.some((c) => c.label === label)

// setupAt: the prompt of label has exactly 1 line with the setup sentence. That line names the command,
// holds no git command (an agent may paste a shell line whole), and sits after the first line holding
// after and before the first line holding before. Returns a problem, or '' when it holds.
function setupAt(r, label, after, before, more = []) {
  if (!has(r, label)) return `${label}: no such call (labels: ${r.calls.map((c) => c.label).join(', ')})`
  const ls = promptOf(r, label).split('\n')
  const at = ls.map((l, i) => (l.includes(SETUP) ? i : -1)).filter((i) => i >= 0)
  if (at.length !== 1) return `${label}: ${at.length} setup lines, not 1`
  const line = ls[at[0]]
  if (!line.includes(`: ${SETUP_CMD}.`) || /\bgit /.test(line)) return `${label}: the setup line does not name the command, or shares a line with a git command: ${line}`
  if (!line.includes('escalation')) return `${label}: the setup line does not say to report a failure in escalation: ${line}`
  for (const m of more) if (!line.includes(m)) return `${label}: the setup line does not name ${m}: ${line}`
  const a = ls.findIndex((l) => l.includes(after))
  const b = ls.findIndex((l) => l.includes(before))
  if (!(a >= 0 && a < at[0] && at[0] < b)) return `${label}: the setup line is not after "${after}" and before "${before}"`
  return ''
}
// nextLine: the line after the first line of the prompt of label that holds anchor.
function nextLine(r, label, anchor) {
  const ls = promptOf(r, label).split('\n')
  const i = ls.findIndex((l) => l.includes(anchor))
  return i >= 0 ? ls[i + 1] || '' : null
}
// throwsWith: the run with args throws an error that matches re.
async function throwsWith(args, re) {
  try {
    await H.run(file, args, H.ANSWERS.wave)
    return 'it did not throw'
  } catch (e) {
    return re.test(e.message) ? '' : `it threw "${e.message}"`
  }
}

async function main() {
  // 1. Every phase runs (ARGS.wave): each agent that makes a fresh worktree gets the setup line.
  const full = await H.run(file, { ...H.ARGS.wave, setup: SETUP_CMD }, H.ANSWERS.wave)
  const sites = [
    setupAt(full, 'build read', 'Make it first with this exact line', 'Run only the focused test'),
    setupAt(full, 'build write read', 'Make it first with this exact line', 'Run only the focused test'),
    setupAt(full, 'rework write 1', 'Make it first with this exact line', 'Run only the focused test'),
    setupAt(full, 'split write', '1. Cut branch', '2. The oracle of the whole task'),
    setupAt(full, 'merge read', 'is missing, make it', 'Otherwise, in it'),
    setupAt(full, 'regression base', 'worktree add --detach', 'run exactly: t scenario'),
    setupAt(full, 'regression head', 'worktree add --detach', 'run exactly: t scenario'),
    setupAt(full, 'oracle check', 'worktree add --detach', 'run the oracle command in list mode', ['oracle-<task>', 'oracle-base']),
  ].filter(Boolean)
  for (const s of sites) expect(false, `setup site: ${s}`)
  const mr = promptOf(full, 'merge read')
  // #281: the command is named twice, once before the merge (fresh worktree) and once again after it, before the oracle and gate.
  const AGAIN = 'Run the setup command again in'
  expect(mr.split(SETUP_CMD).length - 1 === 2 && mr.indexOf(SETUP) < mr.indexOf('git merge --no-ff --no-commit') && mr.indexOf('git merge --no-ff --no-commit') < mr.indexOf(AGAIN) && mr.indexOf(AGAIN) < mr.indexOf('Then run the gate'), 'merge read: the setup command is not named before the merge and again after it, before the gate')
  const readOnly = full.calls.filter((c) => /^(review|blast|skeptic|brief|remote)/.test(c.label) && c.prompt.includes(SETUP)).map((c) => c.label)
  expect(readOnly.length === 0, `a read-only agent got the setup command: ${readOnly}`)
  const logged = full.logs.filter((l) => l === `setup: ${SETUP_CMD}; each agent runs it once in each fresh worktree before any oracle, gate or regression command`)
  expect(logged.length === 1, `the run logs args.setup ${logged.length} times, not once with the pinned text`)

  // 2. 2 chains converge: the converge makes the wave worktree only when missing; Otherwise gets no setup.
  const chains = await H.run(file, { ...H.ARGS.wave, setup: SETUP_CMD, graph: H.twoChains, claims: Object.fromEntries(['a', 'b', 'docs'].map((id) => [id, H.claimUrl(id)])) }, H.ANSWERS.wave)
  const cv = setupAt(chains, 'converge', 'is missing, make it', 'Otherwise, in it')
  expect(!cv, `setup site: ${cv}`)
  const otherwise = (promptOf(chains, 'converge').split('\n').find((l) => l.includes('Otherwise, in it')) || '')
  expect(otherwise && !otherwise.includes(SETUP_CMD), `converge: the Otherwise line runs the setup: ${otherwise}`)

  // 3. A bad value refuses at Setup.
  for (const bad of [5, '', ' ']) {
    const why = await throwsWith({ ...H.ARGS.wave, ...H.waveOne, setup: bad }, /args\.setup must be a command string/)
    expect(!why, `setup ${JSON.stringify(bad)}: ${why}`)
  }

  // 4. No setup: no prompt or log names it, and each site keeps its old next line (no blank line added).
  const none = await H.run(file, { ...H.ARGS.wave, setup: undefined }, H.ANSWERS.wave)
  expect(none.calls.length > 0 && !none.calls.some((c) => /setup command/.test(c.prompt)) && !none.logs.some((l) => l.startsWith('setup:')), 'no setup: a prompt or the log names a setup command')
  const adj = [
    ['build read', 'Make it first with this exact line', /^git /],
    ['build read', 'git worktree add', /^Your files: /],
    ['split write', '1. Cut branch', /^2\. The oracle of the whole task/],
    ['merge read', 'is missing, make it', /^ {3}Otherwise, in it/],
    ['regression base', 'worktree add --detach', /^2\. In that worktree, run exactly/],
    ['regression head', 'worktree add --detach', /^2\. In that worktree, run exactly/],
    ['oracle check', 'worktree add --detach', /^2\. In that worktree, run the oracle command in list mode/],
  ]
  for (const [label, anchor, want] of adj) {
    const n = nextLine(none, label, anchor)
    expect(n !== null && want.test(n), `no setup: in ${label} the line after "${anchor}" is "${n}", not ${want}`)
  }
  for (const p of H.problems) expect(false, `harness: ${p}`)

  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`wave-setup: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('wave-setup: 0 passed, 1 failed')
  process.exit(1)
})
