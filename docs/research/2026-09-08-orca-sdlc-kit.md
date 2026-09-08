# orca-sdlc-kit, read against agentic-sdlc

Read 2026-09-08. Both trees pinned, so every number here is reproducible:

| | commit | date | commits | lines | releases |
|---|---|---|---|---|---|
| `vankhangfet/orca-sdlc-kit` | `fe90d7a` | 2026-09-06 | 95, from 2026-08-29 | 2,924 across 13 files | 7 tags, v1.0.0 → v1.5.0 |
| `cdowin/agentic-sdlc` | `7f4994f` (v0.6.0) | 2026-09-08 | 430, from 2026-09-05 | 21,519 src + 36,291 test | 5 tags, v0.2.0 → v0.6.0 |

Three passes: a mechanical read of `flow.mjs` with file:line citations, an adversarial pass briefed
to make the strongest honest case *against* this project, and my own reading. Where they disagreed
with me, they win — five of my framing claims were wrong and are corrected below rather than
quietly dropped.

**Neither project is mature. Both are about a week old.** This is not a survey of a competitor; it
is two people who have never met, betting opposite ways on adjacent halves of the same problem in
the same fortnight. That makes the places where they *agree* the most interesting thing in the
document.

---

## The short version

**Orca has a pipeline and no ledger. We have a ledger and no pipeline.**

Orca takes one sentence — *"Build a login page"* — and returns working code, having driven a
planner, an architect, two design passes in parallel, a coder, two reviewers, a tester and a writer
through an Orca ADE worktree, looping failures back to the coder and showing you the whole thing on
a dashboard that updates itself. Its unit of work is a **run**. Its memory is `.orca/artifacts/`,
which is gitignored and gone next run.

We take a tree of markdown grains and tell you which of them contradict each other, refusing to
close a milestone whose bugs are open. Our unit of work is a **grain**. Our memory is committed, and
survives everything.

The strongest evidence that these are halves rather than rivals is that **each one's roadmap points
at the other's core.** Orca's next major (`ROADMAP.md`) is titled *"trust & visibility"*, and its
top two items are *config validation before any agent starts* and *a run log — the console,
persisted*. Those are a deterministic gate and a ledger. Meanwhile our
`bg-a-dispatch-nobody-records-leaves-the-spend-surface-empty` sat open for five milestones; Orca
shipped that as v1.5.0 and shipped it better than we would have.

---

## 1. Where they agree, having never met

Convergent design is the most useful signal a two-codebase comparison can produce, because neither
party could have copied the other. Five principles arrived at twice:

| principle | ours | theirs |
|---|---|---|
| behaviour lives in config, not in a fork of the tool | hard rule 5, *config over forks* | *"Pipeline behavior belongs in the configs — not new logic in `flow.mjs`"* (`README.md`, contributing) |
| one file, no dependencies | stdlib-only forever (rule 1) | one 1,803-line Node script, zero npm deps |
| specialists with handoffs, not one agent improvising | the twelve-role installed roster | planner → architect → design ∥ UI/UX → coder → reviewers → tester → writer |
| say what you will **not** build | `pm decide`, with the rejected alternative | `ROADMAP.md § Not building (by design)` |
| **never guess when the answer is ambiguous** | rule 4: a gate that scans nothing FAILS | `heads.size > 1 → return null; // ambiguous — never guess` |

The last one is worth dwelling on. Their usage reporter refuses to attribute tokens when two steps
match, reports `—` with a reason (`"no adapter"`, `"no session found"`, `"prior run"`) rather than a
zero, and prints `N subagent file(s) unattributed` as its own column. **That is our rule 11 — name
what you lack, never fall silent — implemented for telemetry by someone who reached it
independently.** Two people arriving separately at *"a fake zero is worse than an honest dash"* is
better evidence the rule is right than either codebase alone could be.

Their fix loop has the same instinct. A missing verdict becomes `"unknown"`, and `unknown` never
retries — it halts, with this comment at `flow.mjs:1768`:

> a blind retry has double-dispatched a live task before (the reviewer was still working when the
> coder was re-started under it)

That is a real bug, encoded as a refusal to act on an answer they could not read. We would call it
rule 4.

---

## 2. What Orca has that we do not

### 2.1 It executes, and we are the pipeline

This is the whole difference and everything else is downstream of it.

Our position is hard rule 2 (*pure text — boots nothing*) plus `0.5.0/D1` (*the tool emits; a plugin
framework is the rejected alternative*). That constraint is real and load-bearing: the moment a
`git rev-list` landed on `arrive.census()` during 0.6.0, **235 cases failed by nodeid**, each saying
*tried to spawn a process*. It is what makes four concurrent agents on one worktree survivable.

**But it is a constraint on the gates, and we have been citing it as an argument against having an
orchestrator at all.** Those are different claims, and the second one does not follow. The
adversarial pass put it plainly and it is right: closing 0.6.0 took 4 h 31 m across 22 grains with
up to four dispatched agents, and every dispatch brief was hand-written, every returned slice
hand-verified, every commit hand-made by pathspec, and **all four telemetry rows hand-typed.** Orca
automates that loop. We do not, and "boots nothing" does not explain why not.

### 2.2 The record is harvested, not pushed — the single most valuable thing here

Our courier takes the transcript path from the hook payload (`tools/hooks/cc-ledger-subagent.sh:284`,
`agent_transcript_path`). No hook fires → no path → no row. That is a **push** architecture, and
`0.6.0/D8` measured the bet failing: the session that closed the milestone had a project root above
the checkout, so nothing in `.claude/settings.json` was ever loaded.

Orca **pulls**. After the run it scans `~/.claude/projects/<slug>/*.jsonl` and
`~/.codex/sessions/YYYY/MM/DD/`, filters on an mtime window plus an exact `cwd` match against the
worktree, and attributes a session to a step by spec-head substring containment.

The principle generalises past the implementation: **a record that depends on something firing at
the start is a record you will not have; a record reconstructed at the end from what the harness
already wrote is one you will.**

Its limits must be stated with it, because they are not small:

- Attribution for subagents is by **time-window containment only**, and parallel steps have
  overlapping windows by definition — so in their own shipped `detailed-design ∥ uiux-design` group
  (both on claude) subagent tokens fall to the unattributed bucket.
- Only `claude` and `codex` have adapters. Their shipped `opencode` testing step is **permanently
  unmeasured**.

We would not inherit the second problem and would inherit a milder version of the first, because our
attribution target is a **grain** the operator already knows, not a step the tool must infer.

### 2.3 An ambient surface

`pm status` answers when asked. Orca's dashboard tells you without being asked, and does it over
`file://` with no server: `status.js` is an executable script calling `window.__ON_STATUS()`,
re-injected as a cache-busted `<script src>` every two seconds, because classic script tags are not
CORS-blocked on `file://`. That is a genuinely clever trick and it needs nothing we forbid.

Rule 11 says a capability advertises itself in the surface you are standing in. A live surface is
that rule with the polling done for you.

### 2.4 Things we half-have

- **`--dry-run` as a stated habit.** We have `ready-for` (the entry edge), `verify --plan` and
  installer `--diff`. The pieces exist; the *habit* is not stated anywhere as theirs is.
- **Per-step agent swap in one field**, including a one-off `--agent coding=claude`. Our roster
  carries `model:`/`effort:` — and `SDLC.md §3` admits `effort:` is UNVERIFIED. Theirs at least
  reaches the dispatch it names.
- **Resume.** `--from <step>` reuses earlier artifacts; `--from auto` is queued. Our `verify` cache
  is the same instinct at a different grain.

---

## 3. What we have that Orca does not

### 3.1 A gate a self-report cannot walk past — and this is the belief that survived hardest

I had this wrong and the correction makes our case *stronger*, not weaker. I assumed Orca's quality
gate was an LLM reading the review and saying PASS. It is narrower than that.

**`flow.mjs` never opens any step artifact.** Every `readFileSync` in 1,803 lines is the config, a
session transcript, the progress checklist, or its own previous `status.js`. `REVIEW.md`,
`SECURITY_REVIEW.md` and `TEST_REPORT.md` are never read, and the orchestrator does not check they
exist. The verdict is a structured `outcome` field the agent **reports about itself** in its
`worker_done` payload (`outcomeOf`, `flow.mjs:1508`); the instruction to emit `outcome=failed` lives
in config prose (`flow.config.json:109`), not in code.

And the two paths that decide a verdict disagree about what "unreadable" means. The primary
settlement defaults a missing outcome to `"unknown"`, which halts — the safe choice, and a good one.
The **recovery** path, taken when a `worker_done` delivery was missed and the outcome is re-derived
from the task record, ends `|| "succeeded"` (`flow.mjs:1556`) — a missing verdict scores as a pass.

Two readers of one question that can disagree, one of them failing open, in a repo with no test that
could ever find it. That is the `at`-versus-`ts` shape our own 0.6.0 vocabulary work was named
after, and it is worth being precise that it is the recovery path rather than the main gate: the
design is careful, and the careless half is the one nobody looks at.

The honest form of our advantage is not *"our gates are sound and theirs are not."* Ours were hollow
**six times** and 0.6.0's close found every one — three tests blind to two routed verbs, a
`semver-gate.yml` success path that had never fired for any release, an `assertIn(x, X)` tautology,
`check doc`'s rule wired by one unguarded line, and `check hooks` claiming a corpus armed for five
milestones. The advantage is that **we own a mechanism that finds them** — planted-defect probes,
`tests/test_guard_corpus.py`, a reviewer briefed to delete things and watch what stays green — and
Orca ships nothing that could find one.

That advantage is thinner than it looks: **5 of 58 test modules declare a `CORPUS`**, and the tree
holds ~330 lifetime probe rows against ~1,253 cases. Most of our suite has never been probed either.

### 3.2 Cross-run memory

Orca has no answer to *what work exists*, *what is open*, *what did we decide and why*, *what
shipped in v1.3.0*. Every run begins at an objective sentence and its artifacts are gitignored. The
adversarial pass expected this belief to break and it did not move: the PM tree is a product with
586 grains in one consumer and 132 in another.

### 3.3 The published-API discipline, with a live example

Their `package.json` says `"version": "0.1.0"`. Their `ROADMAP.md` says *"Current release: v1.5.0"*
and their tags agree. Our `version-sync` release check exists for exactly this and would refuse the
release; hard rule 7 says the version sites *move together, always*.

Their `bin/init.mjs` carries a file whitelist duplicating `package.json`'s `files`, under the
comment `KEEP THE TWO LISTS IN SYNC` — a second scoreboard, acknowledged in the source. We have
`test_every_installable_on_disk_is_reachable_through_a_verb` for that shape.

And their upgrade path has no drift detection: re-running the scaffolder keeps your file
(`kept yours`) or `--force` overwrites everything including your configs. Nothing tells you a config
you edited is now stale against a newer `flow.mjs`. Our `--diff` + per-file decision + `adopt` is
the answer to precisely that failure, and the release skill already documents why `--force` being
whole-set is a real cost.

### 3.4 A claim of verification that does not ship

`flow.mjs:456` says the usage helpers are *"extract-tested by `.orca/usage-test/run-tests.mjs`"*.
That file is gitignored (`.gitignore:13`) and was never committed in 95 commits. The most intricate
logic in the product carries a claim of testing a reader cannot run.

There is no test file, no assertion, no fixture and no CI anywhere in the repo. Their stated
verification loop is `node --check`, a JSON parse and a `--dry-run`, and the README is accurate
about that — if anything it understates it.

---

## 4. What this comparison found in our own tree

The point of reading someone else's design is what it shows you about yours.

1. **A citation of mine resolved to the wrong decision.** I wrote bare `D1 (emit, never execute)`
   into `bg-a-dispatch-nobody-records-…` during 0.6.0's close. `D1` of *that* milestone is *a parent
   does not close over unresolved children*; emit-never-execute is `0.5.0/D1`. The tree's own
   convention is `<version>/D<n>` — used 47+ times in source and grains. Fixed on this branch. It is
   the milestone's own defect class: a reference that silently resolves to a real, wrong thing.

2. **Our estimate of our own coupling is off by ~2x, in the flattering direction.** The 0.6.0 brief
   says the hard rules are cited *"roughly 600"* times with *"rule 4 alone 194"*. Measured over the
   476 tracked `*.py`/`*.md`/`*.sh`/`*.toml` files outside `.claude/worktrees/`, case-insensitive
   `\brule [0-9]+\b`: **1,107 citations, rule 4 alone 314.** The "600-site migration hazard" we
   documented as the reason never to renumber is an 1,100-site hazard.

3. **Three different numbers are all called "the test count"** — 1,132 (pytest), 1,253 (static
   `def test*`), 1,140 (the `[tests] cases` ceiling). None wrong, none the same, and I used them
   interchangeably in this session.

4. **Nothing in the tree gates on whether a shipped thing was ever used.** Both real consumers are
   pinned at v0.4.0. v0.5.0 and v0.6.0 have reached nobody, and **0 of 718 consumer grains carry the
   `changelog:` field** that 0.6.0 shipped as its headline feature. 44% of the milestone's commits
   touched only `pm/` and `docs/`; consumer-reachable churn was 3,145 lines against 5,322 lines of
   process artifact.

   That is the strongest point against this design and it is not about complexity. **The milestone
   named "the rule reaches the work" did not reach the work** — its own close records that none of
   its four surfaces reached the session that closed it, its ledger holds four hand-typed rows, and
   its headline feature has zero adoption. The tool is honest enough to record all three, which is
   the only reason it is measurable. It is also the one check this checker does not have.

---

## 5. Worth taking, ranked

**1 — a read verb that locates transcripts.** The flagship. `pm ledger record --from-transcript`
already exists; what is missing is a way to *find* the transcript without a hook. The collision is
rule 8 (no file reads a path outside this checkout), and `[emit]` and `[dispatch]` are the precedent
for the resolution: the project **declares** where its transcripts live and the reader refuses by
name when the section is absent — the WORKFLOW-key pattern of rule 5.

The shape that fits `0.5.0/D1` is not a harvester that writes rows. It is a read verb that **lists
candidates** — cwd-matched, time-windowed, with an honest `—` and a reason where it cannot tell —
which the operator pipes into the record verb we already have. Emit, never execute, applied to
discovery. Steal their honest-null discipline verbatim: `u.total > 0 ? {...} : null`, and
`heads.size > 1 → return null`.

**2 — an unattributed column.** Whatever the harvester cannot place must be *counted and named*,
the way they print `N subagent file(s) unattributed`. Rule 11 already demands this; we do not do it
for spend.

**3 — say the `--dry-run` habit out loud.** We have the pieces (`ready-for`, `verify --plan`,
`--diff`) and no sentence anywhere telling an operator to preview first. Cheapest item on this list.

**4 — a rendered status surface, as a read verb.** The ledger already holds everything a dashboard
would show. `file://` polling needs no server and breaks no rule. This is the one item I would
*not* start on: it is a new surface, and item 1 fixes a measured five-milestone defect while this
one improves an experience nobody has complained about.

---

## 6. Not worth taking

- **Their gate model.** Self-reported `outcome`, artifact never read, `|| "succeeded"` on a missing
  payload. This is the thing we exist not to do.
- **A run-scoped, gitignored artifact directory.** It is the absence of the PM tree, not an
  alternative to it.
- **`--force` as the only upgrade lever.** We already have the better answer and have written down
  why.
- **A dependency on a commercial runtime.** Though see below — this cuts both ways.

---

## 7. Two arguments we should stop making

**"They need a commercial IDE; we need only Python."** The *package* is genuinely stdlib-only. The
*workflow* needs twelve agent definitions, 4,463 lines of installables, five `cc-*` Claude Code
hooks, a vendor model roster carrying an `effort:` key our own `SDLC.md` marks UNVERIFIED, and
`uvx`. Orca declares its Orca ADE dependency in the first line of its quickstart. We file ours under
nothing. Keep the rule-1 argument for the CLI; drop it as a comparison of the two systems.

**"Emit, never execute, therefore no orchestrator."** See §2.1. The constraint is about gates. It
has been doing rhetorical work it was never entitled to do.

---

## 8. What we would give them

The guard corpus. `CORPUS` + `catches()` + an `UNCOVERED` roster that can only shrink — a gate that
grades whether a gate can fail. One planted case — *a task record with no outcome field must not
score as success* — kills `flow.mjs:1556` on the day it was written, and a second — *the primary and
recovery paths must agree on what a missing verdict means* — kills the disagreement behind it. Both
are pure-function tests over code the author deliberately kept dependency-free for exactly that
purpose. It is the cheapest possible thing that would have found either, and nothing they ship
could.

---

## 9. Open questions

- **Should `docs/research/` be in `[doc] scope`?** It is not today (`docs/*.md` is one level), so
  this document's own path claims are ungated. A research doc making claims against the tree that
  nobody checks is the exact class `check doc` exists for.
- **Is `pm decide` over-engineered for what it delivers?** Their `ROADMAP.md § Not building (by
  design)` captures most of the value of a rejected-alternative record at a fraction of the cost.
  Recording the rejection is a belief that survived; *the form we record it in* was not tested.
- **What would an adoption gate look like?** §4.4 is the sharpest finding in this document and we
  have no mechanism for it. `adopt` reads a consumer's tree — but only when a consumer runs it, and
  neither has since v0.4.0.
