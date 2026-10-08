// tests/workflows.js - run each workflow of plugin/workflows/ under a stub harness. Node, no packages.
// Each agent() call must pass a schema equal to a $defs shape of the contract, and its model and
// agent type must come from the runtime profile. The stub answers each call with
// tests/fixtures/contract/<shape>.ok.json. Each workflow runs 3 times:
//   1. with no args.runtime: the spawns must equal run 2, so the Claude default matches runtimes.json;
//   2. with runtimes.json "claude": each agent type must be an agent file with a tools: line;
//   3. with a probe runtime: each model and effort are the tier that x-roles gives the role, and no prompt
//      names the Claude worktree root.
// Prints 1 line per problem and the count of checks. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')
const { contract, check } = require('../plugin/contract/check.js')

const root = path.join(__dirname, '..')
const fixtures = path.join(__dirname, 'fixtures', 'contract')
const runtimes = JSON.parse(fs.readFileSync(path.join(root, 'plugin', 'contract', 'runtimes.json'), 'utf8'))
const ROLES = contract['x-roles']
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
// The args each workflow needs to run every phase. A new workflow adds its args here.
const ARGS = {
  split: { issue: 1, branch: '1-x', base: 'main', parts: ['read', { name: 'write', test: 't -k write' }], test: 't' },
  'review-batch': { results: [{ id: 'read', diff: 'a..b', test: 't' }, { id: 'write', diff: 'a..c', test: 't' }] },
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
const shapeOf = (schema) => Object.keys(contract.$defs).find((d) => same(contract.$defs[d], schema))

async function run(file, args) {
  const src = fs.readFileSync(file, 'utf8').replace(/^export /m, '')
  const AsyncFunction = (async () => {}).constructor
  const calls = []
  const agent = async (prompt, opts) => {
    const def = shapeOf(opts.schema)
    calls.push({ prompt, ...opts, def })
    if (!def) throw new Error(`agent ${opts.label}: its schema is no contract shape`)
    return JSON.parse(fs.readFileSync(path.join(fixtures, `${def}.ok.json`), 'utf8'))
  }
  const parallel = (thunks) => Promise.all(thunks.map((t) => t()))
  const result = await new AsyncFunction('args', 'phase', 'agent', 'parallel', 'log', src)(args, () => {}, agent, parallel, () => {})
  return { calls, result }
}

async function main() {
  const files = fs.readdirSync(path.join(root, 'plugin', 'workflows')).filter((f) => f.endsWith('.js'))
  for (const f of files) {
    const name = f.replace(/\.js$/, '')
    const file = path.join(root, 'plugin', 'workflows', f)
    const args = ARGS[name]
    expect(args, `${name}: tests/workflows.js has no ARGS for it`)
    if (!args) continue
    let byDefault, byClaude, byProbe
    try {
      byDefault = await run(file, args)
      byClaude = await run(file, { ...args, runtime: runtimes.claude })
      byProbe = await run(file, { ...args, runtime: probe })
    } catch (e) {
      expect(false, `${name}: ${e.message}`)
      continue
    }
    expect(byDefault.calls.length > 0, `${name}: made no agent call`)
    const spawns = (r) => r.calls.map((c) => `${c.label} ${c.agentType} ${c.model} ${c.effort} ${c.prompt}`)
    expect(same(spawns(byDefault), spawns(byClaude)), `${name}: its Claude default differs from runtimes.json claude`)
    for (const c of byClaude.calls) {
      const agentFile = path.join(root, 'plugin', 'agents', `${c.agentType}.md`)
      const head = fs.existsSync(agentFile) ? fs.readFileSync(agentFile, 'utf8').split('\n---')[0] : ''
      expect(/^tools: /m.test(head), `${name} ${c.label}: agent type ${c.agentType} has no agent file with a tools: line`)
    }
    for (const c of byProbe.calls) {
      const role = String(c.agentType).replace(`${PROBE}-`, '')
      expect(role in ROLES, `${name} ${c.label}: agent type ${c.agentType} is not from the runtime`)
      const tiers = role === 'worker' ? Object.keys(probe.tiers) : [ROLES[role]]
      const tier = tiers.find((t) => c.model === probe.tiers[t].model)
      expect(tier, `${name} ${c.label}: model ${c.model} is not the ${tiers.join(' or ')} tier of the runtime`)
      expect(tier && c.effort === probe.tiers[tier].effort, `${name} ${c.label}: effort ${c.effort} is not the effort of its tier`)
      expect(!c.prompt.includes(runtimes.claude.worktree_root), `${name} ${c.label}: the prompt names the Claude worktree root`)
    }
    for (const c of byClaude.calls) {
      const answer = JSON.parse(fs.readFileSync(path.join(fixtures, `${c.def}.ok.json`), 'utf8'))
      expect(check(c.def, answer).length === 0, `${name} ${c.label}: fixture ${c.def}.ok.json is not valid`)
    }
  }
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`workflows: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main()
