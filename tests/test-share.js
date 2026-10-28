// tests/test-share.js - spec checks of the test-line signal in wave and flow (#342). Node, no packages.
// It runs plugin/workflows/wave.js and flow.js under the stub harness of tests/workflows.js, loaded without
// its main(). Each merge reports test_lines; each metrics row carries the test share before and after; the
// run summary prints "tests at x% of code lines; warn limit y%"; a run that crosses the limit files 1 finding
// (kind tests, severity minor). A line count stops no task.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, problems, check }`)(require, __dirname)
const dir = path.join(__dirname, '..', 'plugin', 'workflows')
const WAVE = '10-wave-1'

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const counted = (before, after) => ({ merge: (n, a) => ({ ...a, test_lines: { before, after } }) })
const wave = (args, over) => H.run(path.join(dir, 'wave.js'), { ...H.ARGS.wave, ...args }, H.answerWith('wave', over))
const flow = (args, over) => H.run(path.join(dir, 'flow.js'), { ...H.ARGS.flow, max_load: undefined, ...args }, H.answerWith('flow', over))
const findingCalls = (r) => r.calls.filter((c) => c.label.startsWith('finding tests'))

async function main() {
  // 1. Wave: 29% before, 40% after, limit 30%: rows carry the share, the summary prints the warn line, 1 finding.
  const over = await wave({ test_share_warn: 30 }, counted({ test: 29, code: 71 }, { test: 40, code: 60 }))
  const rows = (over.result.metrics || []).filter((m) => m.result === 'merged')
  expect(rows.length > 0 && rows.every((m) => m.test_share && m.test_share.before === 29 && m.test_share.after === 40), `wave: metrics rows lack test_share {29, 40}: ${JSON.stringify(rows.map((m) => m.test_share))}`)
  for (const m of rows) {
    const bad = H.check('metrics', m)
    expect(bad.length === 0, `wave: metrics row ${m.task}: ${bad.join('; ')}`)
  }
  const line = `tests at 40% of code lines; warn limit 30% (before 29%, on ${WAVE})`
  expect(over.logs.includes(line), `wave: the summary lacks "${line}": ${over.logs.filter((l) => l.startsWith('tests at')).join(' | ')}`)
  const filed = findingCalls(over)
  expect(filed.length === 1 && filed[0].prompt.includes('--label kind:tests --label sev:minor'), `wave: ${filed.length} kind:tests sev:minor finding calls, not 1`)
  const mr = (over.calls.find((c) => c.label === 'merge read') || { prompt: '' }).prompt
  expect(mr.includes("git grep -I -c '' HEAD -- .") && /git grep -I -c '' [0-9a-f]{40} -- \./.test(mr) && mr.includes('Report test_lines'), 'wave: the merge prompt does not count the lines on the tip and on HEAD')
  expect(mr.includes('A count never fails, stops or changes the merge'), 'wave: the merge prompt lets the count stop the merge')
  // The line count stops no task: the escalations equal those of a run with no count.
  const plain = await wave({}, {})
  expect(JSON.stringify(over.result.escalations) === JSON.stringify(plain.result.escalations), 'wave: a line count changes the escalations')

  // 2. No limit: the summary says off, nothing is filed. Already over before the run: no crossing, nothing filed.
  const off = await wave({}, counted({ test: 29, code: 71 }, { test: 40, code: 60 }))
  expect(off.logs.includes(`tests at 40% of code lines; warn limit off (before 29%, on ${WAVE})`) && findingCalls(off).length === 0, 'wave: with no limit, the summary does not say off, or a finding is filed')
  const above = await wave({ test_share_warn: 30 }, counted({ test: 35, code: 65 }, { test: 40, code: 60 }))
  expect(findingCalls(above).length === 0, 'wave: a share already over the limit files a finding again')
  expect(plain.logs.includes(`tests at an unknown share of code lines; warn limit off (on ${WAVE})`) && !(plain.result.metrics || []).some((m) => m.test_share), 'wave: with no count, the summary or the rows invent a share')

  // 3. Flow: 1 line per group, and the crossing files or votes 1 finding through the findings lane.
  const fl = await flow({ test_share_warn: 30 }, counted({ test: 29, code: 71 }, { test: 40, code: 60 }))
  expect(fl.logs.includes('tests at 40% of code lines; warn limit 30% (before 29%, on 20-save)'), `flow: the summary lacks the 20-save line: ${fl.logs.filter((l) => l.startsWith('tests at')).join(' | ')}`)
  const ff = findingCalls(fl)
  expect(ff.length >= 1 && ff.every((c) => c.prompt.includes('--label kind:tests --label sev:minor')), `flow: ${ff.length} kind:tests sev:minor finding calls`)
  expect((fl.result.metrics || []).some((m) => m.test_share && m.test_share.after === 40), 'flow: no metrics row carries test_share')

  // 4. A bad limit refuses the run.
  let msg = ''
  try { await wave({ test_share_warn: 'high' }, {}) } catch (e) { msg = e.message }
  expect(/args\.test_share_warn must be a percent/.test(msg), `wave: a bad limit does not refuse: ${msg}`)

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`test-share: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('test-share: 0 passed, 1 failed')
  process.exit(1)
})
