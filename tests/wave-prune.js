// tests/wave-prune.js - spec checks of close and prune in wave (#298). Node, no packages.
// It runs plugin/workflows/wave.js under the stub harness of tests/workflows.js (run, ARGS, answerWith),
// loaded without its main(). A task issue closes, and its branch and worktree go, when its own merge is
// validated; the parent issue stays open; after the converge no chain branch is left; a closed task that
// does not end merged reopens. The stub answers every agent with one canned report, so no real git or gh runs.
// Checks that observe BEHAVIOUR: the result rows (tasks, metrics, escalations) and the order of agent calls
// (labels of r.calls): the close, reopen and converge call order, the row of a lying, a half-failed and a
// rework merge. Checks that still pin PROMPT TEXT: the order of the steps inside the one merge prompt (push,
// close, ancestor check, delete), which a single canned report cannot show.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, waveOne, twoChains, claimUrl, problems, check }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'wave.js')
const ROOT = '.claude/worktrees'
const WAVE = '10-wave-1'
const AT = '2026-10-08T12:31:00Z'

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const promptsOf = (r, label) => r.calls.filter((c) => c.label === label).map((c) => c.prompt)
const rowOf = (r, id) => (r.result.metrics || []).find((m) => m.task === id) || {}
const taskOf = (r, id) => (r.result.tasks || []).find((t) => t.task === id) || {}
const closes = (r, issue) => r.calls.filter((c) => c.prompt.includes(`gh issue close ${issue} `))
const RED = (n, a) => ({ ...a, oracle_passed: false, merged: [], escalation: 't read: 1 failed', closed: true, pruned: true })
const wave = (args, over = {}) => H.run(file, { ...H.ARGS.wave, ...args }, H.answerWith('wave', over))
const metricsOk = (r, name) => {
  for (const m of r.result.metrics || []) {
    const bad = H.check('metrics', m)
    expect(bad.length === 0, `${name}: metrics row ${m.task}: ${bad.join('; ')}`)
  }
}

async function main() {
  // 1. A validated merge of read: close with the merge SHA, oracle and gate lines; the ancestor check
  // before the delete; the task worktree removal. The parent issue 10 gets no close anywhere.
  const full = await wave({})
  const mr = promptOf(full, 'merge read')
  const push = mr.indexOf(`git push -q origin ${WAVE}.`)
  const step = mr.indexOf('Close and prune, only when the merge is validated')
  expect(push >= 0 && step > push, 'merge read: the close step is not after the push of the wave branch')
  expect(mr.includes(`gh issue close 11 --repo example/game --comment "Merged ${WAVE}-read into ${WAVE} at <the full SHA of the push>. Oracle: t read:`) && mr.includes('Gate: make check: <its last output line>.'), 'merge read: the close command lacks the merge SHA, the oracle line or the gate line')
  const anc = mr.indexOf(`git merge-base --is-ancestor origin/<branch> origin/${WAVE} exits 0`)
  const del = mr.indexOf('git push -q origin --delete <branch>')
  expect(anc > step && del > anc && mr.includes(`For each of these branches: ${WAVE}-read.`), 'merge read: the delete of the task branch is not behind the ancestor check')
  expect(mr.includes(`git worktree remove --force ${ROOT}/<branch>`) && mr.includes(`Keep the worktree ${ROOT}/${WAVE}`), 'merge read: the task worktree is not removed, or the wave worktree is not kept')
  expect(!/--delete [^<]/.test(mr) && !/--delete \S*\*/.test(mr), 'merge read: a delete names a branch other than the exact listed one, or a pattern')
  expect(closes(full, 10).length === 0 && !full.calls.some((c) => c.prompt.includes('gh issue close 10')), 'the parent issue 10 gets a close command')
  expect(rowOf(full, 'read').closed_at === AT && rowOf(full, 'read').pruned === true, `read: the metrics row has closed_at ${rowOf(full, 'read').closed_at} and pruned ${rowOf(full, 'read').pruned}, not ${AT} and true`)
  expect(taskOf(full, 'read').closed_at === AT && taskOf(full, 'read').pruned === true, 'read: the task row does not record closed_at and pruned')
  // A split task deletes its part branches with its own branch.
  expect(promptOf(full, 'merge write').includes(`For each of these branches: ${WAVE}-write ${WAVE}-write-read ${WAVE}-write-write.`), 'merge write: the split part branches are not deleted with the task branch')
  // A rework merge of a closed task does not close it twice; it comments and deletes the -r1 branch.
  const rw = promptsOf(full, 'merge write').find((p) => p.includes(`${WAVE}-write-r1 at`)) || ''
  expect(rw.includes('do not close it again') && rw.includes('gh issue comment 12 --repo example/game') && !rw.includes('gh issue close 12') && rw.includes(`For each of these branches: ${WAVE}-write-r1.`), 'merge write rework: the closed issue is closed again, or the r1 branch is not deleted')
  metricsOk(full, 'full')
  const fl = labels(full)
  expect(fl.indexOf('merge read') >= 0 && !fl.some((l) => l.startsWith('reopen')) && !fl.some((l) => /\b10\b/.test(l.replace(WAVE, ''))), `full run: a reopen call, or a call for the parent issue 10, in ${fl}`)
  // The close of write is in its first merge only: a rework merge never closes it twice (pinned from the run).
  const firstClose = full.calls.filter((c) => c.prompt.includes('gh issue close 12 ') && !c.prompt.includes(`${WAVE}-write-r1 at`)).length
  expect(firstClose === 1 && closes(full, 12).length === 1, `write: ${firstClose} first-merge close calls and ${closes(full, 12).length} in all, not 1 and 1`)
  const mw = full.calls.filter((c) => c.label === 'merge write')
  expect(mw.length === 2 && mw[1].prompt.includes(`${WAVE}-write-r1 at`) && !mw[1].prompt.includes('gh issue close 12') && rowOf(full, 'write').closed_at === AT, `write rework: ${mw.length} merge calls, closed_at ${rowOf(full, 'write').closed_at}, not 2 calls and ${AT}`)

  // 2. Two chains: the converge deletes each chain branch after the push; the result names them.
  const chains = await wave({ graph: H.twoChains, claims: Object.fromEntries(['a', 'b', 'docs'].map((id) => [id, H.claimUrl(id)])) }, {
    merge: (n, a, label) => (label === 'converge' ? { ...a, branch: WAVE, merged: [`${WAVE}-x`, `${WAVE}-y`], pruned_branch: `${WAVE}-x ${WAVE}-y` } : a),
  })
  const cv = promptOf(chains, 'converge')
  const cpush = cv.indexOf(`git push -q origin ${WAVE}.`)
  const cdel = cv.indexOf('git push -q origin --delete <branch>')
  expect(cpush >= 0 && cdel > cpush && cv.includes(`For each of ${WAVE}-x ${WAVE}-y: when git merge-base --is-ancestor origin/<branch> origin/${WAVE} exits 0`) && cv.includes(`git worktree remove --force ${ROOT}/<branch>`), 'converge: the chain branches are not deleted after the push behind the ancestor check')
  expect(cv.includes(`Never delete ${WAVE} or main`), 'converge: the prompt does not keep the wave branch and main')
  const pb = ((chains.result.converge || {}).merge || {}).pruned_branch || ''
  expect(pb.includes(`${WAVE}-x`) && pb.includes(`${WAVE}-y`), `converge: convergence.merge.pruned_branch is "${pb}"`)
  // A chain task merge deletes its task branch behind an ancestor check on its chain branch, never the chain branch.
  const ma = promptOf(chains, 'merge a')
  expect(ma.includes(`For each of these branches: ${WAVE}-a.`) && ma.includes(`origin/<branch> origin/${WAVE}-x exits 0`), 'merge a: the chain task branch is not deleted behind an ancestor check on its chain branch')
  expect(!chains.calls.some((c) => c.label !== 'converge' && c.prompt.includes('--delete') && /For each of these branches: [^.]*10-wave-1-[xy][ .]/.test(c.prompt)), 'a task merge deletes a chain branch before the converge')
  const cl = labels(chains)
  const cvAt = cl.indexOf('converge')
  expect(cvAt > cl.lastIndexOf('merge a') && cvAt > cl.lastIndexOf('merge b') && cl.lastIndexOf('merge a') >= 0 && cl.lastIndexOf('merge b') >= 0, `chains: the converge is not after every chain task merge: ${cl}`)
  metricsOk(chains, 'chains')

  // 3. The escalated hud and an unvalidated merge keep their issue and branch.
  expect(closes(full, 15).length === 0 && !full.calls.some((c) => c.prompt.includes(`${WAVE}-hud`) && c.prompt.includes('--delete')), 'hud escalated, but an agent got its close or delete')
  expect(rowOf(full, 'hud').closed_at === undefined && rowOf(full, 'hud').pruned === undefined && taskOf(full, 'hud').closed_at === undefined, 'hud escalated, but its row has closed_at or pruned')
  const red = await wave(H.waveOne, { merge: RED })
  expect(labels(red).includes('merge read step-up') && taskOf(red, 'read').state === 'escalated', `a red merge did not escalate read: ${labels(red)}`)
  expect(closes(red, 11).every((c) => /^merge read( step-up)?$/.test(c.label) && c.prompt.includes('When the merge is red, aborted or not pushed, close nothing and delete nothing')), 'a red merge: a close reaches an agent outside the guarded merge step')
  expect(rowOf(red, 'read').closed_at === undefined && rowOf(red, 'read').pruned === undefined && taskOf(red, 'read').closed_at === undefined && taskOf(red, 'read').pruned === undefined, 'a red merge that claims closed and pruned is recorded as closed or pruned')
  metricsOk(red, 'red')
  // A red merge that LIES (closed, pruned and a pruned branch): no row keeps any of them.
  const lie = await wave(H.waveOne, { merge: (n, a) => ({ ...RED(n, a), pruned_branch: `${WAVE}-read` }) })
  expect(taskOf(lie, 'read').state === 'escalated' && [taskOf(lie, 'read'), rowOf(lie, 'read')].every((x) => x.closed_at === undefined && x.pruned === undefined && x.pruned_branch === undefined), `a lying red merge: task ${JSON.stringify([taskOf(lie, 'read').closed_at, taskOf(lie, 'read').pruned, taskOf(lie, 'read').pruned_branch])}, row ${JSON.stringify([rowOf(lie, 'read').closed_at, rowOf(lie, 'read').pruned, rowOf(lie, 'read').pruned_branch])}`)
  // A green merge whose close failed: still merged; no closed_at; the task row records pruned, the metrics row only with a closed_at. A failed close never fails the merge.
  const half = await wave(H.waveOne, { merge: (n, a) => ({ ...a, closed: false, pruned: true, pruned_branch: `${WAVE}-read`, kept: ['x: kept branch'] }) })
  expect(taskOf(half, 'read').state !== 'escalated' && (half.result.done || []).includes('read') && taskOf(half, 'read').closed_at === undefined && rowOf(half, 'read').closed_at === undefined && taskOf(half, 'read').pruned === true && rowOf(half, 'read').pruned === undefined, `a failed close: state ${taskOf(half, 'read').state}, closed_at ${rowOf(half, 'read').closed_at}, task pruned ${taskOf(half, 'read').pruned}, row pruned ${rowOf(half, 'read').pruned}`)
  metricsOk(half, 'half')

  // 4. The claim guard: the merge prompt names the other open claims; a solo run says it has none.
  expect(mr.includes(`No other open claim may name ${WAVE}-read`) && mr.includes("gh issue view 11 --repo example/game --json comments") && mr.includes(H.claimUrl('write')) && mr.includes('close nothing and delete nothing: add "<branch>: named by the open claim <url>" to kept'), 'merge read: the prompt lacks the claim guard')
  const solo = await wave({ ...H.waveOne, claims: 'solo' })
  expect(promptOf(solo, 'merge read').includes('This is a solo run: there is no other claim to check.'), 'solo: the merge prompt does not skip the claim check')

  // 5. Re-run: a pruned, merged task (no branch head, its merge subject on the wave branch) is skipped.
  const again = await wave(H.waveOne, { remote: (n, a, label) => (label === 'remote check' ? { merges: [`Merge ${WAVE}-read into ${WAVE}`], heads: [] } : a) })
  expect(!labels(again).some((l) => /^(build|merge) read/.test(l)) && (again.result.merged_before || []).includes('read'), `a pruned, merged task was not skipped on a re-run: ${labels(again)}`)
  // A zero SHA on a pruned branch whose merge subject is on the target: merged, not rebuilt or escalated.
  const zero = await wave(H.waveOne, {
    report: (n, a) => ({ ...a, sha: '0'.repeat(40) }),
    remote: (n, a, label) => (label === 'remote check read' ? { merges: [`Merge ${WAVE}-read into ${WAVE}`], heads: [{ branch: WAVE, sha: '89abcdef0123456789abcdef0123456789abcdef' }] } : a),
  })
  expect(promptOf(zero, 'remote check read').includes(`If ${WAVE}-read is not on the remote`) && !labels(zero).includes('merge read') && zero.result.transitions.some((t) => t.task === 'read' && t.to === 'integrated'), 'a zero SHA on a pruned, merged branch was not recognised by its merge subject')

  // 6. A task closed at its first validated merge, then escalated (its rework merge is red): its issue
  // reopens with a comment that names the reason, and its rows record reopened with no closed_at.
  const late = await wave({}, { merge: (n, a, label, prompt) => (label.startsWith('merge write') && prompt.includes(`${WAVE}-write-r1 at`) ? RED(n, a) : a) })
  const ro = promptOf(late, 'reopen write')
  expect(taskOf(late, 'write').state === 'escalated' && ro.includes('gh issue reopen 12 --repo example/game --comment') && ro.includes('t read: 1 failed'), `write escalated after its close, but no reopen names the reason: ${labels(late)}\n${ro}`)
  expect(taskOf(late, 'write').reopened === true && taskOf(late, 'write').closed_at === undefined && rowOf(late, 'write').reopened === true && rowOf(late, 'write').closed_at === undefined, 'write reopened, but its rows do not record reopened with closed_at cleared')
  expect(!labels(late).includes('reopen read') && rowOf(late, 'read').closed_at === AT, 'read ended merged, but it was reopened')
  metricsOk(late, 'late')
  const ll = labels(late)
  expect(ll.indexOf('reopen write') > ll.lastIndexOf('merge write') && ll.lastIndexOf('merge write') > ll.indexOf('merge read'), `late: the reopen is not after the last merge write: ${ll}`)
  // A failed reopen keeps closed_at and says so in the escalation.
  const stuck = await wave({}, { merge: (n, a, label, prompt) => (label.startsWith('merge write') && prompt.includes(`${WAVE}-write-r1 at`) ? RED(n, a) : a), verdict: (n, a, label) => (label === 'reopen write' ? { agree: false, reason: 'HTTP 403' } : a) })
  const esc = ((stuck.result.escalations || []).find((e) => e.task === 'write') || {}).reason || ''
  expect(esc.includes('issue #12 is still closed: the reopen failed: HTTP 403') && taskOf(stuck, 'write').closed_at === AT, `a failed reopen is not in the escalation: ${esc}`)

  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`wave-prune: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('wave-prune: 0 passed, 1 failed')
  process.exit(1)
})
