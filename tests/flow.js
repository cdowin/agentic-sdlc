// tests/flow.js - spec checks of the flow loop (#306). Node, no packages.
// It runs plugin/workflows/flow.js under the stub harness of tests/workflows.js (run, ARGS, answerWith),
// loaded without its main(). The stub answers prompts, so these are prompt, order and result checks: no
// real git, gh or uptime runs. A stub answer may be a promise, so a check can see what runs at once.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, claimUrl, flowTask, problems, check }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'flow.js')
const BASE_SHA = H.ARGS.flow.base.sha

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const taskOf = (r, id) => (r.result.tasks || []).find((t) => t.task === id) || {}
const later = (ms, v) => new Promise((resolve) => setTimeout(() => resolve(v), ms))
const shaOf = (n) => n.toString(16).padStart(40, 'c')
const claimsOf = (queue) => Object.fromEntries(queue.map((e) => [String(e.issue), H.claimUrl(String(e.issue))]))
const flow = (args, over = {}) => H.run(file, { ...H.ARGS.flow, max_load: undefined, ...args, ...(args.queue && Array.isArray(args.queue) && !args.claims && { claims: claimsOf(args.queue) }) }, H.answerWith('flow', over))
const metricsOk = (r, name) => {
  for (const m of r.result.metrics || []) {
    const bad = H.check('metrics', m)
    expect(bad.length === 0, `${name}: metrics row ${m.task}: ${bad.join('; ')}`)
  }
  for (const t of r.result.transitions || []) {
    const bad = H.check('transition', t)
    expect(bad.length === 0, `${name}: transition of ${t.task}: ${bad.join('; ')}`)
  }
}

async function main() {
  // 1. 6 independent tasks in 2 parents: up to the slot cap (6 CPUs: 4) build at once, each lands as soon
  // as its report is green, into its own group branch. No chain branch, no converge, no load agent.
  const six = [21, 22, 23].map((n) => H.flowTask(n, 20, '20-save', `src/save${n}.ts`)).concat([31, 32, 33].map((n) => H.flowTask(n, 30, '30-menu', `src/menu${n}.ts`)))
  let now = 0
  let most = 0
  const wide = await flow({ queue: six, cpus: 6 }, {
    report: (n, a) => {
      now++
      most = Math.max(most, now)
      return later(5 + (n % 3), a).then((x) => { now--; return x })
    },
  })
  const ls = labels(wide)
  const builds = ls.filter((l) => l.startsWith('build '))
  expect(most === 4 && builds.length === 6, `6 tasks: ${most} builds ran at once and ${builds.length} ran, not 4 at once and 6 in all`)
  expect(ls.findIndex((l) => l.startsWith('merge ')) < ls.indexOf(builds[4]), `6 tasks: no task landed before the 5th build started: ${ls}`)
  for (const e of six) {
    const id = String(e.issue)
    expect(ls.indexOf(`merge ${id}`) > ls.indexOf(`build ${id}`) && promptOf(wide, `merge ${id}`).includes(`in the group branch ${e.group} of example/game`), `task ${id}: it does not land in ${e.group} after its build`)
    expect(taskOf(wide, id).state === 'integrated' && taskOf(wide, id).closed_at, `task ${id}: ends ${taskOf(wide, id).state}, not integrated and closed`)
  }
  expect(wide.result.landed.length === 6 && wide.result.escalations.length === 0, `6 tasks: landed ${wide.result.landed}, escalations ${JSON.stringify(wide.result.escalations)}`)
  expect(!ls.includes('converge') && !wide.calls.some((c) => /converge|chain/i.test(c.prompt)), 'a flow prompt names a converge or a chain branch')
  expect(!wide.calls.some((c) => /refs\/heads\/\S*-(x|y|chain)\b/.test(c.prompt) || / --delete (20-save|30-menu|main)\b/.test(c.prompt)), 'a flow prompt makes a chain branch or deletes a group branch')
  expect(!ls.includes('load'), 'with no max_load a load agent ran')
  expect(wide.logs.some((l) => l.startsWith('slot cap: 4 tasks at once')), `the slot cap log is ${wide.logs.find((l) => l.startsWith('slot cap'))}`)
  // Only the ship step merges main, and only into its group branch: no prompt pushes or merges into main.
  expect(!wide.calls.some((c) => !c.label.startsWith('ship ') && / main\b.*merge|merge .*origin\/main|push -q origin main/.test(c.prompt)), 'a flow prompt other than ship merges into or pushes main')
  expect(!wide.calls.some((c) => /push -q origin main|push -q origin HEAD:main|checkout main|gh pr merge \S+ --repo \S+ (--admin|--merge$)/.test(c.prompt)), 'a flow prompt pushes main or merges a PR without --auto')

  // Ship (#307): the last task of each parent lands, then 1 full-suite run on its group branch and 1 PR
  // that closes the parent and merges itself on green. The full suite never runs per task.
  const SUITE = H.ARGS.flow.converge_gate
  for (const [g, parent, own] of [['20-save', 20, ['21', '22', '23']], ['30-menu', 30, ['31', '32', '33']]]) {
    const ships = wide.calls.filter((c) => c.label === `ship ${g}`)
    const sp = ships.length === 1 ? ships[0].prompt : ''
    const at = ls.indexOf(`ship ${g}`)
    expect(ships.length === 1 && own.every((id) => ls.indexOf(`merge ${id}`) < at), `ship ${g}: ${ships.length} ship runs, or one runs before the last task of #${parent} landed: ${ls}`)
    expect(sp.includes(`git merge --no-ff --no-edit origin/main`) && sp.includes(`Run the full suite once on that head: ${SUITE}.`) && sp.includes(`--base main --head ${g}`) && sp.includes(`--body "Closes #${parent}\n`) && sp.includes(`gh pr merge <the PR> --repo example/game --auto --merge`), `ship ${g}: the prompt does not merge main in, run the full suite, open a PR that closes #${parent} and set it to merge itself`)
    expect(sp.indexOf('git merge --no-ff --no-edit origin/main') < sp.indexOf('Run the full suite once') && sp.indexOf('Run the full suite once') < sp.indexOf('gh pr create'), `ship ${g}: the steps are not merge, suite, PR in that order`)
    const row = (wide.result.ships || []).find((x) => x.group === g) || {}
    expect(row.parent === parent && row.pr && row.auto_merge === true && row.suite && row.suite.passed, `ship ${g}: result row ${JSON.stringify(row)}`)
  }
  expect(wide.calls.filter((c) => c.prompt.includes(SUITE)).every((c) => c.label.startsWith('ship ')) && wide.calls.filter((c) => c.prompt.includes(SUITE)).length === 2, 'the full suite runs in a prompt other than the 2 ship runs')
  expect((wide.result.findings || []).length === 0 && !ls.some((l) => l.startsWith('finding ')), 'a green ship filed a finding')

  // A red full suite: no PR, 1 holds finding, the group stays open; the other group ships.
  const redSuite = await flow({ queue: six, cpus: 8 }, {
    group_pr: (n, a, label) => (label === 'ship 20-save' ? { ...a, group: '20-save', suite: { command: SUITE, line: '1 failed', passed: false }, pr: '', auto_merge: false, escalation: '1 failed: test/save.test.ts' } : { ...a, group: label.slice(5) }),
  })
  const rls = labels(redSuite)
  const fcalls = redSuite.calls.filter((c) => c.label.startsWith('finding '))
  const rrow = (redSuite.result.ships || []).find((x) => x.group === '20-save') || {}
  expect(rrow.pr === '' && rrow.auto_merge === false && /red on 20-save/.test(rrow.reason || ''), `red suite: the 20-save row is ${JSON.stringify(rrow)}, not no PR and red`)
  expect(fcalls.length === 1 && fcalls[0].label === 'finding 20-save' && rls.indexOf('finding 20-save') > rls.indexOf('ship 20-save') && /--label kind:bug --label sev:holds/.test(fcalls[0].prompt) && fcalls[0].prompt.includes('1 failed: test/save.test.ts'), `red suite: ${fcalls.length} finding runs, not 1 holds finding after the ship: ${rls}`)
  const rf = redSuite.result.findings || []
  expect(rf.length === 1 && rf[0].severity === 'holds' && rf[0].group === '20-save', `red suite: findings ${JSON.stringify(rf)}`)
  expect(redSuite.result.escalations.some((e) => e.task === '20-save' && e.state === 'ship'), 'red suite: the lead gets no escalation for the open group')
  const other = (redSuite.result.ships || []).find((x) => x.group === '30-menu') || {}
  expect(other.pr && other.auto_merge, `red suite: the other group did not ship: ${JSON.stringify(other)}`)
  // A parent with an open sub-issue opens no PR and files no finding.
  const openSub = await flow({ queue: six.slice(0, 2), cpus: 8 }, { group_pr: (n, a) => ({ ...a, suite: { command: SUITE, line: 'not run: open sub-issues', passed: false }, pr: '', auto_merge: false, open: ['#24'], escalation: 'open sub-issues: #24' }) })
  expect(!labels(openSub).some((l) => l.startsWith('finding ')) && /open sub-issues: #24/.test(((openSub.result.ships || [])[0] || {}).reason || ''), 'open sub-issue: a finding was filed, or the row does not say why')
  metricsOk(wide, '6 tasks')

  // 2. 2 tasks lease the same file: the second starts after the first lands, from the head it landed.
  const pair = [H.flowTask(21, 20, '20-save', 'src/save.ts'), H.flowTask(22, 20, '20-save', 'src/save.ts')]
  const leased = await flow({ queue: pair, cpus: 8 }, { merge: (n, a) => ({ ...a, branch: '20-save', sha: shaOf(n) }) })
  const lls = labels(leased)
  const first = leased.calls.find((c) => c.label === 'merge 21')
  expect(lls.indexOf('check 22') > lls.indexOf('merge 21') && lls.indexOf('build 22') > lls.indexOf('merge 21'), `lease: task 22 starts before 21 lands: ${lls}`)
  expect(promptOf(leased, 'build 21').includes(`.claude/worktrees/21-save ${BASE_SHA}\n`), 'lease: the first task does not start from the group head at the base')
  expect(first && first.answer.sha === shaOf(1) && promptOf(leased, 'build 22').includes(`.claude/worktrees/22-save ${first.answer.sha}\n`), 'lease: the second worker does not start from the head the first landing returned')
  expect(promptOf(leased, 'build 22').includes('same time own them: none.'), 'lease: the second worker gets the files of a task that has landed')
  // A task of another group that leases a free file does not wait.
  const third = await flow({ queue: [...pair, H.flowTask(31, 30, '30-menu', 'src/menu.ts')], cpus: 8 })
  const tls = labels(third)
  expect(tls.indexOf('build 31') < tls.indexOf('merge 21') && promptOf(third, 'build 21').includes('same time own them: src/menu.ts.'), `lease: a free task waited, or a worker does not get the leases beside it: ${tls}`)

  // 3. max_load: the first load read is above it, the next is below: no worker starts before that read.
  const loaded = await flow({ queue: pair.slice(0, 1).concat([H.flowTask(31, 30, '30-menu', 'src/menu.ts')]), cpus: 8, max_load: 1 }, {
    load: (n) => (n === 1 ? { load: 64, cpus: 8 } : { load: 4, cpus: 8 }),
  })
  const loads = loaded.calls.map((c, i) => [c, i]).filter(([c]) => c.label === 'load')
  const firstWork = loaded.calls.findIndex((c) => /^(build|brief|check|merge) /.test(c.label))
  expect(loads.length >= 2 && firstWork > loads[1][1], `max_load: an agent of a task started before the load read below max_load: ${labels(loaded)}`)
  expect(loads.length >= 2 && !loads[0][0].prompt.includes('sleep') && loads[1][0].prompt.includes('sleep 60') && loads.every(([c]) => c.prompt.includes('uptime')), 'max_load: the read after an above read does not wait, or a read does not run uptime')
  expect(loaded.calls.filter((c) => c.label.startsWith('build ')).every((c) => loads.length >= 2 && loaded.calls.indexOf(c) > loads[1][1]) && loaded.result.landed.length === 2, `max_load: a worker started above the load, or the tasks did not land: ${labels(loaded)}`)
  expect(loaded.logs.some((l) => /^load: 8 per core, above 1/.test(l)), 'max_load: no log of the load above the limit')
  for (const bad of [0, -1, '1']) {
    let msg = ''
    try { await flow({ queue: pair, max_load: bad }) } catch (e) { msg = e.message }
    expect(/args\.max_load must be a positive number/.test(msg), `max_load ${JSON.stringify(bad)} is not refused: ${msg}`)
  }

  // A base red holds only its group: the other group lands.
  const red = await flow({ queue: [H.flowTask(21, 20, '20-save', 'src/a.ts'), H.flowTask(22, 20, '20-save', 'src/a.ts'), H.flowTask(31, 30, '30-menu', 'src/menu.ts')], cpus: 8 }, {
    merge: (n, a, label) => (label.startsWith('merge 21') ? { ...a, oracle_passed: false, merged: [], closed: false, pruned: false, escalation: 'make check: 1 failed', base_red: { kind: 'base', check: 'make check', line: '1 failed', tip: BASE_SHA } } : a),
  })
  const br = red.result.base_red || []
  expect(br.length === 1 && br[0].target === '20-save' && br[0].holds.includes('21') && br[0].holds.includes('22'), `base red: ${JSON.stringify(br)}, not 1 hold on 20-save over 21 and 22`)
  expect(same(red.result.landed, ['31']) && red.result.escalations.length === 0 && !labels(red).includes('build 22'), `base red: landed ${red.result.landed}, or a held task built or escalated`)

  // A gh command as the queue: 1 read-only agent lists it first.
  const query = await flow({ queue: 'gh issue list --label ready', claims: { 21: H.claimUrl('21') } })
  expect(labels(query)[0] === 'queue' && promptOf(query, 'queue').includes('Run exactly: gh issue list --label ready') && same(query.result.landed, ['21']), `queue query: ${labels(query)}; landed ${query.result.landed}`)

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`flow: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('flow: 0 passed, 1 failed')
  process.exit(1)
})
