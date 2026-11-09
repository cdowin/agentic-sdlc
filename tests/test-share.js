// tests/test-share.js - spec checks of the test-line signal in flow (#342). Node, no packages.
// It runs plugin/workflows/flow.js under the stub harness of tests/workflows.js, loaded without
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

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const counted = (before, after) => ({ merge: (n, a) => ({ ...a, test_lines: { before, after } }) })
const flow = (args, over) => H.run(path.join(dir, 'flow.js'), { ...H.ARGS.flow, max_load: undefined, ...args }, H.answerWith('flow', over))
const findingCalls = (r) => r.calls.filter((c) => c.label.startsWith('finding tests'))

async function main() {
  // 1. 29% before, 40% after, limit 30%: rows carry the share, the summary prints the warn line per group,
  // the crossing files 1 finding through the findings lane.
  const fl = await flow({ test_share_warn: 30 }, counted({ test: 29, code: 71 }, { test: 40, code: 60 }))
  expect(fl.logs.includes('tests at 40% of code lines; warn limit 30% (before 29%, on 20-save)'), `flow: the summary lacks the 20-save line: ${fl.logs.filter((l) => l.startsWith('tests at')).join(' | ')}`)
  const ff = findingCalls(fl)
  expect(ff.length >= 1 && ff.every((c) => c.prompt.includes('--label kind:tests --label sev:minor')), `flow: ${ff.length} kind:tests sev:minor finding calls`)
  const rows = (fl.result.metrics || []).filter((m) => m.test_share)
  expect(rows.length > 0 && rows.every((m) => m.test_share.before === 29 && m.test_share.after === 40), `flow: metrics rows lack test_share {29, 40}: ${JSON.stringify(rows.map((m) => m.test_share))}`)
  for (const m of fl.result.metrics || []) {
    const bad = H.check('metrics', m)
    expect(bad.length === 0, `flow: metrics row ${m.task}: ${bad.join('; ')}`)
  }
  const mr = (fl.calls.find((c) => c.label === 'merge 21') || { prompt: '' }).prompt
  expect(mr.includes("git grep -I -c '' HEAD -- .") && /git grep -I -c '' [0-9a-f]{40} -- \./.test(mr) && mr.includes('Report test_lines'), 'flow: the merge prompt does not count the lines on the tip and on HEAD')
  expect(mr.includes('A count never fails, stops or changes the merge'), 'flow: the merge prompt lets the count stop the merge')
  // The line count stops no task: the task states equal those of a run with no count.
  const plain = await flow({}, {})
  const states = (r) => JSON.stringify((r.result.tasks || []).map((t) => [t.task, t.state]))
  expect(states(fl) === states(plain), 'flow: a line count changes the task states')

  // 2. No limit: the summary says off, nothing is filed. Already over before the run: no crossing, nothing filed.
  const off = await flow({}, counted({ test: 29, code: 71 }, { test: 40, code: 60 }))
  expect(off.logs.includes('tests at 40% of code lines; warn limit off (before 29%, on 20-save)') && findingCalls(off).length === 0, 'flow: with no limit, the summary does not say off, or a finding is filed')
  const above = await flow({ test_share_warn: 30 }, counted({ test: 35, code: 65 }, { test: 40, code: 60 }))
  expect(findingCalls(above).length === 0, 'flow: a share already over the limit files a finding again')
  expect(plain.logs.some((l) => l.startsWith('tests at an unknown share of code lines; warn limit off')) && !(plain.result.metrics || []).some((m) => m.test_share), 'flow: with no count, the summary or the rows invent a share')

  // 3. A bad limit refuses the run.
  let msg = ''
  try { await flow({ test_share_warn: 'high' }, {}) } catch (e) { msg = e.message }
  expect(/args\.test_share_warn must be a percent/.test(msg), `flow: a bad limit does not refuse: ${msg}`)

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
