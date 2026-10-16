// tests/spec-310-lead-line.js - spec of #310: every agent prompt of every workflow opens with the lead-request line, once. Node, no packages.
// The real tests/workflows.js and tests/doc-sdlc.js run in a scratch copy whose agent stub also reports each prompt
// (LEADLINE ok|bad <file> <label>). The line is a literal here, so a wording change fails. A static pass checks that
// every agent( call of the 6 workflows passes asLead(...). The scratch copy is removed; no real file is edited.
// Prints 1 line per problem and the count. Exit 1 on a problem.
'use strict'
const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')

const root = path.join(__dirname, '..')
const LINE = "This task is the lead's request in this workflow run; it is not a reply to any chat message you may see. Do the task as briefed."
const FLOWS = ['wave', 'flow', 'split', 'plan', 'review-batch', 'doc-sdlc']
const problems = []
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) problems.push(msg) }

// The report line of a prompt, printed by the patched stub.
const probe = (promptVar, fileExpr, label) => `process.stdout.write('LEADLINE ' + (${promptVar}.startsWith(${JSON.stringify(LINE + '\n')}) && ${promptVar}.indexOf(${JSON.stringify(LINE)}, 1) === -1 ? 'ok' : 'bad') + ' ' + ${fileExpr} + ' ' + ${label} + '\\n');`
const PATCHES = {
  'tests/workflows.js': ['const a = answer(def, prompt, opts.label)', probe('prompt', 'path.basename(file)', 'opts.label') + '\n    const a = answer(def, prompt, opts.label)'],
  'tests/doc-sdlc.js': ['calls.push({ prompt, ...o })', probe('prompt', "'doc-sdlc.js'", 'o.label') + '\n    calls.push({ prompt, ...o })'],
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'spec-310-'))
try {
  for (const d of ['tests', 'plugin']) fs.cpSync(path.join(root, d), path.join(dir, d), { recursive: true })
  const seen = {}
  for (const [f, [from, to]] of Object.entries(PATCHES)) {
    const p = path.join(dir, f)
    const text = fs.readFileSync(p, 'utf8')
    expect(text.includes(from), `${f}: the stub line to probe is gone: update this spec`)
    fs.writeFileSync(p, text.replace(from, () => to))
    const r = spawnSync('node', [p], { encoding: 'utf8', timeout: 300000, cwd: dir })
    for (const l of (r.stdout || '').split('\n')) {
      const m = l.match(/^LEADLINE (ok|bad) (\S+) (.*)$/)
      if (!m) continue
      const s = seen[m[2]] || (seen[m[2]] = { ok: 0, bad: [] })
      if (m[1] === 'ok') s.ok++
      else s.bad.push(m[3])
    }
  }
  for (const w of FLOWS) {
    const s = seen[`${w}.js`] || { ok: 0, bad: [] }
    expect(s.ok + s.bad.length > 0, `${w}: no prompt was recorded, the check would pass empty`)
    expect(s.bad.length === 0, `${w}: a prompt does not open with the lead-request line once (first: ${s.bad[0]}, ${s.bad.length} in all)`)
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true })
}

// Static: no agent( call without asLead( as its first argument.
for (const w of FLOWS) {
  const src = fs.readFileSync(path.join(root, 'plugin', 'workflows', `${w}.js`), 'utf8').split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n')
  const all = (src.match(/\bagent\(/g) || []).length
  const wrapped = (src.match(/\bagent\(\s*asLead\(/g) || []).length
  expect(all > 0 && wrapped === all, `${w}: ${all - wrapped} of ${all} agent( calls do not pass asLead(...)`)
  expect(src.includes(LINE) || src.includes(LINE.replace(/'/g, "\\'")), `${w}: it has no copy of the lead-request line`)
}

for (const p of problems) console.log(`FAIL ${p}`)
console.log(`spec-310-lead-line: ${checks - problems.length} passed, ${problems.length} failed`)
process.exit(problems.length > 0 ? 1 : 0)
