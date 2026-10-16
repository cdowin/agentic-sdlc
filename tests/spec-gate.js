// tests/spec-gate.js - the repo gate of the plan Spec phase (#264). Node, no packages.
// Runs plugin/workflows/plan.js under a stub that answers by label, and check.js on spec values.
// args.gate: the spec agent runs the gate on its spec commit and reports { command, passed, line }.
// A red gate, a missing report or a report of another command gets 1 rewrite, then escalates.
// Prints 1 line per problem and the count of checks. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const os = require('os')
const path = require('path')
const { execFileSync } = require('child_process')
const { contract, check } = require('../plugin/contract/check.js')

const root = path.join(__dirname, '..')
const fixture = (n) => JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'contract', `${n}.json`), 'utf8'))
const SHA = '0123456789abcdef0123456789abcdef01234567'
const SPEC_SHA = 'fedcba9876543210fedcba9876543210fedcba98'
const ARGS = { goal: 10, repo: 'example/game', branch: '10-wave-1', base: { ref: 'main', sha: SHA } }
const ROUNDS = contract['x-limits'].spec_rounds
const RED = { command: 'make check', passed: false, line: 'comment budget: 3 over' }
const GREEN = { command: 'make check', passed: true }
// 1 task with an uncovered behaviour, so the Spec phase runs once for it.
const TASK = { id: 'art', title: 'Draw the title', outcome: 'The title has art.', done_when: ['t art passes'], area: 'art', tier: 'judgment', blockers: [], files: ['art/title.png'], oracle: { command: 't art', files: ['test/art.test.ts'], uncovered: ['the look'] } }
const SPEC = { ...fixture('spec.ok'), task: 'art', tests: ['test/art.spec.ts'], created: ['test/art.spec.ts'], keep: [], stubs: ['art/title.png'], command: 't art', uncovered: ['the look'], sha: SPEC_SHA }

let checks = 0
const problems = []
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
function NoClock() { throw new Error('Date.now() / new Date() are unavailable in workflow scripts') }
for (const k of ['now', 'parse', 'UTC']) NoClock[k] = NoClock

// run: plan.js with args over ARGS. spec(n, label) is the n-th spec answer (from 1). opts.tasks is the
// graph the architect drafts (each brief keeps its task's files, tier and oracle); opts.parallel the runtime's.
const ALL = (ts) => Promise.all(ts.map((t) => t()))
async function run(args, spec = () => SPEC, opts = {}) {
  const src = fs.readFileSync(path.join(root, 'plugin', 'workflows', 'plan.js'), 'utf8').replace(/^export /m, '')
  const tasks = opts.tasks || [TASK]
  const calls = []
  let n = 0
  const agent = async (prompt, o) => {
    calls.push({ prompt, ...o })
    if (/^architect/.test(o.label)) return { repo: ARGS.repo, branch: ARGS.branch, base: ARGS.base, rework_limit: 0, tasks }
    const t = tasks.find((x) => o.label === `brief-${x.id}`)
    if (t) return { task: t.id, brief: `Build ${t.id}.`, files: t.files, why: 'stub', tier: t.tier, oracle: t.oracle }
    if (/^spec-/.test(o.label)) return spec(++n, o.label)
    if (o.label === 'critic') return fixture('critique.ok')
    throw new Error(`no stub answer for ${o.label}`)
  }
  const AsyncFunction = (async () => {}).constructor
  const result = await new AsyncFunction('args', 'phase', 'agent', 'parallel', 'log', 'Date', src)({ ...ARGS, ...args }, () => {}, agent, opts.parallel || ALL, () => {}, NoClock)
  return { calls, result, specs: calls.filter((c) => /^spec-/.test(c.label)) }
}
// attempt: the run, or its error when it throws.
const attempt = (args, spec, opts) => run(args, spec, opts).catch((e) => ({ error: e }))
const escalated = (r, re) => r.result && r.result.status === 'escalated' && r.result.problems.some((p) => re.test(p))

// task(id, uncovered): a judgment task with its own files and oracle file. answer(id): its green spec,
// which pins all, so withSpec drops it to bounded.
const task = (id, uncovered = ['x']) => ({ ...TASK, id, title: `Build ${id}`, area: id, files: [`src/${id}.ts`], oracle: { command: `t ${id}`, files: [`test/${id}.test.ts`], uncovered } })
const idOf = (label) => label.replace(/^spec-/, '').replace(/-\d+$/, '')
const answer = (id) => ({ ...SPEC, task: id, tests: [`test/${id}.spec.ts`], created: [`test/${id}.spec.ts`], stubs: [`src/${id}.ts`], command: `t ${id}`, uncovered: [], sha: SPEC_SHA })
const SERIAL = async (ts) => { const out = []; for (const t of ts) out.push(await t()); return out }
const tick = (ms) => new Promise((ok) => setTimeout(ok, ms))

async function main() {
  // A red gate: 1 rewrite that names the red, then escalation.
  let r = await attempt({ gate: 'make check' }, () => ({ ...SPEC, gate: RED }))
  expect(!r.error, `red gate: plan threw ${r.error}`)
  if (!r.error) {
    expect(r.specs.length === 1 + ROUNDS && /repo gate failed[\s\S]*comment budget: 3 over/.test(r.specs[ROUNDS].prompt), `red gate: ${r.specs.length} spec calls, or the rewrite does not name the red gate`)
    expect(escalated(r, /spec: the repo gate failed/), 'red gate: the plan did not escalate a spec with a red gate')
  }

  // A red gate fixed in the rewrite: the spec passes and keeps its gate result.
  r = await attempt({ gate: 'make check' }, (n) => ({ ...SPEC, gate: n === 1 ? RED : GREEN }))
  expect(!r.error && r.specs.length === 2 && r.result.status !== 'escalated' && r.result.specs[0].gate.passed === true, `red then green gate: ${r.error || `${r.specs.length} spec calls, status ${r.result.status}`}`)

  // A green gate: 1 spec call; the prompt names the gate after the red step, steps stay numbered 1..n.
  r = await attempt({ gate: 'make check' }, () => ({ ...SPEC, gate: GREEN }))
  expect(!r.error, `green gate: plan threw ${r.error}`)
  if (!r.error) {
    const p = r.specs[0].prompt
    expect(r.specs.length === 1 && r.result.status !== 'escalated' && r.result.specs[0].gate.passed === true, `green gate: status ${r.result.status}, or specs[0] lost its gate result`)
    expect(p.includes('make check') && p.includes('repo gate') && p.indexOf('repo gate') > p.indexOf('red.failed true'), 'green gate: the spec prompt does not tell the agent to run the repo gate make check after the red step')
    expect(p.includes('keep rule') && p.includes('cut fresh'), 'green gate: the spec prompt lost its keep rule or cut fresh step')
    const steps = [...p.matchAll(/^(\d+)\. /gm)].map((m) => Number(m[1]))
    expect(steps.length === 12 && steps.every((s, i) => s === i + 1), `green gate: the spec prompt steps are ${steps.join(',')}, not 1 to 12`)
    expect(r.result.wave && !('gate' in r.result.wave), 'green gate: the wave args carry a gate (#261 owns wave args)')
    expect(r.specs[0].schema.properties.gate !== undefined, 'green gate: the spec schema of plan has no gate property, so the agent cannot report it')
  }

  // A spec that reports no gate, or another command, while the plan has a gate.
  r = await attempt({ gate: 'make check' })
  expect(!r.error && r.specs.length === 1 + ROUNDS && escalated(r, /did not report the gate result \(the plan has a gate: make check\)/), `no gate report: ${r.error || 'plan did not escalate'}`)
  r = await attempt({ gate: 'make check' }, () => ({ ...SPEC, gate: { command: 'make lint', passed: true } }))
  expect(!r.error && escalated(r, /the spec ran make lint, not the gate make check/), `other gate command: ${r.error || 'plan did not escalate'}`)

  // No args.gate: the prompt is unchanged and a spec with no gate passes; a reported red gate is still refused.
  r = await attempt({})
  expect(!r.error && !r.specs[0].prompt.includes('repo gate') && r.specs.length === 1 && r.result.status !== 'escalated', `no gate: ${r.error || 'the prompt names a repo gate, or the spec failed'}`)
  if (!r.error) expect([...r.specs[0].prompt.matchAll(/^(\d+)\. /gm)].length === 11, 'no gate: the spec prompt does not have its 11 steps')
  r = await attempt({}, () => ({ ...SPEC, gate: RED }))
  expect(!r.error && escalated(r, /repo gate failed/), `no gate, red gate reported: ${r.error || 'plan did not escalate'}`)

  // A bad args.gate ends the plan before any agent runs.
  for (const g of ['', ' ', 5, null]) {
    r = await attempt({ gate: g })
    expect(r.error && /args\.gate must be a non-empty command string/.test(r.error.message), `gate ${JSON.stringify(g)}: plan did not throw the args.gate error (${r.error ? r.error.message : 'no error'})`)
  }

  // check.js: shape and meaning of spec.gate, for the CLI that knows no gate.
  const red = { ...SPEC, gate: RED }
  const bad = check('spec', red)
  expect(bad.length === 1 && /repo gate failed on the spec commit[\s\S]*comment budget: 3 over/.test(bad[0]), `check spec, red gate: ${JSON.stringify(bad)}`)
  expect(check('spec', { ...SPEC, gate: GREEN }).length === 0 && check('spec', SPEC).length === 0, 'check spec: a green gate or no gate must pass')
  expect(check('spec', { ...SPEC, gate: { command: 'make check' } }).length > 0, 'check spec: a gate without passed must fail the shape')
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'spec-gate-'))
  try {
    fs.writeFileSync(path.join(tmp, 'red.json'), JSON.stringify(red))
    let code = 0
    try { execFileSync('node', [path.join(root, 'plugin', 'contract', 'check.js'), 'spec', path.join(tmp, 'red.json')], { stdio: 'pipe' }) } catch (e) { code = e.status }
    expect(code === 1, `check.js spec CLI: a red gate exits ${code}, not 1`)
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true })
  }

  // 4 spec tasks: all 4 spec agents start before any returns, and they return in reverse order.
  // A serial Spec phase never fills the barrier: each agent waits 50 ms, then returns, so the order shows it.
  const four = ['a', 'b', 'c', 'd'].map((id) => task(id))
  const events = []
  let started = 0
  let open
  const barrier = new Promise((ok) => { open = ok })
  r = await attempt({}, async (n, label) => {
    events.push(`start ${label}`)
    if (++started === 4) open()
    await Promise.race([barrier, tick(50)])
    await tick(10 * (4 - 'abcd'.indexOf(idOf(label))))
    events.push(`end ${label}`)
    return answer(idOf(label))
  }, { tasks: four })
  const serial = await attempt({}, (n, label) => answer(idOf(label)), { tasks: four, parallel: SERIAL })
  expect(!r.error && !serial.error, `4 spec tasks: plan threw ${r.error || serial.error}`)
  if (!r.error && !serial.error) {
    const firstEnd = events.findIndex((e) => e.startsWith('end'))
    expect(firstEnd === 4 && same(events.slice(0, 4).sort(), ['start spec-a', 'start spec-b', 'start spec-c', 'start spec-d']), `4 spec tasks: not all 4 spec agents started before one returned: ${events.join(', ')}`)
    expect(events[4] === 'end spec-d', `4 spec tasks: the stub did not return in reverse order: ${events.join(', ')}`)
    expect(r.result.status !== 'escalated' && same(r.result.graph.tasks, serial.result.graph.tasks), '4 spec tasks: the parallel graph differs from the serial graph')
    expect(same(r.result.graph.tasks.map((t) => `${t.id} ${t.tier} ${t.spec_sha}`), ['a', 'b', 'c', 'd'].map((id) => `${id} bounded ${SPEC_SHA}`)), `4 spec tasks: the graph is not 4 bounded tasks with spec_sha in task order: ${r.result.graph.tasks.map((t) => `${t.id} ${t.tier}`)}`)
    expect(same(r.result.specs, serial.result.specs) && same(r.result.specs.map((x) => `${x.task} ${x.tier_before} ${x.tier_after}`), ['a', 'b', 'c', 'd'].map((id) => `${id} judgment bounded`)), `4 spec tasks: specs are ${r.result.specs.map((x) => x.task)}, not a b c d in task order with their tiers`)
  }

  // A task whose uncovered entries are all feel: gets no spec agent and keeps its tier; feel: next to another entry does not.
  const feel = task('feel', ['feel: the jump arc'])
  r = await attempt({}, (n, label) => answer(idOf(label)), { tasks: [feel, task('other'), task('mixed', ['feel: a', 'x'])] })
  expect(!r.error, `feel task: plan threw ${r.error}`)
  if (!r.error) {
    expect(same(r.specs.map((c) => c.label), ['spec-other', 'spec-mixed']), `feel task: spec agents ran for ${r.specs.map((c) => c.label)}, not spec-other and spec-mixed`)
    const got = r.result.graph.tasks.find((t) => t.id === 'feel')
    expect(r.result.status !== 'escalated' && got.tier === 'judgment' && !('spec_sha' in got) && same(got.oracle, feel.oracle), `feel task: status ${r.result.status}, or the feel task changed: ${JSON.stringify(got)}`)
    expect(same(r.result.specs.map((x) => x.task), ['other', 'mixed']), `feel task: specs are for ${r.result.specs.map((x) => x.task)}, not other and mixed`)
    expect(r.specs[0].prompt.includes('starts with feel: is play feel: write no check for it'), 'feel task: the spec prompt does not tell the agent to skip feel: entries')
  }

  // 2 tasks whose spec stays red: every round runs for both, then 1 escalation names both.
  r = await attempt({}, (n, label) => ({ ...answer(idOf(label)), red: { line: '0 failed', failed: false } }), { tasks: [task('a'), task('b')] })
  expect(!r.error && r.specs.length === 2 * (1 + ROUNDS), `2 red specs: ${r.error || `${r.specs.length} spec calls, not ${2 * (1 + ROUNDS)}`}`)
  if (!r.error) {
    const ids = r.result.problems.map((p) => (p.match(/^task (\w+): spec: /) || [])[1])
    expect(r.result.status === 'escalated' && ids.includes('a') && ids.includes('b') && ids.every(Boolean) && ids.indexOf('a') < ids.indexOf('b') && r.result.specs.length === 0, `2 red specs: status ${r.result.status}, problems ${JSON.stringify(r.result.problems)}`)
  }

  // A failed chain does not drop the specs of the chains that passed: the escalation carries them, in task order.
  r = await attempt({}, (n, label) => (idOf(label) === 'b' ? { ...answer('b'), red: { line: '0 failed', failed: false } } : answer(idOf(label))), { tasks: [task('a'), task('b'), task('c')] })
  expect(!r.error, `1 of 3 red: plan threw ${r.error}`)
  if (!r.error) {
    expect(r.result.status === 'escalated' && r.result.problems.some((p) => /^task b: spec: /.test(p)), `1 of 3 red: status ${r.result.status}, problems ${JSON.stringify(r.result.problems)}`)
    expect(same(r.result.specs.map((x) => x.task), ['a', 'c']) && r.result.specs.every((x) => x.tier_before && x.tier_after), `1 of 3 red: specs are ${JSON.stringify(r.result.specs.map((x) => x.task))}, not a and c with tier_before and tier_after`)
  }

  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`spec-gate: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length ? 1 : 0)
}
main()
