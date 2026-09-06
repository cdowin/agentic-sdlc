# agentic-sdlc

**agentic-sdlc** is a set of command-line tools for the discipline around a codebase rather than
the code inside it. It scaffolds the structure you work in, runs the work tree from the CLI, and
gates the drift classes that pass a code review in silence — so you're not rebuilding a pile of
shell every time you need an answer or a guarantee. Three verbs: it **informs**, it **scaffolds**,
it **gates**.

It ships as a pinned tag. A project bumps the pin, runs `install-* --diff` to see what changed, and
takes what it wants — which is how a lesson learned in one repo reaches the next. Nothing here boots
anything: it is pure text over git, markdown and shell.

- **Stand a fresh project up in one command.** `init` writes the config, the PM tree, your
  two-line Makefile, the standard target set, the runners, the hooks (armed), the agent roster and
  the CI set — in order, idempotently. → [Wiring it in](#wiring-it-into-your-project)
- **Run a project's work tree from the CLI.** Milestones, features and stories as markdown, status
  moved through code, and a per-milestone ledger that timestamps every transition.
  → [Project management](#project-management-agentic-sdlc-pm-command)
- **Gate the silent-failure classes.** An agent doc whose claims went dead, a hook corpus installed
  but not arming, a PM tree that says two things at once.
  → [Static gates](#static-gates-agentic-sdlc-check-gate)
- **Ship the agent SDLC itself.** `install-agents` writes the roster and the review/build contract;
  `install-hooks` writes the guard corpus that holds an agent to it. The SDLC they run is
  [`SDLC.md`](SDLC.md). → [Installers](#installers-agentic-sdlc-install-what)

## Install

Consumed at a **pinned tag** so every machine and CI runs identical gate code:

```bash
uvx --from "git+https://github.com/cdowin/agentic-sdlc@v0.2.0" agentic-sdlc --version   # agentic-sdlc 0.2.0
```

`v0.2.0` is **this package's own first tag** — it was extracted from `godot-devkit`, and that
project's tags are not this one's version line.

Pin that string once in your Makefile ([Wiring it in](#wiring-it-into-your-project)) and bump it to
adopt a release. **Adopting a bump is three reads:** the CHANGELOG, `pm vocabulary` for what the
closed state/rule sets became, and `install-* --diff` for what the shipped files would change before
you let them. **And one re-run of `pm init`** (idempotent — it fills gaps and rewrites nothing): a
line a release adds to `.gitattributes` reaches an existing tree only that way —
`pm/roadmap/*/ledger.jsonl merge=union`, without which the ledger every branch appends to conflicts
on every merge.

## Quickstart: five minutes

Run these from inside a git repo. **See the whole work tree without opening a file:**

```bash
agentic-sdlc pm list --status building
```

```
[pm] 2 of 27 story/ies
0.2.0/the-extraction-finishes/01-roster-equals-dispatchable	building	orchestrator	0.2.0/the-extraction-finishes
0.2.0/the-extraction-finishes/04-the-first-surfaces-describe-this-package	building	builder-docs	0.2.0/the-extraction-finishes
```

Rows go to stdout and the census to stderr, so the list pipes and the count still reaches you.
`pm status` is the same tree grouped by `phase:` instead of filtered.

**Move one status, and touch nothing else:**

```bash
agentic-sdlc pm story reviewing 0.2.0/the-extraction-finishes/01-roster-equals-dispatchable
```

One frontmatter line is rewritten — every other byte and the file's line endings preserved — and
one timestamped row is appended to that milestone's `ledger.jsonl` after the write lands.

**Then run the gates** — `agentic-sdlc check all`. On a repo that has never used this, **expect red
from `check doc`**: always-loaded agent docs accumulate claims that stopped being true, and nothing
else was looking. That is the tool working. See
[Adopt the gates on an existing repo](#adopt-the-gates-on-an-existing-repo).

## Adopt the gates on an existing repo

A NEW project skips this section: `agentic-sdlc init` writes everything and the last step below is
already done. This is the order for a tree that already has content in it — some steps start red by
design.

| Step | Command | Expect |
|---|---|---|
| 1 | `check doc` | Red on most repos with agent docs nobody has pruned: dead links, dead `make` targets, dead file paths. Every finding is a line to fix or a claim to delete. |
| 2 | `check shell` | Whatever `shellcheck -x` says about `tools/`. Soft-skips if shellcheck isn't installed — so a green run on a machine without it means nothing was scanned. |
| 3 | `pm init` → `check pm` | Green on a fresh tree. On a hand-kept one it names every grain whose status contradicts its children, plus the integrity rules `pm validate` shares with it. |
| 4 | `install-hooks` → `bash tools/setup-hooks.sh` → `check hooks` | Red until arming: installing a hook corpus is not arming it, and `core.hooksPath` is what git actually reads. |
| 5 | Wire `check all` and name your roster in `[checks] all` | Green. |

## Every operation has one verb and one scope

The failure this exists to end is measured: an agent doing STORY-layer work verified it at
MILESTONE-layer scope. A full suite is **154 s**, a single module **0.9 s** — **170x** — and
eleven story-layer fixes verified at milestone scope cost **31 minutes**. Re-checking the same five
modules at story scope took **13 seconds**. The agent was not careless; its dispatch named one
command and never mentioned there was another.

So none of these rungs is "run the biggest thing", and a belt never runs a belt above it:

| You are doing | Verb | Scope |
|---|---|---|
| editing — the inner loop | `verify --changed` | only the paths you touched. Seconds |
| closing a story | `pm ready-for feature <fid>` | is every sibling story in the `done` CATEGORY — by whichever word your flow puts there? |
| closing a feature | `verify --feature` | the composition your `[verify] feature` names. Tens of seconds |
| closing a milestone | `verify --milestone` | everything, every interpreter. Minutes, paid **once** |
| tagging | `pm ready-for tag <mid>` | is every review finding at a disposition other than `open`? |
| bumping your devkit pin | `adopt` | the adoption — **never** your project's own gates |

**`verify --plan` prints all three rungs with their measured costs**, read from the `gate` rows in
your ledger, so a dispatch can carry real numbers instead of an author's guess. Where no run has
been recorded the cost is the word `unknown` — never an estimate, because a fabricated ratio is
worse than none: it gets quoted.

**`adopt` is deliberately not a rung.** It is an operation on the toolchain rather than a grain, and
its `checks-pass` step runs *this package's* `check all` — not your `make check`. A version bump
here cannot change your own gates' verdict, so running them during adoption re-verifies your
project, not your adoption. That subtraction is most of what makes a pin bump cheap.

**`[verify] feature` and `[verify] milestone` name a make TARGET you already have**, not a second
command string. The Makefile stays the authority on what a target runs; `[verify]` is the authority
on which rung it is. One fact each — a `wide` that drifts from the `make milestone` CI actually runs
is two answers to "did the full gate pass".

## Reading a gate failure

Every gate prints a **census** of what it scanned, then a verdict — on the FAIL line as much as the
PASS line. Read the census first; a gate that scanned fewer files than you expected is telling you
your config is wrong, not that your tree is clean. A zero-file census FAILS rather than passing, and a
file that could not be DECODED is reported and dropped from the count rather than counted as scanned.

```
[check:doc] FAIL — scanned 0 docs; check [doc] scope                        <- config, not drift
[check:pm]  FAIL — 1 status-drift violation(s) across 18 milestone(s), 12 feature(s), 28 story/ies; 2 warning(s)
  DRIFT  feature 0.28.0/chronicle-bus is done w/o review record  [pm/roadmap/…/feature.md]
  WARN   story 0.28.0/chronicle-bus/s1 is 'ready' and has an empty `## Acceptance criteria` — …
```

A `  WARN  ` line is messaging, not a finding: it is counted separately on the verdict line and
never moves the exit code. `check pm` warns about a grain that was stamped `ready` (past its
kind's first `todo` state) and says nothing about what must be true — an empty scaffolded
`## Acceptance criteria` or `## Ship criterion`, a feature with no stories, a milestone with no
`branch:` or with a feature carrying no `phase:`. The stamp itself is one command by hand,
`pm <kind> ready <id>`, and nothing writes it for you.

**Precision over reach.** Nothing is a finding unless the whole picture resolved; anything
unresolvable is censused `UNVERIFIED`/`UNVERIFIABLE` and never failed. A false PASS is survivable — a
false FAIL gets the gate switched off, and then nothing is checked at all.

**Exit codes are contract:** `0` pass · `1` findings · `2` usage or config error. A `devkit.toml`
mistake is always `2`, so CI can never read a typo as drift. A retired `[pm]` rule id or config key —
what a pin bump produces — is exit 2 from `check pm` and `pm validate` and nothing else, so the read
verbs keep working while you decide what to change.

## Command reference

`agentic-sdlc --help` and `agentic-sdlc pm --help` are the live rosters; this is the same set with
what each one is for.

### Installers (`agentic-sdlc install-<what>`)

An install verb writes a file. **Once.** A destination that exists and is not byte-for-byte what would
be written is refused by path, naming both remedies — move it aside, or `--force`. `--diff` prints what
a run would change and writes nothing. No manifest, no merge: after the write the file is the repo's.
Every refusal is decided before the first byte; a collision withholds **that file**, so the entries
with nothing in their way are written, every collision is named, and the run exits 1 because a
replacement was held back. A difference confined to the `project config` header the file invites you to
edit is reported as one — the rest of that file is byte-current, so it needs no `--force`, and `--force`
would replace the header too. A destination that cannot be written at all (a directory, a read-only
path, a parent that is a file) still refuses the whole command with nothing written.

| Verb | Writes |
|---|---|
| `init` | **All of the below, in the order a fresh project needs them**, plus the three files nothing else writes: `devkit.toml` (every gate section, commented at its stock default, so the file is inert on arrival), your two-line `Makefile` with this tag substituted into the pin, and a `CLAUDE.md` skeleton naming the standard targets and the installed rules. It also appends the run-artifact directories to `.gitignore` and RUNS `tools/setup-hooks.sh`, because installing a hook is not arming it. Idempotent: re-run any time to fill what is missing. **Two ownerships:** the installed files are devkit-owned and `--force` overwrites them; `devkit.toml`, `Makefile`, `CLAUDE.md` and the PM tree are yours from the first write and `--force` never touches them, so a differing seed is reported rather than refused. Refuses, before writing a byte, in a directory that is not a git repo |
| `install-ci` | The three workflows this kit runs on a push: `verify.yml` (checkout, uv, ARM the checkout — `core.hooksPath` lives in `.git/config`, nothing tracked carries it, so a gate asking whether this tree is armed was red on every CI run until the arming step existed — then `make milestone`, which it ASSUMES is your full gate; a project without the target gets a red step naming it), `semver-gate.yml` (a merge to main must bump the version, and the new version must be the id of a `done` milestone under `PM_ROADMAP`, or main's plus one hotfix component — a building milestone's id refuses) and `auto-tag.yml` (tag the mainline from that same version, then dispatch `RELEASE_WORKFLOW` — the one project-specific string, and its absence is a green "tagged only" rather than a red X). **Your build toolchain is yours to add**, below the write: through 0.1.0 this file installed a game engine and two linters behind `hashFiles('project.godot')` guards — one kit's toolchain hard-coded into the other kit's workflow, which D2 settled. Release, website and social workflows are the project's |
| `install-agents` | The review/build contract (`verification-reviewer.md` + `verification-builder.md`) plus the base agent roster — architect, po, developer, reviewer, milestone-reviewer, simplifier, test-writer, tech-writer, changelog-writer, doc-hygiene, pm-operator — under `.claude/agents/`, each with `model:`/`effort:` frontmatter and a Project config section that is yours to edit after install. The four reviewer-shaped definitions (reviewer, simplifier, milestone-reviewer, verification-reviewer) each carry the instruction to end their own pass in one fenced, machine-readable verdict block, APPENDED rather than replacing an earlier pass's — `pm ledger report`'s yield section reads every block in a record and reports one row per pass. The SDLC they run is [`SDLC.md`](SDLC.md). Deliberately not `.claude/rules/*`: a rules file never reaches a subagent's spawn context; a definition does |
| `install-hooks` | The agent-workflow guard corpus: `tools/hooks/` gets `cc-commit-pathspec.sh` (a `git commit` in a shared tree must name its own paths), `cc-stop-gate.sh` (an agent's stop is blocked while its fast gate is red), `cc-write-confine.sh` (a write outside the session's repo is blocked at the edit, not the commit), `pre-push` (no direct push to a protected branch + a scoped trunk gate) and `prepare-commit-msg` (agent commits get the trailer, the human's never do); `tools/dev/` gets `agent-worktree.sh` (the one sanctioned per-agent worktree create/teardown) and `checks/doctor.sh` (toolchain census that self-heals the hook wiring); plus `tools/setup-hooks.sh`. Each is **standalone** — a `source` of a file your repo lacks fails open, and a guard that fails open is not there — and each carries a `project config` header that is yours to edit after install. Two couriers join the corpus: `cc-ledger-subagent.sh` (`SubagentStop`) and `cc-ledger-session.sh` (`Stop`) hand a transcript path and whatever ids the event carries to `pm ledger record` through `make pm ARGS="…"` — they judge nothing, and every path out is exit 0; both ship a `--self-test` corpus, so wire a `hooks-self-test`-shaped target into your static gate and an edit to a guard cannot quietly change a verdict. The verb itself **prints** the `.claude/settings.json` entries that fire the corpus, the two couriers `"async": true` — printed, never written, since that file is yours to hand-merge |
| `install-gates` | **The gate FRAMEWORK, and what is not in it is the point.** `tools/dev/gdk_gate.sh` (one verdict line per gate naming `.gate-reports/<gate>.log`, `VERBOSE=1` streams; a bounded-run contract that tells a hang from a failure; `gdk_gate_capture` / `gdk_gate_verdict`, which every target routes through so nobody greps a gate's output for its result) plus **`Makefile.devkit`** at the repo root — `check`, `precommit` and `milestone`, which your own two-line `Makefile` `include`s ([Wiring it in](#wiring-it-into-your-project)). Neither half is usable alone: the define sources the library on every gate recipe, and the library publishes verdicts nothing would call without the targets. Through 0.1.0 this plan also carried twelve engine runners and named their targets in `precommit`/`milestone` — one language's roster inside the framework, which is what blocked splitting this package in two. **It now composes**: `precommit` and `milestone` take their language tiers from `GDK_PRECOMMIT_TIERS` / `GDK_MILESTONE_TIERS`, set by a `Makefile.tiers` a LANGUAGE kit installs and pulled in with `-include` (decision D1). A project that builds nothing gets a working `check`, `precommit` and `milestone` from this verb alone; a named tier that resolves to nothing is loud, and every declared tier is `.PHONY` so a tier shadowed by a same-named directory cannot be skipped in silence |
| `install-sdlc` | `docs/sdlc-protocol.md` — the one plan entry that is **RENDERED rather than copied**, from your own `[release]` / `[adopt]` step lists, so the document a human reads cannot drift from the list the conveyor walks. Re-run it after changing a step list |
| `pm install-skills` | `.claude/rules/pm-execution.md` (auto-loads on a `pm/roadmap/**` edit) + `.claude/skills/pm-operations/SKILL.md` (invoked deliberately). Under `pm` because what it writes is the PM tree's own guidance |

Every one takes `--force` and `--diff`. The table's rows are the `install-*` verbs this version routes, and `tests/test_install.py` asserts that — a row for a verb that left, or a verb with no row, fails the build. `install-runners` had both problems: it shipped the Godot runners, it left at 0.2.0, and it was documented here for a release afterwards.

### Static gates (`agentic-sdlc check <gate>`)

`check <gate> --help` prints that gate's contract, its `devkit.toml` section and its
honest scope — the module docstring itself, so the help cannot drift from the code.

Pure git + text parse; nothing is booted, built or imported. Run from anywhere inside the repo.
**Five gates, and the roster is the set that dispatches** — a name the tool advertises always
runs, asserted by a test rather than by two lists agreeing.

| Gate | Guards against |
|---|---|
| `check doc` | Dead claims in always-loaded agent docs (`CLAUDE.md`, `.claude/rules/`, `.claude/agents/`): dead links, dead `make` targets, dead file paths. Plus one placement fact — a flat `.claude/skills/<name>.md` instead of `<name>/SKILL.md` never loads at all |
| `check repo-hygiene` | Close-time git cruft: dirty tree, stashes, dangling worktrees, merged-but-undeleted branches. Runs `git fetch --prune` |
| `check shell` | `shellcheck -x` over every script under `tools/`, incl. extension-less hook entry points. Soft-skips if shellcheck isn't installed |
| `check pm` | PM-tree drift: a `done` feature whose `reviewed:` names no file, a feature whose stories are all done but never advanced, a `done` milestone with live children, a status outside the schema (milestones, features, stories **and bugs**), a `done` story under a live feature, a `building` milestone with everything closed. Also runs the `pm validate` integrity rules (V1–V5). Shares its predicates with the `pm` CLI, so the gate and the tool cannot disagree |
| `check hooks` | A hook corpus that is installed but not GUARDING. Four questions: `core.hooksPath` resolves to `tools/hooks`, every entry is a regular file at all (git's hook universe is every entry in the directory, so a directory or a broken symlink there is a name git tries and cannot start — REPORTED, never subtracted from the census), every entry carries an exec bit (git skips one that does not, in silence), and every hook still RUNS — a `cc-*.sh` fed a payload it cannot read must fail OPEN at exit 0, which executes the whole file including the project-config header you edited, and anything else in the directory must parse. Armed is not the same as working: a stale header under a newer body dies on an unbound variable under `set -u` and exits 1 where only 2 is a BLOCK, so the guard is on disk, executable, and stops nothing. `_*` (sourced libraries) and `*.local` (config drop-ins) are not hooks. Stock OFF — arming is a decision you make once, and `bash tools/setup-hooks.sh` is what makes it |
| `gates-extra` | **Not a gate** — prints `[gates] extra` from `devkit.toml`, one make target per line: the project's OWN gate targets, which `Makefile.devkit`'s `check` runs after the devkit ones. The include shells out to this once per run rather than parsing TOML in make, because a `sed` over section headers is a second TOML reader and a second answer. The value is interpolated into a make command line, so the grammar is narrow: whitespace, a path, a shell or make metacharacter, an over-long name or a non-list is exit 2 with a reason — never a silently dropped entry |
| `check all` | The offline fast set — **`doc` + `shell` by default**, the two that apply to any repo. **`[checks] all` names the roster for your repo**, and the other three are one entry away each: `repo-hygiene` is close-time and hits the network, `pm` would fail a repo for having no PM tree at all, and `hooks` would fail one that has not decided to arm a corpus. Each is stock-OFF for that reason and for no other — turn it on the day the reason stops holding. An unknown name is exit 2 naming the known set, never a quietly narrowed run |

### Project management (`agentic-sdlc pm <command>`)

Milestones → features → stories, as markdown with YAML frontmatter under `pm/roadmap/`. The CLI writes
ONE line and touches nothing else — no line endings, no adjacent fields, no file the caller did not name.

**Your words, three categories, and every question is asked of the category.** The engine's
whole opinion about states is that there are three categories — `todo`, `in_progress`, `done` —
in that order, and that every state you declare sits in exactly one. Which words, how many, and
in what order within a category is `[pm.states.<kind>]` in your `devkit.toml`: `pm init` writes
the seed — **each kind holds the states its belt writes**: a story `planning` `ready` | `building` |
`done` `obe`; a feature adds `reviewing`; a milestone walks all seven (`planning` `ready` |
`building` `reviewing` `accepted` `packaging` | `done` `obe`); a bug `open` | `fixed` | `closed` —
and every run reads what is there. There is no step-to-state table: a belt writes the FIRST state
of its kind's `done` list, and a leftover `[pm.transitions.<kind>]` is refused by name.
**Nothing here compares a status against a word.** "Is this feature's work finished" is
*are its stories all in `done`*; "has this story started under a feature that has not" is *the
story has left `todo` and the feature is still in it*; "which milestone's ledger" is *the one in
`in_progress`*. Rename every word and every answer is unchanged — `tests/fixtures/renamed-vocabulary/`
is that tree, and the gate is proven byte-identical over it. `done` does not mean SHIPPED and
cannot: the flip is itself a commit that has not shipped when it is written. It means everything
inside the tree's authority is finished — changelog written, reviews closed, findings landed, gates
green — and `obe` sits beside it because abandoned work is finished too (delivered-or-not is a
different axis). The state you ask for is validated against your declaration: `pm milestone
butterfly 0.1` is exit 2 naming `[pm.states.milestone]`. The state the file currently holds is never
validated — it is read for the message — so `pm milestone done 0.1` works from any state, including
a hand-edited `status: wombat`, which it prints as `wombat -> done` and repairs. There is no edge
graph and nothing checks an EDGE; a graph would only tax whoever used the sanctioned tool while a
`sed` of the same line reached the state it refused.

**The deprecation window is closed, and so are the flat lists.** `todo`, `wip`, `blocked` and
`review` — the words the seed replaced — rode in the stock set for one release so that no tree
turned red on the pin bump alone; 0.2.0 trims them, and a grain still holding one is a D4 finding
naming your declared words. Rewrite `todo` → `ready`, `wip` → `building`, `review` → `reviewing`,
and `blocked` → `building` (nothing replaces `blocked`: record what is blocking the work in the
grain itself) — or declare them in a category and keep them. `[pm] story_states` and its three
siblings, `[pm] also_done` (the `done` category enumerated by hand before the category existed)
and `[pm] review_slug_fallback` (a review record guessed from a filename) are retired and refused
by name. **The verbs report what they noticed and refuse nothing on process** — stories not in
`done`, features not in `done`, named in the output with the word each file holds. `check pm`
catches an undeclared state from any route, hand-edit included.

| Command | What it does |
|---|---|
| `pm init` · `pm new <milestone\|feature\|story\|bug> …` | Stand up a tree; scaffold a grain — its own frontmatter file and nothing else. **No directory and no shared doc is minted**: git stores no empty directory, and a shared doc appears on first WRITE. `new milestone`/`new feature` are idempotent — re-run to fill gaps. Every failure out is a refusal, never a stack trace |
| `pm story\|bug\|feature\|milestone <status> <id>` | Set a grain's status to any state in its `[pm.states.<kind>]`; anything else is exit 2 naming the declaration. A bug id is `<milestone>/bugs/<slug>`. Appends one timestamped row to the milestone's `ledger.jsonl` — after the write lands, never before, and even for a no-op flip |
| `pm feature <in-progress-state> <id>` | Move, and REPORT the stories not in `done` — on every move into `in_progress`, not on one word |
| `pm feature <done-state> <id> [--review-record <path>]` | Close the feature — any state in the `done` category is the close. **Touches no story file**; the stories not in `done` are named, and the story belt (`agentic-sdlc close story <id>`) closes each by name. A `--review-record` naming no file IS refused, whole — stamping a pointer to nothing is the drift D1 reports |
| `pm status [<milestone>]` | Tree report, drift-aware, grouped by the optional `phase:` bucket |
| `pm list [--status <s>[,<s>…]] [--category <c>] [--owner <n>] [--milestone <id>]` | One tab-separated `<story-id> <status> <owner> <feature-id>` per story, filtered; `--category` asks the category (`todo`/`in_progress`/`done`), whatever the word. Deliberately **no `pm next`**: a verb that picks THE next thing is the tool having an opinion about your priorities. Rows to stdout, census to stderr |
| `pm list --kind milestone [--status …] [--category <c>]` | One tab-separated `<id> <status> <category> <branch>` per milestone (`-` for no branch). What a script asks instead of grepping a status word out of `milestone.md` — `tools/dev/agent-worktree.sh` finds the integration branch this way, and answers the same under any vocabulary |
| `pm validate` | Frontmatter well-formed, ids match paths, parentage consistent, `depends_on`/`consumed_by` resolve, the feature graph acyclic. A ref into a milestone no longer in the tree is UNVERIFIABLE, never failed — git history is the archive |
| `pm get <id> <key>` · `pm set <id> <key> <value>` | Read/write one frontmatter field through code, not a regex — every other byte and the line endings preserved |
| `pm vocabulary [--json]` | **What this version publishes, and what your project declared.** The closed CATEGORY set (`todo`/`in_progress`/`done`), each kind's states with the category each sits in — and nothing else about flow — plus the rule ids `[pm] checks` may name. Its audience is the **pin bump**: it is how you find out what a new release added. A tree that has declared no flow gets the absence named plus the seed `init` would write, at exit 0 — a discovery verb that refused until you had already discovered the answer would be a closed loop |
| `pm sync [--check]` | Re-render the execution lists (feature order, story order) from `phase:` + `depends_on`. Opt-in per file; **V6** gates the same thing and is itself opt-in |
| `pm templates [--force]` | Copy the packaged templates into `[pm] template_dir` to edit. A file present there wins; anything missing falls back |
| `pm decide <id> <title…>` | Append one dated, ordinal-stamped heading to that grain's `decisions.md`, minting the log if it is the first. The reasoning under it is yours |
| `pm ledger record --from-transcript <path> --event SubagentStop\|Stop` · `pm ledger record --grain <id>` | Sum a Claude Code transcript (tokens, tool calls, timestamps, model) into one `dispatch`/`session` row, or file one by hand; appended to the building milestone's `ledger.jsonl` with the tree's live state at that instant. A field the transcript lacks is an absent key, never a zero |
| `pm ledger show <grain-id> [--json]` | That grain's ledger rows oldest first, with the seconds since the previous status row, and a total once the last row enters its vocabulary's terminal state |
| `pm ledger report [<milestone-id>] [--json] [--from <rev>]` | The milestone's raw rows, added up into its five questions, per story/feature/bug: spend, review yield, rework, escapes, overhead shape. Arithmetic only — sum, count, subtract, group — and never exits non-zero on a number. `--from <rev>` reads the same files out of git at that rev instead of the tree, for a milestone already retired; the rev is named, never inferred, and the milestone's own release tag is the usual anchor since the directory is still in the tree at its own release. |
| `pm retire <milestone-id> [<summary…>] [--dry-run]` | Remove a shipped milestone's directory and append its row to the ROADMAP.md table `pm init` already seeds. Reports an undone status or live features/bugs rather than refusing on their account; refuses only when the id or ROADMAP.md itself is missing. `--dry-run` decides and prints, writing nothing |
| `pm move <story-id> <feature-id>` | Re-parent a story to a different feature: renames its file under the target's `stories/` and rewrites `id`/`feature`/`milestone` together. Whole, or not at all — a decided obstruction refuses with nothing touched |
| `pm install-skills [--force] [--diff]` | The auto-loading rule + the operations skill (see [Installers](#installers-agentic-sdlc-install-what)) |

**The ledger, in three sentences.** Every status flip, cascade and `pm decide` heading appends one
timestamped row — the grain, the transition or the decision title, full UTC to the second — to that
milestone's `pm/roadmap/<id>/ledger.jsonl`. The status verbs and `pm decide` write it directly; the
two installed Claude Code hooks (`cc-ledger-subagent.sh`, `cc-ledger-session.sh`) write it by summing
a dispatch or session transcript through `pm ledger record`. It just timestamps transitions and
stamps whatever hook data — judgement and inference are left to the caller (Chris, 2026-09-03), which
is what `pm ledger report` is for.

## Configuration — `devkit.toml`

Optional, at the consuming repo root. Every tool works with stock defaults; a section overrides only
what it names, and a repo with NO `devkit.toml` behaves byte-identically to one declaring the
defaults. A key this package no longer honours is NAMED at exit 2, never silently ignored.

```toml
[checks]
all = ["doc", "shell", "pm"]   # which gates `check all` runs HERE.
                               # Default: doc, shell

[doc]
scope = ["CLAUDE.md", ".claude/rules/*.md", ".claude/agents/*.md"]
ephemeral = ["docs/reviews/"]

[gates]
extra = ["my-scan"]   # your OWN gate targets, which `Makefile.devkit`'s
                      # `check` runs after the devkit ones

[repo_hygiene]
mainline = "origin/main"
protected = "^(main|staging|archive/.*)$"

[shell]
roots = ["tools"]

[pm]
roadmap_dir  = "pm/roadmap"     # the tree, relative to the repo root
template_dir = "pm/templates"   # REQUIRED to override a grain template
review_dir   = "docs/reviews"   # where review records live
story_ordinal_prefix = false    # also resolve stories/NN-<slug>.md
checks = ["D1","D2","D3","D4","D5","D6",   # drift rules       — the stock default.
          "V1","V2","V3","V4","V5"]        # integrity rules    V6 and the FLOW rules
                                           # D8 (version == an in-progress milestone's
                                           # id), D9 (an in-progress milestone declares
                                           # `branch:`) and D10 (that branch: is not
                                           # empty or the [repo_hygiene] mainline)
                                           # are opt-in — name them here. Each reports
                                           # over EVERY milestone in `in_progress`.
version_file    = "project.godot"               # D8: where the version lives
version_pattern = '^config/version="(.*)"$'     # D8: the line that carries it

# THE FLOW — written by `pm init`, LIVE (no runtime fallback), and yours. Every
# state you use, each in exactly one of the three categories the engine knows.
# Order within a category is presentation; no rule keys on it. There is no
# step-to-state table: a belt writes the first state of its kind's `done` list.
[pm.states.milestone]
todo        = ["planning", "ready"]
in_progress = ["building", "reviewing", "accepted", "packaging"]
done        = ["done", "obe"]
# ...and per kind what its belt writes: a feature `building`/`reviewing`, a
# story `building` alone, a bug open / fixed / closed.
```

`agentic-sdlc pm vocabulary` prints the rule ids in full. `bugs/` and `stories/` are walked
recursively, extension compared case-insensitively; a `.md` in either slot with no leading `---` block
is a note parked beside the grains, not a grain with an empty status, and the census says how many it
skipped.

## Wiring it into your project

**A new project — one command.** From inside the repo:

```bash
uvx --from "git+https://github.com/cdowin/agentic-sdlc@v0.2.0" agentic-sdlc init
make help
```

**Your Makefile is two lines plus what is yours.** The pin is the one line that must differ per
project, so it lives in YOUR file and a bump is a one-line diff:

```make
DEVKIT_VERSION := v0.2.0
include Makefile.devkit

my-scan: ## a gate this project owns
	@bash tools/dev/checks/my_scan.sh
```

`Makefile.devkit` is devkit-owned and carries the framework set — `help` `pm` · `check`
`precommit` `milestone` — and nothing a language owns. Your build and test tiers arrive through
`Makefile.tiers`, a file your language kit (or you) writes beside it: it defines the targets and
declares which compositions they join with `GDK_PRECOMMIT_TIERS` / `GDK_MILESTONE_TIERS`. A
project with no tier file gets a working `check`, `precommit` and `milestone` that say they are
`check` alone. **Every gate prints ONE verdict line** naming its full transcript under
`.gate-reports/`; `VERBOSE=1` streams the whole thing. `make help` is the authoritative list and
shows your targets beside the standard ones.

**Your own gates join `check` by config, never by a fork of the include:**

```toml
[gates]
extra = ["my-scan"]
```

**Per-change vs close-time is the split that matters.** `make precommit` (`check` + your
`GDK_PRECOMMIT_TIERS`) belongs in your pre-commit or pre-push hook; `make milestone` (`check` +
your `GDK_MILESTONE_TIERS`) is the full gate and what the installed CI runs; `check repo-hygiene`
belongs at milestone close, because it hits the network and judges the state a close leaves behind.

## Northstar

> **A simple local Jira** — it creates the work, moves it, expresses what the states are and what
> the flow is, and it **infers nothing**.
>
> **Anything a project checks, scaffolds or tracks by hand should be one deterministic command that
> touches nothing else — and provable without reading the tree.**

Expressing the flow is the power. *Deciding what it means to move through the flow is a separate
problem*, and it belongs to whatever is running the flow — an agent with a dispatch, a reviewer, a
person who can be asked. So the engine has two verbs: **move a grain, if the target is a state
you declared**, and **ask which grains are in a category, and name the ones that are not.** Your
states, your flow; `init` writes them into `devkit.toml`, every run reads them, and nothing here
has an opinion about your words (hard rule 9).

For a **human**, the ritual stops being a thing to remember and the diffs stay reviewable. For an
**LLM**: a small stable vocabulary of verbs to compose instead of inventing a bespoke `sed`;
determinism, because a tool that rewrites what it was not asked to touch hides its damage inside a
legitimate diff; and token reduction, because `pm status` answers in a screenful what reading the
tree costs thousands of tokens to reconstruct. Each commitment below is a lesson from a real
incident, not a nice-to-have:

- **Refuse rather than mangle.** The worst outcome is never an error; it is silent partial success. A
  `--review-record` pointing at a file that is not there once stamped a feature `done` and reported
  success; it is refused whole now, and D1 is the gate that reports the drift.
- **Loud failure over a quiet one.** A gate that scans zero files FAILS and says so. A false PASS is
  the one outcome nobody can recover from, because it looks exactly like the truth.
- **Idempotence**, because models retry. **Bounded blast radius** — a verb changes nothing adjacent,
  down to the file's line endings.
- **Encode the footguns as gates,** so the knowledge lives in a gate instead of in a person or prompt.
- **Versioned, not vendored.** Consumers pin a tag in one Makefile variable and put project variation
  in `devkit.toml`, so there is no fork-drift to police.
- **Report, do not refuse — about your tree.** Closing a feature with open stories gets you a
  warning naming them, not a wall. A tool that refuses gets worked around invisibly, and then the
  protocol teaches nothing. A malformed *declaration* is still refused at exit 2: that is reading,
  not deciding.

**Scope boundary.** This is not a linter, a test runner or a build system, and it does not want to
be: it owns the **discipline around** the code — the work tree, the always-loaded agent docs, the
hook corpus, the installed target set — and shells out to your own tools for everything about the
code itself, through `[gates] extra`. It was extracted from `godot-devkit` at 0.2.0, where the
engine-specific half stayed; nothing here knows what a game engine is.

## Development

This repo is its own first consumer: its `Makefile` sets `DEVKIT` to `uv run -q agentic-sdlc`
— the working tree, installed on itself — and includes the same `Makefile.devkit` that
`install-gates` writes for everybody; `Makefile.tiers` adds the Python tiers the way a language
kit would. `make help` lists every target. Never hand-roll an incantation; if the check you need
is not a target, add the target.

```sh
make check       # agentic-sdlc check all, on this repo — ~2 s
make unit        # the inner loop: no subprocess, one process — ~7 s
make precommit   # check + unit — the per-change gate
make test        # both tiers on the 3.11 floor — what a feature close runs
make milestone   # check + matrix + budget — the full gate, and what CI runs
```

`make matrix` runs the whole suite on `PY_FLOOR` and the Python-only slice (`-m "not shell"`)
on every other claimed interpreter, each in its own `.venv-<version>`, and reports which one
failed; `make fuzz` runs the seeded differential + replay harnesses alone.

**Every target here is self-contained.** Nothing in this repo reads a path outside its own checkout,
names a project that consumes it, or asks whether some other repo happens to be cloned on the machine
running the gate — a verdict that depends on whose laptop ran it is not a verdict. Realistic data is
VENDORED: `tests/fixtures/` holds purpose-built repos, hook payloads and agent transcripts, and a
check that needs a construct the fixtures lack vendors one carrying it. Integration against any
particular project is that project's gate, run in that project's repo when it bumps its pin.

## Requirements

- Python 3.11+ (stdlib only) and git. `shellcheck` optional (enables `check shell`).

## License

MIT — see [LICENSE](LICENSE).
