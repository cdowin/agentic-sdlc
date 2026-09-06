# Agent workflow — the devkit SDLC

The loop this repo actually runs, codified after running it. A contract, not a
narrative: each rule below was the resolution of a real failure or a real
decision (the decisions logs under `pm/roadmap/` hold the WHY). The base agent
roster that executes this SDLC in consumer repos is installed by
`agentic-sdlc install-agents`; the sources live under
`src/agentic_sdlc/repo/installables/`, and this repo self-hosts the pair it
runs itself (partial-roster self-hosting — see `tests/test_install.py`).

## 0. The three levels — read this first

**Everything below assumes these three. Get them wrong and the rest reads as
bureaucracy.** Written out on 2026-09-05 after an orchestrator ran this loop
badly enough to need them: it parked twenty-eight finished stories at
`reviewing` and then reviewed the whole milestone in one pass, skipping the
feature level entirely — in the milestone that built the levels.

| grain | you are | it ends when | what runs at the end |
|---|---|---|---|
| **story** | writing code | the work is done and its own narrow check is green | nothing. **Capture it: `done`.** |
| **feature** | done writing; the stories are all `done` | a reviewer has looked at the whole feature and its findings are landed | the **feature review** → a review record → `done` |
| **milestone** | done with features; they are all `done` | the cross-cutting review is landed and the FULL gate is green | the **milestone review**, then `make milestone` — in that order |

### The intent, in four sentences

1. **Rip through stories.** A story is done when its work is done and its unit
   slice is green. Say `done` and move. Chris, 2026-09-05: *"We wanna capture
   work. We want things to be DONE."*
2. **`reviewing` at story grain is a hand-off, not a terminus.** It means a
   builder is saying "look at this". A tree full of stories parked there is a
   tree where finished work is described as waiting.
3. **A feature flips to `reviewing` when every story under it is `done`** — and
   THAT is when a reviewer runs, once, over the whole feature. Not per story.
   Features go in parallel; each is captured on its own.
4. **A milestone flips to `reviewing` when every feature is `done`** — and that
   is where the cross-cutting review and the big integration checks live. One
   full gate, at the end, paid once.

### Why the levels are not the same review three times

Each level asks a question the level below **cannot**:

- a **story** cannot see duplication with its sibling — it was written alone;
- a **feature** review reads the whole feature's commit range and sees a
  function that grew across four stories, a contract two of them broke
  differently, a name that means two things;
- a **milestone** review sees what the features did to each other, and it is
  the only level that can ask *"is this releasable"*.

**A belt never runs a belt above it.** Reviewing a story at milestone scope is
not thoroughness — it is the 170x, and it is measured: 154 s whole against
0.9 s for the module the edit touched.

### What the code does and does not enforce

Not all of this can be enforced, and it should not be. What is enforced is the
**entry condition to each level**, because that is a fact about the tree:

```
agentic-sdlc pm ready-for feature   <fid>    every story `done`?
agentic-sdlc pm ready-for milestone <mid>    every feature `done`, each with a record?
agentic-sdlc pm ready-for tag       <mid>    every finding at a disposition other than `open`?
```

Exit `0` ready · `1` not, **naming every blocker** · `2` usage or config. What
those verbs will not tell you is whether the review was any good, whether the
story was really finished, or whether `done` was honest. That is the judgement
this document exists to describe and a machine cannot hold.

## 1. Milestone-branch SDLC

- **Work happens on `milestone/<id>`.** The milestone's `branch:` frontmatter
  declares it — that is rule **D9** (`agentic-sdlc check pm`): a `building`
  milestone with no `branch:` stamp leaves a fresh session guessing at
  `git branch -a`.
- **`main` is merge-commit-only, at close.** No direct commits to main while a
  milestone is building; close = merge-commit + tag, via the `/release` skill.
- **D10 (opt-in) holds a building milestone off the mainline:** a `building`
  milestone's `branch:` must not equal the `[repo_hygiene] mainline`. This
  repo turns it on for itself — the single-maintainer work-on-main carve-out
  is exactly how the divergence from the consumers' SDLC went unnoticed
  (decision D3, 0.16.0).
- Version bump is at CLOSE here, not at start (D8 stays off in `devkit.toml`;
  the consumers bump at start — both flows are legal, each repo declares one).
- **Forward only.** Nothing pushed is ever amended, rebased, reset or
  force-pushed; a botched commit is repaired with another commit.

## 2. The dispatch loop

**Scout once, not per-agent.** An audit / PO pass runs first and produces a
findings doc under `docs/reviews/` with file:line claims. That doc becomes
every dispatch's reference — each builder gets the claims it needs, already
verified, instead of re-deriving the survey N times.

**PM scaffold before build.** The milestone is a real PM tree
(`agentic-sdlc pm new …`), with features/stories for the ratified scope and a
decisions log appended through `pm decide` — never by hand.

**Phased parallel dispatch on DISJOINT file sets.** Builders run in parallel
only when their file sets cannot collide; overlapping work is serialized.
A dispatch prompt names the files the builder may touch and the files it must
stay out of.

**Builders:**

- never commit — they write, verify their slice, and report;
- **never run a repo-wide git command.** `git stash`, `git checkout -- .`, `git restore`,
  `git reset` and `git clean` act on the WHOLE worktree, and phased parallel dispatch
  puts N builders in one. Measured 2026-09-05: one builder stashed to watch a test
  fail at HEAD — the correct instinct — and stashed six other builders' uncommitted
  work with it, including deletions that were already staged. It popped cleanly and
  nothing was lost, which is the only reason this is a rule rather than an incident.
  **To watch a test fail at HEAD, copy the file to a scratch path and edit the copy.**
  Not `git stash push -- <your own paths>` either: this document said that for four
  hours, and then the ORCHESTRATOR used it — push, read the file, pop, overwrite —
  and destroyed its own edit, because the pathspec form is still a stash and the
  window between push and pop is still a window. **Copy the file. There is no safe
  git verb here.** The orchestrator, which owns the index, is the only one that
  touches it;
- never touch `pm/roadmap/`;
- never edit shared docs — README / CHANGELOG wording is returned as
  **PROPOSED** text in the report, and the orchestrator applies it;
- ship, with every fix, a test that **failed at HEAD** — watched failing on
  the unfixed code, passing on the fixed code;
- run **scoped** verification only (the slice's test file, the affected
  check) — never the full gate.

**The orchestrator:**

- verifies each reported slice against the actual tree (never the narration —
  subagents misreport pre-existing state);
- runs the one authoritative full gate (`make milestone`) itself;
- commits per feature by **explicit pathspec**;
- moves every status through the pm CLI (`pm story building/reviewing`,
  `pm feature done`, …) — `check pm` is the drift gate;
- applies proposed shared-doc wording, appends decisions, opens the close.

## 3. The model mix

Every roster agent carries `model:` and `effort:` frontmatter. **Effort
tracks how much judgment under UNCERTAINTY a role needs — not how important
it sounds.** Table borrowed from the consumers (set 2026-08-27), carried into
the installables:

| role | model | effort | why |
|---|---|---|---|
| `architect` | opus | high | every dispatch inherits its framing |
| `po` | opus | high | writes the briefs N agents execute verbatim — a wrong brief is N wrong builds |
| `developer` / `verification-builder` | opus | high | the job is judgment under a possibly-WRONG premise |
| `reviewer` / `verification-reviewer` | opus | **xhigh** | the gate, and it runs last; a miss here ships |
| `milestone-reviewer` | opus | high | pressure-tests the spec everything downstream builds from |
| `simplifier` | fable | high | *"should this exist"* has no ground truth — the most abstract pass |
| `test-writer` | sonnet | medium | audit-shaped work against a known diff |
| `tech-writer` / `changelog-writer` / `doc-hygiene` / `pm-operator` | sonnet | medium | prose sync + structured ops against a known diff |

**`model:` is overridable per-dispatch, downward.** For genuinely mechanical
stories — doc sweeps, retirements, template chores, renames — drop to a
cheaper model at lower effort in the dispatch itself. Keep the strong model
wherever the brief might be WRONG: judgment-under-possibly-wrong-premise is
the case the strong builders repeatedly earn their keep on. The closing
reviewer always runs strong at the highest effort.

> **`effort:` as a frontmatter key is UNVERIFIED.** A misspelled or
> unsupported frontmatter key is silently ignored — it does not error, it
> just does nothing — and the agent registry loads at session start, so it
> cannot be probed from the session that sets it. `model:` is the field with
> proven effect. To verify: put a deliberately invalid value on a throwaway
> agent and dispatch it; an error means the field is real, silent success
> means the whole column is inert.

## 4. Token economy

- **Builders run scoped test slices only.** One authoritative full-gate run
  per landing point, owned by the orchestrator. N builders each running the
  full suite is N-1 wasted runs — and a builder's green full gate still gets
  re-run before commit, so it bought nothing.
- **Reports are evidence + deltas.** What changed, what ran, what came back —
  numbers, not adjectives — plus what was NOT verified. No narrative recap of
  the dispatch prompt, no pasted PASS walls: gate output is quoted only when
  it FAILED.
- **Reports are capped.** A dispatch report that cannot fit in roughly a
  screenful of findings is doing the orchestrator's synthesis job badly.
  Proposed shared-doc wording rides in the report; artifacts ride in files.
- **Every report ends with its token cost**, so an over-budget dispatch is
  visible while the session can still act on it.

## 5. An input surface ships with its refusal matrix

This package's contracts are universal negatives over input space ("this
cannot write a sibling grain"), and a builder left alone writes existential
tests for intended behavior — which is why every release review before
0.17.0 caught its blocker instead of the pipeline catching it. The
adversarial stage is therefore standing, not a review courtesy. A story that
adds or extends an INPUT SURFACE — a CLI verb, an id/path grammar, a config
key, a payload parser — ships, in the same story:

- a **refusal matrix**: the inputs the grammar rejects — traversal,
  empty/dot segments, backslashes, globs, absolute paths, schemes,
  whitespace, over-long strings — enumerated as tests, each proven to
  refuse without a write;
- **adversarial cases against the code's own docstring claims**: every
  "never", "cannot" and "only" the docstring states gets hostile input
  generated AGAINST the claim, never a re-run of the intended path.

The seeded property harness (`tests/test_fuzz_inputs.py`, in `make fuzz`)
is the standing floor beneath both: it holds the whole CLI to
refuse-or-contained-write; the matrix pins the new surface's specifics on
top of it.

### The matrix belongs to the GRAMMAR, not to each surface

Amended 2026-09-05, because this section is a source of the growth §6 measures.
Read literally, it asks every new input surface to enumerate traversal, empty
segments, backslashes, globs, absolute paths, schemes, whitespace and length —
and there are a dozen such surfaces sharing three grammars
(`model.segment_is_literal`, `version_defect`, `subject_defect`). Twelve
surfaces times twelve spellings is 144 cases proving one rule.

**Enumerate the matrix once, where the grammar lives. A surface that REUSES a
grammar proves that it reuses it** — one case showing the refusal arrives, and
the grammar's own matrix carrying the spellings. A surface that invents a
grammar is a finding before it is a test.

## 6. A new test says why the old ones were not enough

Acceptance criteria say what must be TRUE. They do not say what DEMONSTRATES
it, and that gap is where a suite grows without anyone deciding to grow it: a
builder proving a criterion writes as many cases as feels safe, each cheap
alone, expensive only in aggregate, and nothing downstream asks about the
total. Measured in this package on 2026-09-05: **7,241 executable statements of
source against 13,023 of tests, and one test function per 4.9 statements.**

So a story names, per criterion, the case that proves it and the TIER it runs
in (`## How this is proven`). And before any new case is written:

> **Name the test that already covers this, or the one that could be AMENDED
> to. A new case is warranted only when neither exists.**

*"I could not find one"* is an answer that has to have been looked for. Prefer,
in order: amend an existing case → add a `parametrize` row → a new function →
and only for a genuinely new surface, a new module.

**The reviewer asks it, because nobody upstream will.** Every release review
this package has ever had came back having found a false PASS, and not one of
them mentioned test cost — a reviewer catches what the rules name. The
questions are in the roster's reviewer definitions; the short form is: which
existing test covers this, is this the same rule at a second altitude, and does
what landed match the story's own table.

## Close protocol — GENERATED, not written here

**The ordered steps live in [`docs/sdlc-protocol.md`](docs/sdlc-protocol.md), which
`agentic-sdlc install-sdlc` RENDERS from `[release] steps` and the registry that
walks them.** It is not hand-maintained and must not be edited: a document
describing the steps is a second home for the protocol, and this package spent
three incidents proving that a second home drifts. Run
`agentic-sdlc release <version>`; it stops at the first step whose postcondition
is not true and says what would make it true.

What stays here is the part that is NOT a step — the judgement the machine
cannot make and the rule that orders it:

1. **Cross-cutting review** — a fresh strong reviewer over the milestone's
   whole commit range (adversarial input, RUN — never diff-reading). The
   conveyor's `review-landed` step reads the ARTIFACT of that review; it cannot
   perform it, and it refuses to advance until the artifact exists.
2. **Land every finding** it raised, or defer each one explicitly and in
   writing. `review-landed` passes only when no finding sits at
   `disposition: open`.
3. **When a gate and a judgement both bear on one decision, the judgement runs
   first and the gate answers for its result.** Chris, 2026-09-04, after this
   exact inversion cost two full runs on 0.24.0: *"The make milestone with the
   full test suite is the LAST thing before saying 'yeah, this is done'."* A
   gate that runs before the review answers for a tree nobody will ship: every
   fix landed afterwards voids it, and it reads as readiness while doing so.

   **That ordering is now structural rather than remembered** — `review-landed`
   precedes `gate` in the shipped step list, and a registry that omits the
   dependency is a test failure, watched failing: with the list `('gate',)` the
   recorder file the gate touches exists; with `('review-landed', 'gate')` it
   does not.
4. **The semver call** — patch, minor or major (hard rule 7). Code cannot make
   it; `version-sync` only checks that the number you chose is written in every
   place that carries it.

Everything else in the old numbered list — the tree checks, the changelog
retitle, the version sync, the status flips, the push, the merge, the tag, the
artifact proof — is a step in the generated document, with its own
postcondition, and re-stating it here is exactly what this milestone removed.
