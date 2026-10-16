// tests/shared-helpers.js - the spec of the shared helpers: written once in wave.js between 2 marker
// lines; flow.js holds a copy that `node tests/workflows.js --write` keeps in step. Node, no packages.
// Exit 1 on a problem.
'use strict'
const fs = require('fs')
const path = require('path')

const dir = path.join(__dirname, '..', 'plugin', 'workflows')
const BEGIN = '// ---- shared helpers: begin'
const END = '// ---- shared helpers: end'
const NAMES = ['verify', 'workerPrompt', 'staleAfter', 'resetup', 'makeWave', 'doNotTouch', 'isoSeconds', 'badSha', 'know']
let failed = 0
let checks = 0
const expect = (ok, msg) => { checks++; if (!ok) { failed++; console.log(`FAIL ${msg}`) } }
const count = (src, line) => src.split(`\n${line}\n`).length - 1
const inside = (src) => {
  const a = src.indexOf(`\n${BEGIN}\n`)
  const b = src.indexOf(`\n${END}\n`)
  return a >= 0 && b > a ? src.slice(a + BEGIN.length + 2, b + 1) : null
}
const src = { wave: fs.readFileSync(path.join(dir, 'wave.js'), 'utf8'), flow: fs.readFileSync(path.join(dir, 'flow.js'), 'utf8') }
const block = {}
for (const n of ['wave', 'flow']) {
  expect(count(src[n], BEGIN) === 1 && count(src[n], END) === 1, `${n}: needs the lines "${BEGIN}" and "${END}" once each`)
  block[n] = inside(src[n])
  expect(block[n] !== null, `${n}: the begin line must come before the end line`)
}
if (block.wave !== null && block.flow !== null) {
  // Each name is defined once, inside the block, in both files.
  for (const n of NAMES) {
    const def = new RegExp(`^(?:async )?(?:function|const|let) ${n}\\b`, 'gm')
    expect((block.wave.match(def) || []).length === 1, `wave: ${n} is not defined once inside the shared helpers`)
    for (const f of ['wave', 'flow']) expect(!def.test(src[f].replace(block[f], '')), `${f}: ${n} is defined outside the shared helpers`)
  }
  expect(block.flow === block.wave, 'flow: its shared helpers drift from wave.js; run node tests/workflows.js --write')
  // The eager FULL_SHA line reads reportSchema, so the block must follow it in flow.js.
  const rs = src.flow.search(/^const reportSchema\b/m)
  expect(rs >= 0 && rs < src.flow.indexOf(BEGIN), 'flow: the shared helpers must come after reportSchema')
}
console.log(`${checks - failed} passed, ${failed} failed`)
process.exit(failed ? 1 : 0)
