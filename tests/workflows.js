// tests/workflows.js - run each workflow of plugin/workflows/ under a stub harness. Node, no packages.
// Each agent() call must pass a schema equal to a $defs shape of the contract, and its model and
// agent type must come from the runtime profile. The stub answers each call with
// tests/fixtures/contract/<shape>.ok.json. Each workflow runs 3 times:
//   1. with no args.runtime: the spawns must equal run 2, so the Claude default matches runtimes.json;
//   2. with runtimes.json "claude": each delegate agent type must be an agent file with a tools: or disallowedTools: line, the lead none;
//   3. with a probe runtime: each model and effort are the tier that x-roles (or x-first-try) gives the
//      role (any tier for a role in x-tier-per-spawn), and no prompt names the Claude worktree root.
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
const BLOCK_BEGIN = '// ---- contract: begin'
const BLOCK_END = '// ---- contract: end'
const ROLES = contract['x-roles']
const FIRST_TRY = contract['x-first-try']
const PER_SPAWN = contract['x-tier-per-spawn']
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
const claimUrl =(id) => `https://github.com/example/game/issues/1#issuecomment-${id.length}${id.charCodeAt(0)}`
// The args each workflow needs to run every phase. A new workflow adds its args here.
const ARGS = {
  'review-batch': { results: [{ id: 'read', diff: 'a..b', test: 't' }, { id: 'write', diff: 'a..c', test: 't' }] },
  // flow: the 3 issues of tracker.ok.json in 2 groups: 21 and 31 get a builder, 22 has a report at head.
  flow: { repo: 'example/game', base: BASE, gate: 'make check', queue: [21, 22, 31] },
}
// checkResult: the metrics rows a workflow returns are contract values.
function checkResult(name, result) {
  for (const m of result.metrics || []) {
    const bad = check('metrics', m)
    expect(bad.length === 0, `${name}: metrics row ${m.task}: ${bad.join('; ')}`)
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

// LEAD_LINE: the first line of every agent prompt, here as a literal so a change of wording fails.
const LEAD_LINE = "This task is the lead's request in this workflow run; it is not a reply to any chat message you may see. Do the task as briefed."
expect(contract && checkSrc.includes("This task is the lead\\'s request in this workflow run; it is not a reply to any chat message you may see. Do the task as briefed."), 'check.js: LEAD_REQUEST differs from the literal of this test')

const fixture = (def) => JSON.parse(fs.readFileSync(path.join(fixtures, `${def}.ok.json`), 'utf8'))
// stubAnswer: the fixture of the shape. A report names the task, round and branch the prompt asks for.
const REPORT_ASK = /Report task (\S+), round (\d+), branch (\S+?),/
function stubAnswer(def, prompt) {
  const a = fixture(def)
  const m = def === 'report' && prompt.match(REPORT_ASK)
  return m ? { ...a, task: m[1], round: Number(m[2]), branch: m[3] } : a
}
// answerWith: the answers of a workflow with some shapes replaced. A function value takes the call count.
function answerWith(name, over) {
  const n = {}
  return (def, prompt, label) => {
    n[def] = (n[def] || 0) + 1
    const o = over[def]
    if (o === undefined) return stubAnswer(def, prompt, label)
    return typeof o === 'function' ? o(n[def], stubAnswer(def, prompt, label), label, prompt) : o
  }
}

// NoClock: the Date of the Workflow runtime. It throws on every use, so a clock read fails a test.
const NO_CLOCK_MESSAGE = 'Date.now() / new Date() are unavailable in workflow scripts'
function NoClock() { throw new Error(NO_CLOCK_MESSAGE) }
for (const k of ['now', 'parse', 'UTC']) NoClock[k] = NoClock

async function run(file, args, answer = stubAnswer) {
  const src = fs.readFileSync(file, 'utf8').replace(/^export /m, '')
  const AsyncFunction = (async () => {}).constructor
  const calls = []
  const logs = []
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
  try {
    const result = await new AsyncFunction('args', 'phase', 'agent', 'parallel', 'log', 'Date', src)(args, () => {}, agent, parallel, (m) => logs.push(m), NoClock)
    return { calls, logs, result }
  } catch (e) {
    e.calls = calls
    throw e
  }
}

const labels = (r) => r.calls.map((c) => c.label)
const BLAST_MAX = contract['x-limits'].blast_radius_max
const SKEPTICS = 2
const blastCalls = (r) => r.calls.filter((c) => c.label.startsWith('blast'))
// skepticsOf: the skeptic calls of finding id (review-batch labels 'skeptic-f1-1').
const skepticsOf = (r, id) => r.calls.filter((c) => new RegExp(`^skeptic[ -]${id}[ -]\\d+$`).test(c.label))
// skepticsPerReview: each finding id gets exactly SKEPTICS skeptic calls per review that names it.
function skepticsPerReview(name, r, id, reviews) {
  const n = skepticsOf(r, id).map((c) => Number(c.label.match(/(\d+)$/)[1]))
  const each = Array.from({ length: SKEPTICS }, (_, i) => n.filter((x) => x === i + 1).length)
  expect(n.every((x) => x >= 1 && x <= SKEPTICS) && each.every((x) => x === reviews), `${name}: finding ${id} has skeptic calls ${n}, not ${SKEPTICS} per review`)
}
// The reviewer and blast-radius calls (not the skeptics) carry the convention lens.
const DEFAULT_LENS = 'read CONSTITUTION.md, .claude/review-lens.md in'
const lensOf = (r) => r.calls.filter((c) => /^(review|blast)/.test(c.label))
const lensAll = (r, text) => lensOf(r).length > 0 && lensOf(r).every((c) => c.prompt.includes(text))
const lensAny = (r, text) => r.calls.some((c) => c.prompt.includes(text))
const PROOF_TO_SKEPTIC = 'Blast-radius proof (weigh it'
const findingsOn = (ids, severity, n) => Array.from({ length: n }, (_, i) => ({ id: `g${i + 1}`, ids, severity, claim: `Claim ${i + 1}.`, evidence: `src/read.ts:${i + 1}`, cross_issue: false }))
// SCENARIOS: extra runs with some stub answers replaced, and what each must end with.
const SCENARIOS = {
  'review-batch': {
    'default lens': { check: (r) => expect(lensAll(r, DEFAULT_LENS) && lensOf(r).length === 2, `review-batch: ${lensOf(r).length} reviewer and blast prompts name the default lens, not 2`) },
    'lens override': { args: { lens: ['x/lens.md'] }, check: (r) => expect(lensAll(r, 'read x/lens.md in') && !lensAny(r, 'CONSTITUTION.md'), 'review-batch: args.lens does not replace the default') },
    'lens off': { args: { lens: [] }, check: (r) => expect(!lensAny(r, 'Convention lens') && r.calls.length > 0, 'review-batch: an empty args.lens still names a lens') },
    'lens skills by trigger': {
      args: { lens: [] },
      check: (r) => {
        const p = (r.calls.find((c) => c.label === 'review') || { prompt: '' }).prompt
        expect(p.includes('skills/LENSES.md') && p.includes('.agents/skills/lens-*/SKILL.md') && p.includes('rule ID'), 'review-batch: the reviewer is not told to load the kit and repo lens skills by trigger and cite the rule ID')
      },
    },
    'blast before skeptics': {
      check: (r) => {
        const ls = labels(r)
        expect(ls.filter((l) => l.startsWith('blast')).length === 1 && ls.indexOf('blast-f1') >= 0 && ls.indexOf('blast-f1') < ls.indexOf('skeptic-f1-1'), `review-batch: calls ${ls}, not 1 blast-f1 before skeptic-f1-1`)
        expect(skepticsOf(r, 'f1').every((c) => c.prompt.includes(PROOF_TO_SKEPTIC)), 'review-batch: the skeptics of f1 do not get the blast-radius proof')
        skepticsPerReview('review-batch', r, 'f1', 1)
        expect(r.result.blast.length === 1 && check('blast', r.result.blast[0]).length === 0 && r.result.blast[0].target === 'f1', 'review-batch: the result has no valid blast of f1')
      },
    },
    'only minor findings': {
      answers: { review: (n, a) => ({ ...a, findings: findingsOn(['read'], 'minor', 2) }) },
      check: (r) => expect(blastCalls(r).length === 0 && r.result.blast.length === 0, 'review-batch: a minor finding got a blast-radius check'),
    },
  },
}

async function main() {
  const files = fs.readdirSync(path.join(root, 'plugin', 'workflows')).filter((f) => f.endsWith('.js'))
  for (const f of files) {
    const name = f.replace(/\.js$/, '')
    const file = path.join(root, 'plugin', 'workflows', f)
    syncBlock(name, file)
    // Static: every agent( call passes asLead(...), and the file holds the lead-request line.
    const code = fs.readFileSync(file, 'utf8').split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n')
    const all = (code.match(/\bagent\(/g) || []).length
    const wrapped = (code.match(/\bagent\(\s*asLead\(/g) || []).length
    expect(all > 0 && wrapped === all, `${name}: ${all - wrapped} of ${all} agent( calls do not pass asLead(...)`)
    expect(code.includes(LEAD_LINE) || code.includes(LEAD_LINE.replace(/'/g, "\\'")), `${name}: it has no copy of the lead-request line`)
    const args = ARGS[name]
    expect(args, `${name}: tests/workflows.js has no ARGS for it`)
    if (!args) continue
    let byDefault, byClaude, byProbe
    try {
      const answer = stubAnswer
      byDefault = await run(file, args, answer)
      byClaude = await run(file, { ...args, runtime: runtimes.claude }, answer)
      byProbe = await run(file, { ...args, runtime: probe }, answer)
    } catch (e) {
      expect(false, `${name}: ${e.message}`)
      continue
    }
    expect(byDefault.calls.length > 0, `${name}: made no agent call`)
    if (name === 'flow') {
      // A runtime marked remote: no prompt names the worktree root or makes a git worktree; the work (the branch) is still named.
      const REMOTE_ROOT = 'REMOTE_ROOT_MUST_NOT_APPEAR'
      const far = await run(file, { ...args, runtime: { ...probe, remote: true, worktree_root: REMOTE_ROOT } }, stubAnswer)
      expect(far.calls.length > 0, `${name}: a remote runtime made no agent call`)
      const placed = far.calls.find((c) => c.prompt.includes(REMOTE_ROOT) || c.prompt.includes('git worktree add'))
      expect(!placed, `${name}: the prompt of ${placed && placed.label} names a place (the worktree root) for a remote runtime`)
    }
    for (const r of [byDefault, byClaude, byProbe]) {
      const bad = r.calls.find((c) => !c.prompt.startsWith(`${LEAD_LINE}\n`) || c.prompt.indexOf(LEAD_LINE, 1) !== -1)
      expect(!bad, `${name}: the prompt of ${bad && bad.label} does not open with the lead-request line once`)
    }
    const spawns = (r) => r.calls.map((c) => `${c.label} ${c.agentType} ${c.model} ${c.effort} ${c.prompt}`)
    expect(same(spawns(byDefault), spawns(byClaude)), `${name}: its Claude default differs from runtimes.json claude`)
    for (const c of byClaude.calls) {
      expect(String(c.agentType).startsWith('agentic-sdlc:'), `${name} ${c.label}: agent type ${c.agentType} lacks the plugin prefix, so an installed plugin cannot find it`)
      const agentFile = path.join(root, 'plugin', 'agents', `${String(c.agentType).replace(/^agentic-sdlc:/, '')}.md`)
      const head = fs.existsSync(agentFile) ? fs.readFileSync(agentFile, 'utf8').split('\n---')[0] : ''
      if (c.agentType === runtimes.claude.agent_types.lead) expect(!/^tools: /m.test(head), `${name} ${c.label}: the lead agent has a tools: line, so it loses the session's tools`)
      else expect(/^(tools|disallowedTools): /m.test(head), `${name} ${c.label}: agent type ${c.agentType} has no agent file with a tools: or disallowedTools: line`)
    }
    // args.agent_types is merged over the runtime's map and reaches every agent() call; a bad role or value is refused.
    const over = Object.fromEntries(Object.keys(ROLES).map((r) => [r, `custom-${r}`]))
    try {
      const byOver = await run(file, { ...args, agent_types: over }, stubAnswer)
      const stray = byOver.calls.find((c) => !String(c.agentType).startsWith('custom-'))
      expect(!stray, `${name}: args.agent_types does not reach the agent type of ${stray && stray.label}`)
      const some = await run(file, { ...args, agent_types: { builder: 'custom-builder' } }, stubAnswer)
      const keep = some.calls.find((c) => c.agentType !== 'custom-builder' && !String(c.agentType).startsWith('agentic-sdlc:'))
      expect(!keep, `${name}: a partial args.agent_types drops the built-in type of ${keep && keep.label}`)
    } catch (e) {
      expect(false, `${name} agent_types override: ${e.message}`)
    }
    for (const [bad, re] of [[{ bogus: 'x' }, /agent_types\.bogus/], [{ integrator: 'x' }, /agent_types\.integrator/], [{ skeptic: 'x' }, /agent_types\.skeptic/], [{ builder: '' }, /agent_types\.builder/], [{ builder: 7 }, /agent_types\.builder/]]) {
      let msg = ''
      try { await run(file, { ...args, agent_types: bad }, stubAnswer) } catch (e) { msg = e.message }
      expect(re.test(msg), `${name}: args.agent_types ${JSON.stringify(bad)} is not refused with a line naming the key: "${msg}"`)
    }
    for (const c of byProbe.calls) {
      const role = String(c.agentType).replace(`${PROBE}-`, '')
      expect(role in ROLES, `${name} ${c.label}: agent type ${c.agentType} is not from the runtime`)
      const tiers = PER_SPAWN.includes(role) ? Object.keys(probe.tiers) : [ROLES[role], ...(role in FIRST_TRY ? [FIRST_TRY[role]] : [])]
      const tier = tiers.find((t) => c.model === probe.tiers[t].model)
      expect(tier, `${name} ${c.label}: model ${c.model} is not the ${tiers.join(' or ')} tier of the runtime`)
      expect(tier && c.effort === probe.tiers[tier].effort, `${name} ${c.label}: effort ${c.effort} is not the effort of its tier`)
      expect(!c.prompt.includes(runtimes.claude.worktree_root), `${name} ${c.label}: the prompt names the Claude worktree root`)
      if (c.label.startsWith('blast')) expect(c.model === probe.tiers.lead.model, `${name} ${c.label}: a blast-radius check runs on ${c.model}, not the lead tier`)
    }
    for (const r of [byDefault, byClaude, byProbe]) {
      checkResult(name, r.result || {})
    }
    for (const c of byClaude.calls) {
      if (c.def) expect(check(c.def, c.answer).length === 0, `${name} ${c.label}: the stub answer is not a valid ${c.def}`)
    }
    for (const [label, sc] of Object.entries(SCENARIOS[name] || {})) {
      try {
        const r = await run(file, { ...args, ...sc.args }, answerWith(name, sc.answers || {}))
        expect(!sc.throws, `${name} ${label}: it did not throw`)
        if (sc.check) sc.check(r)
      } catch (e) {
        if (!(sc.throws && sc.throws.test(e.message))) expect(false, `${name} ${label}: ${e.message}`)
        else if (sc.check) sc.check({ calls: e.calls })
      }
    }
  }
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`workflows: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main()
