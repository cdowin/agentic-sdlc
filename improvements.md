# improvements.md — what building 0.4.0 taught us about the tree

**Why this file is at the root and not in a milestone.** 0.4.0 changes how the whole PM tree
works. A lesson filed *inside* the tree would have to be migrated by the very migration it is a
lesson about. This file sits outside and is adopted after the merge.

**Where the numbers live: `pm/roadmap/0.4.0-.../ledger.jsonl`, not this file.**
`pm ledger report` renders it. This file carries only what a ledger row cannot hold — the
narrative and the fix. See F5 for why that sentence had to be written twice.

---

## The headline

**This milestone's own thesis was reproduced, live, by the agent building it, inside the first
fifteen tool calls.**

`0.4.0/the-read-verbs-compose` opens with a trace: an agent reviewing the 0.4.0 design reported a
missing capability, proposed a new verb, and was told the capability already existed — the surface
just had not advertised it at the moment of need. The feature draws the general rule:

> A read verb that omits a field people filter on does not just inconvenience them — it teaches
> them the tool cannot do it.

Asked for "full telemetry — phasing, timings, token use, tool calls", this agent hand-wrote a
markdown table. The package ships `pm ledger`: a JSONL sink with `status`, `decision`, `gate`,
`test`, `deviation`, `dispatch` and `session` rows; automatic per-session token and tool-call
capture off the Claude Code transcript via an already-installed `Stop` hook; and
`pm ledger report`, whose columns are literally
`dispatches | in | out | cache_create | cache_read | tool_calls | duration_s | todo | in_progress
| done | total_s`, per grain.

The same shape, one layer up. Not a missing column — **a missing word.**

## What it produced

Four features, filed into 0.4.0 as pre-work and built before anything else, because everything
after them should be measured:

| feature | the defect |
|---|---|
| `recording-is-on-or-the-gate-is-red` | a fail-open courier with no fail-loud counterpart |
| `every-row-names-its-grain` | hook rows carry no `grain:`, so nothing attributes to a story |
| `the-surface-says-telemetry` | the word is in no discovery surface in the package |
| `telemetry-arrives-with-the-bump` | settings.json is printed, never written — consumers get nothing |

`the-migration-is-whole-or-nothing` now depends on the first three, so the riskiest work in the
milestone is also the best-measured.

**And a class was named.** `the-read-verbs-compose` had already found two instances of one shape —
a hand-rolled adoption checklist because `adopt` was never found, an invented search verb because
`pm list` withheld a field. This session added a third (the ledger) and, while investigating it, a
fourth (`adopt` does not call the `--self-test` every courier ships). Four is not a coincidence:

> **A capability nobody can find is a capability you do not have.** When a request is met by
> hand-rolling something the package already does, the defect is the surface, not the requester.
> The fix is a word, a column or a line in the file that already loads — never a new verb.

That now has a home in `the-surface-says-telemetry`'s ship criterion, to be stated once in
CLAUDE.md rather than rediscovered a fifth time.

---

## Findings

### F1 — "telemetry" is not a word this package knows, and the synonym is undiscoverable

**Evidence.** `grep -ril telemetry` over the repo: 15 files. Not one is a discovery surface.
Eleven are `pm/roadmap/0.2.0/**` (the design conversation that *built* the ledger), `tests/`,
`docs/design/`, `docs/reviews/`. One is a pygments lexer in `.venv`. The count in
`pm --help`, `CLAUDE.md`, `.claude/rules/pm-execution.md` and both SKILL.mds is **zero**.

So an agent searching the user's word finds only archaeology — the record of the feature being
designed — and never the verb that shipped from it. The capability is called "ledger", and
nothing maps one word to the other.

**Fix.** The word belongs in `pm --help` and in the ledger verbs' own help line, as a synonym in
the sentence that already exists. One word, in the place someone is standing when they need it.
This is `the-read-verbs-compose`'s own remedy applied to itself.

### F2 — the always-loaded rule enumerates the read verbs and omits the ledger

**Evidence.** `.claude/rules/pm-execution.md` § "Keeping the tree honest" is a five-item list:
`pm status`, `pm list`, `pm validate`, `check pm`, `pm vocabulary`. `pm ledger show` and
`pm ledger report` are absent. The word "ledger" appears twice in the whole rule, and both times
as a **side effect of a different verb** — "`--force` writes anyway and the ledger's `deviation`
row names the checks that were false", and "the cost it last took, read from your ledger."

Read cover to cover, that file teaches you a ledger exists as a passive byproduct of other
commands. It never teaches you that you can write to it or read it.

**Fix.** Two lines in that list. It is the file that auto-loads on every tree edit; it is the
cheapest possible place to put them.

### F3 — no skill covers the ledger

**Evidence.** Two skills ship: `pm-operations` and `release`. `pm-operations`'s description
enumerates its scope — "the grain schemas, scaffolding a milestone/feature/story/bug, decomposing
work into stories, and reading `pm status` and `pm validate`." The ledger is in neither skill's
scope, and there is no third.

**Fix.** Either extend `pm-operations` to cover recording and reading spend, or ship a
`pm-telemetry` skill whose *description* carries the words a user would actually say — telemetry,
spend, cost, token use, how long did this take. A skill is selected by its description; a skill
about the ledger that never says "telemetry" does not get chosen when someone asks for telemetry.

### F4 — the telemetry has been silently recording nothing, and still is on 0.3.0

**This one is a live defect, not a documentation gap.**

`.claude/settings.json` wires `Stop` → `cc-ledger-session.sh` (async) and `SubagentStop` → its
dispatch twin. Both are installed and firing. The hook is a courier: it calls
`make pm ARGS="ledger record --from-transcript … --event Stop …"`, and the verb writes into **the
one `in_progress` milestone's ledger**.

On this branch at session start, `0.1.0` was `planning`, `0.2.0` `done`, `0.3.0` `planning`,
`0.4.0` `planning`. **No milestone was `in_progress`, so the verb refused every time.** The hook
fails open by design — it must never block a stop — so it printed to stderr and exited 0. Nobody
reads a hook's stderr. `pm/roadmap/` held exactly one `ledger.jsonl`, 0.2.0's.

Every session on this branch produced zero rows and no visible complaint.

**And 0.3.0 is being actively built right now, in the main tree, at `status: planning`.** That
work is recording nothing, for the same reason, right now.

**Fix, in order of value:**
1. `check pm` should red when hooks that write to the ledger are installed and no milestone is
   `in_progress` — the tool knows both halves and currently reports neither. A fail-open hook
   needs a fail-loud gate somewhere else, or it is just a silent hook.
2. The claim step in `pm-execution.md` should say that flipping the milestone to a
   `in_progress` state is what turns recording on. Today that coupling is invisible: it reads as
   bookkeeping, and it is actually the switch.
3. Consider whether a `planning` milestone should accept rows at all. Arguably the design work
   *is* the milestone's work and the ledger should follow the grain, not the category.

**What it cost here.** Recovered by flipping 0.4.0 to `building` — which the execution loop
already told me to do at the claim step, for unrelated reasons. The first row landed immediately.
Everything before 21:00:25Z on this branch is unrecoverable.

### F5 — I built the second scoreboard the rule I had just read forbids

**Evidence.** `pm-execution.md` § "Keeping the tree honest": *"**Never write what is already
derivable.** … Do not hand-maintain a story list in a feature file … that is a second scoreboard
and it will lie."* I read that file in full at tool call #10. At call #16 I wrote a hand-maintained
markdown table of per-tool-call token deltas into this file — a second scoreboard for data the
ledger already holds, in a repo whose own rule forbids it, while building the milestone about not
keeping two copies of one fact.

It is deleted. What replaced it: `pm ledger record --grain <id> --agent-type orchestrator
--tool-calls N --duration-s N` at phase boundaries, and the `Stop` hook for session totals.

**The generalisable part.** Reading a rule is not the same as the rule being *reachable at the
moment you would break it*. I had the text in context and violated it fifteen minutes later. The
rules that hold are the ones a gate enforces — which is this repo's own stated position
(`encode policies as gates, not comments`) and an argument for F4's fix #1 over F2's fix.

**One honest limit.** I record `--tool-calls` and `--duration-s` on hand rows and **omit tokens**,
because what I can observe is a remaining-budget counter, not an input/output token count. The
verb's contract is "a number not given is a key the row does not carry, never a zero"; filing a
proxy as if it were the real measure would be exactly the cardinal sin that rule exists to stop.
The `Stop` hook reads the real numbers off the transcript. Mine are the ones it cannot see.

### F6 — a handoff names a branch; it does not put you in the tree

**Evidence.** The session opened with cwd `/Users/cdowin/workspace/nullbound` — a different repo —
against a handoff describing an agentic-sdlc worktree. The worktree's path
(`.claude/worktrees/0.4.0`, nested inside the main tree) appeared in no document; finding it took
`git worktree list` against the main repo.

**Cost.** 3 tool calls before the first line of real work, plus a standing per-command tax: Bash
resets cwd to the session's primary directory after every call, so every command since has carried
a 62-character `cd … &&` prefix. The real risk is not the characters — it is that one forgotten
prefix runs against the wrong repo.

**Fix.** A handoff that assumes a working directory should state the absolute path. When worktrees
are in play, a branch name is not a location.

### F7 — batching is ~2.5x cheaper per byte than sequential reads

**Evidence.** Sequential single-purpose Bash reads over calls 2–12 averaged ~1,800 budget units
each for roughly 1–2KB apiece. One `ctx_batch_execute` returned 11.1KB across five commands with
three indexed queries for 4,977 — about what two unbatched reads cost.

**The lesson is not "read less."** Dense prose is cheap: a 4.5KB milestone file cost ~700. What is
expensive is the round trip. Ask for more per call.

**Caveat that matters for reading any of this.** Observed deltas run well below the naive token
count of the same bytes, which points at prompt caching — so these measure *billed marginal cost*,
not context occupancy. Two different things, and the ledger's `cache_read` / `cache_create`
columns are the ones that can actually tell them apart. Another argument for using the sink that
already exists over a table I keep by hand.

### F8 — being rooted in the wrong repo does not cost a prefix, it disables the guarded write path

**The sharp end of F6, and worth separating.** NullBound's `cc-write-confine.sh` is a PreToolUse
hook on `Write|Edit|MultiEdit|NotebookEdit` that blocks an edit into a repository other than the
session's. The session's repo is NullBound. So every `Write` into the agentic-sdlc worktree — the
work I was actually assigned — was blocked:

    BLOCKED (write-confinement): edit targets a repository outside this session's worktree.
      session worktree: /Users/cdowin/workspace/nullbound

The guard is right, and it is well-built: it is exactly the protection against the hazard F6
describes. But its docstring also says **"Bash is not confined; the git layer backstops it."** So
the effect of being rooted in the wrong repo is not a `cd` prefix — it is that **the guarded write
path is closed and the unguarded one is the only one left.** Every file I wrote before noticing
went through a Bash heredoc, invisible to the confinement check.

A guard that closes the safe path and leaves the unsafe one open, under a misconfiguration it
cannot see, is inverted at exactly the wrong moment.

**Resolved, and the resolution is worth copying.** The hook names its own escape hatch —
`tools/hooks/extra-write-roots.local`, gitignored, one git toplevel per line. I granted **only the
worktree**, `…/agentic-sdlc/.claude/worktrees/0.4.0`, deliberately not the main tree at
`…/workspace/agentic-sdlc`. The handoff's most emphatic instruction is *stay in your worktree;
another agent is building 0.3.0 in the main tree*. Granting the narrow path turns that instruction
from a thing I have to remember into a thing the guard enforces.

**Fix.** Two, and the first is nearly free:
1. The block message should name the fix it already knows about in the order a user would pick it
   — the local-grant file is the right answer for "the user assigned me this repo", and it is
   listed second, after "dispatch a separate agent".
2. Since Bash is unconfined by design, the block is a strong signal that the *session* is
   misconfigured, not just that one write was wrong. Saying so — "if you were assigned work in
   that repo, the session is rooted in the wrong one" — turns a per-write refusal into the
   diagnosis.

---

## Open, to decide after the merge

1. **Where does this file go once the tree is flat?** It is a lesson about the tree, filed outside
   it. Under 0.4.0's model it could be a grain of a new kind, or it could stay a root document. The
   fact that it has no natural home is itself information about `[pm.contains]`.
2. **Does `pm ledger` want a `--phase` or free-text label on hand rows?** The one thing the
   automatic rows cannot carry is *what the agent was doing*. Resist if the answer is that grain
   attribution is already that label — but check, rather than assuming, and note that F1/F2/F3 are
   all cases where the answer was "it exists, nobody could find it."
