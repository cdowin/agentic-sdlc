export const meta = {
  name: 'doc-sdlc',
  description: 'The document SDLC: brief with a source precedence list, base draft, one layer per lens, parallel review, fix (max 2 rounds), then a validated result with a scorecard per lens.',
  phases: ['Brief', 'Base draft', 'Layers', 'Review', 'Fix', 'Validated'],
}

// args: { brief, kind, target, lenses, screenshots, humanizerPath, skillDir }
//   brief          the request, as text
//   kind           page | post | readme | pdf | ui
//   target         the file to write
//   lenses         optional; default depends on kind
//   screenshots    optional; files the main agent took (375, 1000 and 1440 px wide). The
//                  visual-layout reviewer reads them. A reviewer has no browser, so the main agent
//                  takes them. With none, the screenshot checks score n/a.
//   humanizerPath  optional; path to an installed humanizer SKILL.md. With none, the humanizer
//                  layer and review are skipped with a log line.
//   skillDir       optional; the folder that holds the 5 lens skills. Default: the plugin's skills.
// The humanizer skill is optional and is not part of this plugin. Source: https://github.com/blader/humanizer
// (MIT licence). Install it yourself; this plugin does not copy it.
// This workflow has no contract shapes: its schemas are its own, so tests/workflows.js skips it and
// tests/doc-sdlc.js runs it.

const MODEL = 'sonnet'
const AGENT_TYPE = 'developer'
const MAX_FIX_ROUNDS = 2
const HUMANIZER = 'humanizer'
const KINDS = ['page', 'post', 'readme', 'pdf', 'ui']

// Layer order is fixed: words first, then voice, look, media, access.
const LAYER_ORDER = ['plain-language', HUMANIZER, 'visual-layout', 'multimedia-design', 'accessible-content']

// The humanizer skill has no closing checklist, so the reviewer scores this list. Prose only.
const HUMANIZER_CHECKS = [
  'H1 No stock AI phrases ("in today\'s world", "it is important to note", "plays a crucial role")',
  'H2 No inflated praise or promotional words ("seamless", "robust", "powerful", "game-changing")',
  'H3 No rule-of-three lists or "not only X but also Y" patterns used as filler',
  'H4 No vague attribution ("experts say", "studies show") without a named source',
  'H5 No filler hedges ("it could be argued", "may potentially") and no generic upbeat closing line',
  'H6 Plain "is" and "are" where the text uses "serves as" or "stands as"; no em dash overuse; no emoji',
  'H7 Sentence length and rhythm vary; the text reads as one person with a point of view',
]

// Every reviewer scores this check first, whatever the lens.
const FACTS_CHECK = 'FACTS Every number, date, name and claim in the document matches the highest-ranked source in the precedence list. A mismatch is a blocking fail; quote the document and the source.'

// Ship rule. This workflow owns it. Each skill marks which of its checks block.
// blocking: a fail on a check the skill marks as blocking (for example a WCAG Level A failure), or a FACTS fail.
// should-fix: any other fail. The fixer works on it; it is listed for the person if it remains.
// note: a cosmetic or style-only fail. Recorded, never blocks, not sent to the fixer.
const SHIP = ['blocking', 'should-fix', 'note']
const SHIP_RULE = 'Classify every fail with "ship": "blocking" if the skill marks that check as blocking (look for the words "block" or "blocks" in the skill; a usability severity of 3 or 4 blocks; a FACTS fail blocks), "note" if it is cosmetic or style-only, otherwise "should-fix". The humanizer list has no blocking checks.'

const DEFAULT_LENSES = {
  page: ['plain-language', 'visual-layout', 'multimedia-design', 'accessible-content', 'usability-review', HUMANIZER],
  post: ['plain-language', 'visual-layout', 'multimedia-design', 'accessible-content', HUMANIZER],
  readme: ['plain-language', 'visual-layout', 'accessible-content', HUMANIZER],
  pdf: ['plain-language', 'visual-layout', 'multimedia-design', 'accessible-content', HUMANIZER],
  ui: ['plain-language', 'visual-layout', 'accessible-content', 'usability-review'],
}

const BRIEF_SCHEMA = {
  type: 'object',
  properties: {
    reader: { type: 'string' },
    task: { type: 'string' },
    mainPoint: { type: 'string' },
    sources: { type: 'array', items: { type: 'string' } },
    precedence: { type: 'array', items: { type: 'string' }, description: 'The sources in order, the winner first, each with the rule for a clash of numbers or facts' },
    doneWhen: { type: 'array', items: { type: 'string' } },
  },
  required: ['reader', 'task', 'mainPoint', 'sources', 'precedence', 'doneWhen'],
}

const WRITE_SCHEMA = {
  type: 'object',
  properties: { path: { type: 'string' }, summary: { type: 'string' } },
  required: ['path', 'summary'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          score: { type: 'string', enum: ['pass', 'fail', 'n/a'] },
          evidence: { type: 'string' },
          fix: { type: 'string' },
          ship: { type: 'string', enum: SHIP },
        },
        required: ['id', 'score', 'evidence'],
      },
    },
  },
  required: ['lens', 'checks'],
}

const { brief, kind, target } = args
if (!brief || !target) throw new Error('doc-sdlc needs args.brief and args.target')
if (!KINDS.includes(kind)) throw new Error(`args.kind must be one of: ${KINDS.join(', ')}`)

const wanted = args.lenses && args.lenses.length ? args.lenses : DEFAULT_LENSES[kind]
const lenses = wanted.filter((l) => l !== HUMANIZER || args.humanizerPath)
if (lenses.length < wanted.length) log('humanizer skipped: no args.humanizerPath (no humanizer skill installed). Source: https://github.com/blader/humanizer')
const layers = LAYER_ORDER.filter((l) => lenses.includes(l))
const screenshots = args.screenshots || []
const opts = (label, phaseName, schema) => ({ label, phase: phaseName, schema, model: MODEL, agentType: AGENT_TYPE })
const skillLine = (l) =>
  l === HUMANIZER
    ? `the humanizer skill at ${args.humanizerPath}`
    : args.skillDir
      ? `the skill at ${args.skillDir}/${l}/SKILL.md`
      : `the agentic-sdlc plugin skill "${l}" (its SKILL.md is in the plugin's skills folder; look under ~/.claude/plugins)`
const shotLine = (l) =>
  l !== 'visual-layout'
    ? ''
    : screenshots.length
      ? ` Read these screenshot files as your evidence: ${screenshots.join(', ')}.`
      : ' No screenshots were supplied. Score every check that needs a screenshot as n/a with the evidence "no screenshots supplied".'

const maxAgents = 2 + layers.length + MAX_FIX_ROUNDS * (lenses.length + 1) + lenses.length
log(`doc-sdlc: up to ${maxAgents} agents (${layers.length} layer passes, ${lenses.length} reviewers, max ${MAX_FIX_ROUNDS} fix rounds), all ${AGENT_TYPE}/${MODEL}. Target: ${target}`)

phase('Brief')
const b = await agent(
  `Turn this request into a written brief for a ${kind}. State: the reader, the task they are trying to do, the one main point, the sources to use (files, URLs, issues), the source precedence and the done-when (checkable). The precedence is an ordered list of those sources, the winner first, with the rule for a clash of numbers or facts (for example: the base draft's numbers win unless a newer dated source is named). Do not write the document. Ask nothing; make the smallest sound assumption and say so in doneWhen.\n\nRequest:\n${brief}`,
  opts('brief', 'Brief', BRIEF_SCHEMA),
)
const briefText = JSON.stringify(b, null, 2)
const precedence = `Source precedence (the first source wins when numbers or facts differ):\n${b.precedence.map((p, i) => `${i + 1}. ${p}`).join('\n')}`

phase('Base draft')
await agent(
  `Write the base document for a ${kind} at ${target}, from this brief. Read the listed sources first. This draft is the base context for every later pass, so make it complete and accurate. Do not polish for any lens yet.\n\n${precedence}\n\nBrief:\n${briefText}`,
  opts('base-draft', 'Base draft', WRITE_SCHEMA),
)

phase('Layers')
for (const l of layers) {
  await agent(
    `Open ${target}. Read ${skillLine(l)} and edit the document for that lens only. Do not change the facts, the numbers, the main point or the structure that other lenses own. If a number must change, take it from the winning source.\n\n${precedence}\n\nKeep the brief in mind:\n${briefText}`,
    opts(`layer-${l}`, 'Layers', WRITE_SCHEMA),
  )
}

const UNAVAILABLE = 'unavailable'
const checklistLine = (l) =>
  l === HUMANIZER
    ? `Score each item of this list as pass, fail or n/a:\n${HUMANIZER_CHECKS.join('\n')}\n${FACTS_CHECK}`
    : `Score every item of that skill's closing checklist as pass, fail or n/a, and this check too:\n${FACTS_CHECK}`

// Results are keyed by the lens we asked for, never by the lens string an agent returns.
// A null or failed agent result becomes { available: false }.
const review = async (lensList, round) => {
  const raw = await parallel(lensList.map((l) => async () => {
    try {
      return await agent(
        `Review ${target} against ${skillLine(l)}. Do not edit the file. ${checklistLine(l)} Give evidence for each (quote or line). For each fail give a one-line fix and a "ship" class. ${SHIP_RULE}${shotLine(l)} Set lens to "${l}".\n\n${precedence}\n\nBrief for context:\n${briefText}`,
        opts(`review-${l}-r${round}`, round === 0 ? 'Review' : 'Fix', REVIEW_SCHEMA),
      )
    } catch (e) {
      log(`review of ${l} failed: ${e && e.message}`)
      return null
    }
  }))
  return lensList.map((l, i) => {
    const r = raw[i]
    const ok = r && Array.isArray(r.checks)
    return { lens: l, available: !!ok, checks: ok ? r.checks : [] }
  })
}

const SHIP_RANK = { blocking: 0, 'should-fix': 1, note: 2 }
const shipOf = (c) => c.ship || 'should-fix'
const failsOf = (r) => r.checks.filter((c) => c.score === 'fail')
// The fixer works on blocking and should-fix fails. Notes are recorded only.
const fixableOf = (r) => failsOf(r).filter((c) => shipOf(c) !== 'note')
const needsWork = (r) => !r.available || fixableOf(r).length > 0
const scorecard = {}
const record = (rs) => { for (const r of rs) scorecard[r.lens] = r.available ? r.checks : UNAVAILABLE }

phase('Review')
let results = await review(lenses, 0)
record(results)

phase('Fix')
let round = 0
let pending = results.filter(needsWork).map((r) => r.lens)
while (pending.length && round < MAX_FIX_ROUNDS) {
  round += 1
  const findings = results
    .flatMap((r) => fixableOf(r).map((c) => ({ lens: r.lens, ...c, ship: shipOf(c) })))
    .sort((x, y) => SHIP_RANK[x.ship] - SHIP_RANK[y.ship])
  log(`Fix round ${round}: ${findings.length} findings across ${pending.join(', ')}`)
  if (findings.length) {
    await agent(
      `Fix these ranked findings in ${target}, blocking first. Where two findings conflict, keep the plainer wording and note the conflict in your summary. When a fix touches a number or fact, take it from the source that wins in this list. Change nothing else.\n\n${precedence}\n\nFindings:\n${JSON.stringify(findings, null, 2)}`,
      opts(`fix-r${round}`, 'Fix', WRITE_SCHEMA),
    )
  }
  const rerun = await review(pending, round)
  record(rerun)
  // Keep the earlier result for a lens we did not re-run; replace the rest.
  results = results.map((r) => rerun.find((x) => x.lens === r.lens) || r)
  pending = results.filter(needsWork).map((r) => r.lens)
}

phase('Validated')
const unavailable = results.filter((r) => !r.available).map((r) => r.lens)
const withLens = (r, c) => ({ lens: r.lens, ...c, ship: shipOf(c) })
const remaining = results.flatMap((r) => fixableOf(r).map((c) => withLens(r, c)))
const blocking = remaining.filter((f) => f.ship === 'blocking')
// validated: no blocking check fails and every lens was reviewed. Should-fix items that remain
// are listed in shouldFix for the person to accept; they do not hold validated at false.
return {
  document: target,
  validated: blocking.length === 0 && unavailable.length === 0,
  fixRounds: round,
  scorecard,
  blocking,
  shouldFix: remaining.filter((f) => f.ship === 'should-fix'),
  notes: results.flatMap((r) => failsOf(r).filter((c) => shipOf(c) === 'note').map((c) => withLens(r, c))),
  unavailable,
  skipped: wanted.filter((l) => !lenses.includes(l)),
}
