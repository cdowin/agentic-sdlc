# Changelog

## Unreleased

- **A BUG IS A GRAIN NESTED IN A PARENT — `fix_milestone:` and `caught_in:` retire (breaking).**
  `milestone:` is the parent binding and the only one, so the bug walk is the feature walk. Both
  retired fields are named where they survive, never silently ignored. **`ready-for milestone`
  filtered on `fix_milestone:`, a field `pm new bug` never wrote** — 18 of 24 bugs in this tree
  carried it empty — so the filter matched nothing and `release` could not have refused on an open
  bug for four releases, printing PASS over zero rows the whole time (rule 4's first cardinal sin).
  Its census now reads `N bug(s) nested in <id>` plus `N bug(s) attached to no milestone`, so
  zero-because-none-nested cannot be read as zero-because-none-matched. `pm new bug <milestone>
  <slug>` writes the binding and nothing else — it stamped its argument into `caught_in:` as well,
  one value in two fields with different meanings. `pm list --kind bug`'s second column is
  `caused_by`, and `pm rename` no longer sweeps the two retired keys.

- **`check pm` D11 — a parent in `done` does not hold a child that is not.** One walk off
  `BINDS_TO`, so milestone/feature, milestone/bug and feature/story are one question, and a FINDING
  rather than a warning. **D3 RETIRES INTO IT** and is named at exit 2 in a config that still lists
  it: D3 warned about a single pair and could not redden a gate, which is how seven bugs sat
  unresolved under two shipped milestones with nothing able to say so. There is no per-grain
  opt-out and there will not be one — `fix_milestone:` was exactly that field and defaulted to
  opted-out silently. **The opt-out is the binding**: `pm remove <parent> <child>` returns the
  child to its pool, where it gates nothing and is counted by V7's UNBOUND line. D11 also names a
  retired binding field found on any grain, by PRESENCE rather than value, because an empty
  `fix_milestone:` is the exact shape that gated nothing.

- **`pm add`'s DANGLING notice reads the parent's `order:`, not the child's binding.** Rebinding a
  child inferred order-membership from where it used to be bound, so the notice fired on parents
  whose `order:` had never held the id — and the `pm remove` it named then refused, because
  `remove` verifies membership against the binding the rebind had just changed. **The command the
  tool printed could not succeed at the moment it printed it.**

## v0.5.0 — 2026-09-07 — a move is an event

- **`agentic-sdlc lesson record|show` — a lesson is a ROW bound to a grain.** `lesson record
  --grain <id> --rule <id> --source <path> "<text>"` appends one append-only ledger row, routed to
  the milestone that owns the grain like every other row; `lesson show [--grain <id> | --rule
  <id>]` prints them tab-separated **in the order they were recorded**, columns named in `--help`.
  The row points at its source and never restates it, so a `--source` naming no file — or naming a
  path outside the checkout, which resolves on exactly one machine and cannot be edited back out of
  a committed append-only file — is refused and nothing lands. Nothing is inferred, scored or
  ranked (D1): the filters are `==`, ordering is by the recorded stamp, and an AST guard holds the
  writer and the reader to it. The belts surface them where you stand — against the grain at a
  move, against a check's name beside that check's verdict.

- **A NO-OP MOVE IS NOT AN ARRIVAL, so it can no longer shadow a recorded answer.** Every status
  verb minted a full arrival on the `(no-op)` branch too, so `pm feature building ft-x` run bare
  after `pm feature building ft-x --by agent reviewer` appended `answer: none` for the SAME state
  — and every reader takes the LAST disposition per (grain, state), so `check pm` U5 then named a
  grain that HAD been dispositioned and the pressure line agreed with it. It also hid a
  `close --skip`'s `skipped` field the same way. Now: **nothing transitioned, so no `status` row**,
  and a bare re-run does not replace an ANSWERED state's disposition with `none`. Re-running WITH
  an answer still records it — that is how a fork somebody skipped gets answered — and a bare move
  that IS a transition still writes both rows and records `none`.

  Two readings move with it. `report.arrivals` now folds consecutive arrivals at the SAME state
  rather than at the same stamp, so a `from == to` row already in a ledger — this repo has eight —
  no longer opens a second stint: the time before it stays part of the OPEN charge instead of
  being billed as a closed one. **No migration is needed; the reader tolerates them.** And one
  arrival's two rows are stamped ONCE, so a pair straddling a second boundary cannot read as two
  events.

- **The pressure line now reaches all three surfaces its criterion names.** A belt's write no
  longer flattens the arrival's whole report into one line — measured at 555 characters on a
  `close feature --force`, which is exactly where the fork's two pasteable commands stop being
  commands — and `check pm` prints the census it already computed as a counted `OPEN` line, from
  the same `arrive.census` U5 gates on, so the gate and a `pm` write cannot disagree.
  `[pm] pressure = false` silences all three.

- **`pm ledger report [<grain-id>]` takes the level you name.** A feature or story id was exit 2
  (*"the ledger is per milestone"*), which is true of where the ROWS are and says nothing about
  which level a reader asked for. A milestone id still reports everything; a feature or story id
  reports the `time per state` and `time per actor` blocks rooted at that grain, with its
  descendants under it and the actors narrowed to match. The ledger read is still the milestone's.
  `--help` now names both blocks' columns in order, which is what `awk` needs.

- **A dropped ARRIVAL row is disclosed whichever kind carries it.** `pm ledger report`'s discard
  census counted `status` rows only, so a `disposition` row naming a grain the milestone does not
  hold vanished with no line saying so — in precisely the disposition-only configuration the clock
  claims to be complete in. The line now reads `N arrival row(s) name a grain this milestone does
  not hold`.

- **TIME IS MEASURED PER STATE, AND IT ROLLS UP AT ANY LEVEL**
  (`ft-time-is-measured-per-state-and-rolls-up`). `pm ledger report` summed seconds per CATEGORY,
  and `building` and `reviewing` are both `in_progress` — so the tool collapsed exactly the
  distinction anyone asks about. Section 1 grows two blocks, and the category columns stay,
  DERIVED from the state totals rather than being the only number:

      -- time per state (5)
      grain             building_s  reviewing_s  fixed_s  closed_s  open_s  open_state
      0.1                      600          120       30       750    2400  building
        0.1/alpha              600          120        -       720    2400  building
          0.1/alpha/s0         600          120        -       720       -  -
        0.1/bugs/crash           -            -       30        30       -  -

      -- time per actor (2)
      actor                 arrivals  grains  seconds
      --by agent developer         2       2      930

  **Roll-up is the feature, not a view**: membership is already a field (0.4.0), so a milestone's
  `building_s` is a WALK of its features' and theirs of their stories' — every level the one below
  plus its own. **OPEN time is a CHARGE**: a grain still in a state at read time has its elapsed
  time in `open_s` beside the state accruing it, never folded into a closed total, and **no grain
  gets completed-time credit until it closes** — a running clock and a finished one are different
  facts. A parent's charge is the sum of its open children's plus its own, so the pressure line
  has one number to name. **A state a grain never held is an absent key and no column**, never a
  zero. `--json` carries the same under `clock`, keyed by state name.

  **It reads ARRIVAL rows, so it needs no harness hook** (0.5.0/D3/D6): the `status` row a move has
  always written names the state in `to`, the `disposition` row the same move mints names it in
  `state`, and one move at one stamp is folded to one arrival. A tree where no hook has ever fired
  — this repo's own condition — reports time per state and spend per actor in full.

  **The columns are the filter** (rule 11's read side): *"total review time for this milestone"* is
  `pm ledger report <id> | awk`, never a new flag.

- **NEW `check pm` U5: a grain whose CURRENT state was arrived at with no disposition, BY NAME.**
  A WARN in the USAGE family, never a refusal — a bare `pm feature building ft-x` still writes the
  status and records `answer: none` (D3), because refusing would make the conveyor something
  people route around. The rule names the grains rather than counting them, keys on the last
  disposition for the state the grain is in NOW (a grain that bounced back has arrived again), and
  uses `arrive.census` as its guard so the gate and the move's own pressure line cannot disagree.
  Opt-in like U2/U3/U4; `pm vocabulary` lists it.

- **A MOVE IS AN EVENT, and the event is ARRIVAL** (`ft-every-edge-carries-a-disposition`,
  `ft-the-conveyor-pushes-back`, `ft-a-move-names-the-capability-you-are-standing-in`,
  `ft-a-move-emits-the-breadcrumb-it-prints`; 0.5.0/D3). Every `pm <kind> <status> <id>` write is
  one arrival, and an arrival does four things — all of them derived, none of them a refusal, and
  all of them on **STDERR**, so the stream a consumer parses is byte-identical to 0.4.0's.

      $ agentic-sdlc pm feature reviewing 0.1/alpha
      [pm] feature 0.1/alpha: building -> reviewing
      [pm] next: `agentic-sdlc close feature <feature-id>` asks stories-done, feature-verified, …
      [pm]
      [pm] what happens to it?
      [pm]   a) agentic-sdlc pm feature reviewing 0.1/alpha --review agent <type>
      [pm]   b) agentic-sdlc pm feature reviewing 0.1/alpha --skip review "<why>"
      [pm]
      [pm] open: 3 in_progress, over the declared [pm] wip of 1, oldest 0.1/alpha 6h 6m — 2 of 3 carry no disposition

  **The new declaration is `[pm.arrive.<kind>.<state>]`** — a WORKFLOW key with nothing behind it,
  like `[pm.states.*]` itself:

      [pm.arrive.feature.building]
      ask     = "what is building this?"
      answers = ["--by me", "--by agent <type>"]
      have    = { "tools/dev/agent-worktree.sh" = "isolation for parallel work on this grain" }

  `ask` and `answers` are declared together or not at all — a question with no answers typed is
  advice, and rule 9 forbids the tool having one. Every answer opens with `--` and **is a flag the
  move accepts**, so answering costs one paste; a state with no node prints no question. A bare
  move still writes and mints `disposition: none`, and that grain then shows on the census until
  somebody answers. `have` is a CENSUS of installed files — a declared file that is **absent** is a
  named line, never silence (rule 11).

  **There is no transition table and there never will be one.** The unit is the state ARRIVED AT,
  never the pair `(from, to)`: `building -> planning` is an arrival at `planning`, a second pass
  through a state asks the same question, and backwards was never a special case. The
  `{ts, kind: "disposition", grain, state, answer, value?, skipped}` row carries no `from` for
  that reason, and time in a state is the gap between two arrivals on one grain — telemetry with no
  harness hook involved at all.

  **`pm ledger show` renders that row.** Its columns, in order, are `ts  kind  <what the kind
  says>`: a `status` row says `<from> -> <to>  +<n>s`, a `disposition` says `<state>  <answer>
  [<value>]` and then `skipped: <check> — "<why>"` for every check a belt answered instead of
  asking. The row was on disk from the first arrival and the renderer printed its kind and stopped
  (rule 11's read side).

  Two new `[pm]` knobs, both stock-ON and both in `pm config --seed`: **`pressure`** silences the
  fork, the READY crossing and the census in one line (rule 6), and **`wip`** is the project's own
  work-in-progress limit — `0` declares none, exceeding it is a REPORTED clause and never a
  refusal. `breadcrumbs = false` now silences `have:` beside `next:`; the emitted row carries both
  either way, because it is not on the stream a strict consumer parses.

  Every status move also emits **`rung.leave`** — `{ts, kind, grain, state, answer, rung,
  next_checks, next_actions, have}` — from the SAME `derive_next` the printed breadcrumb renders,
  so a change reaching one renderer and not the other fails a test.

- **A check has THREE answers, and `--skip <check> "<why>"` is the third**
  (`ft-the-close-is-cheap-and-a-check-is-dispositionable`, 0.5.0/D5, which revises 0.2.0/D12).
  `close story`, `close feature` and `release` accept it: the caller ANSWERED that check, so the
  check is **not asked**, the line reads `skipped: <check> — "<why>"`, the status is written, and
  the close is a clean one. **The judgement is a FIELD on the arrival's own `disposition` row**
  (0.5.0/D6) — `skipped: [{check, why}, …]` — because a close is an arrival and this is how that
  arrival's question was answered: one event, one row. Repeatable. A refused close leaves no
  `skipped` behind it, because the row is minted by the write and not during the check run.

      $ agentic-sdlc close feature ft-x --skip review-recorded "one-line fix, read inline"
      [feature] ok: stories-done — [pm] READY — feature ft-x: 1 story/ies, all done
      [feature] ok: feature-verified — `make test` exited 0
      [feature] skipped: review-recorded — "one-line fix, read inline"
      [feature] ok — ft-x → done

  **Which checks are skippable is a DECLARATION** — `[story] / [feature] / [release] skippable =
  ["review-recorded"]` — and **stock declares none**, so a repo with no `devkit.toml` runs exactly
  the belt it ran before. A skip of a check the project did not declare is refused BY NAME at exit
  2, and so is a `skippable` entry naming a check that belt does not run. **A skip with no reason
  is refused**, because an unexplained skip IS a deviation and `--force` is already its verb.
  `--force` is unchanged: it writes anyway, names the false checks, and mints its `deviation` row;
  the two row kinds are siblings and do not bleed. `adopt` takes neither flag — it writes nothing,
  so a skip there would have nowhere to be recorded — and its `--help` names both as refused.

- **`agentic-sdlc pm ready-for story <story-id>`** — the inner loop's entry edge, and the fourth
  rung the verb answers for (`ft-a-rung-has-an-entry-edge`). Exit 0 ready, exit 1 not ready naming
  every blocker, exit 2 usage; writes nothing, like the three rungs beside it. **The condition is
  DERIVED at every call, never a list this package holds**: `[story] steps` (your list, narrowed if
  you narrowed it) × `registry_for("story")` for the check objects × the registry's own
  `ENTRY_CONDITIONS` for which of them is decidable before the work. A project that declares
  different steps is answered about ITS list, and a project whose whole list answers only after the
  work is told `nothing was asked` at exit 1 — a READY over a census of zero is not a pass.

  Every check the belt WILL ask and this rung did not is named in the census with why, so silence
  never teaches a reader the belt is smaller than it is. On stock defaults:

      [pm] READY — story st-…: 1 of 4 [story] check(s) decidable before the work
      (story-exists), all true; 3 the registry does not declare an entry condition,
      asked at the close: story-verified (by `agentic-sdlc verify --story`), committed,
      evidence-written

  **There is no `ready-for adopt`, and asking for one is refused BY NAME** rather than as an unknown
  kind. Every check in the adopt belt is either the work the bump does (`pin-bumped`,
  `installables-current`, `config-updated`) or one that runs a command, which this verb never does —
  so the derived entry set is empty and the rung could only ever answer NOT READY. The refusal says
  that and points at `agentic-sdlc adopt <version>`, which runs the checks and writes nothing.

- **Every `ready-for` rung emits a `rung.enter` event** — `{ts, kind, grain, rung, ready, blockers}`
  — to the sink `[emit]` declares. **A tree with no `[emit]` section emits nothing**, which is how
  the verb keeps its writes-nothing contract. The blocker list is the payload's work queue, whole
  and not capped at what the terminal printed, and each blocker's `check` name is read from the
  belt registry rather than chosen. **Emission is never load-bearing**: a malformed `kinds`, a sink
  of the wrong type, a sink outside the checkout and a sink that cannot be written are each one
  `[emit] WARNING` line on stderr, and none of them moves an exit code or a printed byte.

- **`tree-clean` reads what `committed` reads: no modified path OUTSIDE the roadmap directory**
  (`ft-a-lesson-surfaces-where-you-stand`). `tree-clean` is `release`'s first check and it counted
  every modified path, while `committed` on the story belt already excluded the roadmap directory
  — so the same tree could satisfy one belt and never the other, and the belt DIRTIES that
  directory by design: it writes the milestone's status there, `gate` files its cost rows in the
  milestone ledger, every `[emit]` tap files an event, and the lesson reader surfaces one before
  check number one runs. That last one made the refusal permanent — commit the row, run again,
  another row lands, exit 1 forever — so **a recorded lesson could stop a release for good.** Both
  checks now come from one reading. Two output shapes moved with it: both name the directory they
  skip (`... path(s) outside pm/roadmap/: ...`), and neither counts what is inside it any more,
  because a count that moves with the belt's own writes cannot be a stable line.

- **`install-hooks` emits ABSOLUTE script paths, names the settings file, and offers to write
  it** (`ft-wiring-is-one-act-and-it-is-portable`, issue #13). The block carried
  `bash tools/hooks/<hook>.sh`, which resolves only when the harness's cwd IS the repo root, and
  the run named no destination at all — a fragment pasted by hand, wrong invisibly, with every
  surface reporting success. This milestone's own build recorded **zero ledger rows across nine
  dispatches** because of it. The commands are now absolute, so the same block works in whatever
  settings file the harness actually reads, and the run names `<repo>/.claude/settings.json` as
  the destination. **New flag: `install-hooks --write-settings`** writes that file when nothing
  is in the way, and is a no-op on the second run. A settings file that already exists is
  refused by path and left byte for byte — `--force` included — because it carries permissions,
  env and MCP entries this package knows nothing about.

  The emitted command is SHELL-QUOTED, because a path with a space in it (`~/my repo`,
  `~/Google Drive/…`) produced a block the harness could not run while the write reported
  success — the relative form had no space to break on, so absolutising the path introduced the
  class. The write reports what it did and not what it cannot observe: *"in force for a session
  rooted here"*, with the concrete `export GDK_LEDGER_ROOT=<root>` on the same line, because
  whether a harness LOADS a settings file is not something this package can see. An ABSOLUTE path
  names one machine, so the run also names `.claude/settings.local.json` — the per-user override a
  harness writes for itself and a repo gitignores — as the home for the block in a shared
  checkout; every surface that reads the wiring reads that file too.

  **`agentic-sdlc init` reaches the same step.** It composed the five install verbs with the
  next-step reporting off, so the brand-new consumer this verb exists for got no destination, no
  block and no flag — strictly less than the hand-paste it replaced. Its Next list has an eighth
  entry naming the file and the flag, and the pasteable block is last on stdout.

- **The ledger couriers take their tree from `GDK_LEDGER_ROOT`.** Both couriers derived the repo
  from the stop event's `cwd`, so a session rooted at a parent directory that is not itself a git
  repository filed no row — correctly by the courier's own contract, and unfixable from outside
  it. `GDK_LEDGER_ROOT` in the courier's environment names the tree; unset is normal and the
  payload's `cwd` is still the fallback, so existing wiring behaves exactly as it did. A value
  naming no git tree is a note on stderr and exit 0, never a crash and never a guess at another
  tree. Each courier's `--self-test` corpus — what `agentic-sdlc check hooks` replays — gained
  three rows for it: the session cwd deriving the WRONG tree, the override filing the row from
  that other scope, and an unresolvable override noting rather than falling back.

- **`pm new <kind> <slug>` mints `<kind-prefix>-<slug>` and nothing else**
  (`bg-the-new-verbs-mint-a-compound-id`, issue #8). It minted `<mid>/<slug>` for a feature and
  `<mid>/bugs/<slug>` for a bug while `tools/dev/pm_migrate.py` minted `<prefix>-<slug>` off
  `model.KIND_PREFIX` — so a migrated tree grew BOTH vocabularies, one grain at a time, and
  `check pm` passed either way. There is one minting path now, `model.mint_id`, and the migration
  calls it too. The id also restated the binding `milestone:`/`feature:` already carried, which
  made re-parenting a `pm rename` plus a whole-tree ref sweep — the cost 0.4.0 deleted when it
  retired `pm move`; it is one `pm set` again, and an id is stable for life.

  **The parent argument is unchanged and still positional** — it writes the child's binding field,
  the same fact `pm add` writes — it simply is not in the id. **Nothing grades an id's shape**: a
  prefix or a version in an id is the project's own taste (rule 9), and no check was added.

  A grain authored on 0.4.0 is still found by its compound id, so `pm new feature <mid> <slug>` on
  a tree written before the bump keeps FILLING that document instead of minting a second one
  beside it (rule 3). New grains land at `<pool>/<id>.md`, the name the migration writes.

  `<name...>` is **marked required** in the `--help` synopsis for `new milestone|feature|story`,
  and omitting it now refuses by naming the omitted ARGUMENT — the old
  *"feature 'x' does not exist yet — a new one needs a name"* read as *this grain is missing from
  your tree*.

- **`pm bug <status> <bug-id>` resolves by `kind:`, not by `/bugs/` in the id.** The verb required
  that literal in the id, so **no bug on a migrated tree could be moved by it at all** — and
  `pm new bug` now mints exactly those flat `bg-` ids. The guard was a path test standing in for a
  kind test; `grain_file(..., 'bug')` is the kind test, and a feature id is still refused.

- **`pm retire <id> [<summary...>]` records what it deletes** (`bg-retire-drops-the-summary-it-
  accepts`, issue #5). The summary was joined, interpolated into a sentence and **printed**; on the
  branch actually taken it was not even in the sentence. Only the id survived a retire —
  `version:`, `name:` and the summary went with the document, and a consumer's shipped-release
  table was therefore not derivable from the tree, which is the half of a hand-maintained
  `ROADMAP.md` that was real.

  Retire now appends one **`retire` row** to the tree's own `<roadmap>/ledger.jsonl` — the file it
  explicitly does not touch, and which already carries rows naming no grain — holding `grain`,
  `version`, `name` and `summary`. An empty field is an absent key. The summary's whitespace is
  collapsed at the write so it cannot forge a column downstream. The row is appended AFTER the
  removal lands; a ledger that cannot be written is a refusal carrying the whole row by value.

- **`pm roadmap` prints a shipped release fully.** Columns IN ORDER are now
  `version  milestone  state  name  summary`, `-` for an empty cell, and a plan entry whose
  milestone has been retired prints `retired` with the version, name and summary from its
  `retire` row. An entry that names no grain and has no row is still `DANGLING` — which is the
  distinction R1 could previously only report as UNVERIFIABLE.

- **`check pm` reads each document ONCE, and walks each pool once per run**
  (`bg-check-pm-reopens-every-file-per-field`, issue #6). `field_of` opened and re-split the whole
  file for every field, so a resolver answering one grain's question by walking every grain made the
  gate n²: a consumer's ~700-document tree made **2.1M `open()` calls** and took `make check` from
  8.4 s to **87 s**, past its own 20 s `check budget` ceiling. A document is now parsed once into a
  frontmatter dict that every reader answers off, and `check pm` — a gate, which reads and prints and
  writes nothing — asks for the pool walk once for the length of its run. Measured here: a
  711-document tree **33.3 s -> 0.26 s**, this repo's own tree **10.6 s -> 0.12 s**, with the gate's
  verdict, census and every finding line **byte-identical** (rule 6).
  Both caches are per process and neither touches disk. Rule 4 governs the invalidation and it is
  what the new cases pin: every parse re-`stat`s its file and re-reads when the stamp moved, so a
  document rewritten by a verb, a test or an editor is never answered from bytes that have moved on;
  a git blob read by `pm report --rev` has no `stat` and so is never cached; and the walk snapshot is
  dropped the instant anything in the process mutates a file, which `core.apply` now counts because
  it is the only place this package moves a byte.

- **`verify` remembers its last green, and what it was green ON.** `[verify] feature = "make test"`
  is tree-wide by design, so a tree has one state at a time and closing seven features ran one 90 s
  suite seven times — nine of the ten and a half minutes were repetition of a question whose input
  had not changed. Each rung now records a `verify` row in the tree's ledger, beside the `gate` cost
  rows `verify --plan` already reads: which rung, which make target, the verdict, the target's own
  exit code, what it cost, the census the gate itself filed, and the **tree state** it ran on — git
  HEAD plus a SHA-256 over every path `git ls-files --cached --others --exclude-standard` names,
  each file's CONTENT, its executable bit and its symlink target, and, for a **submodule**, that
  checkout's own state recursively, so a vendored library rolled back one commit is drift and not a
  constant. A later run whose state is byte-identical prints three `[verify:cache]` lines — the run
  it came from, its age, its census, its cost, the state's own file count, and **what the read did
  not re-measure** — and exits with the recorded code **without running the target**. What this
  buys is a rung asked twice about one tree: a second `verify --feature`, or a `close feature`
  straight after a green standalone one, is a read. **It is not N closes for one gate run** — a
  belt's one write is the grain's `status:` line, a tracked byte, so close #1 is exactly what
  invalidates close #2's state; making that free is a design question about where a belt computes
  its state, not a cache setting.
  Hard rule 4 is the whole design: **the state covers untracked files**, so a new module that breaks
  collection invalidates it; **a reuse is always printed**, because a reused green that reads like a
  fresh green is the first cardinal sin; **`--no-cache` runs the target anyway** and records what it
  found; **a malformed, missing or unreadable row re-runs** — a row is refused unless every field
  reads whole and its verdict and exit code agree; and **the state is re-read after the target**, so
  a tree edited mid-run records nothing and says the tree moved. Ignored files are not in the state,
  and a ledger is read ROW BY ROW rather than hashed whole: the rows a run files about ITSELF (the
  wrapper's `gate` cost row, the tier's `test` rows, this verb's own `verify` row, the couriers'
  session rows) are out, because a state covering what a gate writes while it runs could never
  repeat — and every other row is IN, because a status flip or a decision is a fact about the tree.
  Two of the dropped kinds are graded anyway, by `check budget` inside `make milestone`, so the row
  carries **a digest of them as that run left them** — not a count, which a row edited in place by a
  merge or a trim would slip past — and a reuse over a ledger whose graded rows moved runs the target
  and says which check reads them. `verify` records where a PM tree already is and **never
  creates one**. `--no-cache` beside `--plan` or `--check` is exit 2 — those run no rung.

- **The two files `pm install-skills` writes stop asserting behaviour this package retired, and
  a test now holds every installable to that.** `.claude/rules/pm-execution.md` auto-loads into
  every session and `.claude/skills/pm-operations/SKILL.md` is the manual, and both told an
  operator to do things that are gone: maintain `ROADMAP.md` (retired in 0.3.0, replaced by
  `pm roadmap` + `releases.md`), read `pm validate` as holding an id to its path (V2/V3, retired
  in 0.4.0), read the plan's `order` as a list of versions (0.4.0 made it milestone ids), and
  remove a retired milestone's DIRECTORY by hand — where `pm retire` deletes that milestone's
  grains and a pooled tree has no such directory. `pm new`'s entry said it *"scaffolds to the
  schema"*; it now says what the verb mints, names the open defect
  (`bg-the-new-verbs-mint-a-compound-id`, issue #8), and tells the reader to check the id it got.
  **And step 3 of the loop instructed a command the stock vocabulary refuses:**
  `pm story reviewing <id>` exits 2 naming `[pm.states.story]`, which declares no review word —
  review is a FEATURE act (`pm feature reviewing <id>`), and the same rule's own drift example
  used the refused word as its GOOD case. Both corrected.
  These files are neither code nor a doc in `[doc] scope`, so nothing graded them:
  `tests/test_install.py` now sweeps every packaged installable for the names in the code's own
  retirement registries (`RETIRED_COMMANDS`, `RETIRED_KEYS`, `RETIRED_CHECKS`, `[verify]`'s
  `RETIRED`) plus `ROADMAP.md`, `<!-- pm:execution -->` and `[[verify.narrow]]`, and fails a line
  that names one without also saying "retired". **Consumers: run
  `agentic-sdlc pm install-skills --diff`, then `--force`.**

- **`prepare-commit-msg` recognises any Co-Authored-By trailer it should not duplicate, not only
  the exact string it writes.** The dedupe guard was `grep -qF "$TRAILER"`, which holds only while
  this hook is the sole writer of a trailer — and it is not: a harness signs its own session off
  with a MODEL-NAMED line (`Co-Authored-By: Claude Opus 5 <…>`), which the fixed string never
  matched, so every dispatched-agent commit ended with TWO trailers. `is_agent_context` gates the
  hook, so it never fired on a trunk commit anyone reads. What the hook WRITES (`TRAILER`) is now
  separate from what counts as ALREADY WRITTEN (`TRAILER_RE`, an ERE); both live in the
  `project config` header, so editing either is not a drift. The hook now answers
  `--self-test` with a five-row message corpus — the model-named input among them — so
  `check hooks` replays three corpora rather than two. **Re-install with
  `agentic-sdlc install-hooks --force` and re-read the header.**

- **`tools/dev/pm_migrate.py` rewrites a ref on TOKEN boundaries, not on quote characters, and
  prints the ref census either side of the move.** The sweep required a quote on both sides of an
  id, so `depends_on: ["a/b"]` was rewritten and `consumed_by: [a/b,c/d]` — an ordinary YAML
  inline sequence — was not. A 497-grain consumer tree came out of the migration with **52 refs
  naming pre-migration ids**, and nothing failed: a ref that names a grain under an id nothing
  answers to is counted UNVERIFIABLE, the same bucket a retired milestone's refs land in, so the
  migration reported success and `check pm` exited 0. The id grammar says what a token is, so
  `0.1/alpha` is still not a ref inside `0.1/alphabet` — by construction rather than by
  punctuation. The run now prints `refs: N -> N; UNVERIFIABLE: N -> N` and WARNS by name when the
  second number rose. **If you migrated a tree with an earlier copy of this script, run
  `agentic-sdlc pm validate` and read the UNVERIFIABLE count.**

- **NEW `[emit]`: the conveyor's events are WRITTEN to a sink you declare, and this package never
  runs anything to deliver them.** `sink` takes the word `"ledger"` (the same `ledger.jsonl` every
  other row already lands in, routed by the grain the event names), a path inside the checkout
  (appended to as JSON lines), or `"-"` (one JSON line per event on stdout, beside the human prose
  and never inside it — a consumer parsing prose keeps parsing prose). `kinds` narrows which of the
  three taps — `enter`, `verdict`, `leave` — produce a row. **Declaring the section is what turns
  emission on**: both keys are stock-defaulted inside it, so a bare `[emit]` is the ledger and all
  three taps and `pm config --seed` carries both commented at their real values — while **a tree
  declaring no `[emit]` at all emits nothing and behaves exactly as 0.4.0 did, exit codes and
  stdout included**, which `emit()` itself holds rather than each call site. A sink this package
  cannot write to — or a row it cannot serialise — is a `[emit] WARNING — …` line on stderr naming
  it: never a crash, never a changed exit code and never silence, because emission is not
  load-bearing for any verdict. **No code path spawns a process, imports a module named in config,
  or resolves a config string to a callable** — a hook is an event this package writes, never a
  command it runs (0.5.0/D1), which is what keeps every gate here safe to run from a git hook in
  parallel. `tests/test_boundaries.py` holds
  `repo/emit.py` to an import allowlist and to the same no-subprocess derivation the `shell` tier
  is built on, so a spawn added there is a build break rather than a review.

- **NEW `check pm` U3: a declared `[emit]` sink that has never been written to is a WARN, and a
  tree declaring no `[emit]` gets no line at all.** `recording-is-on-or-the-gate-is-red` (0.4.0)
  exists because the ledger couriers were wired, executable, and recorded nothing for the whole of
  0.3.0 with nobody able to tell; a declared sink that is silent is that trap on a fresh surface,
  because it looks exactly like a tree that opted out. **Opting out stays quiet** — the finding is
  *declared AND silent*, a contradiction the tree is holding. The rule READS: it never writes a
  probe row to find out, because a gate that mutates to measure is a gate that lies about what it
  measured. The `"-"` sink leaves nothing in the tree, so it is UNVERIFIABLE by name rather than
  passed over. A malformed `[emit]` value is still exit 2, never a finding.

- **NEW `check pm` U4: the LAST hook-written row is named with its age, beside the wiring.**
  `adopt`'s `telemetry-live` read `.claude/settings.json`, confirmed both couriers were wired and
  PASSED — but whether a harness ever LOADS that file depends on the session's project root, so a
  session rooted above the checkout records nothing while every wiring answer stays green. U2 did
  not fire, because the ledgers were not empty: they held the `status`, `decision` and `gate` rows
  this checkout writes itself, and **no rule counted row KINDS**. U4 counts them: `dispatch` and
  `session` are the kinds a courier files (`ledger.EVENT_KINDS`), everything else is written from
  inside the repo and is not evidence a hook ever fired. A tree that has recorded one gets a
  counted `RECORDING  last hook-written row: dispatch, 3h ago` line; a tree that has not gets a
  WARN naming what the ledgers DO hold. A tree that wires no courier AND has recorded nothing
  stays silent — telemetry is *clearly available, warned when absent, never mandatory*
  (0.4.0/D5).

  **The kind alone is not the courier's signature: the row must also carry a `session_id`.**
  `pm ledger record SubagentStop` mints `dispatch` and `session` rows by hand from inside a
  checkout, and this repo's own gate counted sixteen of them as *"came from a courier"* when no
  courier had ever run. The session id comes from the hook payload; a hand row has none. The
  failure direction is noisy, never blind — a courier row that somehow arrives without one reads
  as `never`.

  **The wiring is READ, not grepped.** `.claude/settings.json` was searched as raw text for a
  courier's filename, so an allowlist entry (`Bash(bash tools/hooks/cc-ledger-session.sh
  --self-test)`, which this package's own next-step text tells consumers to add) fired the full
  WARN on a tree with no hook registered anywhere, and a registration in `.claude/
  settings.local.json` was invisible. Both files are parsed, only `command` entries under `hooks`
  count, and the line names which file was read. **The LEDGER outranks the config**: a tree with
  no in-checkout settings file and a courier row still gets its `RECORDING` line, because the
  block works in a settings file above the repo and reading only the config called such a tree
  dead.

- **`adopt`'s `telemetry-live` reports the row it observed, not only the config it read.** Its
  verdict line now carries the same phrase U4 prints — `the last hook-written row is dispatch, 3h
  ago`, or `last hook-written row: never` — off one shared reader, so the belt and the gate cannot
  disagree about whether a tree is recording. It still never refuses an adoption on its own, and
  the line no longer says `telemetry is live` over a tree where nothing has ever come through:
  `wired` alone is the tool asserting an outcome it did not observe (rule 4). Nor over a ledger it
  could not read — the shared reader has always had a third answer, `UNVERIFIABLE`, and a belt
  branching on two of the three let it fall through to a pass while `check pm` U4 on the same tree
  called it *"not a finding, and not a pass either"*. It is `UNVERIFIABLE` on both surfaces now.
  It reads the wiring through the same reader too, so a registration in
  `.claude/settings.local.json` no longer reads as unwired and a tree recording through a settings
  file above the checkout is no longer reported as having no telemetry. Its refusal names
  `install-hooks --write-settings` and `GDK_LEDGER_ROOT` — it is the only surface a fresh consumer
  reaches, because `check pm` U2 returns early on a tree that wires nothing.

- **NEW OUTPUT LINE: a recorded `lesson` surfaces at the belt that touches its grain or runs its
  rule** (`ft-a-lesson-surfaces-where-you-stand`). A `lesson` row in the ledger is printed beside
  the verdict it belongs to — `[<op>] lesson: grain|rule <name> — <text> (source: <path>)` — at
  exactly three moments and no others: the belt ENTERS on a grain a lesson names, a CHECK runs
  whose name a lesson names, and a check's `pm ready-for` NAMES a blocker a lesson names. Each is
  also emitted on the `[emit]` sink as a `lesson.enter` / `lesson.verdict` row carrying the
  recorded row verbatim under one key, so a human reading stdout and an agent reading the stream
  get the same fact at the same instant. **It is never a gate**: no verdict, no exit code and no
  existing line changes whether a lesson exists or not, and a sink or a `[emit]` section it cannot
  reach is one WARNING line beside the lesson rather than a refused belt. **And never a nag**:
  scope is the grain named or the rule named, EXACTLY — no fuzzy matching, no "related", no
  ranking or scoring, because anything inferred needs a feedback edge and a reader/writer has
  nowhere to put one (0.5.0/D1). When several match, all of them print in recorded order; choosing
  is inference, and the caller has the source paths.

## v0.4.0 — 2026-09-07 — authoring is separate from binding

> **The northstar: the path is where a file lives; the frontmatter is what it is and what it
> belongs to.** A grain's kind, its id and its parent were all functions of where its file sat,
> and `id:`/`milestone:`/`feature:` were copies that V2 and V3 existed to police — one fact stored
> twice, which is the defect this package forbids everywhere else. The pools are the tables,
> membership is the child's field, sequence is the parent's list, and nothing reads a path as
> schema.
>
> **What that cost, honestly.** Fourteen defects of one shape survived into review: a rule written
> inside a walk that descends by binding answers only for the grains that walk reaches, and 0.4.0
> made authored-but-unbound the NORMAL state. Two BLOCKERs, four CRITICALs and about twenty MAJORs
> came out of the feature reviews — a migration that could not run and then deleted twelve files it
> never named, a scaffold that blinded a 138-grain tree, a telemetry probe that ran in its own
> `mktemp` repo and reported "telemetry is live", a shape gate that decided what a document IS from
> its filename and whose printed repair destroyed the document. **Every one passed its own tests.**

- **`pm add` binds AND sequences, at every level, and it is exactly `set` plus a list insert.**

  ```
  agentic-sdlc pm add <parent-id> <child-id> [--position N | --before <id> | --after <id>]
  agentic-sdlc pm remove <parent-id> <child-id>
  ```

  Membership is the child's field; SEQUENCE is the parent's `order:` block list. One shape at
  every level — root → milestones, milestone → features and bugs, feature → stories — and
  **neither argument names a kind**: each id resolves to the grain that declares one, so the pair
  is read off the ids rather than from a check written per level. Bare `add` appends. `remove`
  unbinds and unsequences together; `pm set <id> <field> ""` still unbinds alone.

  `add` does two writes and nothing else: the child's binding field, and the parent's list. It
  never reaches into a grain it was not given — re-binding a child says which old parent is now
  left with a DANGLING entry and names the `pm remove` that clears it.

- **`[pm.contains]` declares which kinds may hold which**, and `pm add` refuses off it at exit 1
  naming BOTH kinds. Stock (hard rule 5 — a repo declaring nothing behaves byte-identically):

  ```toml
  [pm.contains]
  roadmap   = ["milestone"]
  milestone = ["feature", "bug"]
  feature   = ["story"]
  ```

  It NARROWS: which field a child names its parent with is fixed, so a project that files no bugs
  drops `"bug"` and `pm add <milestone> <bug>` is then refused by name. A pairing no field could
  carry (`milestone = ["story"]`) is a malformed declaration at exit 2, naming the field.

- **`order` is OPTIONAL per container, and `check pm` counts both directions.** A bound child in
  no parent's `order` is `UNSEQUENCED` — a counted line, never a finding, because authoring and
  sequencing are separate acts. An entry naming a grain its parent does not hold is `DANGLING`
  and FAILS (V7). One naming no grain at all is `UNVERIFIABLE` and WARNS, for the reason R1 has
  always given: a retired grain and one never written look identical from here.

- **The plan lists MILESTONE IDS, and `pm order` retires into `pm add` against the root.**
  `pm/roadmap/releases.md` is a container like any other: it declares its own `id:` (`roadmap`
  when it declares none, so an existing plan needs no edit) and `kind: roadmap`, and its `order`
  sequences milestone ids rather than version strings. **A milestone that re-versions no longer
  touches the plan**, and `pm rename` sweeps the entry with every other inbound reference.

  **CONSUMER ACTION:** rewrite `order` in `pm/roadmap/releases.md` from versions to the ids of the
  milestones claiming them, and replace `pm order --append <version>` in any script with
  `agentic-sdlc pm add <plan-id> <milestone-id>`. `pm order` is refused at exit 2 naming its
  replacement, never as an unknown command. Reading the plan is still `pm roadmap`; `pm next`
  still prints `version  milestone  status`, taking the version from the milestone.

  R1's second half changes with it: *a `version:` on no plan* was a FAIL and is now the
  `UNSEQUENCED` counted line above. R4 and R6 name the milestone id where they named a version.

  **Line shapes that moved** (rule 6, all of them grep-visible): `pm roadmap` prints
  `(no version)` for a scheduled milestone that declares none and `-	<id>	DANGLING` for an entry
  naming no milestone, where it printed `(unclaimed)`/`unverifiable`; its backlog header says
  *"on no plan — not scheduled as a release"*. `pm status` prints one
  `-- <n>/<m> feature(s) done` line per milestone instead of one per phase bucket.

- **RETIRED: `<!-- pm:execution -->`, `pm sync` and V6.** A rendered roster of a parent's children
  was a second scoreboard, and keeping it in agreement with the tree was V2's defect one level
  down. **Replacement:** `order:` on the parent — written by `pm add`, read by `pm status`,
  `pm roadmap` and `pm ledger report`, and graded by the UNSEQUENCED/DANGLING pair above. `pm sync`
  and `V6` in `[pm] checks` are both refused at exit 2 naming that replacement. The block itself
  is inert markdown; delete it when convenient.

- **RETIRED: `[pm] story_ordinal_prefix`.** A story's FILE name is not its identity — `id:` is,
  and the file may be called anything. **Replacement:** the feature's own `order:` list, one
  sequence in the parent instead of `NN-` in forty filenames. `pm new story <fid> 01-boots` now
  keeps `01-boots` as the id segment rather than stripping the ordinal out of it. The key is
  refused at exit 2 by name, with that replacement.

- **RETIRED: `phase:` as a grouping.** `pm status` grouped a milestone's features into phase
  buckets with a per-bucket tally; it now prints them in the milestone's declared `order:` with
  one `-- N/M feature(s) done` line, and `check pm`'s *"carries no phase:"* READY warning is
  gone. **Replacement:** `order:` on the milestone. The field is inert where it is still written;
  nothing reads it.

- **A shared doc is scaffolded on demand, its ABSENCE is a warning, and a missing instruction
  line is a finding.** Three changes to the same document class — `decisions.md`, `handoff.md`,
  `review.md` — which sit beside their grain in a pool, under the grain's own stem
  (`milestones/0.1-handoff.md`).

  **`agentic-sdlc pm new handoff <milestone-id>`** mints `handoff.md` from the shipped template
  with the id and name filled. It had a template and a `SLOT_TEMPLATE` entry and NO code path
  wrote it, so an absent handoff was an empty canvas rather than an unfilled slot. It never
  clobbers: section 3, *"Traps this milestone has already sprung"*, is the one thing in the tree
  no command can regenerate.

  **`check pm` WARNS when a milestone in an `in_progress` state has no handoff** — the doc is
  deliberately never auto-minted, which is exactly why its absence can mean something. A WARN,
  never the exit code, and only `in_progress`: warning on `done` would fire once per historical
  milestone on every consumer's tree.

  **`check grain-shape` gains `NO HEADER`**, a FINDING, on a shared doc that does not open with
  its slot instruction line — the one channel that reaches a dispatched subagent, so a doc that
  lost it is silently unguided. **This can flip an unchanged tree from PASS to exit 1**: a
  hand-authored or hand-trimmed `decisions.md` was never asked for that line before. The finding
  names the literal line and the verb that restores it, derived per grain — `pm new feature
  0.1/alpha` for a feature's log, not a generic `pm new milestone`. Any KNOWN header passes,
  including retired spellings, so rewording one never reddens a doc written under the old words.

  `pm install-skills` writes a third file with them: `.claude/skills/handoff/SKILL.md`.

- **THE PM TREE IS FOUR POOLS, AND A GRAIN'S IDENTITY IS ITS FRONTMATTER.** The largest change
  this package has made to a consumer's tree. Before: a grain's kind came from which slot its
  document sat in, its parent came from the directory above, and `id:`/`milestone:`/`feature:`
  were copies of those facts that V2 and V3 existed to police — one fact stored twice, which is
  the defect this package forbids everywhere else. After:

  ```
  pm/roadmap/milestones/<slug>.md          pm/roadmap/ledgers/<milestone-id>.jsonl
  pm/roadmap/features/<slug>.md            pm/roadmap/ledger.jsonl   (rows naming no grain)
  pm/roadmap/stories/<slug>.md             pm/roadmap/milestones/<stem>-decisions.md
  pm/roadmap/bugs/<slug>.md                pm/roadmap/milestones/<stem>-handoff.md
  ```

  **The path is where a file lives; the frontmatter is what it is and what it belongs to.** Every
  document declares `id:`, `kind:` and its binding — `milestone:` on a feature or a bug,
  `feature:` on a story. Membership is the child's field; sequence is the parent's `order` list.
  Nothing reads a path as schema any more, and the filename is yours: rename a document and every
  reader still finds it, because none of them was ever looking at the name.

  **A nested tree keeps working.** Every resolver falls back to the old reading when no pool holds
  a document, so the day you bump nothing changes. Moving is
  `python3 tools/dev/pm_migrate.py`, run from your checkout — deliberately NOT a verb: the CLI is
  a published API, and a one-time move does not earn a shape every consumer's gate then depends on
  forever. It reports slug collisions and writes nothing rather than inventing an id (D4).

  **What you LOSE, and what answers instead.** `git log -- pm/roadmap/<milestone>/` stops
  answering *"this milestone's history"* — `git log -- pm/roadmap/ledgers/<id>.jsonl` and
  `pm ledger report <id>` do. `ls pm/roadmap/<milestone>/` stops answering *"what is in this
  milestone"* — `pm status <id>` does, and it always answered better, because it reads status.

- **V2 and V3 RETIRE; V7 arrives.** V2 held `id:` to the path and V3 held a binding to the
  directory a document sat in; both kept two copies of one fact in agreement, and there is one
  copy now. Naming either in `[pm] checks` is exit 2 with the reason, never a silent no-op.

  **V7 is what replaced the half of V3 that was a real fact**: a binding that is empty, names no
  grain in the tree, or names a grain of the wrong kind. It walks the POOLS rather than descending
  from the milestones, and that is the whole point — a feature bound to a milestone that is not
  there is exactly what a descent cannot see, so it was counted by the census and reached by
  nothing. **V1 grew the other half**: a document whose frontmatter declares no `id:` is reported
  BY NAME and counted as skipped, and two documents claiming one id are named together. A resolver
  keeps the first it reads, because uniqueness cannot be a runtime lock without an allocator and a
  git repo has none — so the collision is a finding rather than a refusal.

- **`.gitattributes` becomes `<roadmap>/**/*.jsonl merge=union`.** The old
  `<roadmap>/**/ledger.jsonl` reached both 0.3.0 homes because both were NAMED `ledger.jsonl`; a
  pooled milestone's ledger is `<roadmap>/ledgers/<id>.jsonl`, which that pattern misses entirely.
  Every branch appends to the ledger of the milestone it is building, so the miss is a merge
  conflict on every parallel branch, quietly, with nothing connecting it to this change.
  `pm init` appends the new line; **delete the old one** — the last match wins, so it is inert
  rather than wrong, but it reads as a second rule.

- **`pm move` is DELETED.** It existed only because position was parentage. Re-parenting is one
  line now — `pm set <story-id> feature <fid>` — the id never changes, and there is nothing to
  rewrite. `pm move` also renamed the file and did NOT rewrite the refs pointing at the moved
  story, so every `depends_on` naming it went stale, silently, at the moment of the move.

- **NEW VERB: `pm rename <old-id> <new-id>`** — the one ref-rewriting path that still has to
  exist, which is the defect `pm move` had, done once in the verb that needs it. It rewrites the
  grain's own `id:` and **every inbound reference in the tree** — `depends_on`, `consumed_by`,
  `reviewed`, `caused_by`, `caught_in`, `fix_milestone`, the bindings (`milestone:` / `feature:`)
  and every `order` entry — in one pass, **whole or not at all**: one reference it cannot rewrite
  and nothing at all is written, named. References are matched WHOLE-TOKEN, so `0.1/alphabet` and
  `0.1/alpha/s0` are not references to `0.1/alpha`. A `<new-id>` failing the id grammar is refused
  before the tree is read (exit 2); one another grain already holds is refused naming that grain
  (exit 1) and never auto-resolved, which is what `tools/dev/pm_migrate.py` tells you to run when
  it reports a slug collision. Frontmatter only: prose naming the id is yours, the ledger keeps
  its rows under the old id because history is not rewritten, and the document keeps its
  FILENAME — nothing reads a path as schema.

- **`pm retire` removes a milestone's GRAINS, not a directory.** The same set of bytes the
  directory used to hold — the milestone, every feature and bug bound to it, every story bound to
  those, each grain's shared docs, and its ledger — addressed by binding instead of by location.
  `pm/roadmap/` is the tree and always survives, and the tree's own ledger is untouched, because
  those rows were never about the milestone.

- **Each pool renders its own census.** `1 story/ies, 2 note(s) skipped (…), 0 bug(s), 1 note(s)
  skipped (…)` rather than one aggregate: a note beside the FEATURES now discloses beside the
  feature count, which an aggregate could say the size of but never the place of. A dot-prefixed
  path is still a deliberate hide, still out of scope, and still counted.

- **`pm new` refuses an id the grammar rejects before it walks anything**, and the four grain
  templates carry `kind:`. `pm new bug --caused-by <fid>` echoes what it stamped: a field the
  caller asked for and never sees confirmed is a field they have to open the file to trust.

- **A row naming no grain lands in the tree's own ledger, `<roadmap>/ledger.jsonl`.** A `gate`
  row (a gate run is not work on a grain), a `test` row, a session nobody could attribute, a hand
  entry with no `--grain`: all of them had to be routed by asking the tree something, and every
  such rule had a refusal path — which is a telemetry write being dropped. **They are the residue,
  not the destination**: `pm ledger report` reads a milestone's ledger AND this one, shows these in
  the `rows naming no grain` bucket it already printed, and never folds one into a grain's line.
  After this there is no place a row can be refused for want of somewhere to put it, except a tree
  with no `pm/roadmap` at all.

  **`.gitattributes` moves from `<roadmap>/*/ledger.jsonl` to `<roadmap>/**/ledger.jsonl`** —
  gitignore-style `a/**/b` matches `a/b` too, so one pattern covers both homes. Without it the
  file every branch appends to would conflict on every branch, as a merge conflict nobody connects
  to this change. `pm init` appends the new line on the next run; **a consumer whose
  `.gitattributes` still carries the `*/` pattern should delete it** — the last match wins, so it
  is inert rather than wrong, but it reads as a second rule.

  `check budget` and `verify --plan` follow the rows and read the same one file. That is also a
  fix they get for free: `pm retire` used to take a milestone's gate history away with its
  directory, so the next milestone printed `unknown` for its rungs until it had run each one.

  **On the first run after the bump both will say they have no numbers** — every historical `gate`
  row is in a milestone ledger and neither reads those any more. `verify --plan` prints `unknown`
  and `check budget` reports UNMEASURED for each tier until you have run it once. Both degrade
  loudly and neither invents a cost, which is the intended behaviour; run `make <tier>` once and
  the numbers come back. Old rows are not migrated: they are history, and moving them would be
  rewriting an append-only log.

  **`pm ledger report`'s `gate cost` section is now about the TREE, not the milestone in its
  heading**, and says so on the line. Every gate row lands in one file, so two milestones' reports
  print identical gate rows and `runs`/`delta_ms` are lifetime-of-tree numbers. Windowing them by
  a milestone's timestamps was the alternative and it loses: a milestone declares no time range,
  so the window would be inferred and then quoted as though somebody had stated it.

  **`pm ledger show` reads both ledgers**, because a row naming no grain can still name a grain
  through its `tree` snapshot — so `show` and `report` had begun to disagree about the same row,
  with `report` billing a story for time `show` said did not exist.

- **`check pm` gains U2: the ledger couriers are wired and this tree holds no row.** In the USAGE
  family beside U1, because it asks U1's question one layer out — not *is this word used* but
  *is this capability doing anything* — and STOCK-ON for U1's own argument: an opt-in warning
  about silence is itself silence. A tree that wires nothing stays quiet either way, so a
  non-adopter pays nothing. A **WARN**, never the exit code. The telemetry in this repo recorded nothing for a whole
  milestone with the hooks installed, executable, self-testing and firing: the verb they called
  refused every row, and a courier fails open by design (it must never block a session stop), so
  the refusal went to a stderr nobody reads. Zero rows, zero complaints, for weeks.

  `one-rule-routes-a-row` deleted that specific cause and none of the class. The rest all produce
  the same silence: the entries were never pasted; the `pm` make target is not `.PHONY`, so `make`
  exits 0 without ever reaching the verb; `[pm.states.*]` is undeclared, so every work-moving verb
  refuses; `python3` or the transcript path does not resolve. The warning names all four in the
  order they cost people time and names the one command that answers them —
  `bash tools/hooks/cc-ledger-session.sh --self-test`.

  **A tree that wires nothing stays silent.** It opted out, and this package does not conscript; a
  `.claude/settings.json` that will not parse is UNVERIFIABLE, never a failure. An EMPTY
  `ledger.jsonl` counts as no rows, because that is exactly what a courier leaves behind when it
  created the file and then refused the row.

  `pm-execution.md`'s claim step now says the flip is bookkeeping and **not** what turns recording
  on — it never was after the routing change, and reading it that way is how the silence lasted.

- **Three absences the tool could already see and did not say** (all WARN, none in an exit code):
  a **story in an `in_progress` category with no `owner:`** — a live bug, not a tidy-up:
  `pm-execution.md` step 1 says to set it in the same edit as the claim, two modules READ the
  field, and nothing asked whether it was there, so a tree could run a milestone with every story
  unowned; a **feature past `todo` with an empty `## Proof budget`** — the anti-bloat contract
  every feature template carries and nothing had ever checked was filled in, which is a contract
  nobody verifies, i.e. a suggestion; and **`verify --plan` names a gate in `[checks] all` that has
  filed no cost row** while its neighbours have. That last is silent when NONE of them has one,
  because a tree running its gates inside a composed target has rows for the composition and none
  per gate — the join only means something when some are measured and one never is.

  No new rule id, no new verb, no new gate module: two lines in the READY family and one in a
  report that already existed. That is what "fix at the cheapest layer" looks like.

- **`adopt` gains `telemetry-live`: is this tree recording, and if not, which of the three ways.**
  A consumer bumps the pin, gets the courier scripts, and pastes the `.claude/settings.json` block
  **by hand** — and nothing verified the paste. The failure is files present, hooks unarmed, zero
  rows, zero complaints, which is the state this package's own tree was in for a whole milestone.

  **A probe, not an inspection.** Reading settings.json proves a string is present; the courier's
  own `--self-test` drives *your* vehicle end to end, which is the only thing that answers *does
  `make -s pm ARGS=…` reach the verb here*. Every courier already shipped that corpus and no belt
  called it. The three ways it reports: the entries were never pasted; the `pm` target is not
  `.PHONY` so `make` exits 0 without reaching the verb; `[pm.states.*]` is undeclared so every
  work-moving verb refuses. In plain words rather than a rule id — *no ledger setup for this tree,
  no telemetry*.

  **Never mandatory.** A tree that has not wired the couriers opted out and is not broken; what it
  must never be is *silently* opted out. `install-hooks` now says the printed block is **not yet in
  force** and that `adopt` and `check pm` U2 will report it until it is.

- **Every status write breadcrumbs what the conveyor asks next**, and every read verb names its
  columns. `pm story building <id>` now prints, on stderr, the belt that closes that grain and the
  checks the belt will actually run — `close feature` asks stories-done, feature-verified,
  review-recorded, findings-landed — read from the belt registry and from `[pm.states.<kind>]` at
  runtime. **A breadcrumb that is not DERIVED does not ship**: *"you should run a review now"* is
  the engine having an opinion, which is what hard rule 9 forbids. A project declaring different
  state words gets its own words back. `[pm] breadcrumbs = false` turns it off; stock is ON,
  because a breadcrumb nobody sees teaches nobody. **STDOUT is byte-identical** — the status line
  is still the one line a consumer parses.

- **`pm status` says how long each open grain has been open, and `pm ledger report` gives the
  distribution.** The ledger already timestamped every move and `total_seconds` deliberately
  answered `None` while a grain was in flight, so the number that creates pressure was the one
  nothing measured: 0.3.0 built eleven features in 64 minutes and spent 93 more reviewing them,
  with every one of those features sitting `building` and nothing anywhere saying so. `ledger
  open_seconds` is first-status-row-to-now; a grain nobody has moved is **UNMEASURED, never zero**.
  Nothing is gated on the number — a ceiling on how long a feature may stay open is this package
  having an opinion about somebody's week.

- **The word "telemetry" is now in the surfaces you are standing in when you need it.** It was in
  none of them: not `pm --help`, not the rule that auto-loads on every tree edit, not either
  shipped skill's `description:`. `grep -ril telemetry` over the package returned five design
  documents, four tests and a vendored lexer — the archaeology of the feature, never the verb that
  shipped from it. So an agent asked for *"full telemetry — phasing, timings, token use, tool
  calls"* hand-wrote a markdown table while the package sat on `pm ledger`: seven row kinds,
  automatic per-session capture off the transcript, and a per-grain spend report.

  Three edits and **no new capability**: `pm --help`'s two ledger lines say what those verbs ARE;
  `pm-execution.md`'s read-verb list names `pm ledger show` and `pm ledger report` and what each
  answers; and `pm-operations`' skill `description:` carries the vocabulary a person actually types
  — telemetry, spend, cost, tokens, *how long did this take* — because the description is the only
  part a selector reads. A consumer gets all three on the bump (`pm install-skills --force`).

- **`pm list` emits the NAME, and both listing forms take `--json`.** OUTPUT-SHAPE CHANGE, and
  it is a fifth column at the END of each row: `id status owner feature name` for stories,
  `id status category branch name` for milestones. **A consumer whose parser ends in a catch-all
  will silently absorb it** — `IFS=$'\t' read -r a b c branch` makes `branch` hold
  `branch<TAB>name`, because the last variable of a `read` takes every remaining field. This
  package's own `agent-worktree.sh` broke exactly that way and is fixed with one extra variable;
  check yours. `--help` now names each form's columns IN ORDER so a pipeline is writable without
  reading source, and a tab inside a `name` is replaced by a space in the tab-separated form so it
  cannot forge a column (`--json` keeps the byte).

  The reason it is a column and not a flag: `pm list | grep "<a name>"` returned nothing, and the
  conclusion drawn was that the tool could not search — so a `--grep` flag was proposed for a
  capability the shell already had. **A read verb that omits a field people filter on teaches them
  the tool cannot do it.** The rule is now in this package's `CLAUDE.md`: read verbs emit lines,
  composition is the shell's job, and if you cannot pipe it the missing thing is a COLUMN, never a
  verb. No filter flag is added by this change and the existing ones all stay.

- **The report stops un-doing the recorder's refusal.** `pm ledger record` omits a row's `grain`
  key when two stories are live, because a row filed against the wrong story is uncorrectable —
  and `pm ledger report` then attributed that same row through its `tree` snapshot, to BOTH
  stories and to their feature. So the bucket the whole thing exists for printed
  `rows naming no grain (0)` in the one case it was built to handle. Now: **a snapshot places a row
  only when it names one candidate at its finest kind**, judged over stories first (a feature named
  alongside its own story is a roll-up, not a second candidate).

  **And a row that STATES a grain is attributed by it and by nothing else, even when this milestone
  cannot place it** — the fall-through billed a row naming a since-renamed story to whichever other
  story happened to be live, and disclosed nothing. Those get their own counted line,
  `stated_elsewhere` (a new `--json` key), rather than joining `rows naming no grain`: the two are
  opposites, and every milestone's report reads the tree's shared ledger, so rows from elsewhere
  are the ordinary case.

  **`GDK_LEDGER_GRAIN` has a documented producer, which it did not.** Nothing in this package
  exported it — not the printed settings block, not a hook, not a rule, not the README — so a
  courier read a variable no surface told anyone to set. `pm-execution.md` and `install-hooks`'
  next step now say who exports it and when. **Unverified, and said out loud:** whether a
  `SubagentStop` hook's environment can carry a per-dispatch value under Claude Code, or only one
  per session.

- **A row with no `--grain` resolves one from the tree, or carries no `grain` key at all.** The
  dispatched agent is told its grain; an orchestrator session nobody dispatched has no prompt to
  read one out of, and that is the session type most of a milestone's work happens in. So: exactly
  one story in an `in_progress` category is used and **routes the row to that grain's milestone**;
  zero or several omit the key, and several print both candidate ids on stderr — which the
  couriers pass through verbatim, so ambiguity is countable rather than assumed rare. `--grain`
  always wins and the lookup does not even run.

  **An unresolvable grain is an OMITTED KEY, never a zero and never a guess.** A row filed against
  the wrong story is uncorrectable; a row filed against none is visible in a bucket that already
  exists and can be fixed later. Resolution never changes an exit code, because the couriers'
  fail-open promise now depends on it.

- **Every automatic ledger row can name the grain it came from.** The telemetry worked and landed
  **unattributed**: `grain` has been `ROW_KEYS`' third key since the ledger shipped and neither
  courier filled it, so every hook-written row went to `rows naming no grain` and the per-grain
  spend table — the one a human actually reads — showed `0` dispatches against every feature and
  story in the milestone. The numbers were captured; nothing said what they bought.

  `--grain` is now accepted **alongside** `--from-transcript` rather than exclusive with it: the
  transcript is where the numbers come from and `--grain` is what the work was ON. The couriers
  pass it from **`GDK_LEDGER_GRAIN`** in their environment, exported by whoever started the
  session or dispatch — not a payload field, because no hook event carries a grain, and the fact
  already exists at the moment of dispatch. Unset is normal and passes no flag; an id that
  resolves to nothing is refused rather than dropped, on both forms, because a typo silently
  becoming an omitted key is how a row is misattributed forever.

  **`pm ledger report` now reads `grain:` and prefers it to the tree snapshot**, which it had been
  ignoring — so a row that says which story it was for lands on that story's line and on nobody
  else's. The snapshot stays for the rows already written, and for a row that states its grain it
  is not consulted at all: a dispatch billed for every other story that happened to be live is the
  read-side of the drift rule.

- **A ledger row is filed against the milestone that owns its GRAIN, at any status.** The
  telemetry writes went through a lookup that asked which milestone was `in_progress` and refused
  when none was and when several were — so **a tree recorded nothing at all while it was still
  planning, and said so only on a hook's stderr**, and two milestones in flight (the workflow this
  package is built for) refused every row with *"which one owns this row is the one thing this
  verb cannot know"*. The row knows: it names a grain, and the grain's document sits under exactly
  one milestone. `_stamp` had routed that way since the ledger shipped; this deletes the second
  mechanism rather than the first. **No status is read on any write path**, so a `planning`
  milestone records, and nothing that used to be written is now refused. `pm ledger report` with
  no id reports the CURRENT RELEASE's milestone — from `order` plus `[pm] version_at`, the same
  answer `pm next` gives — instead of "the one milestone in progress"; a tree with no plan is
  refused in the plan's own words, naming the argument that answers it.

## v0.3.0 — 2026-09-06 — the bump explains itself

> **The northstar: the tool teaches the conveyor.** A project that has just adopted the flow should
> be able to SEE whether it is using it. Every finding below came from two real adoptions of the
> same devkit split on 2026-09-06 that failed in mirror-image ways: one tree declared the flow and
> used three of its eight states; the other never declared one and shipped a green `make check` over
> a PM CLI that was refusing every work-moving verb. **Both passed every gate.**

- **BREAKING — a milestone declares `version:`, and D8 became R5.** A repo with `D8` in
  `[pm] checks` goes from exit 0 to **exit 2** on `check pm` and `check all`, and `adopt`
  refuses; `make check` fails until the key is removed. The message names R5 and says where
  the rule went — it is refused BY NAME rather than silently ungated, which is the point. The id goes back to being a slug: a
  milestone says which version it ships as in one optional frontmatter field, and the engine
  never parses, compares or increments the string — `"1.1.1"` and `"cow"` are equally valid.
  Order comes from `order` in `pm/roadmap/releases.md`, a block-style list read by the same
  reader as every grain, so "did the version increase" is a POSITION rather than a comparator.
  **`[pm] checks` naming `D8` is now exit 2 naming R5**, never a silent ungating: R5 grades the
  version file against the CURRENT entry in `order`, selected by the new `[pm] version_at`
  (`"start"`, the default and bump-at-start, or `"ship"`, bump-at-close). D8's hotfix special
  case is gone with it — a hotfix is an entry in the plan like anything else.
- **`pm order`, `pm next` and `pm roadmap`** — the plan is `order` in `pm/roadmap/releases.md`,
  block-style frontmatter edited by `pm order --append|--insert|--remove`. `release` with no
  argument takes the current version from it, and refuses one that is out of order naming both.
- **The release rules R1-R4 and R6** hold the plan and the tree to each other, all opt-in via
  `[pm] checks`. R1 is the UNBOUND family's first member — an `order` entry no milestone claims
  (a WARN: a dangling entry and a retired milestone's surviving row are indistinguishable) and a
  `version:` on no plan (a finding). R2 counts the backlog and never reddens on planning. R3 stops
  two milestones claiming one version, so which release ships is never decided by a directory name.
  R4 is history-is-a-prefix. R6 catches a release behind the last shipped one whose milestone never
  closed, and a `done` milestone whose version is on no plan.
- **`pm/roadmap/ROADMAP.md` is RETIRED, and `pm roadmap` replaces it.** The file was two things
  wearing one name: a hand-maintained index of milestones still in the tree — the second scoreboard
  this package forbids one grain down — and the only surviving record of milestones `pm retire`
  deleted. `pm roadmap` derives the first from the tree (every scheduled release with its milestone
  and state, then the backlog) and writes nothing. The second needs no file: `order` in
  `releases.md` keeps the version and R1 reports it UNVERIFIABLE once the directory is gone, so the
  row survives its milestone with nobody maintaining it. **`pm init` no longer seeds the file and
  `pm retire` no longer appends to it** — `retire` now says what outlives the directory, and tells
  you to schedule the version first if nothing would. An existing `ROADMAP.md` is left alone: this
  release does not delete a consumer's file, it stops writing to it.
- **The gate ledger binds to the CURRENT RELEASE, not to the one in-progress milestone.** A cost
  row is filed against the first unshipped entry in `order` — the release being WORKED ON — which
  answers with exactly one by construction. It does NOT read `[pm] version_at`: that key says which
  entry the version FILE is graded against, and conflating the two filed cost rows into an already
  shipped milestone's closed ledger. `no milestone in pm/roadmap is in progress, so there is no ledger this gate row
  belongs to` stops being a refusal: gate cost is a fact about a RUN, and the run happened whether
  or not somebody had flipped a status. A tree planning two milestones with neither flipped used to
  drop every cost row silently. `check budget` and `verify --plan` read through the same resolver,
  so the number a human sees and the number the gate grades cannot disagree. A tree that can answer
  from neither the plan nor a single in-progress milestone still refuses, naming `pm order`.

- **`pm init` reports a MEANING, not a write, and `check pm` gains U1.** `init` printed
  `appended the flow to devkit.toml` and a project adopted the conveyor as a CONFIG FIX — nobody
  then asked whether the tree USED the states, and one tree used three of its eight for its whole
  life with every gate green. D4 asks "is this word declared", never "is this word used". `init`
  now prints the ladder it wrote AGAINST THE TREE — per kind, how many states are declared, how
  many the tree uses, and which have never been held — so the sentence *"this project now declares
  8 milestone states; your tree uses 3"* is on screen at the moment of adoption. **U1** keeps
  saying it after the install scrolls away, as a WARN with the count, never a finding: a tree
  mid-adoption legitimately has unused states. U1 is OPT-IN like every other flow-shaped rule —
  stock-on it would add three lines to every consumer's `check pm`, and those shapes are grepped.
  A kind with no grains at all is silent rather than reporting every word unused.

- **A `devkit.toml` read reports EVERY defect, and the flow first.** The messages were already
  good and arrived one at a time in an order nothing ranked: a tree with a retired `[pm]` key AND
  no `[pm.states.*]` was told about the retired key — the cosmetic one — and had to fix it and
  re-run to learn that the flow was missing, which stops every work-moving verb in the package.
  `check pm` now prints one line per defect at a single exit 2, flow first. **And a `[checks] all`
  roster error no longer HIDES them**: an unknown gate name is reported together with what the
  correctly-named gates would have said about their own config, because routing a whole adoption at
  the roster is how a green `make check` ended up over a PM CLI that was refusing every verb.

- **`[gates] extra` refuses a gate name and says which key runs it.** The key takes make targets
  and the adjacent `[checks] all` takes gate names; neither error said so, so `extra = ["budget"]`
  reached GNU make as `No rule to make target 'budget'` — three layers below the config that caused
  it. It is now exit 2 at the config read, naming the entry, the namespace and `make check`. A
  target that merely CONTAINS a gate name (`budget-check`) is unaffected.

- **`adopt <version>` no longer requires a milestone directory named for the version.** A project
  that folds the pin bump into an open milestone as a feature — a day of work inside a month of
  game — could not run the belt at all: it refused with `no milestone directory pm/roadmap/<v>-*`
  before the first check, so the belt for that exact job was unreachable and all seven checks got
  done by hand in an invented order. `adopt` writes nothing (D12), so that directory is only where
  a ledger row WOULD land; the run now says which it found and asks all seven checks either way.
  `release` and `close story|feature`, which write a status, still refuse without it. The `adopt`
  line in `--help` now says it adopts a devkit PIN, so it reads differently from `release <version>`
  beside it.

- **`[adopt] ours`** — the installed files a project has taken over. `installables-current` grades
  the REST and names what was claimed on every run, pass or fail. The installables INVITE local
  edits (each ships a `Project config` section, "yours to edit after install"), so a project owning
  eleven of them sat at 6/7 forever, which is the same as no belt. Claiming is visible in the belt's
  own output every run, so the list is a statement rather than a hiding place. An unclaimed drifted
  file is still false with its `install-* --diff`; a claim naming a file this version does not
  install is REPORTED, not refused, because install plans change between versions; a malformed list
  is exit 2 through the same path grammar every other path key uses.
- **`check budget --help` no longer documents an exit code the gate does not return.** It said a
  tier with no `gate` row was UNMEASURED and that "both are findings, never a pass"; the gate exits
  0 for it and always has. The claim arrived in a docs-only commit that compressed the docstring to
  one screen and fused two true sentences — *UNMEASURED is never counted as a pass* and *NOT GRADED
  is a finding* — into one false one. A consumer read it, believed the gate would redden a tree with
  nothing measured yet, and had to run the binary to learn the contract. The BEHAVIOUR is unchanged
  and deliberate: a run that stopped is a finding because its numbers are the cost of a stop, and a
  tier nobody ran has not got slower. **What DID change: ceilings declared with not one `gate` row
  in the whole ledger is now a FAIL** — that is rule 4's zero census, a verdict over nothing, and it
  is a different condition from a single tier not having run.
- **`pm --help` names the belt beside the path that bypasses it.** `pm feature <done-state> <id>
  --review-record <path>` writes the status and stamps `reviewed:` in one go, skipping `close
  feature`'s `stories-done` and `findings-landed`, and it is the command every older consumer doc
  already contains. The entry now says so and points at `close feature`, and at `--force` for the
  deliberate deviation.

- **`tests/test_cli_surface.py` holds every `--help` in the package to the exit codes it claims.**
  It enumerates 21 surfaces, reads the exit contract each one states, and RUNS the condition to
  compare — the expected code is read out of the help at run time rather than restated in the test,
  so the pair under test is the documentation against the binary. A zero census fails loudly.
- **`core.apply` refuses a tree delete whose parent is not writable.** It unlinks from its parent
  exactly as a file delete does and was not checked for it, so the walk could empty a directory and
  then fail to remove it — leaving a gutted grain, the half-applied state that module exists to
  make unreachable.

- **An installer reports every file it touched and every target it withdrew.** `--diff` printed a
  header for a NEW file and a bare unified diff for a CHANGED one, so the obvious
  `grep '^\[install\]'` summarised a 1,211-line diff as ONE file and silently omitted the most
  consequential one. Every file an installer owns now gets a header line in `--diff` and in a real
  run, whatever its disposition — added, modified, already current, not installed. And an installer
  knows what it used to ship: a run reports `no longer shipped` for the make targets and the retired
  verb FLAGS over the span between the installed stamp and this version. A split once dropped seven
  targets in silence, one of them named in a consumer's `[gates] extra`, so `make check` simply
  broke; and a removed `--cascade` flag survived a bump inside a consumer's own written rules, green,
  because no gate anywhere can read a sentence about a flag. The tool saying it is the only way
  anyone finds out.

## v0.2.0 — 2026-09-06

- **`check grain-shape` stock caps tightened** — story 60, feature 80, bug 50, milestone 120,
  decisions 300 (were 200 / 200 / 150 / 200 / 500), plus a new `review` kind capped at 120 over
  every markdown file under `[pm] review_dir`. A consumer whose records are over these goes red
  on the pin bump: raise `[grain_shape] caps` in devkit.toml, visibly, or split the records.
- **`verify --story --to <rev>`** closes the range at a commit: `--ref <first>^ --to <last>` is
  the story's own edits, and `close story` now passes both from the `done:` line, so a story
  closed after other work has landed is verified against what it changed rather than against
  everything up to HEAD. Without `--to` nothing changes.
- **The story rung is a make target.** `[verify] story = "make unit"` sits beside `feature`
  and `milestone` — three lines, one shape — and `verify --story` runs it the way the other
  two rungs run theirs. Gone: the `[[verify.narrow]]` table (a config still carrying it, or a
  `[verify] narrow` key, is exit 2 naming the key and the line that replaces it), the `--ref`,
  `--to`, `--ignore` and `--changed` flags, the path census `--check` and `--plan` printed, and
  the git read the verb made — `verify` spawns nothing but the target. `verify --check` now
  holds the declared targets to the Makefile and nothing else; its verdict line reads
  `[verify:check] PASS — 3 of 3 rung(s) declared, held to N target(s) in <Makefile>`.
  `close story`'s test check is `story-verified` (was `narrow-verified`; a `[story] steps` or
  `[story.commands]` entry under the old name is exit 2): it runs the story rung once — no
  commit range, no `done:`-hash parsing, no "nothing to scan" — and reports its exit. The one
  line a consumer adds: `story = "make <target>"`; `verify --story` without it is exit 2.

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
- **The check lists.** `close story`: `story-exists`, `story-verified` (`verify --story`),
  `committed` (nothing outside the roadmap directory
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
  `pm-validates`, `story-verified`, `feature-verified`). A command for a check that reads
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

### The review findings land: a flow-less tree exits 2, `pm set` refuses `status`

`docs/reviews/2026-09-05-every-question-is-asked-of-a-category.md`, V1–V9.

- **A tree that declares no `[pm.states.*]` exits 2 on one line from every `pm` verb** — the
  same line `check pm` already printed, naming the key and `agentic-sdlc pm init`. It was a Python
  traceback at exit 1 (rule 6's code for FINDINGS) from `pm status`, `list`, `ready-for`, the four
  status verbs and `ledger report`: the absent-declaration refusal is raised mid-walk, after
  dispatch, and `main` did not catch it there. This is the tree every consumer has on the day it
  bumps its pin, before `pm init`.
- **`pm set <id> status <word>` is refused at exit 2**, naming the `pm <kind> <word> <id>` that
  does it right. `set` asked nothing of the declaration and stamped no ledger row, so it wrote any
  word at exit 0 where the four status verbs refuse; every status write now goes through
  `move_defect` and lands a row. Every other key is `set`'s as before.
- **`pm status`'s feature status column is as wide as the longest word the project declared for a
  feature**, instead of a fixed 8 that `reviewing` overflowed under the seed. Alignment only; the
  row's words are unchanged.
- The readiness warnings key on the CATEGORY alone — see the next section's first bullet, which
  used to disclose an order dependence within `todo` and no longer needs to.

### ready is one command, and an empty ready is a warning

- **`check pm` prints `  WARN  ` lines** (new line shape, rule 6) for a grain that has left
  `todo` — its status sits in the `in_progress` or `done` category, under whatever words the
  project declared; the order of words within `todo` changes nothing — and says nothing about
  what must be true: a story with an empty or absent `## Acceptance criteria`,
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

**Data-format change, additive** (decision U1 — "keep and extend"). The dispatch snapshot a
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
  it always was. A row that names nothing of this milestone is a dispatch over an idle tree,
  over another milestone's work, or over a tree whose words the old shape could not spell, and
  the report says so rather than counting it as empty: a line under `rows naming no grain` —
  `N of these predate category keys and name no grain of this milestone — an idle tree, another
  milestone's work, or words that shape could not spell; not counted as empty` — and a `legacy`
  key in `--json` (`{"rows": N, "unattributed": M}`, zeros when there is no boundary).
- **A new-shape row that names a grain only through a deprecated key is disclosed, not
  dropped.** Both key families are on every new row; when a grain sits at a seed word your
  declaration does not place in `in_progress` (a story at `reviewing` under the stock seed,
  since each kind seeds only the states its belt writes), the frozen key names it and the
  category key does not. The report reads the category key — attributing by the deprecated one
  would read a new row through an old seed — and says what that dropped, under the grain's
  table: `<grain> named only through a deprecated key — at a word this declaration does not
  place in in_progress, so counted in no column above: N dispatch row(s)`, with a `frozen_only`
  key per grain in `--json` (`N`, or `null` when nothing was dropped). Before this the grain
  printed `dispatches 0` and nothing said a row had named it.
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
