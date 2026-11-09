// tests/flow.js - spec checks of the v5 flow loop (#414). Node, no packages.
// It runs plugin/workflows/flow.js under the stub harness of tests/workflows.js (run, ARGS, answerWith),
// loaded without its main(). The stub answers each agent, so these are prompt, order and result checks: no real
// git or gh runs. The tracker is a stub too (sim): each read answers from the issues the test gives it, with each
// issue the run landed marked landed, and 1 group PR per group that Closes its open issues.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, probe, problems, check }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'flow.js')
const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'contract', 'tracker.ok.json'), 'utf8')).issues

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const later = (ms, v) => new Promise((resolve) => setTimeout(() => resolve(v), ms))
const sha = (c) => c.repeat(40)
const AT = '2026-10-08T12:00:00Z'
// issue: 1 tracker entry of group <parent>-x; extra facts override.
const issue = (n, parent, more = {}) => ({ issue: n, title: `Issue ${n}`, state: 'open', parent, group: `${parent}-x`, branch: `${n}-x`, tier: 'judgment', blocked_by: [], landed: false, ...more })
const passed = (branch, s) => ({ branch, sha: s, passed: true })
// sim: the answers of a tracker that remembers each landing. list(n, prompt) gives the issues of read n;
// closes and holds override a group's PR Closes list and its open holds findings.
function sim(list, over = {}, { closes = {}, holds = {} } = {}) {
  const landed = new Set()
  return {
    ...over,
    landing: (n, a, label, prompt) => Promise.resolve(over.landing ? over.landing(n, a, label, prompt) : a).then((x) => {
      if (x && x.merged) landed.add(Number(label.split(' ')[1]))
      return x
    }),
    tracker: (n, a, label, prompt) => {
      const is = list(n, prompt).map((e) => (landed.has(e.issue) ? { ...e, landed: true } : e))
      const gs = [...new Set(is.map((e) => e.group))].map((g) => ({ group: g, pr: `https://x/pull/${g}`, closes: closes[g] || is.filter((e) => e.group === g && e.state === 'open').map((e) => e.issue), holds: holds[g] || [] }))
      return { at: AT, issues: is, groups: gs }
    },
  }
}
const flow = (args, over) => H.run(file, { ...H.ARGS.flow, ...args }, H.answerWith('flow', over))
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)
const metricsOk = (r, name) => {
  for (const m of r.result.metrics || []) {
    const bad = H.check('metrics', m)
    expect(bad.length === 0, `${name}: metrics row ${m.task}: ${bad.join('; ')}`)
  }
}
const fixture = (over, opts) => sim(() => FIXTURE, over, opts)

async function main() {
  // 1. A re-run mid-way, with no journal: the tracker alone says what is done. 41 is closed, 42 landed before,
  // 43 has a passed report at head, 44 went quiet 3 h ago, 45 has a live worker (it reports once the read waits),
  // 46 is blocked, and 47 has a report without passed (a failing run): it never lands.
  const mid = (n, prompt) => [
    issue(41, 40, { state: 'closed' }),
    issue(42, 40, { landed: true, report: passed('42-x', sha('2')) }),
    issue(43, 40, { report: passed('43-x', sha('3')), activity_at: '2026-10-08T11:50:00Z' }),
    issue(44, 40, { branch: '44-old', activity_at: '2026-10-08T09:00:00Z' }),
    issue(45, 40, prompt.includes('wait-reports') ? { report: passed('45-x', sha('5')) } : { activity_at: '2026-10-08T11:55:00Z' }),
    issue(46, 40, { question: 'Which save slot?' }),
    issue(47, 40, { report: { branch: '47-x', sha: sha('7') }, activity_at: '2026-10-08T11:58:00Z' }),
  ]
  const re = await flow({ queue: [41, 42, 43, 44, 45, 46, 47] }, sim(mid))
  const ls = labels(re)
  expect(!ls.some((l) => /^(build|land) (41|42|46|47)$/.test(l)), `re-run: a closed, landed, blocked or not-passed issue got an agent: ${ls}`)
  expect(!ls.includes('build 43') && promptOf(re, 'land 43').includes(`merge 43-x at ${sha('3')}, by that SHA`), `re-run: the report of 43 does not land as it is: ${ls}`)
  expect(ls.indexOf('build 44') >= 0 && ls.indexOf('build 44') < ls.indexOf('land 44') && promptOf(re, 'build 44').includes('An earlier builder went quiet on 44-old') && promptOf(re, 'build 44').includes('git push -q -u origin 44-old'), `re-run: the stale 44 does not restart on its branch: ${ls}`)
  const waitRead = re.calls.find((c) => c.def === 'tracker' && c.prompt.includes('wait-reports'))
  expect(waitRead && waitRead.prompt.includes("/bin/wait-reports\" 'example/game#45@45-x'") && waitRead.prompt.includes('WAIT_REPORTS_STALL=60') && !ls.includes('build 45') && ls.indexOf('land 45') > ls.indexOf(waitRead.label), `re-run: the live 45 is not watched, then landed: ${ls}`)
  expect(same(re.result.landed, [43, 44, 45]) && same(re.result.skipped, [41, 42]), `re-run: landed ${re.result.landed}, skipped ${re.result.skipped}`)
  expect(same(re.result.escalations.map((e) => e.issue), [46, 47]) && /without passed/.test(re.result.escalations[1].reason), `re-run: escalations ${JSON.stringify(re.result.escalations)}`)
  expect(!ls.includes('ready 40-x'), `re-run: a group with a blocked issue left draft: ${ls}`)
  metricsOk(re, 're-run')
  // The read is queue-state, run as is: the agent invents no fact.
  const rp = promptOf(re, 'read 1')
  expect(rp.includes('/bin/queue-state') && rp.includes("'example/game' '41 42 43 44 45 46 47'") && /stdout/.test(rp), `read: the tracker read does not run queue-state: ${rp.slice(0, 300)}`)

  // 2. Intent-first PR: the draft PR opens before the first builder finishes; an issue that joins mid-run adds its
  // Closes line; after the last landing the PR is marked ready and set to merge itself.
  const events = []
  const join = (n) => [issue(21, 20), ...(n > 1 ? [issue(23, 20)] : [])]
  const intent = await flow({ queue: 'gh issue list --label status:ready --json number -q .[].number' }, sim(join, {
    pr: (n, a, label, prompt) => later(30, { ...a, closes: (prompt.match(/Closes #\d+/g) || []).map((x) => Number(x.slice(8))) }).then((p) => { events.push(`${label} ${n}`); return p }),
    report: (n, a) => later(10, a).then((r) => { events.push(`report ${r.task}`); return r }),
  }))
  const il = labels(intent)
  expect(events.indexOf('pr 20-x 1') >= 0 && events.indexOf('pr 20-x 1') < events.indexOf('report 21'), `intent: the draft PR did not open before the first builder finished: ${events}`)
  const open = promptOf(intent, 'pr 20-x')
  expect(open.includes('gh pr create --repo example/game --draft --base main --head 20-x') && /Refs #20\n\nCloses #21\n/.test(open) && open.includes('git commit -q --allow-empty'), 'intent: the PR prompt does not open a draft with Refs #20 and Closes #21 on a fresh group branch')
  const add = intent.calls.filter((c) => c.label === 'pr 20-x')[1]
  expect(add && add.prompt.includes('Closes #23') && !add.prompt.includes('Closes #21') && il.lastIndexOf('pr 20-x') < il.indexOf('land 23'), `intent: the mid-run issue 23 does not add its Closes line before it lands: ${il}`)
  expect(promptOf(intent, 'read 1').includes("'gh issue list --label status:ready --json number -q .[].number'"), 'intent: a gh command queue is not passed to queue-state')
  const ready = promptOf(intent, 'ready 20-x')
  expect(il.indexOf('ready 20-x') > il.indexOf('land 23') && ready.includes('gh pr ready <url> --repo example/game') && !/--auto/.test(ready) && il.indexOf('merge 20-x') > il.indexOf('ready 20-x') && promptOf(intent, 'merge 20-x').includes('--merge --match-head-commit abcdefabcdefabcdefabcdefabcdefabcdefabcd') && (intent.result.prs[0] || {}).merged === true, `intent: the PR is not made ready, then merged pinned to its head after its checks: ${il}`)
  // The ready gate: a required check SKIPPED on the draft push (GitHub counts a skip as passing), SKIPPED after
  // ready, or still pending, never merges; the lead gets the PR and the check by name.
  const readyWith = (checks) => flow({ queue: [21] }, sim(() => [issue(21, 20)], { pr: (n, a, label) => (label.startsWith('ready ') ? { ...a, ready: true, auto_merge: undefined, merged: undefined, required: ['ci'], ready_at: '2026-10-08T12:45:00Z', checks } : a) }))
  for (const [name, checks, why] of [
    ['draft skip', [{ name: 'ci', status: 'completed', conclusion: 'skipped', started_at: '2026-10-08T12:40:00Z' }], /ci has no run since ready/],
    ['skip after ready', [{ name: 'ci', status: 'completed', conclusion: 'skipped', started_at: '2026-10-08T12:46:00Z' }], /ci was SKIPPED/],
    ['pending', [{ name: 'ci', status: 'in_progress', conclusion: '', started_at: '2026-10-08T12:46:00Z' }], /ci is in_progress/],
    ['other check only', [{ name: 'lint', status: 'completed', conclusion: 'success', started_at: '2026-10-08T12:46:00Z' }], /ci has no run since ready/],
  ]) {
    const r = await readyWith(checks)
    expect(labels(r).includes('ready 20-x') && !labels(r).includes('merge 20-x') && r.result.escalations.some((e) => e.group === '20-x' && why.test(e.reason)), `ready gate, ${name}: ${labels(r)} ${JSON.stringify(r.result.escalations)}`)
  }
  const green = await readyWith([{ name: 'ci', status: 'completed', conclusion: 'skipped', started_at: '2026-10-08T12:40:00Z' }, { name: 'ci', status: 'completed', conclusion: 'success', started_at: '2026-10-08T12:46:00Z' }])
  expect(labels(green).includes('merge 20-x'), `ready gate: a passed run since ready does not merge: ${labels(green)}`)

  // 3. Finding 1 (critical): ready only when every issue the PR Closes is landed per the read. 29 is in the
  // Closes list (an earlier run added it) and is not landed: the PR stays a draft, though 21 landed.
  const closes = await flow({ queue: [21] }, sim(() => [issue(21, 20), issue(29, 20, { question: 'Which slot?' })], {}, { closes: { '20-x': [21, 29] } }))
  expect(labels(closes).includes('land 21') && !labels(closes).includes('ready 20-x') && /#29/.test((closes.result.prs[0] || {}).reason || ''), `closes: ${labels(closes)} ${JSON.stringify(closes.result.prs)}`)
  const closesGone = await flow({ queue: [21] }, sim(() => [issue(21, 20)], {}, { closes: { '20-x': [21, 30] } }))
  expect(!labels(closesGone).includes('ready 20-x'), `closes: an issue of the Closes list that the read lacks still made the PR ready: ${labels(closesGone)}`)
  // Finding 6: an open holds finding of the group (from an earlier run) keeps it a draft.
  // m7: an issue the PR Closes that was closed with no landing keeps the PR a draft and goes to the lead by name.
  const shut = await flow({ queue: [21] }, sim(() => [issue(21, 20), issue(29, 20, { state: 'closed' })], {}, { closes: { '20-x': [21, 29] } }))
  expect(!labels(shut).includes('ready 20-x') && shut.result.escalations.some((e) => e.issue === 29 && /closed without a landing/.test(e.reason) && e.reason.includes('https://x/pull/20-x')), `closed in Closes: ${labels(shut)} ${JSON.stringify(shut.result.escalations)}`)
  // A branch with a leading - or .. is unsafe: escalated, never built.
  const unsafe = await flow({ queue: [21, 22] }, sim(() => [issue(21, 20, { branch: '-rf' }), issue(22, 20, { branch: 'a/../b' })]))
  expect(!labels(unsafe).some((l) => /^(build|land) /.test(l)) && unsafe.result.escalations.filter((e) => /shell would read/.test(e.reason)).length === 2, `unsafe ref: ${labels(unsafe)}`)
  const heldBefore = await flow({ queue: [21] }, sim(() => [issue(21, 20)], {}, { holds: { '20-x': ['https://x/issues/90'] } }))
  expect(!labels(heldBefore).includes('ready 20-x') && /issues\/90/.test((heldBefore.result.prs[0] || {}).reason || ''), `holds before: ${labels(heldBefore)}`)
  // The ready decision reads the tracker after the reviews end.
  const il2 = labels(intent)
  expect(il2.lastIndexOf('read ' + (il2.filter((l) => l.startsWith('read ')).length)) > il2.lastIndexOf('review batch 1') && il2.lastIndexOf('read ') < il2.indexOf('ready 20-x'), `ready: no tracker read between the reviews and ready: ${il2}`)

  // 4. Order is blocked-by: 32 starts after 31 lands in its group. 52 (another group) waits on 31 until 31 is
  // closed: its code is not on 50-x (#418). 33 waits on an issue outside the queue.
  const order = await flow({ queue: [31, 32, 52, 33] }, sim(() => [issue(31, 30), issue(32, 30, { blocked_by: [31] }), issue(52, 50, { blocked_by: [31] }), issue(33, 60, { blocked_by: [99] })]))
  const ol = labels(order)
  expect(ol.indexOf('build 32') > ol.indexOf('land 31') && !ol.includes('build 33') && !ol.includes('build 52') && ol.includes('ready 30-x'), `blocked-by: ${ol}`)
  expect(order.result.escalations.some((e) => e.issue === 33 && e.reason === 'waits on #99') && order.result.escalations.some((e) => e.issue === 52 && e.reason === 'waits on #31'), `blocked-by: ${JSON.stringify(order.result.escalations)}`)

  // 5. A holds finding of a review keeps its group a draft; the other group is made ready.
  const HOLDS = { task: '21', kind: 'bug', severity: 'holds', title: 'the save file is empty', evidence: 't load: 1 failed', minutes: 5 }
  const held = await flow({}, fixture({ landing_review: (n, a, label) => (label === 'review 21' ? { landings: ['21'], findings: [HOLDS] } : a) }))
  const hl = labels(held)
  expect(hl.includes('finding review 21 1') && !hl.includes('ready 20-save') && hl.includes('ready 30-menu') && /holds finding/.test((held.result.prs[0] || {}).reason || ''), `holds: ${hl}`)
  expect(((held.result.metrics.find((m) => m.task === "21") || {}).findings || {}).critical === 1, `holds: the metrics row of 21 does not count its holds finding: ${JSON.stringify(held.result.metrics)}`)

  // 6. Finding 3: no untrusted text inside a double-quoted shell argument. A finding title with quotes and $( )
  // goes in a quoted heredoc only.
  const EVIL = { task: '21', kind: 'bug', severity: 'major', title: 'a "quote" $(touch /tmp/pwned) `id`', evidence: 'x"; rm -rf ~; "', minutes: 1 }
  const shell = await flow({}, fixture({ landing_review: (n, a, label) => (label === 'review 21' ? { landings: ['21'], findings: [EVIL] } : a) }))
  const fp = promptOf(shell, 'finding review 21 1')
  // docLines: the index of each line inside a quoted heredoc (<<'X' up to the line X), in shell order.
  const docLines = (text) => {
    const inside = new Set()
    const pending = []
    text.split('\n').forEach((l, i) => {
      if (pending.length > 0 && l === pending[0]) return pending.shift()
      if (pending.length > 0) return inside.add(i)
      for (const m of l.matchAll(/<<'(\w+)'/g)) pending.push(m[1])
    })
    return inside
  }
  const lines = fp.split('\n')
  const outside = lines.map((l, i) => [l, i]).filter(([l]) => l.includes('$(touch') || l.includes('rm -rf'))
  const inDoc = ([, i]) => docLines(fp).has(i)
  expect(fp.includes('--body-file -') && fp.includes("<<'AGENTIC_SDLC_EOF'") && outside.length > 0 && outside.every(inDoc), `shell: an untrusted line is outside a quoted heredoc: ${outside.filter((x) => !inDoc(x)).map((x) => x[0]).join(' | ')}`)
  expect(!shell.calls.some((c) => /--(body|title) "(?!\$\()/.test(c.prompt)), `shell: a prompt passes --body or --title as a double-quoted literal: ${shell.calls.filter((c) => /--(body|title) "(?!\$\()/.test(c.prompt)).map((c) => c.label)}`)

  // 7. Local is the fast check only; CI is the gate. A red check escalates with no step-up and posts the refusal
  // on the issue, so a re-run does not land it; a conflict steps up once. args.gate is required.
  const lp = promptOf(held, 'land 21')
  expect(lp.includes('Run the fast check once: make check.') && lp.includes('CI on the push is the gate') && !held.calls.some((c) => /full suite|converge/i.test(c.prompt.replace('Never run the full suite', ''))), 'fast check: a prompt runs more than the fast check')
  expect(lp.includes('WORKER BLOCKED branch=21-save') && lp.includes('--body-file -'), 'refusal: a red landing does not post WORKER BLOCKED on the issue')
  const red = await flow({}, fixture({ landing: (n, a, label) => (label === 'land 21' ? { ...a, merged: false, check: { command: 'make check', line: '1 failed', passed: false }, escalation: '1 failed' } : a) }))
  expect(labels(red).filter((l) => l === 'land 21').length === 1 && red.result.escalations.some((e) => e.issue === 21 && e.reason === '1 failed') && !labels(red).includes('ready 20-save'), `red check: ${labels(red)}`)
  const conflict = await flow({ runtime: H.probe }, fixture({ landing: (n, a, label, prompt) => (label === 'land 21' && prompt.includes('Do not resolve it') ? { ...a, merged: false, escalation: 'conflict: src/save.ts' } : a) }))
  const steps = conflict.calls.filter((c) => c.label === 'land 21')
  expect(steps.length === 2 && steps[0].model === 'probe-bounded' && steps[1].model === 'probe-judgment' && steps[1].prompt.includes('resolve it when both sides are clear') && conflict.result.landed.includes(21), `conflict: ${steps.map((c) => c.model)}`)
  for (const [over, re2] of [[{ converge_gate: 'x' }, /args\.converge_gate is gone in v5: CI is the gate/], [{ claims: 'x' }, /args\.claims is gone in v5/], [{ gate: undefined }, /flow needs args\.gate/]]) {
    let msg = ''
    try { await flow(over, {}) } catch (e) { msg = e.message }
    expect(re2.test(msg), `args ${JSON.stringify(over)} is not refused: "${msg}"`)
  }

  // 8. Runtime environment (#331): rest tracker access, extra branches and no display change the prompts.
  const envRt = { ...H.probe, environment: { tracker: { access: 'rest', evidence: 'x' }, extra_branches: { status: 'enforced', evidence: 'x' }, display: { status: 'absent', evidence: 'x' } } }
  const envRun = await flow({ runtime: envRt }, fixture())
  const bp = promptOf(envRun, 'build 21')
  expect(bp.includes('gh api repos/example/game/issues/21/comments -F body=@-') && !bp.includes('gh issue view') && !bp.includes('gh issue comment') && bp.includes('no display'), 'environment: the builder prompt does not use REST calls or move captures to the lead')
  expect(bp.includes('WORKER REPORT branch=21-save head=<the SHA you pushed> passed') && /only when the test and the fast check passed/.test(bp), 'environment: the builder is not told to post passed only on green')
  expect(promptOf(envRun, 'land 21').includes('git fetch -q origin 0123456789abcdef0123456789abcdef01234567') && promptOf(envRun, 'land 21').includes('extra_branches'), 'environment: with extra branches the lander does not land by SHA')
  expect(!promptOf(await flow({}, fixture()), 'build 21').includes('no display'), 'environment: a default runtime moves captures to the lead')
  const blind = await flow({ runtime: { ...H.probe, environment: { tracker: { access: 'none', evidence: 'x' } } } }, sim(() => [issue(21, 20, { body: 'Save the game to slot 1.' })]))
  expect(promptOf(blind, 'build 21').includes('Save the game to slot 1.') && !promptOf(blind, 'build 21').includes('WORKER STARTED') && promptOf(blind, 'read 1').includes('queue-state" --body'), 'environment: with no tracker access the builder does not get the body, or is asked to post')
  expect(promptOf(blind, 'land 21').includes('WORKER REPORT branch=21-x head='), 'environment: with no tracker access the lander does not post the report for the builder')

  // 9. A remote runtime: the builder and lander prompts name the branch, never a place.
  const far = await flow({ runtime: { ...H.probe, remote: true } }, fixture())
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
