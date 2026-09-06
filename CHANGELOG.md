# Changelog

## Unreleased

### The repo is a consumer of what it ships

- **This repo's Makefile is now a consumer's Makefile** — `DEVKIT := uv run -q agentic-sdlc`
  (the working tree installed on itself, editable, re-synced every call) and
  `include Makefile.devkit`, with the Python tiers in a `Makefile.tiers` on the same seam a
  language kit uses. `make precommit` here and in a consumer are one program. The `gates`,
  `hooks-self-test` and `hooks` targets are gone: `check` is the static gate, `check hooks`
  inside it replays the corpora, and `bash tools/setup-hooks.sh` arms a tree. Closes
  `0.2.0/bugs/the-repo-forks-the-framework-it-ships`.
- **`Makefile.devkit`: a project may set `DEVKIT` itself and skip the pin.** `DEVKIT_VERSION`
  is required only when the include has to build the `uvx` command. Re-install with
  `install-gates --force`.
- **`Makefile.devkit`: `gdk_gate` takes an optional fifth argument, the census** — a command
  run over the transcript that prints how many things the gate walked. It lands on the
  gate's ledger row (`--census`) and `check budget` holds it to `[tests] cases`. Four-argument
  calls are unchanged.
- **`check doc` and `verify --check` follow the tier seam.** Both readers stopped at
  `include Makefile.devkit` and skipped `-include $(GDK_TIERS_MK)`, so every tier target a
  language kit adds was reported as an unknown make target in every consumer's docs and
  rungs. One reader now (`core/makefile.py`), resolving a plain `$(VAR)` in an include path
  from the assignments already read. Widening only.

### The belts report, and the walk always finishes

**Behaviour change, and it is the largest one in this release.** `release`, `adopt`,
`close story` and `close feature` no longer stop at the first step whose postcondition
is not true. Every step is a check, every check reports, and the run reaches its last
step whatever any check said. Chris's ruling: *"Everything is just a check. `release`
should release on a red tree if I want (we mostly wouldn't but why stop someone?)"*

- **A release over a red `make gates` now reaches `tag`.** The engine cannot know whether
  a not-true step is wrong — descoped? a hotfix? deliberate? — and a machine that blocks
  on a question it cannot ask is asserting an answer. `agentic-sdlc check <gate>` is still
  the thing that FAILS a tree, in CI and pre-push, with an exit-code contract for exactly
  that. **`pm` moves and reports; `check` gates.**
- **`--skip <step> --reason "<why>"` is REMOVED.** It existed to escape a refusal, and
  nothing refuses. A script still passing it gets exit 2 naming the removal and the
  replacement, rather than "unknown option". **The ledger row it wrote is now written by
  the machine** — one `deviation` row per step that is not true, carrying the reason the
  step itself gave. `deviation.outcome` widens from the constant `"skipped"` to
  `"not-true"` / `"unverifiable"`; rows already carrying `"skipped"` stay readable.
- **Output shapes changed** (rule 6): the per-step verdict `STOPPED` is now `NOT-TRUE`,
  the `[op] STOPPED — …` summary is now `[op] step N/M 'name' (KIND) is not true; what
  would make it true: …`, and the final line is a scoreboard —
  `[release] 19/21 true · 1 not true: gate · 1 unverifiable: ci-green`. A fully-true run
  still prints `[release] PASS — N/N steps`. Exit codes are unchanged: 0 everything holds,
  1 one or more does not, 2 the declaration could not be read.
- **A step whose `check()` or `do()` raises no longer tracebacks.** It becomes an
  UNVERIFIABLE answer — not FALSE, because a step that crashed did not answer "no", it
  failed to answer — so an unexpected exception can no longer reach a consumer's CI as
  exit 1 with a stack trace. `ConfigError` is still re-raised: a malformed declaration is
  the reader failing, which is exit 2 before the walk.
- **`check hooks` prints a new clause** naming how many of the hooks that can BLOCK
  (a non-comment `exit 2`) replay a `--self-test` corpus. Zero was already loud; *how few*
  was not. Reporting only — refusing a consumer's corpus for being small would be this
  package deciding rather than reading.
- **The rendered protocol says so too.** `pr-open` and `ci-green`'s postcondition sentences in
  `docs/sdlc-protocol.md` read *"the operator is asked and the run refuses to advance"*; they now
  read *"the step is reported not true; the walk finishes"*, so the document `install-sdlc`
  writes no longer describes the halt this release removed.
- `pm ready-for feature`'s `--help` and `README.md`'s ladder row said *"every story at
  `reviewing`"*; the verb has asked whether every story is FINISHED since `f7465c2`.
  `pm feature reviewing`'s advisory asked a third question again — `not in (reviewing,
  'done')` — so a feature whose stories were all at `reviewing` flipped with no advisory
  and was then named by `ready-for`. All three ask `model.is_terminal` now.
- `pm ready-for tag` counted one review record twice when two features spelled its path
  differently. The census is what the verb prints as its proof of what it read.
- `README.md`'s installer table documented `install-runners`, which left at 0.2.0, and had
  no row for `install-gates` or `install-sdlc`. A test now asserts the table IS
  `install.PLANS`, both directions.
- `agentic-sdlc version` is documented. It was routed and named in no `--help` line.

### The suite is cheap, or it declares itself

**Measured before: 1842 tests, 240 s of wall clock, 150 s of CPU inside it — 62%. Spawn-bound,
not compute-bound.** `make precommit` ran every one of those tests after every edit. This package
exists to end a measured 170x — a wide gate run in an inner loop — and its own suite was the same
defect one layer down.

- **`repo_root` walks up for `.git` instead of running `git rev-parse --show-toplevel`.** Every
  config read came through it, so that was a process per config read — and because it is an
  `lru_cache` with no argument, the only way a test could point it at another tree was `chdir` +
  `cache_clear()`, which meant every fixture had to be a real `git init` repo. It answers the same
  question for a clone, a worktree, a submodule, a subdirectory and a tree outside a repo, and a
  better one on a machine with no `git` on `PATH`. **`git_lines` still spawns**: asking git what
  CHANGED is genuinely git's question; asking where the checkout starts is not.
- **New targets `make unit` and `make integration`**, and **`make precommit` is now the narrow
  rung** — gates, the hook self-tests, and the unit tier. 7 s in one process, against 240 s. The
  integration tier runs at the close; `make milestone` still runs everything on every interpreter.
  The `shell` mark that selects them is not new — it was derived for the matrix and had no target,
  so the fast half of the suite was unreachable from the command line.
- **New gate `check budget`** (`[tests] budget = { unit = 20, integration = 130 }`, seconds per
  tier). It reads the `duration_ms` on the `gate` rows the targets already file and fails a tier
  over its ceiling. **It ships with no ceiling and it is OFF the stock roster**: "twenty seconds"
  is a claim about a machine, and this package knows nothing about its consumers' machines
  (rule 8) — a stock number would redden every tree whose CI runner is slower than the laptop it
  was picked on. It runs in `make milestone`, never in `check all`, because a per-change gate that
  reddens over last night's timing is one somebody deletes. Every number it prints carries its own
  AGE, because a ceiling graded against last week's row is graded against last week's code.
- **`check budget` grades only what it measured** (feature review S1–S3). A tier whose newest
  `gate` row did not end `PASS` is `NOT GRADED` and a finding (exit 1) — a run that stopped is
  cheaper and smaller than one that finished, so it was the run most likely to read `ok`. The
  row graded is the newest BY TIMESTAMP, not the last in the file: the ledger is appended by
  concurrent writers and merged, and on this repo's own ledger the last `unit` line was a run
  from eight minutes before the newest one; a row whose `ts` will not parse fails the gate by
  line number rather than being ordered silently. The summary line names the tiers it measured
  and says which it did not (`PASS — within their time budget: unit; unmeasured: integration`)
  instead of counting every declared ceiling as within budget. **Output-format change** on the
  `[check:budget]` summary and FAIL lines.
- **New config key `[tests] floor = { unit = 1000 }`** — the case-count ceiling pointed the
  other way (feature review S4). `cases` only looked up, so a tier that had shrunk 35% under
  its declared baseline read `ok`; a census under its floor is `UNDER FLOOR` and a finding, the
  same shape as `OVER COUNT`. A floor above its tier's `cases` ceiling is a config error. With
  or without a floor, every counted tier's line now carries its census DELTA against the run
  before it (`734 of 1250 case(s), 389 fewer than the run before (1123)`), so a drop is visible
  with no second number to maintain. No stock value, for the reason `cases` has none. This
  repo's own `devkit.toml` does not yet declare a floor.
- **Hard rule 10**: *prove it the cheapest way that can actually fail.* The counterweight rule 4
  never had — and `test-writer`, `developer`, `reviewer`, `simplifier` and `verification-reviewer`
  now carry it, so a consumer's roster inherits the rule instead of re-learning it at 240 s a run.
- The test suite runs under `pytest-xdist`. It is a TEST-time dependency, exactly like pytest;
  hard rule 1 governs the runtime, and a consumer's pre-push hook resolves neither.

  240 s -> 189 s   the walk, and 14 fixtures that stopped building repos
  189 s ->  96 s   xdist
   96 s ->  62 s   two corpus constants in `gdk_gate.sh --self-test`
   62 s ->  39 s   `--dist loadgroup`, and the tests that share this repo saying so

### The project declares its flow

**New config, and it is the one section that ships LIVE rather than commented.** `[pm.states.<kind>]`
maps every state this project uses into one of three categories — `todo`, `in_progress`, `done` —
and `[pm.transitions.<kind>]` maps a conveyor step to the exact state it writes. `init` writes both;
the runtime reads them every run and **does not fall back**. Hard rule 5 now says why: a GATE ships
stock defaults and a repo with no `devkit.toml` runs every gate byte-identically to one declaring
them; a WORKFLOW does not, because a default nobody can see is the engine's opinion wearing the
project's clothes.

- **This release adds the section and changes no question the engine asks.** Every predicate still
  asks by name. Only the workflow verbs refuse a tree that has not declared a flow — `check doc`,
  `check shell` and `check repo-hygiene` are untouched — and the refusal names
  `agentic-sdlc pm init` rather than pasting the table for you to copy wrong.
- **The engine gets two verbs**, which the design has specified since it was written and nothing had
  built: `move(grain, to_state)` asks whether the target is a state this project declared, and
  `holds(grains, category)` answers whether they are all there **and names who is not**. A status the
  project never declared blocks rather than passes.
- **A state mapped to no category or to two, a transition to a state nobody declared, a category
  outside the closed set, or a partial declaration is exit 2** naming the key. Refusing a malformed
  declaration is the engine READING, which is the one thing it is always allowed to do.
- **The seed carries `obe` in `done`.** It is the one place the seed is not literally the old
  `LIFECYCLE`, and it is deliberate: without it a freshly-initialised tree has no word for abandoned
  work, and `[pm] also_done`'s live defect — a story at `obe` holding its feature open forever —
  comes straight back for every new consumer. A tree that never types `obe` is unaffected.
- **`pm vocabulary` is the pin-bump verb and it stopped saying there are no transitions to print.**
  It now prints the categories, your declared flow, and the conveyor step names a transitions table
  may key on — read from the registry, because that key set is the ENGINE's: a project selects from
  a published vocabulary and cannot invent a step, which is the same shape `[<operation>] steps`
  already works in. `--json` is additive; every existing key keeps its meaning.

### The story belt verifies the story rather than the moment

- **`close story`'s narrow rung used to pass over a census of zero.** `verify --story` reads the diff
  against HEAD, and by the time a story is closeable its work is committed — which is the ordering
  the belt itself requires, since `evidence-written` demands a `done:` line naming a real commit. So
  the step reported `ALREADY-TRUE — no changed paths` inside `PASS — 5/5 steps`. **Measured: a story
  closed `done` with its narrow check red and the check never run.**
  It now scans the story's own RANGE, taken from the base the author already wrote down — the
  hashes in the `done:` line — and answers **UNVERIFIABLE** when there is nothing to scan.
- **`verify --story` takes `--ignore <path>`**, so a caller can name the paths IT wrote during this
  run. `close story`'s first step moves a `status:` line inside `pm/roadmap/`, which arrived at the
  narrow rung as a changed path, matched no rule in a project that never declared one for its PM
  tree, and sent the story close to the **milestone** rung — a full gate inside the step advertised
  as four already-computed facts. It is not a claim that a PM tree needs no verification; that is
  the project's call, made by declaring a rule.

### The conveyor's steps stop reporting things they did not ask

- **`adopt`'s `config-updated` asked six readers and reported over a hand-written list of
  ten.** Four sections it NAMED — `[checks]`, `[grain_shape]`, `[repo_hygiene]`, `[verify]` —
  were never asked, so it printed *"6 reader(s) accept this repo's devkit.toml; declared
  here: verify"* over a `[verify]` table that made `verify --check` exit 2. The census is now
  derived from the reader list, all ten sections have a reader, and every refused section is
  reported rather than the first. **Output shape changed** (rule 6): the pass line reads
  `N reader(s) accept …` where N is the number asked, and the failure names how many of how
  many hold a value this version does not accept.
- **`[repo_hygiene] mainline` / `protected` were spelled in two places.** The gate read them
  inline at the top of `run()`, which then fetches and walks, so there was nothing pure for
  `config-updated` to call. `repo_hygiene.read_config()` is now the one reader, and a
  malformed value raises before the gate prints its first line rather than after.
- **`init` gitignores three more run-artifact paths**: `.agentic-sdlc/` (the conveyor's own
  run state, which falsified the `tree-clean` step it sits beside), `.agent-scope` and
  `.claude/worktrees/` (both planted by `agent-worktree.sh`, whose own comment says to
  gitignore the second). A tree initialised before this gets them on the next `init` — the
  verb appends what is missing and rewrites nothing.
- **`main-merged` fetches before it answers.** It read `origin/<mainline>` and never
  refreshed it, so on a clone two commits behind it answered *"origin/main is an ancestor of
  HEAD"* — TRUE, over a mainline that had moved. A remote-tracking ref is a cache of somebody
  else's repository. It now refuses (UNVERIFIABLE) rather than answering off a ref it could
  not refresh, which is `tag`'s existing ruling; a repo with no remote still answers from its
  local mainline. **This adds one network round trip to a `release` run.**
- **`tree-clean` names the ledger as the belt's own.** The `gate` step files its cost rows in
  the tracked `ledger.jsonl`, so the belt dirtied the tree it later measured and then told
  the operator to stash a file it had written itself. Nothing is subtracted from the count
  (rule 4); the attribution is what was missing.
- `adopt`'s `installable-decisions-recorded` accepted a decision line by path SUBSTRING, so
  `tools/hooks/pre-push-extra: keep` satisfied a drifted `tools/hooks/pre-push`.
- `[<operation>] steps` printed its duplicate-name notice once per asking step — five times on
  one run. Memoised on the config file's own bytes, so a changed file re-derives.

### `verify --check` asks whether a rule can ever fire

- **A rule shadowed by an earlier one is now a finding.** `--check` asked each rule's glob
  whether it matched anything; it now asks the SELECTOR whether the rule is ever FIRST for
  a path. A rule with matches but no first-match is dead config — it is named, together
  with the rule that claims one of its paths and the path itself. (Rules whose `run` lines
  substitute to the same command are *not* shadowing each other: `select` deduplicates by
  command, and a check that read that as drift would have filed four false findings against
  this repo's own twenty rules.)
- **The census counts the UNION of matched paths.** It summed per-rule matches, so six rules
  over one file in a three-file repo reported *"6 matched file(s) scanned of 3 tracked"* —
  a census reporting more files than the tree holds. **Output shape changed** (rule 6):
  `N rule(s), M of T tracked file(s) matched by a rule, K run(s) unvalidated`.
- **A `run` line that is not `make <target>` is counted rather than validated, and the
  ruling is printed.** Whether `uv run … pytest` is runnable is a fact about the machine,
  not about the checkout, and a gate whose verdict moves with `PATH` answers differently in
  CI than on a laptop. The silence is what went: `K run(s) unvalidated` plus a `NOTE` line.

### The extraction finishes

- **A stock consumer's `check all` exited 2.** `KNOWN_GATES` named thirteen gates and five
  dispatched; three of the eight phantoms (`uid`, `tres`, `props`) sat in the DEFAULT roster, so
  the path a new adopter takes was the broken one and the error message named the gate it had
  just refused as a known one. The roster is now `doc`, `shell`, `repo-hygiene`, `pm`, `hooks`,
  with `doc` + `shell` as the default. **A repo pinning a removed gate in `[checks] all` gets
  exit 2 naming it** — that is the intended adoption step, not drift.
- **`_check_module` is derived from the roster** rather than an `if` chain beside it, so the two
  cannot disagree, and `tests/test_gate_roster.py` asserts `roster == dispatchable` by asking the
  function instead of restating the answer. The test is the change; the pruning is the small half.
- **`--help` listed ~14 verbs this package does not route** — the scene family, which left with
  the Godot half. `_usage()` prints that text on any typo, so a mistyped command handed the reader
  a menu of nothing. `tests/test_cli_surface.py` parses the verb list back out of the docstring
  and asserts both directions.
- **`src/agentic_sdlc/data/classdb.json` is gone** — 129,490 bytes of Godot ClassDB with zero
  readers, inside the wheel root, downloaded on every cold `uvx` resolve. So are `RETARGET_FLAG`,
  two orphaned `.tscn` fixtures, and `tests/support.temp_repo()`.
- **`README.md`'s install pin said `@v0.24.0`** — `godot-devkit`'s tag, on a copy-pasteable line.
  It names this package's own tag now. The scene-introspection and scene-surgery tables, the
  uid-in-refs migration appendix and the ClassDB regeneration steps are gone with the code.
- `CLAUDE.md` hard rule 2 is the rule this package holds — pure text, boots nothing — and records
  that its own *"if that stops being true, it leaves"* clause fired in 0.2.0, in the other
  direction: the scene half left and the repo family kept the pinned-tag channel.
- `devkit.toml` drops `[uid]`, `[tres]` and `[props]`.

### The middle tier splits — what unblocks the other kit

- **`Makefile.devkit` is the gate FRAMEWORK and nothing else**, 314 lines down to 243, naming no
  language's target. `precommit` and `milestone` compose from `GDK_PRECOMMIT_TIERS` /
  `GDK_MILESTONE_TIERS`, set by a `Makefile.tiers` a LANGUAGE kit installs and pulled in with
  `-include $(GDK_TIERS_MK)`. **Breaking for a Godot consumer:** `parse lint warnings unit
  integration* scenario smoke capture import-cache scene scene-diff refs orphans autoloads
  uid-scan pm-scan hermetic-scan hooks-self-test runners-self-test doctor` are gone from this
  file and arrive from the Godot kit instead. Re-install and install that kit's tier file.
- **A project with no language kit is a supported shape**, not a degraded one: no
  `Makefile.tiers`, `precommit` is `check` alone — **and it says so**, one `[TIERS] …` line ahead
  of the gate, so a one-gate run can never read as a five-gate run.
- **A tier that resolves to no target stops the run at PARSE time**, naming both the tier and the
  variable that named it — including the case where `GDK_TIERS_MK` points at a file that is not
  there. `-include`'s silence serves the empty-list case and only that one.
- **`install-runners` is now `install-gates`** and writes two files: `tools/dev/gdk_gate.sh` and
  `Makefile.devkit`. `tools/dev/gdk_runners.sh` is `gdk_gate.sh`, the framework half only —
  `gdk_gate_log` / `gdk_gate_capture` / `gdk_gate_publish` / `gdk_gate_verdict` / `gdk_run_bounded`
  / `gdk_timeout_is_hang` / `gdk_on_exit` unchanged byte-for-byte; the sandbox HOME, the project-file
  restore, the compile-sweep readers and the import-cache rebuild left with the runners. A consumer
  that sources it renames the path.
- **`install-ci` writes three workflows**, not four. `uid-guard.yml` left with the gate it ran, and
  `verify.yml` no longer installs a game engine and two linters behind a `hashFiles()` guard — the
  toolchain seam ships empty and marked, for the project to fill after the write.
- **`install-hooks` no longer writes the engine-boot sandbox hook or `doctor.sh`.** `check hooks`
  is the surface that reports an unarmed corpus and names the repair.
- **`agentic-sdlc init` no longer refuses a repo with no engine project file.** Its one remaining
  refusal is "not a git repository", because every gate resolves its scope through `git ls-files`.
- **`[pm] version_file` defaults to `pyproject.toml`** and `version_pattern` to `^version = "(.*)"$`.
  A project on the old pair sets two keys; one that relied on the default and IS a game repo needs
  those two lines. Same for `install-ci`'s semver-gate and auto-tag workflows, which now carry
  `VERSION_FILE` / `VERSION_PATTERN` at the head of the file — **and fail the step when a version
  cannot be read**, naming the file and the pattern. Previously auto-tag could mint a tag named `v`.
- `make hooks-self-test` **was passing over an empty corpus**: `for h in $(EMPTY)` exits 0 and the
  summary reported `0 hook(s) SELF-TEST OK` as a PASS. It counts first now.
- `check doc` stripped one engine's resource scheme by name; it strips any `<scheme>://`.
- `[gates] extra` accepted a target name ending in a newline — `$` matches before one — so
  `["check\n"]` reached a make command line as two goals. `fullmatch` now.

### The vocabulary

- **The deprecation window is closed.** `todo`, `wip`, `blocked` and `review` are removed from the
  stock `milestone_states` / `feature_states` / `story_states`; a grain still holding one is a D4
  finding, `check pm` no longer prints the census NOTE, and the `pm` verbs refuse the word as
  plainly out-of-vocabulary instead of naming a replacement. **Rewrite before bumping the pin:**
  `todo` → `ready`, `wip` → `building`, `review` → `reviewing`, `blocked` → `building`.
  `pm ledger report`'s dwell columns narrow from ten states to six, and `pm vocabulary --json`
  drops the per-grain `deprecated` key.

### The belts

- **`pm ledger record --gate <name> --verdict <v> --duration-ms <n> [--census <n>]`** files what one
  gate run cost. A census not given is an absent key, never a zero — a zero is a measurement, and it
  reads forever after as the empty census rule 4 calls a cardinal sin. Milliseconds, because fourteen
  of twenty measured gates are under a second and an integer-second row cannot resolve the cheap half
  of its own headline comparison.
- `ledger.append_row` no longer joins a torn last line: a ledger whose previous writer died mid-line
  gets a newline in front of the new row instead of `{…}{…}` on one unparseable line.
- **`devkit.toml` gains `[verify]`** — forward (`paths` + `run`) and reverse (`declares` + `scan` +
  `run`) rules for the story rung, plus `feature` and `milestone` naming the make targets that ARE
  the wider rungs. A capture never spans `/`, a rule is forward XOR reverse, and a malformed rule
  set exits 2 naming every bad rule's own index rather than dropping it in silence.
- **`agentic-sdlc verify --story | --feature | --milestone`** — the ladder, one verb and one
  scope per operation. `--plan` prints all three rungs with their **measured** cost from the
  ledger's `gate` rows and the word `unknown` where none exists; it never estimates, because a
  fabricated ratio is worse than none — it gets quoted. `--check` fails a rule whose glob matches
  zero tracked files or whose `run` names a target that does not exist, each naming the rule's own
  index. **A changed path matching no rule is NAMED and the widest rung runs**: a narrow verifier
  that matches nothing and exits 0 reports success for work it never checked.
- **`agentic-sdlc pm ready-for feature|milestone|tag <id>`** — the belt entry conditions as exit
  codes (0 ready, 1 not, 2 usage/config). Exit 1 **names** every blocker — the stories not at
  `reviewing`, the features not `done` or without a record, the findings still `open` and the
  record each came from — and never prints a tally. A verdict block that does not parse is
  UNVERIFIABLE, never a pass.
- **`gdk_gate.sh` files one cost row per gate RUN**, through the pair `gdk_gate_log` (opens the
  slot) → the first `gdk_gate_verdict` naming it (closes it), so a runner with five alternative
  exits files one row and not five. Entirely OFF until `GDK_LEDGER_CMD` is set, and it **fails
  open**: an unset, missing, failing, chatty, hanging or unwritable recorder never changes a
  gate's exit code or its verdict line. `Makefile.devkit` exports the one line that bridges it,
  because a sourced shell library cannot see a make variable.
- **`pm ledger report` grows a `gate cost` section** — runs, first/last milliseconds, a signed
  delta, and the census beside it. A delta whose census moved or is absent is starred and counted
  in the heading, because the same gate is legitimately slower on a bigger tree.
- **`check grain-shape`** — the prose cap over grain documents, owned by the kit that defines the
  grain schema. One in-process pass, no subprocess per file. Caps are `[grain_shape] caps` with
  shipped defaults, merged over rather than replacing, so naming one kind never un-caps the other
  five. A repo with no PM tree, or with a tree holding no grain yet, is a **no-op that says so** —
  `check pm` is the gate with an opinion about a PM tree being there.
- `check hooks` now replays each installed hook's own `--self-test` corpus, and a corpus list that
  empties out **fails** rather than reporting `0 hook(s) OK` as a pass.
- **`agentic-sdlc release <version>` and `agentic-sdlc adopt`** — a resumable step machine over
  `[release] steps` / `[adopt] steps` that **refuses to advance** past a step whose postcondition
  is not true. Three kinds: `AUTOMATIC` (code does it, then re-asks — `do()` never decides its own
  outcome), `GATE` (a command, exit 0), and `JUDGEMENT` (code cannot perform it; it reads the
  artifact, or a `[release.commands]` command the project supplies, and with neither answers
  UNVERIFIABLE, which is a refusal). `pr-open`, `ci-green` and `prove-artifact` ship with **no**
  default command — stdlib only, forever, so this package will not reach for `gh` or a URL.
  Position lives in `.agentic-sdlc/run/<operation>.json`, gitignored, as a **cache of `check()`
  answers and never the authority**: a step the file calls done is re-checked, the tree wins any
  disagreement, and the correction is printed.
- **`--skip <step> --reason "…"` writes a `deviation` ledger row.** Deviation stays possible;
  invisible deviation does not.
- **`install-sdlc`** renders your release protocol from your own step list, so the protocol a
  human reads and the protocol that runs cannot drift. `agentic-sdlc init` composes it, after
  `install-agents`, because the agents cite it.
- `[doc] scope` and `[doc] ephemeral` were bound at IMPORT, so a malformed section stopped exiting
  2 once the module was loaded — findings, or none, where the contract says 2. Config is read per
  run now, and a boundary test holds every module in the package to it.
- **`agentic-sdlc adopt <milestone>` walks an eight-step list scoped to the ADOPTION**, on the
  same driver as `release`: `pin-bumped`, `installables-diffed`,
  `installable-decisions-recorded`, `config-updated`, `hooks-self-test`, `runner-targets-resolve`,
  `checks-pass`, `pm-validates`. **`checks-pass` runs this package's `check all` and never your
  `make check`** — your gates verify your code against your rules, and a version bump here cannot
  change their verdict. The whole adoption answers in ~3 s on this repo's tree. New config:
  `[adopt] steps`, `pin_file`, `runner_targets`, `[adopt.commands]`; a repo declaring none behaves
  byte-identically to one declaring the defaults.
- `check shell` reported `check [shell] roots` when a fresh `init` had simply not `git add`ed the
  scripts it just wrote. The census was honestly zero and the FAIL correct; only the cause was
  wrong, and it sent the operator to a config key that was right. It now names the untracked files.

- **This repo is the agentic half of `godot-devkit`, extracted at that project's `v0.24.0`.** SDLC, CI,
  hooks, the PM tree, installables and release automation; no Godot knowledge of any kind. The split was
  the code's own — there were ZERO imports between `godot-devkit`'s `repo/` and `godot/` halves in either
  direction, and its checks had already sorted themselves by side with nobody enforcing it. The shared
  substrate (~440 lines of config + tracked-file walking) is DUPLICATED rather than extracted to a third
  package or depended upon across the boundary; if both kits stay config-forward and that surface grows,
  the answer becomes a published shared config utility.
- **Version restarts at 0.1.0 and the PM tree starts empty.** The inherited `0.24.0` was another
  artifact's number, and `godot-devkit`'s roadmap is that project's story. Its history stays there.
