# agentic-sdlc

**A reader/writer over a PM tree.** The tree is markdown grains with YAML frontmatter under
`pm/roadmap/` — one flat pool per kind, `milestones/ features/ stories/ bugs/` — and the tool
reads and writes the same files, in the same places, over and over. The tree is packed context: it
holds the work, its state and its record. It echoes state back; it infers nothing and polices
nothing.

**The path is where a file lives; the frontmatter is what it is and what it belongs to.** Every
document declares `id:`, `kind:` and its binding — `milestone:` on a feature, `feature:` on a
story. Membership is the child's field, sequence is the parent's `order` list, and the filename is
yours: nothing reads a path as schema, so renaming a document breaks no reader.

- **`pm` writes one status.** `agentic-sdlc pm story building <id>` rewrites one `status:` line,
  preserves every other byte, and appends one timestamped row to the ledger of the milestone that
  owns the GRAIN — never to whichever milestone happens to be in progress.
- **`check` reads the same files and echoes findings and warnings.** `check pm` names every
  status that contradicts another; `check doc` names every dead claim in the docs. A finding is a
  line and the exit code is the verdict.
- **`release` checks, then writes one status or refuses.** It runs a check list, prints one line
  per check, and then writes exactly one status — or writes nothing and names every false check.
  `--force` writes anyway, and the ledger records which checks were false.

It does not build your code or decide what a status *means*. Your states, your flow: `init` writes
them into `devkit.toml`, every run reads them, and the tool has no opinion about your words.

### The flow it is built for: build wide, integrate once

1. **The architect writes a story and moves it**: `pm new story` plus a body, then
   `pm story building <id>`. The story is the brief.
2. **It dispatches a builder** with the brief `dispatch --grain <id>` prints. Each builder works
   in its own worktree on `feat/<slug>`.
3. **The builder runs the spot check** (`[verify] spot`: lint plus one unit slice, under 30 s),
   commits, pushes `feat/<slug>`, reports and stops. No wide gate, no PR, no merge.
4. **The integrator runs `integrate <slug>...` once per batch**: it merges each lane with
   `--no-ff`, runs one proof over the batch, fast-forwards the milestone branch and writes `done`
   on each merged story.
5. **`release <version>`** writes the milestone `done`. CI runs the full tiers once, on the
   release PR.

**Validate once:** a PASS is a receipt keyed on the tree, and nothing re-runs a gate on a tree
that has one. Hooks refuse only acts that cannot be undone or that harm another tree; they never
run a gate. [`SDLC.md`](SDLC.md) is the whole loop.

## Install

The kit is a wheel on its own static index, `https://cdowin.github.io/agentic-sdlc/simple/`, one
per release tag and never rebuilt. A project pins it in `uv.lock`, so every machine and CI runs the
same hash-checked bytes, and a dependency bot can see the pin. `X.Y.Z` below is the release you
pin; the index page lists them. From inside a git repo with no `pyproject.toml`:

```bash
uvx --index https://cdowin.github.io/agentic-sdlc/simple/ agentic-sdlc@X.Y.Z init
uv sync
make help
```

`init` writes a tooling-only `pyproject.toml` that pins the kit (below). A repo that already has one
declares the kit itself, and then runs `init` from the lock:

```bash
uv add --dev agentic-sdlc==X.Y.Z --index agentic-sdlc=https://cdowin.github.io/agentic-sdlc/simple/
uv run agentic-sdlc init
```

`uv add --index` writes the source pin and not `explicit = true`; add it by hand, or uv searches
the index for every package ahead of PyPI. The block, as `init` writes it:

```toml
[dependency-groups]
dev = ["agentic-sdlc==X.Y.Z"]

[[tool.uv.index]]
name = "agentic-sdlc"
url = "https://cdowin.github.io/agentic-sdlc/simple/"
explicit = true

[tool.uv.sources]
agentic-sdlc = { index = "agentic-sdlc" }
```

`init` writes `devkit.toml` (with your flow declared), your one-line `Makefile`, `Makefile.devkit`,
the hook corpus (armed), the agent roster, the CI workflows, the rendered SDLC document, a
`CLAUDE.md` skeleton and an empty PM tree — in order, idempotently. The devkit-owned files are
overwritten by `--force`; `devkit.toml`, `Makefile`, `pyproject.toml`, `CLAUDE.md` and the tree are
yours from the first write and never touched again. `make` runs `.venv/bin/agentic-sdlc`, runs
`uv sync --frozen` first when it is missing or older than `uv.lock`, and exits 2 with the `uv add`
line when `uv.lock` does not name the kit.

**Adopting a bump** is: `uv add --dev agentic-sdlc==X.Y.Z` (or merge a Renovate/Dependabot PR),
then **take `Makefile.devkit` first**, with the locked form, because every other command below goes
through the targets it defines (a `Makefile.devkit` from before 0.8.0 has no `sdlc` target):
`uv run agentic-sdlc install-gates --force`. **Coming from a `DEVKIT_VERSION` git pin** (before
1.0.0): run `adopt 1.0.0` from that pin once, and its `pin-bumped` check prints the move — the
`uv add` line, `install-gates --force` for the new `Makefile.devkit`, then delete the
`DEVKIT_VERSION` line.
Read the release notes (`agentic-sdlc changelog <milestone-id>` on the source tree, where
`agentic-sdlc pm roadmap` prints each release's version beside its milestone id — the changelog is a
`changelog:` field on each grain, not a file, since 0.6.0; a release before 0.6.0 has its notes only
in the retired file at its tag, and `git show v0.5.0:CHANGELOG.md` in a clone of this repo prints
v0.5.0 back to v0.2.0), run `make sdlc ARGS='install-agents --diff'` (and each other `install-*`) to
see what the release would change, take what you want, re-run `make pm ARGS=init` once, and
`make sdlc ARGS='adopt <version>'` to read the result.

## The ladder — one verb, one scope

Nothing runs a rung wider than the thing you changed, and nothing proves the same tree twice.

| Who | When | Run |
|---|---|---|
| anyone | after a PM-tree or doc edit | `make check` |
| builder | after each edit, and before the commit | the spot check, `[verify] spot`: lint plus one unit slice, under 30 s |
| integrator | once per batch of lanes | `integrate <slug>...`: merge, ONE proof, `done` on each merged story |
| architect | the milestone | `make sdlc ARGS='release <version>'`: status and version sites; CI runs `make milestone` once, on the release PR |
| anyone | bumping the devkit pin | `make sdlc ARGS='adopt <version>'` — the adoption, never your own gates |

`make sdlc ARGS='verify --plan'` prints each `verify` rung with the cost it last took, read from
your ledger. Ask it instead of guessing.

**A PASS is a receipt.** A rung records its verdict against the state of the tree it ran on, so
asking the same rung about the same tree twice costs one run and one read. The state leaves out
what a status write changes (each grain's `status:` line and the ledger rows), so a close or a
release after a green run is a read. A project whose rung target READS statuses sets `[verify]
reuse_ignores_status = false`. The reuse is always printed, naming the run it came from, its age
and what it did NOT re-measure; one other byte in the working tree, tracked or untracked, and it
re-runs. `--no-cache` re-runs unconditionally. `[verify.history_independent] story = true` takes
HEAD out of a rung's key; the declared inputs, the tool version, the command, the Makefiles, the
lockfile, the config, the Python runtime and `[verify] environment = ["CI"]` stay in it.

## Quickstart

```bash
agentic-sdlc pm new milestone first-light "First light" --version 0.1  # ms-first-light
agentic-sdlc pm new feature ms-0.1 the-thing "The thing"   # mints ft-the-thing
agentic-sdlc pm new story ft-the-thing works "it works"    # mints st-works
agentic-sdlc pm story building st-works                # one line written, one ledger row
agentic-sdlc pm add ft-the-thing st-works              # bind it, and sequence it there
agentic-sdlc pm status                                 # the tree, in its declared order
make check                                             # check all: doc + shell + pm + …
agentic-sdlc dispatch --grain st-works                 # the builder's brief, printed
agentic-sdlc pm story done st-works                    # the close: one status write, no gate
```

`release` prints one line per check, then one line saying what happened: `ok: <check>` or
`error: <check>: <what is false>`, then the one write and `next:` lines, or nothing written. Fix
what it named and run it again; every check is a read of the tree, so nothing is carried between
runs.

**A check has three answers, not two.** `--skip <check> "<why>"` is the third: the caller ANSWERED
that check, so it is not asked, the line reads `skipped: <check> — "<why>"`, the write happens, and
the milestone's ledger gets a `disposition` row carrying the reason against the grain. Only a check
your project named in `[<belt>] skippable` may be skipped — **stock declares none**, so stock is
today's belt — and a skip with no reason is refused, because an unexplained skip is a deviation and
`--force` is already the verb for one. `--force` still writes over false checks and still mints a
`deviation` row; the two are different in kind, and *"which closes skipped a review, and why"* is a
question the tree answers.

## Verbs

`agentic-sdlc --help` and `agentic-sdlc pm --help` are the live rosters; this is the same set. `pm <verb> --help` prints one verb's entry, at exit 0.

| Verb | Reads / writes |
|---|---|
| `pm <kind> <status> <id> [<answer>…]` | **One ARRIVAL.** Writes one `status:` line — any state in `[pm.states.<kind>]`, anything else is exit 2 — plus a `status` row, a `disposition` row and a `rung.leave` event. On **stderr**, all derived and never a refusal: `next:` (the belt that closes it and the checks it will ask), `have:` (the installed files `[pm.arrive.<kind>.<state>] have` binds to this state — a declared one that is ABSENT is a named line), the FORK that state declares with **both answers already typed as commands you can paste**, `ready:` when the write made a PARENT ready, and one census of the tree's open work. An `<answer>` is whichever flag `[pm.arrive.…] answers` declares; it is recorded as a claim and never verified, a flag the state does not declare is refused naming the ones it does, and a bare move still writes and records `none` — which puts the grain on the census until somebody answers. **There is no transition table**: the unit is the state arrived at, never the pair, so `building -> planning` is an arrival at `planning` and asks `planning`'s question. `pm feature <done-state> <id> --review-record <path>` stamps `reviewed:` too; a path naming no file is refused whole. **`pm story` and `pm bug` take several ids** (each resolves before any write), and **`[pm] arrival_gates`** runs each declared make target ONCE per call, with `GRAIN=<id>[,<id>…]`, for the ids that moved into a todo or in_progress state — a failure is a `WARN arrival gate <target>` line with its last output line, and the exit stays 0. **A milestone's start under `version_at = "start"` names the version edit** R5 will demand (`next: set <file> version <held> -> <want>`) and never writes the file |
| `pm new`, `pm init`, `pm retire`, `pm set`, `pm rename` | The other writes: scaffold a grain, stand up a tree, retire a milestone, set one frontmatter field. **`pm set` writes the SHAPE `check pm` grades**: a list-shaped field (`depends_on`, `consumed_by`) lands as the inline list `["a", "b"]` whatever form the value arrived in, a shape the gate's parser cannot read is refused at exit 2 with nothing written, and `order` is refused by name pointing at `pm add`/`pm remove`, because it is a BLOCK list. **A milestone `branch:` under the agent-worktree prefix is refused** (exit 1, `[pm] agent_branch_prefix`, stock `feat/`) by `pm set` and by the milestone's first move into `in_progress`, naming `milestone/<version>-<slug>` instead — by name, such a branch reads as an agent's to every hook. `pm new <kind> <slug>` mints **`<kind-prefix>-<slug>`** — the same id `tools/dev/pm_migrate.py` mints, one path for both — and the parent argument writes the child's BINDING, never a piece of the id. A milestone's VERSION is the same shape of fact: `pm new milestone <slug> <name...> --version <ver>` stamps `version:` and leaves the id a slug, and a milestone with no version is backlog rather than a finding. `pm retire <id> [<summary...>]` keeps the milestone's id on the plan and files a `retire` row in `<roadmap>/ledger.jsonl` holding its version, name and summary, which `pm roadmap` prints, and every id it removed, so a `depends_on`/`consumed_by` naming one reads UNVERIFIABLE (retired) in `pm validate` and `check pm` rather than INVALID — each live grain that names one is printed as a `noticed:` line before the write, and never edited; `pm retire <id> --version <v> --name <name> [<summary...>]` backfills that row, marked `backfilled`, for a milestone no grain claims any more — one pruned before 0.5.0. `pm new bug <milestone> <slug> [<name...>]` stamps `name:`; without one the bug is still created and a `next:` line names the empty field. **`pm move` is gone (0.4.0)** — re-parenting is `pm set <id> feature <fid>`, and the id never changes. Setting a grain's own binding moves its `order` entry too: out of the old parent's, appended to the new one's, both printed; an empty value takes it out of the old one only. `pm rename <old> <new>` is the one path that still rewrites refs: the grain's `id:` and every inbound reference (`depends_on`, `consumed_by`, `reviewed`, `caused_by`, `caught_in`, `fix_milestone`, the bindings, every `order` entry), matched whole-token, in one pass — **whole or not at all**, and one reference it cannot rewrite means nothing is written |
| `pm config --seed` | Prints the seed `devkit.toml` this pinned version ships — every gate key commented at the default the code actually holds, and the two declarations spelled out with their arguments. Writes nothing. `init` serves a new repo once; this serves every bump after it |
| `pm status`, `pm list`, `pm get`, `pm validate`, `pm vocabulary`, `pm ready-for`, `pm roadmap` | Reads. `ready-for story\|feature\|milestone\|tag <id>` is a belt's entry condition as an exit code, naming every blocker and never a tally. **`story` is the inner loop's edge**: it asks the story belt's own `[story] steps` narrowed to what the registry declares decidable before the work, and NAMES every check it did not ask with why. There is no `adopt` rung — every adopt check is either the work the bump does or one that runs a command, so the derived condition is empty; the refusal says so rather than reading as a typo. Emits `rung.enter` where `[emit]` declares a sink, and nothing where a tree declares none |
| `pm ledger record\|show\|report` | The ledger — telemetry: one JSONL row per status flip, decision, dispatch, session and gate run, carrying tokens, tool calls and wall-clock. `report` adds them up per grain (spend, cost, how long something took) and never exits non-zero on a number; **name more than one milestone and it compares them** — every block gets one row per milestone and a `delta` row, `last - first`, marked `*` where the census under it moved, and `--json` is one joined document rather than a nested report per milestone to join by hand. `--help` names every block it prints with that block's columns in order. **Two homes**: one `ledger.jsonl` per milestone for rows naming a grain, and `<roadmap>/ledger.jsonl` for the rest — a retire, a session nobody could attribute. `show` and `report` both read both. What a run on this machine cost — `gate`, `test` and `verify` rows — lands beside it in the **gitignored** `<roadmap>/ledger.local.jsonl` (`pm init` and `init` add the ignore line), so a commit whose hook runs the gates leaves the tree clean; every reader of those rows (`verify --plan`, `report`) reads both files, committed history first. A row names its grain from `--grain` (the couriers pass **`GDK_LEDGER_GRAIN`** from their environment — **you export it**; nothing here does), else the prompt's `GDK-STAMP` line that `dispatch --grain` renders, else the one story in progress, else not at all. **One lane that built several grains is ONE row**: `ledger record --grain a,b,c` names each (one milestone), and `report` counts it once in every total and once per feature, and its `by grain` block shows the whole spend on each grain marked `*` — never a split |
| `pm ledger stamp start\|stop <grain> [--issue <id>]... [--agent <type>] [--tokens N] [--outcome O]` | Stamp your own work: one `stamp` row per edge in the grain's milestone ledger. `--issue` repeats and is a first-class field; `--agent` is refused off the agent roster (exit 2); `--tokens` and `--outcome` (`landed`, `superseded`, `stopped:<reason>`) go on `stop`. A stop with no open start, or a start over an open one, is refused (exit 1) and writes nothing. `ledger show <grain>` prints each start/stop pair as ONE line: start, stop, duration, issue, agent, tokens, outcome. `dispatch --grain` renders a `GDK-STAMP` line into the prompt, and `ledger record --from-transcript` copies grain and issue back from it, so a concurrent dispatch attributes itself with no exported variable. Every row the ledger appends also carries the checkout's `branch`, read from `.git/HEAD` as text |
| `pm decide <id> <title…>` | Appends one dated heading to that grain's decisions log, which sits beside it as `<stem>-decisions.md` |
| `pm new handoff <milestone-id>` | Mints the milestone's `handoff.md` from the template. Never auto-minted by `pm new milestone`, so an absent one is a signal `check pm` warns on; never clobbers what is there |
| `pm new reconcile <milestone-id>` | **The forward reconcile (#92).** A milestone that changes contracts the plans ahead were written against opts in with `reconcile: forward` in its frontmatter; absent is today's behaviour, any other value is exit 2 by name. This mints `<stem>-reconcile.md` beside it from the template — `## Contracts` (contract, what the plan said, what the code does, the file that states it), `## Forward grains updated` (grain ids) and `## Needs you` (forward features to add or drop, never added silently) — and never clobbers. The record is complete when its table has a row or the line `none changed`, every listed id resolves, and each milestone owning one has a `decisions.md` heading naming this milestone. `release` refuses on `forward-reconciled`, `ready-for milestone` names each gap, and `check pm` WARNs on an in-progress milestone with no record. `dispatch --reconcile <milestone-id>` renders the pass |
| `pm add <parent-id> <child-id> [--position N\|--before <id>\|--after <id>]` | **Binds AND sequences**, in one pair of writes: the child's own field names the parent, the parent's `order:` list says where. A child bound elsewhere moves: it leaves the old parent's `order:` as `pm set` makes it leave, and both edits print. Exactly `set` plus a list insert, and nothing else. Neither argument names a kind — each id resolves to the grain that declares one, and `[pm.contains]` says whether that pair is allowed, so ONE verb serves root → milestones, milestone → features and bugs, feature → stories. Bare, it appends. Off the mapping it refuses naming both kinds and writes nothing. `order` is OPTIONAL per container: a bound child nobody sequenced is a counted line, never a finding |
| `pm remove <parent-id> <child-id>` | Unbinds and unsequences together, as `pm set <id> <field> ""` does. Given a parent the child is not bound to, it takes out only that parent's DANGLING entry |
| `pm next` | The first entry in `order` that has not shipped, with the version its milestone declares |
| `pm install-skills` | Writes `.claude/rules/pm-execution.md`, `.claude/skills/pm-operations/SKILL.md`, `.claude/skills/handoff/SKILL.md`, and the planning pair `.claude/skills/writing-plans/SKILL.md` (plan only when needed) and `.claude/skills/executing-plans/SKILL.md` (file and continue), and `.claude/skills/run-the-sdlc/SKILL.md` (the orchestrator's loop, found by "use the sdlc, get to work"), each of those three with a `## Project config` block the install keeps |
| `check doc \| shell \| grain-shape \| pm \| repo-hygiene` | The gates. Pure text over git, markdown and shell; each prints a census of what it scanned and one verdict line. `check all` runs `[checks] all` (stock: `doc`, `shell`, `grain-shape`), and reuses a gate whose inputs — the files it reads, the git-ignored ones under its scope included, devkit.toml, the binaries it runs and their versions, this tool's own version and source — are byte-identical to a recorded PASS, and every path it asked about (a doc's cited path, ignored or outside the tree) is as that run saw it: it prints that run's whole output again, WARN lines included, its PASS line ending in `; reused — green at <ts> on inputs <short>`, and a `[check:cache]` line counting the reuses. A FAIL is never reused, `repo-hygiene` always runs, `check <gate>` alone always runs, and `check all --no-cache` runs every gate and reads and records nothing (`adopt` runs it so). A `make check` that reused a gate and passed files no `gate` cost row; one with a FAIL files it. `check <gate> --help` is that gate's contract. **A ready close ends the verdict line**: while a close stands open whose checks that need no run pass, and whose rung did not last record FAIL, `check pm`'s verdict line, and the `[CHECK]` line `make check` prints last, end `; N close(s) ready to run — <command>`, the ids named (a count, never the exit code); the rung itself runs at the close. |
| `gates-extra [--inputs \| --run <target>]` | Not a gate: prints `[gates] extra`, one make target per line, for `Makefile.devkit`'s `check`. `--inputs` prints the targets `[gates.inputs]` declares paths for; `--run <target>` runs one of them, or reuses its PASS while those paths, the makefiles and this tool are byte-identical |
| `verify --story \| --feature \| --milestone \| --plan \| --check` `[--no-cache]` | The three rungs, each the make target `[verify] <rung>` names — `story = "make unit"`, `feature = "make precommit"`, `milestone = "make milestone"`; a rung not declared is exit 2. A rung records its verdict against the tree state it ran on (HEAD plus a digest over every file git lists, tracked and untracked, a submodule's own checkout included) and a run over a byte-identical tree prints `[verify:cache] REUSED …` with that run's age, census, cost and what it did not re-measure, and exits with its code, instead of running the target; `--no-cache` runs it anyway. `[verify.inputs] story = ["src", "tests"]` keys a rung's state on the paths its target reads, so a doc edit does not re-run it. A rung can opt out of HEAD with `[verify.history_independent] story = true`; default is history-sensitive. The tool version, command, `uv.lock`, `devkit.toml`, Python runtime, and named `[verify] environment` values remain in the key. Every rung's state leaves out only what a belt writes (each grain's `status:` line and the ledger rows a belt files about its own run), so a batch of closes and `release` reuse one green run; `[verify] reuse_ignores_status = false` (stock `true`) keys every rung on every byte, for a project whose rung target reads statuses. Under that exclusion a `--milestone` reuse of a PASS first runs the static rung, `[verify] static` (stock `make check`), on the tree as it is now — the stock milestone target runs `check pm`, which grades statuses — and names it on the reuse line (`; static rung re-asked: make check exited 0`); a static rung that fails is exit 1 with its output. `--plan` prints all three with their measured cost and runs nothing; `--check` holds the three targets to the Makefile |
| `lesson record --grain <id> --rule <id> --source <path> "<text>"`, `lesson show [--grain <id> \| --rule <id>]` | **Capture, and only capture.** One append-only ledger row naming the grain it came from, the rule or check it is about, and the record it was derived from — routed by the grain like every other row. The row POINTS at its source and never restates it: a `--source` naming no file, or one outside this checkout, is refused and nothing lands. `show` prints one tab-separated row per lesson **in the order they were recorded**, columns named in `--help`; nothing is ranked, scored or weighed, and composition is the shell's job. The belts read them back where you stand — against the grain at a move, against a check's name beside that check's verdict |
| `close story <id> [<id> …]`, `close feature <id> [<id> …]`, `close feature <id> --review-record <path>` | The inner belts: checks, then the grain's status set to the first state of its kind's `done` list, or nothing. **`--review-record <path>` closes on a record that just landed, in one command**: `review-recorded` and `findings-landed` read `<path>`, and the one write stamps `reviewed:` with the status — a refused close stamps nothing. Close one by one, as each is ready; both take many ids, for grains ready together: `close story` runs the story rung and `committed` once, `close feature` runs the feature rung once, and each grain gets its own verdict and write; a grain already done is skipped. One close after another on the same commit reuses the rung's green run, because its state leaves out what a belt writes (`[verify] reuse_ignores_status`). A review record that grades several features writes one block per feature, and the line directly after each `verdict:` line is `feature: <id>`, which names the feature that block grades |
| `land <feature-id> --branch <branch> --commit <sha> --story <id>… --review-record <path> --gate-owner <name> --actor <name>` | **One frozen lane, one resumable close.** It verifies the feature, stories, milestone branch, review record, immutable worktree base marker and exact commit before merging. The actor must match the declared final-gate owner. It serializes land attempts with a nonblocking repository lock, merges with `--no-ff`, then runs the declared feature rung (`make sdlc ARGS='verify --feature'`). It records the pre-merge SHA as provenance, closes the named stories and feature through their belts, then runs `agent-worktree.sh done` last. The full integration gate runs at milestone end. A failed phase leaves the branch and worktree for repair. Phase state lives in Git's common directory, not the project tree; a retry resumes from the last completed phase. If a merge conflicts, resolve and commit the merge in the integration checkout (or abort it) before retrying. It does not commit unrelated PM edits |
| `changelog [<grain-id>] [--json]` | The consumer-visible sentence each grain earned, rendered. `changelog:` is a FIELD on every grain kind and this is the view: it collects `<grain-id>` and everything beneath it **in the `order:` each parent declares**, read whole across kinds so a milestone's interleaved bugs and features come out in the sequence the work shipped. `none` is an ANSWER — the grain earned no consumer-visible line — and prints nothing; an EMPTY field has answered nothing and `check pm` D12 names it. Columns in order: `id kind status changelog`. Writes no file: **`CHANGELOG.md` is retired (0.6.0)**, the way `ROADMAP.md` was in 0.3.0, and for the same reason — a hand-maintained second copy nothing could check against the tree. Redirect this if you want a file |
| `cite [--sites]` | **The rule-citation census: how many times each `rule <n>` is cited in your tree, and where.** The number a brief quotes, as a command's output — this package's own 0.6.0 brief asserted *"roughly 600 citations, rule 4 alone 194"* against a tree holding 1,107, and nobody could ask, so the wrong number was quoted forward through three milestones. The universe is `git ls-files` from the repo root, so a venv, a cache and a nested worktree are out without a roster to keep current; a tracked SYMLINK is skipped rather than followed, because it may leave the checkout. Columns in order: `rule citations files`, and with `--sites` one row per citation, `rule path line text`. **Rows on stdout, the census line on stderr**, so a pipe carries rows only; there is no `--rule` flag, because the rule is the first column and one rule is a grep. The grammar's whitespace may be a LINE BREAK, so a wrapped `hard rule 4` counts where a line-based grep loses it — six of this repo's own do. It reports and never grades: a rising count is what a rule being USED looks like, and a census of ZERO files is exit 1 naming what it scanned |
| `dispatch [--grain <id>] [--role <name>] [--mode serial\|parallel] [--reconcile <milestone-id>]` | The contract preamble a dispatched agent needs **before its first tool call**. What it RENDERS is read from the same declaration the verb it describes reads — the ladder from `[verify]`, the gate roster from `[checks]`, the state vocabulary from `[pm.states.*]` — so none of it is retyped and none can drift. `[dispatch] contracts` are named as reference, never copied — CLAUDE.md is named as already loaded — and the builder's git and scope rules are inlined, so a builder starts building instead of reading. A milestone's `mode:` (or `--mode`) picks the mode; parallel renders the agent-owned worktree loop on the milestone's `branch:`, ending at a committed branch the orchestrator merges. A declared path that resolves to nothing is exit 2. `[dispatch]` is a DECLARATION — nothing stands behind it and the reader refuses by name when it is absent. With `--grain` it also prints the `GDK-STAMP` line that attributes the dispatch's ledger rows and the `pm ledger record --grain <id>` line that files what it cost on return. `--reconcile <milestone-id>` renders a forward-reconcile pass: the milestone's range (its `branch:` against the mainline), the milestones after it in `releases.md` `order:`, and the record's path, sections and state. **It renders; it never spawns** — the record line is yours to run |
| `preflight` | **What this session can do, said before the first dispatch** — five tab-separated rows, columns in order `capability value meaning`: `subagent-resume` (`denied`, `allowed` or `unknown` — `SendMessage` in `permissions.deny`/`allow` of `.claude/settings.json` and `.claude/settings.local.json`; a launch flag is not readable as text, so neither file naming it is `unknown`, never `allowed`), `hooks` (`wired` or `not wired` — every `cc-*` hook under `tools/hooks/` registered, the missing ones named; the wiring half of `check hooks`, read and never run), `attribution` (how many stories are in progress — exactly 1 is what the ledger couriers' fallback attributes to; 0 and several attribute nothing without a dispatch's `GDK-STAMP` line or `GDK_LEDGER_GRAIN`), `subagent-channel` (the rendered `dispatch --grain <id>` preamble is the only channel to a subagent), and `repository` (`ok`, `bare` or `unknown` — `core.bare` in the checkout's common git config, read as text through a linked worktree's `.git` file → gitdir → `commondir`; `bare` is `core.bare = true` under a working tree, which fails every git command in it, and its meaning starts `git config core.bare false`). `install-hooks` ships `cc-session-preflight.sh`, which runs it at **SessionStart** and prints the rows into the session. It reports and never gates: exit 0 whenever it could read, `unknown` rows included; 2 on usage or config |
| `ship <version> "<line>"` | **A release with no milestone to close, in one verb.** Refuses a dirty tree, a mainline branch and an existing grain before writing; then mints `ms-release-<version>` at that version with the changelog line, scheduled last in `order`, bumps every `[release.version_files]` entry (`[pm] version_file` when none is declared), runs the `[verify] feature` rung, writes the grain done, and prints the commit, push and PR that are yours. The mainline's auto-tag tags it on merge. Measured: the release belt over two merged PRs cost seven minutes of invented records; this is the one minute of work |
| `release <version>` | The outer belt: tree clean, on the milestone branch, **the milestone itself and every closed grain answered the changelog question** (a sentence or `none` — it counted bullets in a file until 0.6.0, which passed a release of forty grains on one bullet), features done, findings dispositioned, version sites in sync, the forward-reconcile record complete (`forward-reconciled`; passes as not declared without `reconcile: forward`), gate green → the milestone's status. When the gate is the stock `make milestone` and `[verify] milestone` names the same target, the gate is asked through `verify --milestone`: a green run on the same tree state is reused, and the check line carries `; reused — green at <ts> on tree <short>`. That state leaves the `status:` lines out (`[verify] reuse_ignores_status`), so the reuse first asks the static rung (`[verify] static`, stock `make check`) with the milestone at `done`, and the line ends `; static rung re-asked: make check exited 0`; a static rung that fails fails the gate. **The gate is asked of the tree the belt leaves**: the milestone reads its `done` state while the gate runs and every byte is restored after, so a check only a closed milestone trips fails here, not at the next `make check`. Push, PR, merge and tag are printed as `next:` — never performed |
| `adopt <version>` | Checks only, nothing written: pin bumped, installables current — except the files `[adopt] ours` claims, which are named and counted on every run — config accepted, hooks armed, targets resolve, this package's `check all` and `pm validate` green — and `checks-pass` names every gate outside the roster and every `[gates] extra` target it did not run, beside the `[adopt.commands] checks-pass` key that would run them. Runs wherever the project tracks the bump (a milestone, a feature, a story, or nowhere); it sets no status and files no row of its own |
| `init` | Everything below, in order, plus the files nothing else writes |
| `install-ci` | `.github/workflows/`: `verify.yml` (arms the hooks, runs `make milestone` once per pull request into `main`, cancels a stale run, times out at 30 minutes; a `python` job runs the story rung on each interpreter past the floor at the same time, and a `matrix` job answers for all of them), `semver-gate.yml`, `auto-tag.yml`. `--ruleset branch\|tag` writes nothing: it prints ONE GitHub ruleset that holds the flow on the server as bare JSON — `branch` is `protected-main` (merge commits only, `verify` and `matrix` required), `tag` is `release-tags-immutable`. Apply it with `agentic-sdlc install-ci --ruleset branch \| gh api -X POST repos/<owner>/<repo>/rulesets --input -`; `--help` says why each is shaped as it is |
| `install-agents` | `.claude/agents/`: the four the loop dispatches — architect, developer, reviewer, tech-writer — each pointing at `make sdlc ARGS='dispatch …'` for the ladder, gate roster and vocabulary rather than carrying a hand-edited copy, with the judgement calls the tool cannot derive left yours after install, and a closing `## Project` section for your own role prose that `--force` keeps line for line |
| `install-hooks` | `tools/hooks/` (commit-pathspec, stop-gate, which holds the trunk session's stop once while `check pm` names a ready close — stock `CLOSE_READY="block"`, and `inform` only names it; write-confine, the git-allowlist and agent-isolation guards, two ledger couriers, the SessionStart preflight, `pre-push`, `prepare-commit-msg`), `tools/dev/agent-worktree.sh` and `tools/setup-hooks.sh`, which arms them. Names `.claude/settings.json` and prints its entries as `bash "$CLAUDE_PROJECT_DIR/tools/hooks/<hook>"`, so the block is the same on every machine and a hook still resolves when an agent's cwd moves; `--write-settings` writes that file when nothing is in the way, and never merges into or replaces one that exists. `check pm` and `adopt` read it and the gitignored `.claude/settings.local.json` both. The couriers take their tree from **`GDK_LEDGER_ROOT`** when the session cwd is not inside it |
| `install-gates` | `Makefile.devkit` (`help`, `pm`, `sdlc`, `check`, `precommit`, `milestone`) and `tools/dev/gdk_gate.sh`, the one-verdict-line gate library. `sdlc` reaches every verb at your pin, and it is how every command the CLI prints is spelled |
| `install-sdlc` | `docs/sdlc-protocol.md`, **rendered** from your `[story]` / `[feature]` / `[release]` / `[adopt]` check lists and the `done` state each belt writes |
| `version` | This package's version |

Every installer writes a file once. A destination that differs is refused by path (move it aside,
or `--force`); `--diff` prints what would change and writes nothing; a difference confined to a
file's project-config block — a hook's `project config` header, an agent brief's ```` ```text ````
fence — is reported as one and is current. **`--force` keeps what is yours**: that block is carried
into the new body line for line (a CRLF file comes back LF) and named on the file's line, with any
stock key the packaged block has and yours lacks; a file `[adopt] ours` claims is left alone and named,
by `pm install-skills` too. A claim is a destination spelled exactly, and one that matches none is
named on every run, `--diff` included. `install-* --force <path>` takes one destination, claimed or
not. The withdrawal report's floor is the pin; after the bump the pin
IS the running version and the report says it compared nothing — pass `--since <the version you are
leaving>`.

## Reading the output

**Exit codes are contract:** `0` pass · `1` findings, or a belt that wrote nothing · `2` usage or
config error. A `devkit.toml` mistake is always `2`, so CI never reads a typo as drift.

Every gate prints a **census** — how many files it scanned — before its verdict, and a zero-file
census FAILS rather than passing. A `  WARN  ` line is messaging, counted on the verdict line and
never in the exit code: `check pm` warns about a parent whose category disagrees with its
children's, and nothing moves a parent on a child's account. A `DRIFT` line is a finding.

```
[check:doc] FAIL — 2 unresolved claim(s), across 10 doc(s), 137 fenced line(s) skipped
  README.md:176  dead path: `tools/dev/checks/doctor.sh`
[check:pm]  FAIL — 1 status-drift violation(s) across 1 milestone(s), 3 feature(s), 9 story/ies; 1 warning(s)
  DRIFT  feature 0.1/the-thing is done w/o review record  [pm/roadmap/features/the-thing.md]
  WARN   feature 0.1/other is todo over 2 story/ies in done: …
```

The tool refuses facts about the **input** — a state in no category, a config value of the wrong
shape, a review record that is not there — at exit 2. It reports facts about the **tree** and
carries on; whether an open child should stop you is your question, and `--force` is the answer
on the record.

A belt prints one more line shape, and it decides nothing:

```
[feature] lesson: rule findings-landed — the record's ids drift from the tree (source: docs/reviews/alpha.md)
```

A `lesson` row you recorded surfaces where you are standing — the belt ENTERS on a grain it names,
a CHECK runs whose name it names, or a check's `pm ready-for` NAMES a blocker it names — with its
`source`, so you go to the record instead of trusting a paraphrase. It is **never a gate** (no
verdict and no exit code changes whether it exists or not) and **never a nag**: the scope is the
grain or the rule named, exactly, with no fuzzy matching and no ranking. Several matches all print,
in the order they were recorded. Each is also emitted on your `[emit]` sink as a `lesson.enter` or
`lesson.verdict` row carrying the recorded row verbatim.

## `devkit.toml`

At the repo root. Every GATE key has a stock default, so a repo with no file runs every gate
byte-identically to one declaring them. The two declarations have none, because they are yours:
`[pm.states.<kind>]`, which `pm init` writes and without which every work-moving verb is refused
by name, and `[verify]`, whose rungs name make targets only your Makefile has. `agentic-sdlc pm
config --seed` prints the whole seed as your pinned version ships it — every gate key commented at
its real default — which is what to read on a bump. These are the keys the tool reads:

```toml
[checks]
all = ["doc", "shell", "grain-shape", "pm"]   # the `check all` roster here

[doc]
scope     = ["CLAUDE.md", ".claude/rules/*.md", ".claude/agents/*.md"]
ephemeral = ["docs/reviews/"]                 # paths a doc may name and lose

[shell]
roots = ["tools"]
shellcheck_version = "0.11.0"                 # the one shellcheck `check shell` may run; the
                                              # stock verify.yml installs it. "" = any version

[repo_hygiene]
mainline  = "origin/main"
protected = "^(main|staging)$"

[gates]
extra = ["my-scan"]                           # MAKE TARGETS your own makefile defines, run by
                                              # `make check` after the devkit gates. A devkit GATE
                                              # name here is exit 2: gates go in [checks] all
inputs = { my-scan = ["tools/my-scan.sh", "src"] }  # reuse its PASS while these are unchanged;
                                              # name the target's own script. Stock: none

[pm]
roadmap_dir  = "pm/roadmap"
template_dir = "pm/templates"                 # `pm templates` copies the stock ones here
review_dir   = "docs/reviews"
contains = { roadmap = ["milestone"], milestone = ["feature", "bug"], feature = ["story"] }
                                              # which kinds `pm add` lets hold which. It
                                              # NARROWS the stock mapping — drop "bug" and
                                              # `pm add <ms> <bug>` refuses by name
checks = ["D1", "D2", "D4", "D5", "D6",       # the stock roster, DEFAULT_CHECKS; a declared
          "D11", "D12", "U1",                 # list REPLACES it, and `check pm` names any
          "V1", "V4", "V5", "V7"]             # stock rule it omits on a ROSTER line.
                                              # Opt-in: D9 D10 R1-R6 U2-U5.
                                              # U2: the ledger couriers are wired and the
                                              # tree holds no row at all. U3: [emit] is
                                              # declared and its sink has never been
                                              # written to. U4: the LAST hook-written row,
                                              # named with its age — recording that goes
                                              # nowhere is silent otherwise. U5: a grain
                                              # whose CURRENT state was arrived at with no
                                              # disposition, BY NAME — a bare move records
                                              # `answer: none` and is never refused
version_file    = "pyproject.toml"            # R5 and `version-sync`: where the version lives
version_pattern = '^version = "(.*)"$'
version_at      = "start"                     # R5: which entry in `order` the version file
                                              # must match — "start" (the last in_progress or
                                              # done, bump-at-START) or "ship" (the last done)
arrival_gates   = { story = ["dest-scan"] }  # per kind (story, bug): make targets a move runs
                                              # once per call with GRAIN set; a failure WARNs

[emit]                                        # where the conveyor's events are WRITTEN. Nothing
sink  = "ledger"                              # here is RUN: "ledger" (routed by the event's
                                              # grain), a path appended to as JSON lines, or "-"
                                              # for one JSON line per event on stdout
kinds = ["enter", "verdict", "leave"]         # which taps fire. A sink that cannot be written is
                                              # a WARNING naming it, never a changed exit code

[pm.states.story]                             # one table per kind: milestone, feature, story, bug
todo        = ["planning", "ready"]
in_progress = ["building"]
done        = ["done", "obe"]                 # a belt writes the FIRST of these

[pm.arrive.feature.building]                  # WHAT ARRIVING AT A STATE ASKS. Declared or absent;
ask     = "what is building this?"            #   never a transition table — the unit is the state
answers = ["--by me", "--by agent <type>"]    #   ARRIVED AT, so backwards is a move like any other
have    = { "tools/dev/agent-worktree.sh" = "isolation for parallel work" }

[pm.templates.feature]                        # one table per kind. `pm new` appends one `## `
extra_sections = ["Patterns"]                 #   heading per name to the template it reads, and
                                              #   skips one it has. Stock []: nothing to copy out

[pm.required.story]                           # one table per kind; nothing behind it. `pm new`
lines = ["Destination:", "Scenarios:"]        #   writes each prefix; a move into in_progress and
                                              #   `check pm` WARN on one missing or empty, and
                                              #   `close story`'s `required-lines` check refuses

[pm]
pressure    = true                            # the fork, the READY crossing and the open-work
                                              #   census, on stderr; off in one line
wip         = 0                               # YOUR work-in-progress limit; 0 declares none, and
                                              #   exceeding it is a reported line, never a refusal

[verify]
story     = "make unit"                       # the make TARGET each rung runs
feature   = "make precommit"
milestone = "make milestone"
static    = "make check"                      # asked before a milestone reuse (stock)

[release]                                     # also [adopt], [story], [feature]:
steps = ["tree-clean", "gate"]                #   the check list, when not the shipped default
skippable = ["review-recorded"]               #   which checks `--skip <check> "<why>"` may answer;
                                              #   STOCK IS EMPTY, so nothing is skippable until you say so
[release.commands]
gate = "make milestone"                       # the command a named check runs
prove-artifact = "uvx --index <url> agentic-sdlc@{version} --version"
[release.version_files]                       # a TABLE: one "<path>" = '<regex>' row per site
"pyproject.toml" = '^version = "(.*)"$'       # `version-sync` reads every row
"src/pkg/__init__.py" = "^__version__ = '(.*)'$"   # a second site, if you carry one
[adopt]
runner_targets = ["precommit", "milestone"]   # what `runner-targets-resolve` asks `make -n` about
ours = [".github/workflows/verify.yml"]        # installed files this project OWNS: not graded, named every run
```

`make pm ARGS=vocabulary` prints your declared states with their categories and the rule ids
`[pm] checks` may name — read it after a pin bump. A key this version no longer reads is named at
exit 2, never silently ignored.

## The release plan

A milestone declares the version it ships as, in one optional frontmatter field:

```yaml
id: stationary-enemies-spawn
version: "0.91.0"
```

**The id is a slug and the version is a fact.** A milestone with no `version:` is backlog — it has
not been proposed as a release at all, and that is never a finding.

The order they ship in is a DECISION, so it is declared rather than sorted —
`pm/roadmap/releases.md`, block-style frontmatter, one entry per line so a re-sequence diffs as a
move. **The entries are MILESTONE IDS**, like every other `order` in the tree, so re-versioning a
milestone never touches the plan and `pm rename` sweeps the entry with every other reference:

```yaml
---
id: roadmap
kind: roadmap
order:
  - "ms-stationary-enemies-spawn"
  - "ms-the-hud-lands"
---
```

**Nothing here parses, compares or increments a version string.** `"1.1.1"` and `"cow"` are equally
valid, and `0.90.3.2` — not semver, and the shape real trees reach for when work has to go between
two planned releases — orders fine, because "did it increase" is a POSITION in that list. A
comparator could not sort it, and sorting would re-couple the two facts `version:` just separated.

Authoring and scheduling are separate acts: `pm add <plan-id> <milestone-id>` puts a milestone on
the plan — the same verb that sequences a story under a feature, because the plan is a container
like any other — `pm next` says what is next, and `pm roadmap` prints the whole sequence. `release`
with no argument takes the current version from the plan, and refuses one that is out of order
naming both.

`R5` (opt-in) grades `[pm] version_file` against the current entry; `[pm] version_at` picks which
one — `"start"`, the last entry that has STARTED (`in_progress` or `done`; a `todo` milestone never
claims the file), or `"ship"`, the last that has shipped, for a project that bumps in the release
commit.

## Wiring

**Your Makefile is one line plus what is yours.** The pin lives in `uv.lock`, so a bump is
`uv add --dev agentic-sdlc==X.Y.Z` and a two-file diff:

```make
include Makefile.devkit

my-scan: ## a gate this project owns
	@bash tools/dev/checks/my_scan.sh
```

**The stock wiring never puts `agentic-sdlc` on PATH; `make` reaches it at your pin.**
`make sdlc ARGS='close story <id>'` runs any verb and `make pm ARGS='story building <id>'` any `pm`
verb, and every command the CLI prints for you to run is spelled that way. The recipe hands `ARGS`
to the CLI through the environment, never to a second shell, and the CLI splits it with shell
quoting: `make pm ARGS="new story <feature> <slug> The HUD reads f(host), then g"` works as typed,
an apostrophe is `\'`, and an unbalanced quote is exit 2 with one line. Free text with spaces is
still one argument in quotes, as the printed lines do:
`make pm ARGS='set <id> changelog '"'"'costs $5'"'"''`, and each `'` INSIDE that free text is typed `'"'"'"'"'"'"'"'"'` (it has to survive both shells). Through make, any nonzero exit is make's
2, and the verb's own code is the N in make's `Error N` line.

`Makefile.devkit` is devkit-owned: `help`, `pm`, `sdlc`, `check`, `precommit`, `milestone`. Your build and
test tiers arrive through `Makefile.tiers`, a file you (or a language kit) write beside it: it
defines the tier targets and declares which compositions they join with `GDK_PRECOMMIT_TIERS` and
`GDK_MILESTONE_TIERS`. With no tier file, `precommit` and `milestone` are `check` alone and say so.
`GDK_MILESTONE_SKIP` names milestone tiers another job runs: the stock `verify.yml` sets it to
`matrix` and runs the interpreters in a `python` job beside `verify`, and `milestone` prints a
`[TIERS] milestone skips [...]` line for what it left out.
Your own static gates join `check` through `[gates] extra`, never through a fork of the include.

**The two lists next to each other are two namespaces.** `[checks] all` names **gates this package
ships** (`agentic-sdlc check <name>`); `[gates] extra` names **make targets your own makefile
defines**. `make check` runs the first list, then the second, and a red gate does not stop the
next. With extras declared, its last line is the verdict over all of them —
`[CHECK] FAIL — <n> of <m> gate(s) failed: <name>, …` or `[CHECK] PASS — <m> gate(s)` — and it
exits the worst code any gate gave. A gate name in `[gates] extra` is
refused at exit 2 and told which key runs it, because make's own answer —
`No rule to make target 'budget'` — arrives three layers below the config that caused it.  <!-- doc-scan:allow -->
A target that `[gates.inputs]` keys on the paths it reads is reused while they are unchanged, the
way `check all` reuses a devkit gate; a target with no entry runs every time.

Every gate prints ONE verdict line naming its transcript under `.gate-reports/`; `VERBOSE=1`
streams it. The spot check belongs in a builder's loop; `make milestone` is the full gate, and the
installed CI runs it once; `check repo-hygiene` belongs at milestone close, because it fetches.
It fails on dirt outside `[pm] roadmap_dir`; dirt inside is one WARN line naming the commit to run.

## Northstar

> **A simple local Jira.** It creates the work, moves it, expresses what the states are and what
> the flow is — and it infers nothing. This tool is a reader/writer: it reads and writes the same
> things, in the same places, over and over again. It just echoes state back — it doesn't DO
> anything. *(Chris, 2026-09-05)*

The whole doctrine follows from that: a write touches only what it was asked to touch, a gate that
scans nothing says so, a malformed declaration is refused and a fact about the tree is reported,
and every footgun becomes a check instead of a sentence somebody has to remember.

## Development

This repo is its own first consumer: `Makefile` sets `DEVKIT` to `uv run -q agentic-sdlc` — the
working tree, installed on itself — and includes the same `Makefile.devkit` that `install-gates`
writes for everybody; `Makefile.tiers` adds the Python tiers. `make help` lists every target.

```sh
make check       # agentic-sdlc check all, on this tree
make unit        # the spot check: no subprocess, one process
make test        # both tiers on the floor interpreter — part of a batch proof
make milestone   # check + test + matrix + budget — the full gate CI runs once
```

`make matrix` runs the `-m "not shell"` slice on every interpreter in `PY_MATRIX` past `PY_FLOOR`, in
parallel, one log each; `test` has already run the whole suite on the floor. CI runs the same legs
as jobs of their own, so its `make milestone` skips `matrix`. `make fuzz` runs the seeded harnesses alone. Nothing here reads a path
outside its own checkout or names a project that consumes it: `tests/fixtures/` holds purpose-built
repos, hook payloads and transcripts, versioned with the code that reads them. The operating
contract for agents working here is [`SDLC.md`](SDLC.md); the hard rules are [`CLAUDE.md`](CLAUDE.md).

## Requirements

Python 3.11+ (stdlib only) and git. `shellcheck` optional — without it `check shell` soft-skips, unless `[shell] shellcheck_version` pins one.

## License

MIT — see [LICENSE](LICENSE).
