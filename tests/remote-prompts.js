// tests/remote-prompts.js - spec checks of #316: a prompt names work, never the place an agent runs.
// With a runtime marked remote, the worker, sub-lead, integrator and fix prompts of wave, flow and
// split name no path under runtime.worktree_root but still name the task branch, wave caps its slots
// by runtime.concurrency only, and flow reads no load on the workflow host. Node, no packages.
// It runs the workflows under the stub harness of tests/workflows.js (run, ARGS, probe), loaded without its main().
// The marker is whatever tests/fixtures/contract/runtime.ok-remote.json adds to a runtime: no name is invented here.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const harnessSrc = fs.readFileSync(path.join(__dirname, 'workflows.js'), 'utf8').replace(/\nmain\(\)\s*$/, '\n')
const H = new Function('require', '__dirname', `${harnessSrc}\nreturn { run, ARGS, ANSWERS, probe, problems }`)(require, __dirname)
const dir = path.join(__dirname, '..', 'plugin', 'workflows')
const ROOT = 'REMOTE_ROOT_MUST_NOT_APPEAR'
const BASE_FIELDS = ['provider', 'tiers', 'worktree_root', 'agent_types', 'concurrency', 'capabilities']
// The labels of the worker, sub-lead, integrator and fix roles that name a task branch or a checkout.
const ROLE_LABEL = /^(build|rework|split|merge|fix|integrate|converge)/

const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }

// remoteRuntime: the probe runtime plus the marker fields of the remote fixture (none: null).
function remoteRuntime(concurrency) {
  const f = path.join(__dirname, 'fixtures', 'contract', 'runtime.ok-remote.json')
  if (!fs.existsSync(f)) return null
  const fx = JSON.parse(fs.readFileSync(f, 'utf8'))
  const marker = Object.fromEntries(Object.entries(fx).filter(([k]) => !BASE_FIELDS.includes(k)))
  return Object.keys(marker).length ? { ...H.probe, ...marker, worktree_root: ROOT, concurrency } : null
}
// branchOf: the branch a local prompt makes its worktree for (the first path under the probe root).
const branchOf = (prompt) => ((prompt.match(new RegExp(`${H.probe.worktree_root}/([^\\s'")]+)`)) || [])[1] || '').replace(/[.,;:]+$/, '')

async function main() {
  const remote = remoteRuntime(null)
  expect(remote, 'no remote marker: tests/fixtures/contract/runtime.ok-remote.json adds no field to a runtime (316-runtime-contract is not merged)')
  if (remote) {
    for (const name of ['wave', 'flow', 'split']) {
      const file = path.join(dir, `${name}.js`)
      const args = H.ARGS[name]
      const local = await H.run(file, { ...args, runtime: H.probe }, H.ANSWERS[name])
      const far = await H.run(file, { ...args, runtime: remote }, H.ANSWERS[name])
      const sites = far.calls.filter((c) => ROLE_LABEL.test(c.label))
      expect(sites.length > 0, `${name}: no worker, sub-lead, integrator or fix call (labels: ${far.calls.map((c) => c.label).join(', ')})`)
      for (const c of sites) {
        expect(!c.prompt.includes(ROOT), `${name} ${c.label}: the prompt names a path under the runtime worktree_root`)
        const branch = branchOf((local.calls.find((l) => l.label === c.label) || { prompt: '' }).prompt)
        if (branch) expect(c.prompt.includes(branch), `${name} ${c.label}: the prompt does not name the branch ${branch}`)
      }
      expect(!far.calls.some((c) => c.prompt.includes('git worktree add')), `${name}: a remote prompt tells the agent to make a git worktree`)
    }
    // wave: a remote runtime's cap is runtime.concurrency alone; null is no cap, whatever args.cpus says.
    const wave = await H.run(path.join(dir, 'wave.js'), { ...H.ARGS.wave, cpus: 4, runtime: remoteRuntime(null) }, H.ANSWERS.wave)
    expect(wave.logs.includes('concurrency cap: set by the runtime'), `wave: no "concurrency cap: set by the runtime" log (logs: ${wave.logs.filter((l) => l.startsWith('concurrency')).join(' | ')})`)
    // flow: max_load is a limit of the workflow host; a remote runtime sets where agents run, so no load agent runs.
    const flow = await H.run(path.join(dir, 'flow.js'), { ...H.ARGS.flow, runtime: remoteRuntime(null) }, H.ANSWERS.flow)
    expect(!flow.calls.some((c) => c.label === 'load'), 'flow: a remote runtime still reads the load on the workflow host')
    expect(flow.logs.includes('max_load: not read on the workflow host; the runtime sets where agents run'), 'flow: no "max_load: not read on the workflow host" log')
  }
  for (const p of H.problems) expect(false, `harness: ${p}`)
  for (const p of problems) console.log(`FAIL ${p}`)
  console.log(`remote-prompts: ${checks - problems.length} passed, ${problems.length} failed`)
  process.exit(problems.length > 0 ? 1 : 0)
}

main().catch((e) => {
  console.log(`FAIL ${e.stack}`)
  console.log('remote-prompts: 0 passed, 1 failed')
  process.exit(1)
})
