// tests/doc-sdlc.js - run plugin/workflows/doc-sdlc.js under a stub harness. Node, no packages.
// The workflow has its own schemas, so tests/workflows.js skips it. The stub answers by label.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const file = path.join(__dirname, '..', 'plugin', 'workflows', 'doc-sdlc.js')
const src = fs.readFileSync(file, 'utf8').replace(/^export /m, '')
const AsyncFunction = (async () => {}).constructor
const PRECEDENCE = ['The base draft: its numbers win unless a newer dated source is named', 'Issue comments']
const ARGS = { brief: 'Write the post', kind: 'post', target: 'out.md', lenses: ['plain-language', 'visual-layout', 'humanizer'] }
const fail = (id, ship, score = 'fail') => ({ id, score, evidence: 'e', ship })
const brief = { reader: 'r', task: 't', mainPoint: 'm', sources: ['s'], precedence: PRECEDENCE, doneWhen: ['d'] }

// run: the workflow under a stub. review(label, n) answers a reviewer with its checks.
async function run(args, review = () => [fail('1', 'x', 'pass')]) {
  const calls = [], logs = [], phases = []
  const agent = async (prompt, o) => {
    calls.push({ prompt, ...o })
    if (o.label === 'brief') return brief
    if (o.label.startsWith('review-')) {
      const checks = review(o.label)
      if (!checks) throw new Error('down')
      return { lens: o.label, checks }
    }
    return { path: 'out.md', summary: 's' }
  }
  const parallel = (ts) => Promise.all(ts.map((t) => t()))
  const result = await new AsyncFunction('args', 'phase', 'agent', 'parallel', 'log', src)(
    { ...ARGS, ...args }, (p) => phases.push(p), agent, parallel, (m) => logs.push(m))
  return { calls, logs, phases, result }
}

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const all = (r, re) => r.calls.filter((c) => re.test(c.label))

async function main() {
  const plain = await run({})
  expect(plain.phases.join() === 'Brief,Base draft,Layers,Review,Fix,Validated', `phases: ${plain.phases}`)
  expect(plain.calls.every((c) => c.agentType === 'developer' && c.model === 'sonnet'), 'every agent is developer on sonnet')
  expect(plain.result.validated === true, 'a clean run validates')
  for (const bad of [{ brief: '' }, { target: '' }, { kind: 'book' }]) {
    expect(await run(bad).then(() => false, () => true), `args ${JSON.stringify(bad)} must throw`)
  }

  // Fix 1: the brief records a precedence list and every later agent sees it.
  expect(plain.calls[0].prompt.includes('source precedence') && plain.calls[0].schema.required.includes('precedence'), 'the brief asks for a precedence list')
  const later = plain.calls.slice(1)
  expect(later.length > 4 && later.every((c) => c.prompt.includes('1. ' + PRECEDENCE[0])), 'every agent after the brief gets the precedence list')
  const reviewers = all(plain, /^review-/)
  expect(reviewers.length === 2 && reviewers.every((c) => c.prompt.includes('FACTS') && c.prompt.includes('1. ' + PRECEDENCE[0])), 'every reviewer checks facts against the precedence list')

  // Fix 2: screenshots reach the visual-layout reviewer only; none supplied means n/a.
  const shots = await run({ screenshots: ['s375.png', 's1000.png'] })
  const [vis] = all(shots, /^review-visual-layout/), [pl] = all(shots, /^review-plain-language/)
  expect(vis.prompt.includes('s375.png, s1000.png') && !pl.prompt.includes('s375.png'), 'screenshot files go to the visual-layout reviewer only')
  expect(/No screenshots were supplied.*n\/a/.test(all(plain, /^review-visual-layout/)[0].prompt), 'no screenshots: the reviewer is told to score n/a')

  // Fix 3: validated is true on should-fix and note items; blocking, or an unreviewed lens, holds it false.
  const should = await run({}, (l) => (l.includes('visual') ? [fail('2', 'should-fix'), fail('3', 'note')] : [fail('1', 'x', 'pass')]))
  expect(should.result.validated === true, 'should-fix and note items alone must validate')
  expect(should.result.shouldFix.length === 1 && should.result.notes.length === 1 && should.result.fixRounds === 2, 'should-fix items are listed, notes kept, 2 fix rounds run')
  const block = await run({}, (l) => (l.includes('visual') ? [fail('FACTS', 'blocking')] : [fail('1', 'x', 'pass')]))
  expect(block.result.validated === false && block.result.blocking.length === 1, 'a blocking fail keeps validated false')
  const down = await run({}, (l) => (l.includes('visual') ? null : [fail('1', 'x', 'pass')]))
  expect(down.result.validated === false && down.result.unavailable.join() === 'visual-layout', 'an unreviewed lens keeps validated false')

  // The humanizer layer is optional.
  expect(!plain.calls.some((c) => /humanizer/.test(c.label)) && plain.logs.some((m) => /humanizer skipped/.test(m)) && plain.result.skipped.join() === 'humanizer', 'no humanizerPath: the layer is skipped with a log line')
  const hum = await run({ humanizerPath: '/h/SKILL.md' })
  expect(all(hum, /^layer-humanizer/)[0].prompt.includes('/h/SKILL.md') && all(hum, /^review-humanizer/).length === 1, 'humanizerPath: the layer and the review run')

  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`doc-sdlc: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length ? 1 : 0)
}
main()
