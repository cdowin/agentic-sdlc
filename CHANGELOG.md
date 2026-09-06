# Changelog

## Unreleased

### A belt is its checks, then one write or a clean error (D12)

- **Every belt — `close story`, `close feature`, `release`, `adopt` — is a check list followed
  by AT MOST ONE write.** Every check runs and prints one line; all true → the subject grain's
  status is set to the FIRST state of its kind's `done` category (`[pm.states.<kind>] done`,
  read from the config, never a literal), exit 0; any false → nothing written, exit 1.
  `--force` writes anyway. `adopt` writes nothing and refuses `--force`. **Nothing else is
  written, moved, bumped, retitled, pushed or tagged by a belt** — every `do()` is gone: the
  status flips of other grains (`claimed`, `milestone-reviewing/accepted/packaging`,
  `feature-reviewing`), `version-sync`'s bump, `readme-pins`' rewrite, `changelog-retitle`,
  `push-branch`, `tag`, and the `pr-open` / `ci-green` / `merge` / `prove-artifact`
  judgements. What a caller must still do is printed as `next:` lines after a successful
  write, and rendered into `docs/sdlc-protocol.md` under each belt.
- **New line shapes (minor bump at least, rule 6).** One per check —
  `[<op>] ok: <check> — <detail>`, `[<op>] error: <check>: <what is false>`,
  `[<op>] unverifiable: <check>: <why>` (D11; counts as false for the write) — then one of
  `[<op>] ok — <grain> → <state>`, `[<op>] error — N check(s) false; nothing written`,
  `[<op>] forced — <grain> → <state> over N false check(s)`, or for `adopt`
  `[adopt] ok — N check(s) true; nothing to write`; then `next: …` lines on success. The
  `ALREADY-TRUE` / `SAID` / `DONE` / `NOT-TRUE` / `CORRECTED` / `REFUSED` lines and the
  scoreboard are gone.
- **The check lists.** `close story`: `story-exists`, `narrow-verified` (`verify --story` over
  the story's own commit range), `committed` (nothing outside the roadmap directory
  uncommitted), `evidence-written` (a `done:` line). `close feature`: `stories-done`
  (`pm ready-for feature`), `review-recorded` (`reviewed:` points at a record that parses),
  `findings-landed` (none `open`); `feature-verified` (`verify --feature`) stays registered
  and is opt-in through `[feature] steps`. `release`: `tree-clean`, `on-milestone-branch`,
  `changelog-unreleased-nonempty`, `features-done` (`pm ready-for milestone`),
  `findings-resolved` (`pm ready-for tag`), `version-sync` (READS every configured site),
  `gate`. `adopt`: `pin-bumped`, `installables-current` (every installed file byte-current
  with what this version ships, each drifted one named with its `install-* --diff`),
  `config-updated`, `hooks-self-test`, `runner-targets-resolve`, `checks-pass`,
  `pm-validates`. Gone from the lists: `review-landed` (asked once, as `findings-resolved`),
  `main-merged`, `readme-pins`, `installables-diffed` and `installable-decisions-recorded`
  (both read a report the belt itself used to write).
- **Two ledger rows at most per run**: the `status` row `pm <kind> <state> <id>` mints, and
  on `--force` one `deviation` row with `outcome: forced`, `step` naming every false check
  and `reason` carrying each one's own sentence. A run that writes nothing writes no row —
  the per-step `not-true` / `unverifiable` rows are gone.
- **The run-state cache under `.agentic-sdlc/run/` is gone** — every run re-reads the tree —
  and with it `--status`. `--skip`, `--reason` and `--status` are refused by name.
- **`[release.commands]` accepts `gate` and the three after-belt commands** (`pr-open`,
  `ci-green`, `prove-artifact` — printed on their `next:` line, `{version}` filled in);
  `[adopt.commands]` / `[story.commands]` / `[feature.commands]` accept a command only for
  a check that runs something (`hooks-self-test`, `runner-targets-resolve`, `checks-pass`,
  `pm-validates`, `narrow-verified`, `feature-verified`). A command for a check that reads
  the tree is exit 2: two authorities over one fact. `[release] pin_files` is gone with
  `readme-pins`.
- **`docs/sdlc-protocol.md` renders from the four check lists, the state each belt writes
  and each belt's after-list**; a tree that has declared no flow renders the absence rather
  than exiting 2. Re-render with `install-sdlc --force`.
### Every surface describes the tool that ships

- **`README.md` is a consumer's ten-minute read**: what the tool is (a reader/writer over the
  PM tree — `pm` writes one status, `check` echoes findings, a belt is its checks then one write
  or a clean error), the ladder, the verb table (exactly what `--help` routes), the
  `devkit.toml` keys the tool actually reads, and the two-line Makefile. Every retired target,
  key and history paragraph is gone.
- **The `CLAUDE.md` seed (`init`) carries the same ladder** — `make check` → `verify --story`
  → `make precommit` → `close story` → `close feature` → `release` → `adopt` — and describes
  the belts as D12 does. The installed `pm-execution` rule and `pm-operations` skill say the
  same thing, so `pm install-skills --diff` will show it on a pin bump.
- **`tools/dev/agent-worktree.sh` ships `WARM_DIRS=()`** — the pre-warm list carried one
  language's cache directories as its stock value; it is now empty, and the header is where a
  project names its own. An empty list is handled under `set -u`.
- Installable comments and agent briefs name only this kit's own targets and verbs; the
  `review-recorded` check's description no longer cites a source path that does not exist in a
  consumer's tree. The stock `check all` roster is spelled out in `--help` as `doc` + `shell` +
  `grain-shape`, which is what `KNOWN_GATES` has run since `grain-shape` landed.

### The review findings land: `pm init` writes the flow it is named for

- **`pm init` appends `[pm.states.<kind>]` to a `devkit.toml` it did not write** — after the
  project's own bytes, in the file's own line endings (a CRLF config gets a CRLF block), idempotent
  (a tree that already declares its flow is not touched), and creating the file holding the flow
  alone when there is none. `agentic-sdlc init` takes the same path for a pre-existing config it
  leaves alone otherwise. F2/F3 of `docs/reviews/2026-09-05-the-project-declares-its-flow.md`:
  the refusal for a flowless tree named this command, and the command left the file untouched.

### An open bug against the milestone is named, and two of the three open bugs are fixed

- **`pm ready-for milestone <id>` names every bug whose `fix_milestone:` is `<id>` and whose
  status is not in the `done` category** — one `  BLOCKED  <bug-id> is <status> — a bug whose
  fix_milestone is <id>` line each, exit 1 (behaviour change: bugs used to be ignored). The whole
  active tree is read, because a bug is filed where it was caught and promised to the milestone
  that fixes it; a bug promised to another milestone is counted, not asked, and the census line
  says both numbers: `N feature(s), M bug(s) naming fix_milestone <id> of K read`.
- **`pm retire` retires a milestone in any `done`-category state — `obe` included — and the
  ROADMAP.md row says which**: the last cell opens with the state the file held (`done — shipped
  X`, `obe — collapsed into 0.3`, and `building — pulled` for a milestone retired unfinished),
  so the "What shipped" column never calls abandoned work delivered. Closes
  `0.2.0/bugs/a-collapsed-milestone-has-no-verb`. (Row-shape change, rule 6.)
- **The grain-slot names `stories` and `bugs` have one spelling**, `model.STORIES_DIR` /
  `model.BUGS_DIR`; `report.py`'s own three literals and `cli.py`'s six are gone, and a census
  test walks the pm tracker and the gates for a survivor. Closes
  `0.2.0/bugs/the-slot-names-are-spelled-in-six-places`.

### A parent behind its child is a warning, not a finding, and nothing moves it

- **D2, D3, D5 and D6 are `  WARN  ` lines now, never `  DRIFT  `, and never an exit code**
  (behaviour change, rule 6). A story at work under a feature still in `todo` (D5), a `todo`
  feature over finished stories (D2), a `todo` milestone over finished features (D6), a `done`
  milestone over an unfinished feature (D3): each line names both grains and both categories,
  the verdict line counts them apart (`[check:pm] PASS — …; 3 warning(s)`), and `check pm` exits
  0 on a tree whose only complaint is one of the four. Chris, 2026-09-05: *"If I do a check on a
  feature and it shows to-do and a story in progress, that's a warn. Not a fail, no action, just
  messaging."* D1, D4, D8/D9/D10 and V1–V6 are facts about the input and stay findings. The four
  still answer to `[pm] checks`. A CI that relied on D2/D3/D5/D6 to redden a tree reads the
  `warning(s)` count instead.
- **A status write prints what it wrote and nothing else.** `pm feature <state>` no longer names
  the stories not in `done` on a move into `in_progress`; `pm feature <done-state>` no longer
  prints `N story/ies not done and NOT touched`; `pm milestone <done-state>` no longer prints
  `N feature(s) not done`. Those facts are `check pm`'s WARN lines, asked of the tree.
- **`pm status` marks `<WARN: …>` for D2** (a feature behind its own finished stories) and keeps
  `<DRIFT: …>` for D1 (a dangling record) — the board says what the gate says.

### ready is one command, and an empty ready is a warning

- **`check pm` prints `  WARN  ` lines** (new line shape, rule 6) for a grain that has been
  readied — past its kind's FIRST `todo` state, under whatever words the project declared — and
  says nothing about what must be true: a story with an empty or absent `## Acceptance criteria`,
  a feature or a milestone with an empty or absent `## Ship criterion`, a feature with no stories,
  a milestone with no `branch:` or with a feature carrying no `phase:`. The three headings are the
  ones `pm new` scaffolds; a section holding only the template's `<!-- … -->` prompt is empty.
  **Warnings are counted separately and never move the exit code**: the verdict line gains
  `; N warning(s)` only when there are any, so a tree with none prints exactly what it did.
- **`pm <kind> ready <id>` is the only stamp.** Nothing readies a grain for you — Chris,
  2026-09-05: *"nothing fancy and automatic. If I want a feature to go in progress, I move it."*

### Each kind declares its own states, and there is no transitions table

- **The seed is per kind, and it is what the belts write.** `pm init` now writes a story
  `planning ready | building | done obe`, a feature that adds `reviewing`, a milestone with all
  seven, a bug `open | fixed | closed`. Under the all-seven seed this repo's own tree held
  thirty stories at `reviewing`, a state no belt writes and no gate reads. A tree that adopted
  the earlier seed keeps its declaration — `[pm.states.<kind>]` is the project's — and a grain
  holding a word its kind no longer declares is D4's finding, repaired by `pm <kind> <state>`.
- **`[pm.transitions.<kind>]` is gone and a leftover table is refused by name** (exit 2, naming
  each `[pm.transitions.<kind>]` present and saying to remove it). It was read by nothing: a
  belt writes the FIRST state of its kind's `done` list, and a hand move reaches any declared
  state. `model.transition_target` and the `[pm] <kind>_transitions` wording went with it.
- **`pm vocabulary` echoes each kind's states with their category and nothing else about flow**
  (output-format change, rule 6): the `[pm.transitions.<kind>]` block, the `published steps`
  list and the two flow notes are gone from the plain output; `--json` drops `published_steps`,
  `grains.<kind>.flow.transitions` and `notes.transitions`/`notes.feature_done`. Every other
  key keeps its meaning.
- **`pm ledger report`'s `reopens` column is deleted** (output-format change): it counted
  `reviewing -> building` by name, and with `reviewing` out of the story seed it could only
  ever print `-`. Section 3's per-story table is `feature story after_review`; the summary line
  reads `N story(s), M pass(es) with a verdict`; `--json` drops `rework.stories[].reopens` and
  `rework.totals.reopens`.
- **`pm ledger report`'s section 3 per-story table is deleted** (output-format change): the
  `after_review` column counted dispatches after a story's first move into `reviewing`, by
  name, and could only ever print `-` beside the `reopens` column that already left. A reader
  stops seeing the `story (N)` block with `feature story after_review`; the summary line reads
  `M pass(es) with a verdict`; `--json` drops `rework.stories` and `rework.totals.stories`. The
  verdict distribution and `rework.verdicts` / `rework.totals.passes` are unchanged.
- **`pm list --kind milestone [--status …] [--category <c>]`** prints one tab-separated
  `<id> <status> <category> <branch>` per milestone (`-` for no branch), census to stderr; and
  `pm list` takes `--category todo|in_progress|done` for stories. New flags; the story listing is
  unchanged.
- **`tools/dev/agent-worktree.sh` asks the CLI for the integration branch** —
  `make pm ARGS="list --kind milestone --category in_progress"`, through a new `PM_CMD` line in
  its project-config header — instead of grepping `status: building` out of `milestone.md`, a
  literal that stopped matching the day a project renamed the word. A CLI that cannot answer (no
  PM tree, no flow, no `make pm`) is said on stderr and the base falls back to `FALLBACK_BASE`;
  "answered" is the CLI's own census line, not the exit code, because `make pm` in a tree with no
  Makefile exits 0 saying nothing. Re-install with `install-hooks --force`.

### The belt's findings land (D11)

- **A callee's exit 2 is UNVERIFIABLE, never NOT-TRUE (D11).** A GATE or JUDGEMENT step that
  runs this package's own CLI (`narrow-verified`, `feature-verified`, `checks-pass`,
  `hooks-self-test`) and gets exit 2 back — a config or usage error in the callee — is now
  reported `UNVERIFIABLE … nothing was decided (D11)` and counted in that column; it used to be
  folded into `NOT-TRUE`, and a `close story` then stamped the story `done` over a narrow check
  that never ran. The walk still finishes. Configured `[<operation>.commands]` strings are
  unchanged: exit 0 is true and nothing else is, because `make` says 2 for a failed recipe.
- **A `ConfigError` met DURING a walk is one line at exit 2, never a traceback at exit 1.** A key
  only one step reads (`[release.version_files]`, at `version-sync`) used to escape `main` as a
  stack trace with exit 1 — hard rule 6's code for findings — and the steps already walked
  printed nothing. Now the transcript so far is printed, one
  `[release] REFUSED — step 6/21 'version-sync' (AUTOMATIC): …` names the step and the key, the
  run state is saved, and the CLI exits 2 with one line on stderr. Nothing after that step walks.
- **`{version}` in a configured command is substituted with the walk's subject** — the release
  or pin version, the grain id on a close belt — so
  `prove-artifact = "uvx --from git+…@v{version} pkg --version"` works as written. A
  `{placeholder}` this package cannot fill is refused at exit 2 naming the known set; the shell's
  own braces (`${HOME}`, `{}`, `awk '{print $1}'`) pass through untouched.
- **A step that is not true and gave no reason still writes its ledger row**, carrying
  `the step answered NOT-TRUE and gave no reason — a defect in the step, not a fact about the
  tree`; the row used to be silently skipped while the scoreboard counted the step.
- **`--status` says when the ledger row and the run cache disagree** — the row is written once
  (the machine's first account) and the cache on every walk, so a step that is true now still has
  its NOT-TRUE row; the two lines used to sit adjacent contradicting each other with nothing
  saying so.
- **Every shipped surface stops describing the machine D8 removed**: the rendered
  `docs/sdlc-protocol.md` (its intro said the walk *stops at the first step* sixteen lines above
  *no step halts the walk*), `install-sdlc`'s closing message, `SDLC.md`, the release skill (which
  still taught `--skip`, exit 2 since 0.2.0), the `close story` belt's own `SAID` line for
  `committed` (which printed `--skip --reason` as live advice), and the `findings-resolved` row,
  which told the operator to delete the review record `check pm` D1 needs to resolve. Re-render
  with `install-sdlc --force`.

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
- **`Makefile.devkit`: `precommit` and `milestone` open a gate slot of their own.** Both were
  prerequisite-only, so every member filed a cost row and the composition filed none, and
  `verify --plan` answered `unknown` for the wide rungs on every project following the shipped
  layout. Each composition now runs `check` and its declared tiers as the goals of one sub-make
  inside `gdk_gate_capture`, so the ledger gains a `gate` row named `precommit` / `milestone`
  timing the whole target, beside its members' rows. Nothing new on the console: the members'
  verdict lines stream through unchanged and the composition's own verdict goes to
  `.gate-reports/precommit.log` / `.gate-reports/milestone.log` (a new transcript each; a
  member's stderr now rides the composition's stdout, as any captured gate's does). `make -n
  precommit` still runs nothing; it prints the composition's one recipe, which names every
  member in order, rather than each member's recipe. Re-install with `install-gates --force`.
  Closes `0.2.0/bugs/a-composition-has-no-slot`.
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

### The ledger rows carry categories

**Data-format change, additive** (decision D7 — "keep and extend"). The dispatch snapshot a
`ledger record` writes — the `tree` on every dispatch and session row — now carries three
category keys beside the five it always had:

- **New keys: `milestones_in_progress`, `features_in_progress`, `stories_in_progress`** — every
  grain of that kind whose status is in your `in_progress` category, whatever the words.
  `pm ledger report` attributes a dispatch by these.
- **`milestones_building`, `features_building`, `features_review`, `stories_wip` and
  `stories_review` are DEPRECATED and removed at the next major.** They still match the seed's
  words by name and are still written, because they are inside rows already on disk in every
  consumer tree and rows are never rewritten. A renamed vocabulary records them empty beside full
  category keys, which is a true statement about what each key can spell.
- **An old-shape row is read as it was written, never through your current declaration** — that
  would be inventing history. A row that names a grain through the frozen keys is attributed as
  it always was. A row that names nothing is EITHER a dispatch over an idle tree OR one over a
  tree whose words the old shape could not spell, and the report says so rather than counting it
  as empty: a line under `rows naming no grain` — `N of these predate category keys and name no
  grain — unreadable under a renamed vocabulary, and not counted as empty` — and a `legacy`
  key in `--json` (`{"rows": N, "unattributed": M}`, zeros when there is no boundary).
- **The dwell columns of `pm ledger report` are per CATEGORY — `todo`, `in_progress`, `done` —
  for every grain kind**, so a twelve-state project gets three columns and not twelve. A stint
  in `building` and a stint in `reviewing` are one `in_progress` number; `done` has a column
  because a reopened grain spent a measurable stint finished. A stint in a word your declaration
  no longer names lands in no column and is disclosed by grain under the table (`unplaced_s` in
  `--json`). The old per-word columns are gone.

### Every question is asked of a category

**Behaviour change.** No question the engine asks about a status is asked of the word any more —
every predicate in the pm tracker, the gates and the ledger goes through `holds(grains, category)`
or `move_defect(kind, to_state)`, over the three categories your `[pm.states.<kind>]` maps your
words into. A project that renames every state gets identical answers, proven byte-for-byte on
`tests/fixtures/renamed-vocabulary/`; the inference census is enumerated in `tests/test_pm_flow.py`
and no state literal survives outside the seed `pm init` writes.

**What a consumer STOPS seeing** — the categories are coarser than the seven old positions:

- **D2 no longer reports a `building` feature whose stories are all done**, and **D6 no longer
  reports a `building` milestone whose features are all done.** Both fire only while the parent is
  still in `todo` (`planning`/`ready` in the seed). A parent in `in_progress` over finished children
  has started, and which in-progress word it should hold is not a question the gate asks. D5 lost
  nothing: it always compared across the one split, and that split IS the `todo` boundary.
- **D8, D9 and D10 report over EVERY milestone in `in_progress`** (`reviewing`, `accepted`,
  `packaging` included), not over the one at `building`. A tree with two in progress gets two
  answers; D8's "2 milestones are building — close one" is gone, because that was the engine
  deciding there can only be one. The messages say `in-progress milestone`.
- **`pm ledger record`, `pm ledger report`, `check budget` and `verify --plan` find the ledger by the
  one milestone in `in_progress`**; none or several is a refusal naming them, as before.
- **`pm feature done --cascade` is removed.** Which stories to move and to what was the engine's
  opinion about two words; the story belt (`agentic-sdlc close story <id>`) closes each by name, and
  the close reports the stories not in `done` with that hint. A move into ANY `done`-category state
  (`obe` too) is the close and stamps `--review-record`. The advisory "N story/ies not finished"
  now prints on every feature move into `in_progress`, not on `reviewing` alone.
- **`pm ready-for feature` and `pm ready-for milestone` ask the `done` category.** An `obe` story no
  longer holds its feature open (the `also_done` two-call-site disagreement, P9, is gone because
  there is one call site), and the exit-2 refusal for a vocabulary without the word `done` is gone
  because there is no word to lack.
- **`pm retire` reports a bug as still open when it is not in `done`** (`fixed` included), where it
  used to look for the literal `open`.
- **`[pm] milestone_states`, `feature_states`, `story_states`, `bug_states`, `also_done` and
  `review_slug_fallback` are retired** and refused by name by `check pm` and `pm validate` — the
  vocabulary is `[pm.states.<kind>]`, the `done` category is its `done` list, and a review record is
  the `reviewed:` pointer and nothing else. `pm vocabulary`'s flat per-kind list is now the declared
  order (category-major) and reads `(undeclared)` for a tree with no flow.
- **`pm status` and the execution list no longer know the phase word `seam`.** Numbered phases
  first, then named phases in your own spelling, then unphased; `seam` sorts where any name does,
  which is where it sorted before.
- `pm --help` opens with the category question; the conveyor's milestone status step reads the
  declared flow and reports an undeclared step word as UNVERIFIABLE instead of crashing (R4).

### The project declares its flow

**New config, and it is the one section that ships LIVE rather than commented.** `[pm.states.<kind>]`
maps every state this project uses into one of three categories — `todo`, `in_progress`, `done`.
`init` writes it, and `pm init` APPENDS it to a devkit.toml it did not write — every other byte
preserved, the file's own line endings kept, idempotent; the runtime reads it every run and **does
not fall back**. (An earlier draft of this note said `init` wrote a `[pm.transitions.<kind>]` table
too; nothing ever wrote one, and the key is refused by name now — see *Each kind declares its own
states*.) Hard rule 5 now says why: a GATE ships
stock defaults and a repo with no `devkit.toml` runs every gate byte-identically to one declaring
them; a WORKFLOW does not, because a default nobody can see is the engine's opinion wearing the
project's clothes.

- **Every question the engine asks is asked of the declaration** (`model.holds`, `model.category_of`,
  `model.move_defect` — the routing landed in `32b20b1`), and the workflow verbs and `check pm`
  refuse a tree that has not declared a flow — `check doc`, `check shell` and `check repo-hygiene`
  are untouched — with a refusal that names `agentic-sdlc pm init` rather than pasting the table for
  you to copy wrong. (The earlier draft said "changes no question" and "only the workflow verbs
  refuse" of a build in which nothing yet asked; F1/F4 of the flow's review.)
- **The engine gets two verbs**, which the design has specified since it was written and nothing had
  built: `move(grain, to_state)` asks whether the target is a state this project declared, and
  `holds(grains, category)` answers whether they are all there **and names who is not**. A status the
  project never declared blocks rather than passes.
- **A state mapped to no category or to two, a category outside the closed set, or a partial
  declaration is exit 2** naming the key. Refusing a malformed declaration is the engine READING,
  which is the one thing it is always allowed to do.
- **The seed carries `obe` in `done`.** It is the one place the seed is not literally the old
  `LIFECYCLE`, and it is deliberate: without it a freshly-initialised tree has no word for abandoned
  work, and `[pm] also_done`'s live defect — a story at `obe` holding its feature open forever —
  comes straight back for every new consumer. A tree that never types `obe` is unaffected.
- **`pm vocabulary` is the pin-bump verb.** It prints the categories and your declared flow — each
  kind's states with the category each sits in — beside the rule ids. `--json` is additive over the
  0.1.x payload; every existing key keeps its meaning.

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
