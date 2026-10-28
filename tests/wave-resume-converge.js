// tests/wave-resume-converge.js - a re-run after a converge pruned a chain branch (#340). Node, no packages.
// It runs plugin/workflows/wave.js under the stub harness of tests/workflows.js. The earlier run merged
// a1 into chain x and b into chain y, converged both into the wave branch and deleted both chain branches;
// a2 escalated. The re-run gives a2 an answer. The merged chain tasks are skipped, a2 starts from and
// merges into the wave branch, and no chain branch is made or merged again.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, answerWith, claimUrl }`)(require, __dirname)
const file = path.join(__dirname, '..', 'plugin', 'workflows', 'wave.js')
const WAVE = '10-wave-1'
const A2_SHA = 'fedcba9876543210fedcba9876543210fedcba98'

const task = (id, chain, blockers = []) => ({ id, tier: 'judgment', ...(chain && { chain }), blockers, files: [`src/${id}.ts`], brief: `Build ${id}.`, oracle: { command: `t ${id}`, files: [], uncovered: ['layout'] } })
const graph = { ...H.ARGS.wave.graph, tasks: [task('a1', 'x'), task('a2', 'x', ['a1']), task('b', 'y'), task('docs', undefined, ['a2', 'b'])] }
const claims = Object.fromEntries(graph.tasks.map((t) => [t.id, H.claimUrl(t.id)]))

const problems = []
const expect = (ok, msg) => { if (!ok) problems.push(msg) }
const labels = (r) => r.calls.map((c) => c.label)
const promptOf = (r, label) => (r.calls.find((c) => c.label === label) || { prompt: '' }).prompt
const wave = (remote, over = {}) => H.run(file, { ...H.ARGS.wave, graph, claims, answers: { a2: 'Use the system font.' } }, H.answerWith('wave', { remote: (n, a, label) => (label === 'remote check' ? remote : a), ...over }))

async function main() {
  // 1. Both chains converged and pruned: the wave branch holds every chain merge, no chain branch is left.
  const both = await wave({
    merges: [`Merge ${WAVE}-a1 into ${WAVE}-x`, `Merge ${WAVE}-b into ${WAVE}-y`, `Merge ${WAVE}-x into ${WAVE}`, `Merge ${WAVE}-y into ${WAVE}`],
    heads: [{ branch: WAVE, sha: A2_SHA.replace(/f/g, '1') }, { branch: `${WAVE}-a2`, sha: A2_SHA }],
  })
  const ls = labels(both)
  expect(!ls.some((l) => /^(build|merge) (a1|b)\b/.test(l)), `both: a chain task merged before the converge ran again: ${ls}`)
  expect(JSON.stringify([...(both.result.merged_before || [])].sort()) === '["a1","b"]', `both: merged_before is ${both.result.merged_before}, not a1 and b`)
  expect(!ls.includes('converge'), `both: the converged chains converge again: ${ls}`)
  const ba2 = promptOf(both, 'build a2')
  expect(ba2.includes(`origin/${WAVE}\n`) || ba2.includes(`origin/${WAVE})`) || ba2.includes(`merge -q --no-edit origin/${WAVE}\n`), `both: a2 does not start from the wave branch: ${ba2.split('\n').find((l) => l.includes('worktree add')) || ''}`)
  expect(!both.calls.some((c) => c.prompt.includes(`origin/${WAVE}-x`) && c.label !== 'remote check'), `both: an agent after the remote check names the pruned chain branch origin/${WAVE}-x: ${both.calls.filter((c) => c.prompt.includes(`origin/${WAVE}-x`)).map((c) => c.label)}`)
  expect(promptOf(both, 'merge a2').includes(`into the wave branch ${WAVE} `), 'both: a2 does not merge into the wave branch')
  const rc = promptOf(both, 'remote check')
  expect(rc.includes(`--format=%s ${H.ARGS.wave.graph.base.sha}..origin/${WAVE} | grep -qxF "Merge <branch> into ${WAVE}"`), 'both: the remote check makes a chain branch again that the converge merged into the wave branch')
  expect(ls.includes('build docs') && ls.includes('review wave'), `both: docs or the end review did not run after the earlier converge: ${ls}`)
  const done = (both.result.done || []).slice().sort()
  expect(JSON.stringify(done) === '["a2","docs"]', `both: done is ${done}, not a2 and docs`)

  // 2. Only chain y converged and was pruned; chain x is still on the remote. x converges, y does not.
  const one = await wave({
    merges: [`Merge ${WAVE}-a1 into ${WAVE}-x`, `Merge ${WAVE}-b into ${WAVE}-y`, `Merge ${WAVE}-y into ${WAVE}`],
    heads: [{ branch: `${WAVE}-x`, sha: A2_SHA.replace(/f/g, '2') }],
  })
  const lo = labels(one)
  expect(!lo.some((l) => /^(build|merge) (a1|b)\b/.test(l)), `one: a merged task ran again: ${lo}`)
  expect(promptOf(one, 'build a2').includes(`origin/${WAVE}-x`) && promptOf(one, 'merge a2').includes(`into the chain branch ${WAVE}-x`), 'one: a2 does not build and merge on its chain branch x')
  const cv = promptOf(one, 'converge')
  expect(lo.filter((l) => l === 'converge').length === 1 && cv.includes(`in this order: ${WAVE}-x.`), `one: the converge does not merge only chain x: ${lo}`)

  // 3. A report SHA that is no commit, after the converge: the merge of a2 into its pruned chain branch,
  // found on the wave branch, counts as merged; a2 is not merged again.
  const CONVERGED = { merges: [`Merge ${WAVE}-a1 into ${WAVE}-x`, `Merge ${WAVE}-x into ${WAVE}`], heads: [] }
  const lost = await wave(CONVERGED, {
    report: (n, a, label) => (label.startsWith('build a2') ? { ...a, sha: '0'.repeat(40) } : a),
    remote: (n, a, label) => (label === 'remote check' ? CONVERGED : label === 'remote check a2' ? { merges: [`Merge ${WAVE}-a2 into ${WAVE}-x`], heads: [{ branch: WAVE, sha: A2_SHA }] } : a),
  })
  const ll = labels(lost)
  expect(promptOf(lost, 'remote check a2').includes(`"Merge ${WAVE}-a2 into ${WAVE}" or "Merge ${WAVE}-a2 into ${WAVE}-x"`), 'lost: the remote check of a2 does not look for its merge into the pruned chain branch')
  expect(ll.includes('remote check a2') && !ll.some((l) => l.startsWith('merge a2')) && (lost.result.done || []).includes('a2'), `lost: a2 merged into its pruned chain branch is not counted as merged: ${ll}`)

  for (const x of problems) console.log(`FAIL ${x}`)
  console.log(`wave-resume-converge: ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}
main().catch((e) => { console.log(`FAIL ${e.stack}`); process.exit(1) })
