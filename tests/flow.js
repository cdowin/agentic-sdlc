// tests/flow.js - spec checks of the v5 flow loop (#414). Node, no packages.
// It runs plugin/workflows/flow.js under the stub harness of tests/workflows.js (run, ARGS, answerWith),
// loaded without its main(). The stub answers each agent, so these are prompt, order and result checks: no real
// git or gh runs. The tracker is a stub too: each read answers from the issues the test gives it.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, probe, problems, check }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'flow.js')

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const later = (ms, v) => new Promise((resolve) => setTimeout(() => resolve(v), ms))
const sha = (c) => c.repeat(40)
const AT = '2026-10-08T12:00:00Z'
// issue: 1 tracker entry of group <parent>-x; extra facts override.
const issue = (n, parent, more = {}) => ({ issue: n, title: `Issue ${n}`, state: 'open', parent, group: `${parent}-x`, branch: `${n}-x`, tier: 'judgment', blocked_by: [], ...more })
// tracker: the tracker answer; list(n, prompt) gives the issues of read n.
const tracker = (list) => (n, a, label, prompt) => ({ at: AT, issues: list(n, prompt) })
const flow = (args, over) => H.run(file, { ...H.ARGS.flow, ...args }, H.answerWith('flow', over))
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)
const metricsOk = (r, name) => {
  for (const m of r.result.metrics || []) {
    const bad = H.check('metrics', m)
    expect(bad.length === 0, `${name}: metrics row ${m.task}: ${bad.join('; ')}`)
  }
}

async function main() {
  // 1. A re-run mid-way, with no journal: the tracker alone says what is done. 41 is closed, 42 landed before,
  // 43 has a report at head, 44 went quiet 3 h ago, 45 has a live worker (it reports once the read waits), 46 is blocked.
  const mid = (n, prompt) => [
    issue(41, 40, { state: 'closed' }),
    issue(42, 40, { landed: true, report: { branch: '42-x', sha: sha('2') } }),
    issue(43, 40, { report: { branch: '43-x', sha: sha('3') }, activity_at: '2026-10-08T11:50:00Z' }),
    issue(44, 40, { branch: '44-old', activity_at: '2026-10-08T09:00:00Z' }),
    issue(45, 40, prompt.includes('wait-reports') ? { report: { branch: '45-x', sha: sha('5') } } : { activity_at: '2026-10-08T11:55:00Z' }),
    issue(46, 40, { question: 'Which save slot?' }),
  ]
  const re = await flow({ queue: [41, 42, 43, 44, 45, 46] }, { tracker: tracker(mid) })
  const ls = labels(re)
  expect(!ls.some((l) => /^(build|land) (41|42|46)$/.test(l)), `re-run: a closed, landed or blocked issue got an agent: ${ls}`)
  expect(!ls.includes('build 43') && promptOf(re, 'land 43').includes(`merge 43-x at ${sha('3')}, by that SHA`), `re-run: the report of 43 does not land as it is: ${ls}`)
  expect(ls.indexOf('build 44') >= 0 && ls.indexOf('build 44') < ls.indexOf('land 44') && promptOf(re, 'build 44').includes('An earlier builder went quiet on 44-old') && promptOf(re, 'build 44').includes('git push -q -u origin 44-old'), `re-run: the stale 44 does not restart on its branch: ${ls}`)
  const waitRead = re.calls.find((c) => c.def === 'tracker' && c.prompt.includes('wait-reports'))
  expect(waitRead && waitRead.prompt.includes('wait-reports example/game#45@45-x') && waitRead.prompt.includes('WAIT_REPORTS_STALL=120') && !ls.includes('build 45') && ls.indexOf('land 45') > ls.indexOf(waitRead.label), `re-run: the live 45 is not watched, then landed: ${ls}`)
  expect(same(re.result.landed, [43, 44, 45]) && same(re.result.skipped, [41, 42]), `re-run: landed ${re.result.landed}, skipped ${re.result.skipped}`)
  expect(same(re.result.escalations, [{ issue: 46, reason: 'WORKER BLOCKED: Which save slot?' }]), `re-run: escalations ${JSON.stringify(re.result.escalations)}`)
  expect(!ls.includes('ready 40-x') && /#46 not landed/.test(re.result.prs[0].reason || ''), `re-run: a group with a blocked issue left draft: ${JSON.stringify(re.result.prs)}`)
  metricsOk(re, 're-run')

  // 2. Intent-first PR: the draft PR opens before the first builder finishes; an issue that joins mid-run adds its
  // Closes line; after the last landing the PR is marked ready and set to merge itself.
  const events = []
  const join = (n) => [issue(21, 20), ...(n > 1 ? [issue(23, 20)] : [])]
  const intent = await flow({ queue: 'gh issue list --label status:ready --json number' }, {
    tracker: tracker(join),
    pr: (n, a, label, prompt) => later(30, { ...a, closes: (prompt.match(/Closes #\d+/g) || []).map((x) => Number(x.slice(8))) }).then((p) => { events.push(`${label} ${n}`); return p }),
    report: (n, a) => later(10, a).then((r) => { events.push(`report ${r.task}`); return r }),
  })
  const il = labels(intent)
  expect(events.indexOf('pr 20-x 1') >= 0 && events.indexOf('pr 20-x 1') < events.indexOf('report 21'), `intent: the draft PR did not open before the first builder finished: ${events}`)
  const open = promptOf(intent, 'pr 20-x')
  expect(open.includes('gh pr create --repo example/game --draft --base main --head 20-x') && open.includes('Refs #20\n\nCloses #21"') && open.includes('git commit -q --allow-empty'), 'intent: the PR prompt does not open a draft with Refs #20 and Closes #21 on a fresh group branch')
  const add = intent.calls.filter((c) => c.label === 'pr 20-x')[1]
  expect(add && add.prompt.includes('Closes #23') && !add.prompt.includes('Closes #21') && il.lastIndexOf('pr 20-x') < il.indexOf('land 23'), `intent: the mid-run issue 23 does not add its Closes line before it lands: ${il}`)
  expect(promptOf(intent, 'read 1').includes('each issue this command lists, in its order: gh issue list --label status:ready'), 'intent: a gh command queue is not run by the read')
  const ready = promptOf(intent, 'ready 20-x')
  expect(il.indexOf('ready 20-x') > il.indexOf('land 23') && ready.includes('gh pr ready <url> --repo example/game') && ready.includes('--auto --merge') && intent.result.prs[0].auto_merge === true, `intent: the PR is not made ready with auto-merge after the last landing: ${il}`)

  // 3. Order is blocked-by: 32 starts after 31 lands; 33 waits on an issue outside the queue and its group stays a draft.
  const order = await flow({ queue: [31, 32, 33] }, { tracker: tracker(() => [issue(31, 30), issue(32, 30, { blocked_by: [31] }), issue(33, 50, { blocked_by: [99] })]) })
  const ol = labels(order)
  expect(ol.indexOf('build 32') > ol.indexOf('land 31') && !ol.includes('build 33') && !ol.includes('ready 50-x') && ol.includes('ready 30-x'), `blocked-by: ${ol}`)
  expect(order.result.escalations.some((e) => e.issue === 33 && e.reason === 'waits on #99'), `blocked-by: ${JSON.stringify(order.result.escalations)}`)

  // 4. A holds finding of a review keeps its group a draft; the other group is made ready.
  const HOLDS = { task: '21', kind: 'bug', severity: 'holds', title: 'the save file is empty', evidence: 't load: 1 failed', minutes: 5 }
  const held = await flow({}, { landing_review: (n, a, label) => (label === 'review 21' ? { landings: ['21'], findings: [HOLDS] } : a) })
  const hl = labels(held)
  expect(hl.includes('finding review 21 1') && !hl.includes('ready 20-save') && hl.includes('ready 30-menu') && /holds finding/.test(held.result.prs[0].reason || ''), `holds: ${hl}`)

  // 5. Local is the fast check only; CI is the gate. A red check escalates with no step-up; a conflict steps up once.
  const lp = promptOf(held, 'land 21')
  expect(lp.includes('Run the fast check once: make check.') && lp.includes('CI on the push is the gate') && !held.calls.some((c) => /full suite|converge/i.test(c.prompt.replace('Never run the full suite', ''))), 'fast check: a prompt runs more than the fast check')
  const red = await flow({}, { landing: (n, a, label) => (label === 'land 21' ? { ...a, merged: false, check: { command: 'make check', line: '1 failed', passed: false }, escalation: '1 failed' } : a) })
  expect(labels(red).filter((l) => l === 'land 21').length === 1 && red.result.escalations.some((e) => e.issue === 21 && e.reason === '1 failed') && !labels(red).includes('ready 20-save'), `red check: ${labels(red)}`)
  const conflict = await flow({ runtime: H.probe }, { landing: (n, a, label, prompt) => (label === 'land 21' && prompt.includes('Do not resolve it') ? { ...a, merged: false, escalation: 'conflict: src/save.ts' } : a) })
  const steps = conflict.calls.filter((c) => c.label === 'land 21')
  expect(steps.length === 2 && steps[0].model === 'probe-bounded' && steps[1].model === 'probe-judgment' && steps[1].prompt.includes('resolve it when both sides are clear') && conflict.result.landed.includes(21), `conflict: ${steps.map((c) => c.model)}`)
  for (const [k, re2] of [['converge_gate', /args\.converge_gate is gone in v5: CI is the gate/], ['claims', /args\.claims is gone in v5/], ['max_load', /args\.max_load is gone in v5/]]) {
    let msg = ''
    try { await flow({ [k]: 'x' }, {}) } catch (e) { msg = e.message }
    expect(re2.test(msg), `retired args.${k} is not refused: "${msg}"`)
  }

  // 6. Runtime environment (#331): rest tracker access, extra branches and no display change the prompts.
  const envRt = { ...H.probe, environment: { tracker: { access: 'rest', evidence: 'x' }, extra_branches: { status: 'enforced', evidence: 'x' }, display: { status: 'absent', evidence: 'x' } } }
  const envRun = await flow({ runtime: envRt }, {})
  const bp = promptOf(envRun, 'build 21')
  expect(bp.includes('gh api repos/example/game/issues/21/comments -f body=') && !bp.includes('gh issue view') && !bp.includes('gh issue comment') && bp.includes('no display'), 'environment: the builder prompt does not use REST calls or move captures to the lead')
  expect(promptOf(envRun, 'land 21').includes('git fetch -q origin 0123456789abcdef0123456789abcdef01234567') && promptOf(envRun, 'land 21').includes('extra_branches'), 'environment: with extra branches the lander does not land by SHA')
  expect(!promptOf(await flow({}, {}), 'build 21').includes('no display'), 'environment: a default runtime moves captures to the lead')
  const blind = await flow({ runtime: { ...H.probe, environment: { tracker: { access: 'none', evidence: 'x' } } } }, { tracker: tracker(() => [issue(21, 20, { body: 'Save the game to slot 1.' })]) })
  expect(promptOf(blind, 'build 21').includes('Save the game to slot 1.') && !promptOf(blind, 'build 21').includes('WORKER STARTED') && promptOf(blind, 'read 1').includes('body: the issue body, verbatim'), 'environment: with no tracker access the builder does not get the body, or is asked to post')

  // 7. A remote runtime: the builder and lander prompts name the branch, never a place.
  const far = await flow({ runtime: { ...H.probe, remote: true } }, {})
  expect(promptOf(far, 'build 21').includes('build on branch 21-save') && promptOf(far, 'land 21').includes('Get branch 20-save at origin/20-save'), 'remote: a prompt does not name the branch')

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`flow: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('flow: 0 passed, 1 failed')
  process.exit(1)
})
