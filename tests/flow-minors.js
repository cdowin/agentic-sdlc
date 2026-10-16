// tests/flow-minors.js - spec checks of #308 (a fix lands through the landing lane) and #309 (a group
// ships after the batched reviews that read it). Runs plugin/workflows/flow.js under the stub harness of
// tests/workflows.js. Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, claimUrl, flowTask, problems }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'flow.js')

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const later = (ms, v) => new Promise((resolve) => setTimeout(() => resolve(v), ms))
const claimsOf = (queue) => Object.fromEntries(queue.map((e) => [String(e.issue), H.claimUrl(String(e.issue))]))
const flow = (args, over = {}) => H.run(file, { ...H.ARGS.flow, max_load: undefined, ...args, ...(args.queue && !args.claims && { claims: claimsOf(args.queue) }) }, H.answerWith('flow', over))
const HOLDS = { kind: 'bug', severity: 'holds', title: 'the save file is empty after a load', evidence: 't load: 1 failed', minutes: 15 }
const Q = [H.flowTask(21, 20, '20-save', 'src/a.ts'), H.flowTask(22, 20, '20-save', 'src/b.ts'), H.flowTask(31, 30, '30-menu', 'src/menu.ts')]
const FOUND = { ...HOLDS, url: 'https://github.com/example/game/issues/42', voted: false, votes: 1 }

async function main() {
  // 308: the fix agent pushes only its own branch; the fix lands through the lane like a task.
  const held = await flow({ queue: Q, cpus: 8 }, {
    report: (n, a) => (a.task === '21' ? { ...a, findings: [HOLDS] } : a),
    finding: FOUND,
  })
  const hl = labels(held)
  const fixP = promptOf(held, 'fix 20-save')
  const landP = promptOf(held, 'merge fix-1')
  expect(fixP !== '' && !fixP.includes('HEAD:20-save') && !/push -q origin (HEAD:)?main\b/.test(fixP) && fixP.includes('Never push to'), 'holds: the fix agent pushes the group branch, or pushes main')
  expect(landP.includes('Merge 20-save-fix-1') && landP.includes('group branch 20-save') && landP.includes(H.ARGS.flow.gate || ''), `holds: no fix landing prompt for 20-save-fix-1 on the group branch: ${hl}`)
  expect(hl.indexOf('merge fix-1') > hl.indexOf('fix 20-save') && hl.indexOf('merge fix-1') < hl.indexOf('merge 22') && hl.indexOf('merge fix-1') < hl.indexOf('ship 20-save'), `holds: the fix did not land between its agent and merge 22: ${hl}`)
  expect(hl.filter((l) => l.startsWith('fix ')).length === 1 && !hl.includes('review fix-1') && held.result.landed.join() === '21,22,31' && held.result.fixes.length === 1 && held.result.fixes[0].sha, `holds: fix count, review of a fix landing, landed ${held.result.landed} or fixes ${JSON.stringify(held.result.fixes)}`)

  const stuck = await flow({ queue: Q, cpus: 8 }, {
    report: (n, a, label) => (label === 'fix 20-save' ? { ...a, status: 'escalated', escalation: 'Which "save" format?', test: { ...a.test, passed: false } } : a.task === '21' ? { ...a, findings: [HOLDS] } : a),
    finding: FOUND,
  })
  expect(!labels(stuck).some((l) => l.startsWith('merge fix-')), `holds stuck: a fix that escalated was landed: ${labels(stuck)}`)

  // A red fix landing holds its group like a fix agent that did not fix.
  const red = await flow({ queue: Q, cpus: 8 }, {
    report: (n, a) => (a.task === '21' ? { ...a, findings: [HOLDS] } : a),
    finding: FOUND,
    merge: (n, a, label) => (label.startsWith('merge fix-') ? { ...a, oracle_passed: false, sha: '', escalation: 'the fix breaks t load' } : a),
  })
  const rl = labels(red)
  expect(rl.includes('merge fix-1') && !rl.includes('ship 20-save') && rl.includes('merge 31') && (red.result.held || []).some((h) => h.target === '20-save') && !red.result.landed.includes('22') && red.result.fixes.length === 1 && red.result.fixes[0].reason, `holds red landing: the group is not held on a red fix landing: ${rl}; held ${JSON.stringify(red.result.held)}; fixes ${JSON.stringify(red.result.fixes)}`)

  // 309: a holds finding of a batched review gets its fix landed before the group ships.
  const batchHolds = await flow({ queue: Q.slice(0, 2), cpus: 8, review_every: 2 }, {
    landing_review: (n, a, label) => (label === 'review batch 1' ? later(60, { landings: ['21', '22'], findings: [{ ...HOLDS, task: '21' }] }) : { landings: [label.slice(7)], findings: [] }),
    finding: FOUND,
  })
  const bl = labels(batchHolds)
  expect(bl.filter((l) => l.startsWith('fix ')).length === 1 && bl.indexOf('fix 20-save') >= 0 && bl.indexOf('fix 20-save') < bl.indexOf('ship 20-save') && bl.indexOf('merge fix-1') > bl.indexOf('fix 20-save') && bl.indexOf('merge fix-1') < bl.indexOf('ship 20-save'), `batch holds: the group shipped before the fix of a batched holds finding landed: ${bl}`)

  // A final partial batch is read before its group ships.
  let batchDone = false
  let sawBatch = null
  const partial = await flow({ queue: [H.flowTask(21, 20, '20-save', 'src/a.ts'), H.flowTask(22, 20, '20-save', 'src/b.ts'), H.flowTask(23, 20, '20-save', 'src/c.ts')], cpus: 8, review_every: 2 }, {
    landing_review: (n, a, label) => (label === 'review batch 2' ? later(60, { landings: ['23'], findings: [] }).then((v) => { batchDone = true; return v }) : { landings: [label.slice(7)], findings: [] }),
    group_pr: (n, a, label) => { if (label === 'ship 20-save') sawBatch = batchDone; return a },
  })
  expect(labels(partial).includes('review batch 2') && sawBatch === true, `batch: a group shipped (saw batch ended: ${sawBatch}) before its final partial batch review ended`)

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`flow-minors: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('flow-minors: 0 passed, 1 failed')
  process.exit(1)
})
