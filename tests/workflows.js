// tests/workflows.js - run each workflow of plugin/workflows/ under a stub harness. Node, no packages.
// Each agent() call must pass a schema equal to a $defs shape of the contract, and its model and
// agent type must come from the runtime profile. The stub answers each call with
// tests/fixtures/contract/<shape>.ok.json. Each workflow runs 3 times:
//   1. with no args.runtime: the spawns must equal run 2, so the Claude default matches runtimes.json;
//   2. with runtimes.json "claude": each agent type must be an agent file with a tools: line;
//   3. with a probe runtime: each model and effort are the tier that x-roles (or x-first-try) gives the
//      role, and no prompt names the Claude worktree root.
// Each workflow holds a generated contract block: the x- keys of the contract, the shared blocks of
// check.js and the Claude profile of runtimes.json. The test fails when the block drifts;
// `node tests/workflows.js --write` writes it again.
// Prints 1 line per problem and the count of checks. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')
const { contract, check } = require('../plugin/contract/check.js')

const root = path.join(__dirname, '..')
const fixtures = path.join(__dirname, 'fixtures', 'contract')
const runtimes = JSON.parse(fs.readFileSync(path.join(root, 'plugin', 'contract', 'runtimes.json'), 'utf8'))
const checkSrc = fs.readFileSync(path.join(root, 'plugin', 'contract', 'check.js'), 'utf8')
const WRITE = process.argv.includes('--write')
// The workflows that run the graph checks, so their block holds the shared meaning of check.js.
const MEANING = ['plan', 'wave']
// The workflows with their own schemas and no contract block. tests/doc-sdlc.js runs them.
const OWN_TESTS = ['doc-sdlc']
const BLOCK_BEGIN = '// ---- contract: begin'
const BLOCK_END = '// ---- contract: end'
const ROLES = contract['x-roles']
const FIRST_TRY = contract['x-first-try']
const PROBE = 'probe'
const PROBE_EFFORT = { bounded: 'low', judgment: 'medium', lead: 'high' }
const probe = {
  provider: PROBE,
  tiers: Object.fromEntries(Object.keys(contract['x-tiers']).map((t) => [t, { model: `${PROBE}-${t}`, effort: PROBE_EFFORT[t] }])),
  worktree_root: `${PROBE}-worktrees`,
  agent_types: Object.fromEntries(Object.keys(ROLES).map((r) => [r, `${PROBE}-${r}`])),
  concurrency: 1,
  capabilities: {},
}
const SHA = '0123456789abcdef0123456789abcdef01234567'
const BASE = { ref: 'main', sha: SHA }
const claimUrl = (id) => `https://github.com/example/game/issues/1#issuecomment-${id.length}${id.charCodeAt(0)}`
// The plan the architect stub returns. The brief of save recommends a lower tier (the plan keeps
// judgment); the brief of art recommends a higher tier (the plan raises it).
const PLAN_TASKS = [
  { id: 'save', title: 'Save the game', outcome: 'A save round-trips.', done_when: ['t save passes'], area: 'save', tier: 'judgment', blockers: [], files: ['src/save.ts'], oracle: { command: 't save', files: ['test/save.test.ts'], uncovered: [] } },
  { id: 'art', title: 'Draw the title', outcome: 'The title screen has art.', done_when: ['t art passes', 'the lead approves the look'], area: 'art', tier: 'bounded', blockers: ['save'], files: ['art/title.png'], needs: ['image_generation'], split: ['logo', 'sky'], oracle: { command: 't art', files: ['test/art.test.ts'], uncovered: [] } },
]
const PLAN_BRIEFS = {
  save: { tier: 'bounded', oracle: PLAN_TASKS[0].oracle },
  art: { tier: 'judgment', oracle: { ...PLAN_TASKS[1].oracle, uncovered: ['the look'] } },
}
const planGraph = (tasks) => ({ repo: 'x/y', branch: 'b', base: BASE, rework_limit: 0, tasks })
const CYCLE = planGraph(PLAN_TASKS.map((t) => ({ ...t, blockers: [PLAN_TASKS.find((o) => o.id !== t.id).id] })))
// The args each workflow needs to run every phase. A new workflow adds its args here.
const ARGS = {
  split: { issue: 1, branch: '1-x', base: 'main', parts: ['read', { name: 'write', test: 't -k write' }], test: 't' },
  plan: { goal: 10, repo: 'example/game', branch: '10-wave-1', base: BASE },
  'review-batch': { results: [{ id: 'read', diff: 'a..b', test: 't' }, { id: 'write', diff: 'a..c', test: 't' }] },
  // The task ids match the ids review.ok.json scores, so its major finding sends write to rework
  // until the rework limit. art needs a capability no test runtime has; menu waits on art. The
  // worker of hud escalates. docs has no claim.
  wave: {
    gate: 'make check',
    claims: Object.fromEntries(['read', 'write', 'art', 'menu', 'hud'].map((id) => [id, claimUrl(id)])),
    graph: {
      repo: 'example/game', parent: 10, branch: '10-wave-1', base: BASE, rework_limit: 2,
      tasks: [
        { id: 'read', issue: 11, tier: 'bounded', blockers: [], files: ['src/read.ts'], brief: 'Read a save.', oracle: { command: 't read', files: ['test/read.test.ts'], uncovered: [] } },
        { id: 'write', issue: 12, tier: 'bounded', blockers: ['read'], files: ['src/write.ts'], split: ['enc', 'io'], oracle: { command: 't write', files: ['test/write.test.ts'], uncovered: [] } },
        { id: 'art', issue: 13, tier: 'judgment', blockers: [], files: ['art/x.png'], needs: ['image_generation'], oracle: { command: 't art', files: [], uncovered: ['the look'] } },
        { id: 'menu', issue: 14, tier: 'judgment', blockers: ['art'], files: ['src/menu.ts'], oracle: { command: 't menu', files: [], uncovered: ['layout'] } },
        { id: 'hud', issue: 15, tier: 'judgment', blockers: [], files: ['src/hud.ts'], oracle: { command: 't hud', files: [], uncovered: ['layout'] } },
        { id: 'docs', issue: 16, tier: 'judgment', blockers: [], files: ['docs/x.md'], oracle: { command: 't docs', files: [], uncovered: ['tone'] } },
      ],
    },
  },
}
// checkResult: the metrics rows and phase changes a workflow returns are contract values, and each
// task's changes form 1 chain from planned.
function checkResult(name, args, result) {
  const limit = args.graph ? args.graph.rework_limit : undefined
  for (const m of result.metrics || []) {
    const bad = check('metrics', m)
    expect(bad.length === 0, `${name}: metrics row ${m.task}: ${bad.join('; ')}`)
  }
  const state = {}
  for (const t of result.transitions || []) {
    const bad = check('transition', t, limit === undefined ? {} : { limit })
    expect(bad.length === 0, `${name}: transition of ${t.task}: ${bad.join('; ')}`)
    expect((state[t.task] || 'planned') === t.from, `${name}: ${t.task} moves from ${t.from}, but it is ${state[t.task] || 'planned'}`)
    state[t.task] = t.to
  }
}

let checks = 0
const problems = []
const expect = (ok, msg) => {
  checks++
  if (!ok) problems.push(msg)
}
const canon = (v) =>
  Array.isArray(v) ? v.map(canon) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])])) : v
const same = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b))
// inline: a $defs shape with each $ref replaced by its target, as a workflow must copy it.
const inline = (v) =>
  Array.isArray(v) ? v.map(inline) : v && typeof v === 'object'
    ? v.$ref ? inline(contract.$defs[v.$ref.replace('#/$defs/', '')]) : Object.fromEntries(Object.entries(v).map(([k, x]) => [k, inline(x)]))
    : v
const shapeOf = (schema) => Object.keys(contract.$defs).find((d) => same(inline(contract.$defs[d]), schema))

// between: the lines of src after the line `${begin}` and before the line `${end}`.
function between(src, begin, end) {
  const i = src.indexOf(`${begin}\n`)
  const j = src.indexOf(`${end}\n`, i)
  if (i < 0 || j < 0) throw new Error(`no ${begin} ... ${end} block`)
  return src.slice(i + begin.length + 1, j)
}
// lines: an object literal with 1 key per line.
const lines = (o) => `{\n${Object.entries(o).map(([k, v]) => `  ${JSON.stringify(k)}: ${JSON.stringify(v)},`).join('\n')}\n}`
// block: the generated contract block of a workflow, without its 2 marker lines.
function block(name) {
  const xs = Object.fromEntries(Object.entries(contract).filter(([k]) => k.startsWith('x-')))
  const c = runtimes.claude
  const claude = {
    provider: c.provider,
    tiers: Object.fromEntries(Object.entries(c.tiers).map(([t, s]) => [t, { model: s.model, ...(s.effort && { effort: s.effort }) }])),
    worktree_root: c.worktree_root,
    agent_types: c.agent_types,
    capabilities: Object.fromEntries(Object.entries(c.capabilities).map(([n, x]) => [n, { status: x.status }])),
  }
  return [
    '// Generated from plugin/contract by node tests/workflows.js --write. Do not edit.',
    `const contract = ${lines(xs)}`,
    between(checkSrc, '// ---- shared: begin', '// ---- shared: end').trimEnd(),
    ...(MEANING.includes(name) ? [between(checkSrc, '// ---- shared meaning: begin', '// ---- shared meaning: end').trimEnd()] : []),
    '// The Claude profile: runtimes.json "claude" without the evidence. The default of args.runtime.',
    `const CLAUDE_RUNTIME = ${lines(claude)}`,
    '',
  ].join('\n')
}
// syncBlock: check the contract block of a workflow file, or write it with --write.
function syncBlock(name, file) {
  const src = fs.readFileSync(file, 'utf8')
  let got
  try {
    got = between(src, BLOCK_BEGIN, BLOCK_END)
  } catch (e) {
    return expect(false, `${name}: ${e.message}`)
  }
  const want = block(name)
  if (WRITE && got !== want) fs.writeFileSync(file, src.replace(`${BLOCK_BEGIN}\n${got}${BLOCK_END}\n`, `${BLOCK_BEGIN}\n${want}${BLOCK_END}\n`))
  else expect(got === want, `${name}: its contract block drifts from plugin/contract; run node tests/workflows.js --write`)
}

const fixture = (def) => JSON.parse(fs.readFileSync(path.join(fixtures, `${def}.ok.json`), 'utf8'))
// stubAnswer: the fixture of the shape. A report names the task, round and branch the prompt asks for.
const REPORT_ASK = /Report task (\S+), round (\d+), branch (\S+?),/
function stubAnswer(def, prompt) {
  const a = fixture(def)
  const m = def === 'report' && prompt.match(REPORT_ASK)
  return m ? { ...a, task: m[1], round: Number(m[2]), branch: m[3] } : a
}
// The stub answers of a workflow that needs more than the fixtures: (def, prompt, label) -> answer.
const ANSWERS = {
  wave: (def, prompt, label) => {
    if (label === 'build hud') return { ...stubAnswer(def, prompt), status: 'escalated', escalation: 'Which font?', test: { command: 't hud', line: 'skipped', passed: false } }
    // A brief keeps its task's own files and oracle, so the second file check passes.
    const t = def === 'brief' && ARGS.wave.graph.tasks.find((x) => label === `brief ${x.id}`)
    return t ? { ...stubAnswer(def, prompt), files: t.files, oracle: t.oracle } : stubAnswer(def, prompt)
  },
  plan: (def, prompt, label) => {
    if (def === 'graph') return planGraph(PLAN_TASKS)
    if (def !== 'brief') return stubAnswer(def, prompt)
    const t = PLAN_TASKS.find((x) => label === `brief-${x.id}`)
    return { task: t.id, brief: `Build ${t.id}.`, files: t.files, why: 'stub', ...PLAN_BRIEFS[t.id] }
  },
}
// answerWith: the answers of a workflow with some shapes replaced. A function value takes the call count.
function answerWith(name, over) {
  const n = {}
  return (def, prompt, label) => {
    n[def] = (n[def] || 0) + 1
    const o = over[def]
    if (o === undefined) return (ANSWERS[name] || stubAnswer)(def, prompt, label)
    return typeof o === 'function' ? o(n[def], (ANSWERS[name] || stubAnswer)(def, prompt, label)) : o
  }
}

async function run(file, args, answer = stubAnswer) {
  const src = fs.readFileSync(file, 'utf8').replace(/^export /m, '')
  const AsyncFunction = (async () => {}).constructor
  const calls = []
  const agent = async (prompt, opts) => {
    const def = shapeOf(opts.schema)
    if (!def) {
      calls.push({ prompt, ...opts })
      problems.push(`agent ${opts.label}: its schema is no contract shape`)
      throw new Error(`agent ${opts.label}: its schema is no contract shape`)
    }
    const a = answer(def, prompt, opts.label)
    calls.push({ prompt, ...opts, def, answer: a })
    return a
  }
  const parallel = (thunks) => Promise.all(thunks.map((t) => t()))
  const result = await new AsyncFunction('args', 'phase', 'agent', 'parallel', 'log', src)(args, () => {}, agent, parallel, () => {})
  return { calls, result }
}

// taskIs: the wave left task id in state, and its reason matches why (when given).
function taskIs(name, result, id, state, why) {
  const t = (result.tasks || []).find((x) => x.task === id)
  const e = (result.escalations || []).find((x) => x.task === id)
  expect(t && t.state === state, `${name}: task ${id} ends ${t && t.state}, not ${state}`)
  if (why) expect(e && why.test(e.reason), `${name}: task ${id} stops for "${e && e.reason}", not ${why}`)
}
const labels = (r) => r.calls.map((c) => c.label)
// OUTCOMES: what each run of a workflow on its ARGS must end with.
const OUTCOMES = {
  wave: (r, args) => {
    const res = r.result
    taskIs('wave', res, 'read', 'done')
    taskIs('wave', res, 'write', 'escalated', new RegExp(`stand after ${args.graph.rework_limit} rework rounds`))
    taskIs('wave', res, 'art', 'escalated', /needs image_generation/)
    taskIs('wave', res, 'menu', 'planned', /blocker art/)
    taskIs('wave', res, 'hud', 'escalated', /escalated: Which font\?/)
    taskIs('wave', res, 'docs', 'planned', /no claim/)
    const write = res.tasks.find((t) => t.task === 'write')
    expect(write.rounds === args.graph.rework_limit, `wave: write has ${write.rounds} rework rounds, not ${args.graph.rework_limit}`)
    expect(write.tier === 'judgment', `wave: the brief of write raises bounded to judgment, but it runs at ${write.tier}`)
    expect(!labels(r).some((l) => / (menu|docs)\b/.test(l)), 'wave: a task that never starts spawned an agent')
    const claimed = res.transitions.filter((t) => t.to === 'claimed')
    expect(same(claimed.map((t) => t.task).sort(), ['hud', 'read', 'write']), `wave: claimed ${claimed.map((t) => t.task)}, not hud, read and write`)
    for (const t of claimed) expect(t.reason === args.claims[t.task], `wave: the claim of ${t.task} does not name its claim URL`)
    expect(same(res.done, ['read']), `wave: done is ${res.done}, not read`)
  },
  plan: (r) => {
    const res = r.result
    expect(res.status === 'gaps', `plan: status ${res.status}, not gaps when the critic lists a gap`)
    expect(same(res.missing, fixture('critique').missing), 'plan: missing is not the critic list')
    expect(check('graph', res.graph).length === 0, `plan: the graph is not valid: ${check('graph', res.graph)}`)
    const tier = Object.fromEntries(res.graph.tasks.map((t) => [t.id, t.tier]))
    expect(tier.save === 'judgment', `plan: a brief may not lower save to ${tier.save}`)
    expect(tier.art === 'judgment', `plan: a brief raises art to judgment, not ${tier.art}`)
    const art = res.issues.find((i) => i.task === 'art')
    expect(art && same(art.labels, ['area:art', contract['x-need-labels'].image_generation]), `plan: art labels ${art && art.labels}`)
    for (const want of ['Parent: #10', 'Outcome: The title screen has art.', '- [ ] t art passes', 'Oracle: `t art`', 'Blocked by tasks: save.', 'Split into parts: logo, sky.']) {
      expect(art && art.body.includes(want), `plan: the art issue body has no "${want}"`)
    }
    expect(res.issues.length === res.graph.tasks.length, 'plan: 1 issue draft per task')
    expect(res.wave && res.wave.graph === res.graph && same(res.wave.claims, {}), 'plan: wave args are the graph and empty claims')
    expect(same(labels(r).filter((l) => l.startsWith('architect')), ['architect']), 'plan: a good first draft needs no redraft')
  },
}
// SCENARIOS: extra runs with some stub answers replaced, and what each must end with.
const waveOne = { graph: { ...ARGS.wave.graph, tasks: ARGS.wave.graph.tasks.slice(0, 1) }, claims: { read: claimUrl('read') } }
const refuse = (patch, why) => ({
  args: waveOne,
  answers: { report: (n, a) => ({ ...a, ...patch }) },
  check: (r) => taskIs('wave', r.result, 'read', 'escalated', why),
})
const SCENARIOS = {
  wave: {
    'escalated report': refuse({ status: 'escalated', escalation: 'Which save?' }, /escalated: Which save\?/),
    'report of another task': refuse({ task: 'other' }, /names task other/),
    'report of another branch': refuse({ branch: 'other' }, /names branch other/),
    'short SHA': refuse({ sha: '0123abc' }, /not a full SHA/),
    'red test': refuse({ test: { command: 't', line: '1 failed', passed: false } }, /focused test is red: 1 failed/),
    'brief widens into a parallel task': {
      args: { graph: { ...ARGS.wave.graph, tasks: ARGS.wave.graph.tasks.filter((t) => t.id === 'hud' || t.id === 'docs') }, claims: { hud: claimUrl('hud'), docs: claimUrl('docs') } },
      answers: { brief: (n, a) => ({ ...a, files: n === 1 ? ['docs/x.md'] : a.files }) },
      check: (r) => expect((r.result.escalations || []).some((e) => /run in parallel and both edit docs\/x\.md/.test(e.reason)), 'wave: a brief that widens into a parallel task passed the file check'),
    },
    'no claims': {
      args: { ...waveOne, claims: {} },
      check: (r) => {
        taskIs('wave', r.result, 'read', 'planned', /no claim/)
        expect(r.calls.length === 0, 'wave: an unclaimed task spawned an agent')
      },
    },
  },
  plan: {
    'redraft a bad graph': {
      answers: { graph: (n) => (n === 1 ? CYCLE : planGraph(PLAN_TASKS)) },
      check: (r) => {
        const arch = r.calls.filter((c) => c.def === 'graph')
        expect(arch.length === 2, `plan: ${arch.length} architect calls, not 2`)
        expect(arch[1] && /failed these checks[\s\S]*blocker cycle/.test(arch[1].prompt), 'plan: the redraft prompt does not name the failed check')
        expect(r.result.status === 'gaps', `plan: status ${r.result.status} after a good redraft`)
      },
    },
    'graph still bad after the redrafts': {
      answers: { graph: CYCLE },
      check: (r) => {
        expect(r.calls.filter((c) => c.def === 'graph').length === contract['x-limits'].rework_rounds + 1, 'plan: wrong count of redrafts')
        expect(r.result.status === 'escalated' && r.result.problems.some((p) => /blocker cycle/.test(p)), 'plan: a bad graph must escalate with its problems')
        expect(r.result.issues.length === 0 && !r.result.wave, 'plan: an escalated plan returns no issue drafts and no wave args')
        expect(!r.calls.some((c) => c.def === 'brief'), 'plan: a bad graph must not reach the brief-writers')
      },
    },
    'issue text missing': {
      answers: { graph: () => planGraph(PLAN_TASKS.map(({ title, ...t }) => t)) },
      check: (r) => expect(r.result.status === 'escalated' && r.result.problems.some((p) => /title is empty/.test(p)), 'plan: a task with no title must escalate'),
    },
    'complete plan': {
      answers: { critique: { complete: true, missing: [] } },
      check: (r) => expect(r.result.status === 'done' && r.result.missing.length === 0, `plan: status ${r.result.status} when the critic finds no gap`),
    },
  },
}

async function main() {
  const files = fs.readdirSync(path.join(root, 'plugin', 'workflows')).filter((f) => f.endsWith('.js'))
  for (const f of files) {
    const name = f.replace(/\.js$/, '')
    if (OWN_TESTS.includes(name)) continue
    const file = path.join(root, 'plugin', 'workflows', f)
    syncBlock(name, file)
    const args = ARGS[name]
    expect(args, `${name}: tests/workflows.js has no ARGS for it`)
    if (!args) continue
    let byDefault, byClaude, byProbe
    try {
      const answer = ANSWERS[name] || stubAnswer
      byDefault = await run(file, args, answer)
      byClaude = await run(file, { ...args, runtime: runtimes.claude }, answer)
      byProbe = await run(file, { ...args, runtime: probe }, answer)
    } catch (e) {
      expect(false, `${name}: ${e.message}`)
      continue
    }
    expect(byDefault.calls.length > 0, `${name}: made no agent call`)
    const spawns = (r) => r.calls.map((c) => `${c.label} ${c.agentType} ${c.model} ${c.effort} ${c.prompt}`)
    expect(same(spawns(byDefault), spawns(byClaude)), `${name}: its Claude default differs from runtimes.json claude`)
    for (const c of byClaude.calls) {
      expect(String(c.agentType).startsWith('agentic-sdlc:'), `${name} ${c.label}: agent type ${c.agentType} lacks the plugin prefix, so an installed plugin cannot find it`)
      const agentFile = path.join(root, 'plugin', 'agents', `${String(c.agentType).replace(/^agentic-sdlc:/, '')}.md`)
      const head = fs.existsSync(agentFile) ? fs.readFileSync(agentFile, 'utf8').split('\n---')[0] : ''
      expect(/^tools: /m.test(head), `${name} ${c.label}: agent type ${c.agentType} has no agent file with a tools: line`)
    }
    for (const c of byProbe.calls) {
      const role = String(c.agentType).replace(`${PROBE}-`, '')
      expect(role in ROLES, `${name} ${c.label}: agent type ${c.agentType} is not from the runtime`)
      const tiers = role === 'worker' ? Object.keys(probe.tiers) : [ROLES[role], ...(role in FIRST_TRY ? [FIRST_TRY[role]] : [])]
      const tier = tiers.find((t) => c.model === probe.tiers[t].model)
      expect(tier, `${name} ${c.label}: model ${c.model} is not the ${tiers.join(' or ')} tier of the runtime`)
      expect(tier && c.effort === probe.tiers[tier].effort, `${name} ${c.label}: effort ${c.effort} is not the effort of its tier`)
      expect(!c.prompt.includes(runtimes.claude.worktree_root), `${name} ${c.label}: the prompt names the Claude worktree root`)
    }
    for (const r of [byDefault, byClaude, byProbe]) {
      checkResult(name, args, r.result || {})
      if (OUTCOMES[name]) OUTCOMES[name](r, args)
    }
    for (const c of byClaude.calls) {
      if (c.def) expect(check(c.def, c.answer).length === 0, `${name} ${c.label}: the stub answer is not a valid ${c.def}`)
    }
    for (const [label, sc] of Object.entries(SCENARIOS[name] || {})) {
      try {
        sc.check(await run(file, { ...args, ...sc.args }, answerWith(name, sc.answers || {})))
      } catch (e) {
        expect(false, `${name} ${label}: ${e.message}`)
      }
    }
  }
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`workflows: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main()
