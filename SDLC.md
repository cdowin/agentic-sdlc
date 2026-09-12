# Agent workflow — the devkit SDLC

The loop this repo runs, as a contract; the decisions logs under `pm/roadmap/` hold the why. The
agent roster that executes it in consumer repos is installed by `agentic-sdlc install-agents` from
`src/agentic_sdlc/repo/installables/`; this repo self-hosts its own pair (`tests/test_install.py`).

## 0. The three levels

| grain | you are | it ends when | what runs at the end |
|---|---|---|---|
| **story** | writing code | the work is done and its own narrow check is green | nothing. **Capture it: `done`.** |
| **feature** | done writing; the stories are all `done` | a reviewer has looked at the whole feature and its findings are landed | the **feature review** → a review record → `done` |
| **milestone** | done with features; they are all `done` | the cross-cutting review is landed and the FULL gate is green | the **milestone review**, then `make milestone` — in that order |

### The review is part of the CLOSE, and the close is a stopwatch

**One reviewer per MILESTONE, dispatched the moment its last feature lane merges**, writes every
feature's record and the milestone's cross-cutting record in one pass (0.9.0–0.11.0: one pass of
~10 minutes where 0.8.0 ran five of 16–26 minutes each, then a sixth). The belt still refuses a
feature close without a record, so the records land before the closes and the release, with
nothing batched after them. **Every grain is on a stopwatch from its first status write to its
last**: close a grain as fast as it can honestly close.

**ONE review pass per grain.** A second pass is an emergency ripcord — for a feature whose review
turned up something that changes the shape of the work — not a routine. Two passes over one
changeset mostly finds the second reviewer's taste.

**A feature review is scoped to the CHANGESET and the SHIP CRITERION**, and asks two questions:
*does this feature do what its criterion says*, and *does it commit either of rule 4's sins*. It is
not a general audit of everything the change touched. The cross-cutting pass at the milestone is
where the wide questions live — §0's own rule, that each level asks a question the level below
cannot.

**Severity gates the hold** (0.3.0): `BLOCKER`, `CRITICAL` and `MAJOR` block a close; everything
below is recorded, reported on every run, and carried. An open NIT used to hold a feature exactly
as hard as a shipping bug, which taught reviewers to stop writing NITs — losing the cheap
observation, which is the one you most want written down. **Bugs will come up after the close. That
is fine; file them.** A milestone that ships with three known MINORs and a bug record beats one
that ships a week later with none.

### The intent, in three sentences

1. **Rip through stories:** done when the work is done and its unit slice is green.
2. **A feature flips to `reviewing` when every story under it is `done`;** the milestone's one
   review pass writes its record.
3. **A milestone flips to `reviewing` when every feature is `done`;** cross-cutting review, one gate.

Each level asks a question the level below cannot, and a belt never runs a belt above it (the 170x).

### What the code does and does not enforce

Only the entry condition to each level is enforced, because that is a fact about the tree:

```
agentic-sdlc pm ready-for story     <sid>    what the story belt asks that is decidable
                                             BEFORE the work — `[story] steps` narrowed to
                                             what the registry declares an entry condition
agentic-sdlc pm ready-for feature   <fid>    every story `done`?
agentic-sdlc pm ready-for milestone <mid>    every feature `done`, each with a record?
agentic-sdlc pm ready-for tag       <mid>    every finding at a disposition other than `open`?
```

Exit `0` ready · `1` not, naming every blocker · `2` usage or config. Honesty is judgement.

There is no `ready-for adopt`: every check in that belt is either the work the bump does or one
that runs a command, so nothing is decidable up front and the rung could only ever say NOT READY
(0.5.0/D4). `agentic-sdlc adopt <version>` is checks-only and writes nothing. Each rung files a
`rung.enter` event where `[emit]` declares a sink — **this repo declares none, so its own tree
emits nothing**, and turning that on is a milestone-scope call about the self-hosting clause.

## 1. Milestone-branch SDLC

- **Work happens on `milestone/<id>`**, declared by the milestone's `branch:` frontmatter (D9).
- **`main` is merge-commit-only, at close:** merge-commit + tag, via the `/release` skill.
- **D10 (opt-in) holds an in-progress milestone off the `[repo_hygiene] mainline`;** on here.
- Version bump is at CLOSE here (D8 off in `devkit.toml`); consumers bump at start.
- **Forward only:** nothing pushed is amended, rebased, reset or force-pushed.

## 2. The dispatch loop

The `run-the-sdlc` skill is this loop with its commands; this section is the contract it runs.

- **No planning pass over planned work.** A feature, story or bug with a Fix that outlines the work
  IS the brief: no po, scout or spec review first. An unplanned feature gets its open questions
  DECIDED by the orchestrator, inline, in the dispatch; decisions with a rejected alternative go
  through `pm decide`.
- **One developer per feature, or per lane of features that share files,** in one context: write,
  then refine. Reviewers polish.
- **A worktree per lane, off an explicit base.** Lanes on disjoint files run concurrently, each in
  the kit's own `tools/dev/agent-worktree.sh new <slug> <base>`, never a harness's worktree option
  (Claude Code's `isolation: "worktree"` bases on the default branch, not the milestone's). The
  builder commits on its branch; the orchestrator merges it into the milestone branch when it
  reports (`git -C <root> merge --no-ff --no-edit <branch>`, then `agent-worktree.sh done <slug>`),
  and `*.jsonl merge=union` keeps the ledgers conflict-free. Builders never share one tree: the story
  belt's `committed` check is false while ANY builder has files in flight.
- **Milestones stack.** The next milestone's branch is cut early from the current tip; its lanes
  that collide with nothing in flight start at once, and the earlier milestone merges forward when
  it lands.
- **Two builders splitting one area get one written CONTRACT in both prompts**, such as a row
  schema, and build against it concurrently.
- **The brief is short:** the grain path(s), what is decided, the files other lanes own, `make unit`
  only, commit on your branch, and a ≤15-line report with the changelog sentence, NEEDS YOU and NOT
  verified. It never says read SDLC.md, write a plan, or run a wide gate.

**Builders:**

- **never run a repo-wide git command** (`git stash`, `git checkout -- .`, `git restore`,
  `git reset`, `git clean`); **to watch a test fail at HEAD, copy the file to a scratch path** —
  the pathspec stash form is still a stash;
- never touch `pm/roadmap/` or a file another lane owns; a grain's `changelog:` is written with
  `pm set`, not by hand;
- ship, with every fix, a test that **failed at HEAD**;
- run **scoped** verification only, never the full gate — and *scoped* means a TIER TARGET, never a
  bare `pytest <file>`: selecting a module by path collects every tier in it, including the cases
  that spawn real processes. A builder that believes it needs a wide gate reports and stops.

**The orchestrator decides builder questions itself** unless they face outward, and asks for the
release acts (push, PR, merge, tag, issues) ONCE, up front. **It runs the belts as the NEXT ACTION,
never as a batch:**

    a lane reports                        →  merge it, record its cost, close story <id> per slice
    every feature is built                →  ONE reviewer, effort `high`, over the milestone's
                                             range: every feature record + the milestone record
    its BLOCKER/CRITICAL/MAJOR are fixed  →  every other finding gets a disposition (landed /
                                             deferred:<bug> / rejected:<why>), close feature <id>
                                             for each, close their GitHub issues, release

**Measure every dispatch** — duration, tool calls, tokens — in the ledger, against the previous
milestone: `pm ledger record --grain <id> --agent-id <id> …` when it returns, `pm ledger report
<previous> <this>` to compare. Nothing runs above effort `high`.

**The orchestrator is bound by the builders' git rules too.** No `bisect`, `stash`, `reset`,
`checkout -- .`, `restore`, `clean`, `rebase`, or ad-hoc `worktree add`. A red test is diagnosed by
reading the test and the code at HEAD, never by rewinding the tree.

**A fix dispatch after a review lands the MAJOR-and-worse findings only**, per §0: a MINOR is recorded,
not held for. Pure-text edits (a README row, a brief's sentence, a description) the orchestrator
makes itself rather than dispatching.

**The orchestrator:**

- verifies each reported lane against the actual tree, never the narration;
- runs the one authoritative full gate (`make milestone`) itself;
- moves every status through the pm CLI — `check pm` is the drift gate;
- appends decisions and runs each belt as its input lands;
- **closes the GitHub issues a feature names, as part of accepting it.** For each issue on the
  feature's `Issues:` line, it pushes the branch first so the hash resolves on GitHub. Then it posts
  a comment naming the feature id, the commit hash(es) that fixed the issue and the version it ships
  in, and runs `gh issue close <n> --reason completed`. **Cite a hash, never the branch:** `milestone/*`
  branches are deleted after the merge, and hashes survive it because `main` is merge-commit-only and
  forward-only. An issue the feature only partly fixes gets the comment, stays open, and the comment
  names what remains and where it is tracked.

## 3. The model mix

Every roster agent carries `model:` and `effort:`; **effort tracks judgment under UNCERTAINTY, and
nothing runs above `high`** (2026-09-12: a builder that re-writes code is cheaper than one that
ruminates; the extra effort bought length, not correctness). **The loop dispatches `developer` and
`reviewer`.** The rest are optional tools an orchestrator reaches for, never a mandatory pass.

| role | model | effort | why |
|---|---|---|---|
| `architect` | opus | high | every dispatch inherits its framing |
| `po` | opus | medium | optional: briefs work no grain outlines yet — a wrong brief is N wrong builds |
| `developer` / `verification-builder` | opus | medium | the job is judgment under a possibly-WRONG premise |
| `reviewer` / `verification-reviewer` | opus | high | the gate, and it runs last; a miss here ships |
| `milestone-reviewer` | opus | medium | optional: pressure-tests a spec nobody has outlined, never planned work |
| `simplifier` | fable | medium | *"should this exist"* has no ground truth — the most abstract pass |
| `test-writer` | sonnet | medium | audit-shaped work against a known diff |
| `tech-writer` / `doc-hygiene` / `pm-operator` | sonnet | medium | prose sync + structured ops against a known diff |

**`model:` is overridable per-dispatch, downward.**

> **`effort:` as a frontmatter key is UNVERIFIED**, because an unsupported key is silently ignored.
> To verify: put an invalid value on a throwaway agent and dispatch it; an error means it is real.

## 4. Token economy

- **Builders run scoped test slices only;** one full-gate run per landing point, the orchestrator's.
  This is ENFORCED, not asked: outside the spawning tier a subprocess fails the
  test that made it, by nodeid (`tests/conftest.py`). The static mark reads a
  module's source and cannot see a spawn reached four frames down — which is how
  the full matrix gate once ran inside `make unit`, taking it from 7 s to 153 s
  with nothing saying why.
- **Reports are evidence + deltas** plus what was NOT verified; gate output only when it FAILED.
- **Reports are capped** at roughly a screenful of findings; artifacts ride in files.
- **Every report ends with its token cost**, so an over-budget dispatch is visible in time.

## 5. An input surface ships with its refusal matrix

The contracts are universal negatives over input space and a builder left alone writes existential
tests, so a story that adds or extends an INPUT SURFACE (a verb, a grammar, a config key) ships:

- a **refusal matrix**: the inputs the grammar rejects (traversal, empty/dot segments, backslashes,
  globs, absolute paths, schemes, whitespace, over-long strings), each proven to refuse, no write;
- **adversarial cases against the code's own docstring claims**: every "never", "cannot" and
  "only" gets hostile input generated AGAINST the claim.

The seeded harness (`tests/test_fuzz_inputs.py`, in `make fuzz`) is the floor beneath both.

### The matrix belongs to the GRAMMAR, not to each surface

Amended 2026-09-05: a dozen surfaces share three grammars (`inventory.segment_is_literal`,
`version_defect`, `subject_defect`), so **enumerate the matrix once, where the grammar lives; a
surface that REUSES a grammar proves that it reuses it** with one case. Inventing one is a finding.

## 6. A new test says why the old ones were not enough

Acceptance criteria say what must be TRUE, not what DEMONSTRATES it, and that gap is where a suite
grows (7,241 statements of source against 13,023 of tests). So a story names, per criterion, the
case that proves it and its tier (`## How this is proven`), and:

> **Name the test that already covers this, or the one that could be AMENDED to. A new case is
> warranted only when neither exists.**

Prefer, in order: amend an existing case → a `parametrize` row → a new function → a module.
**The reviewer asks it, because nobody upstream will.**

## Close protocol — GENERATED, not written here

**The check lists live in [`docs/sdlc-protocol.md`](docs/sdlc-protocol.md), which
`agentic-sdlc install-sdlc` RENDERS from the step lists,** because a second home drifts.

**A belt is its checks, then one write or a clean error** (D12): `close story <id>`,
`close feature <id>` or `release <version>` runs every check, prints `ok: <check>` or
`error: <check>: <what is false>`, and writes AT MOST the grain's status — all true → exit 0 and
`next:` lines; any false → exit 1. `--force` writes anyway on the ledger. `adopt` is checks only.

What stays here is the judgement the machine cannot make and the rule that orders it:

1. **Cross-cutting review** — the milestone's one reviewer over its whole commit range, RUN,
   never diff-read; `findings-resolved` reads its ARTIFACT through `pm ready-for tag`.
2. **Land every finding** it raised, or defer each one explicitly and in writing.
3. **When a gate and a judgement both bear on one decision, the judgement runs first and the gate
   answers for its result;** Chris: *"The make milestone with the full test suite is the LAST thing."*
4. **The semver call** — patch, minor or major (hard rule 7); `version-sync` only checks the
   number you chose is written everywhere, and the bump itself is the release commit, yours.

Everything else is a check in the generated document, or a `next:` line that `release` prints
(release notes, push, PR, merge, tag, artifact proof, mainline sync).
