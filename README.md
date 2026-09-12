# agentic-sdlc

**A reader/writer over a PM tree.** The tree is markdown grains with YAML frontmatter under
`pm/roadmap/` — one flat pool per kind, `milestones/ features/ stories/ bugs/` — and the tool
reads and writes the same files, in the same places, over and over. It echoes state back; it does
not *do* anything.

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
- **A belt is its checks, then one write or a clean error.** `close story`, `close feature`,
  `release` and `adopt` each run a check list, print one line per check, and then write exactly
  one status — or write nothing and name every false check. `--force` writes anyway, and the
  ledger records which checks were false.

It does not run your tests, build your code, or decide what a status *means*. Your states, your
flow: `init` writes them into `devkit.toml`, every run reads them, and the tool has no opinion
about your words.

## Install

Pin a tag so every machine and CI runs identical code. `vX.Y.Z` below is the release you pin;
`git ls-remote --tags https://github.com/cdowin/agentic-sdlc` lists them:

```bash
uvx --from "git+https://github.com/cdowin/agentic-sdlc@vX.Y.Z" agentic-sdlc --version
```

Then, from inside a git repo:

```bash
uvx --from "git+https://github.com/cdowin/agentic-sdlc@vX.Y.Z" agentic-sdlc init
make help
```

`init` writes `devkit.toml` (with your flow declared), your two-line `Makefile`, `Makefile.devkit`,
the hook corpus (armed), the agent roster, the CI workflows, the rendered SDLC document, a
`CLAUDE.md` skeleton and an empty PM tree — in order, idempotently. The devkit-owned files are
overwritten by `--force`; `devkit.toml`, `Makefile`, `CLAUDE.md` and the tree are yours from the
first write and never touched again.

**Adopting a bump** is: bump `DEVKIT_VERSION` in your Makefile, then **take `Makefile.devkit`
first**, with the pinned form, because every other command below goes through the targets it
defines (a `Makefile.devkit` from before 0.8.0 has no `sdlc` target):
`uvx --from "git+https://github.com/cdowin/agentic-sdlc@vX.Y.Z" agentic-sdlc install-gates --force`.
Read the release notes (`agentic-sdlc changelog <milestone-id>` on the source tree, where
`agentic-sdlc pm roadmap` prints each release's version beside its milestone id — the changelog is a
`changelog:` field on each grain, not a file, since 0.6.0; a release before 0.6.0 has its notes only
in the retired file at its tag, and `git show v0.5.0:CHANGELOG.md` in a clone of this repo prints
v0.5.0 back to v0.2.0), run `make sdlc ARGS='install-agents --diff'` (and each other `install-*`) to
see what the release would change, take what you want, re-run `make pm ARGS=init` once, and
`make sdlc ARGS='adopt <version>'` to read the result.

## The ladder — one verb, one scope

Nothing runs a rung wider than the thing you changed.

| You are | Run |
|---|---|
| editing the PM tree or a doc | `make check` |
| editing code, inner loop | `make sdlc ARGS='verify --story'` — the make target `[verify] story` names, e.g. `make unit` |
| about to commit | `make precommit` — `check` + your `GDK_PRECOMMIT_TIERS` |
| closing a story | `make sdlc ARGS='close story <id>'` |
| closing a feature | `make sdlc ARGS='close feature <id>'` — its check runs what `[verify] feature` names |
| closing a milestone | `make sdlc ARGS='release <version>'` — its `gate` check runs `make milestone` |
| bumping the devkit pin | `make sdlc ARGS='adopt <version>'` — the adoption, never your own gates |

`make sdlc ARGS='verify --plan'` prints the three `verify` rungs with the cost each one last took, read
from your ledger. Ask it instead of guessing.

A rung also RECORDS its verdict, against the state of the tree it ran on — so asking the same rung
about the same tree twice costs one gate run and one read, and `close feature` straight after a
green `verify --feature` is a read. Closing seven features is still seven runs: a belt writes the
grain's `status:` line, which is a byte in the state the next close computes. The reuse is always
printed, naming the run it came from, its age and what it did NOT re-measure; one byte anywhere in
the working tree, tracked or untracked, and it re-runs. `--no-cache` re-runs unconditionally.

## Quickstart

```bash
agentic-sdlc pm new milestone first-light "First light" --version 0.1  # ms-first-light
agentic-sdlc pm new feature ms-0.1 the-thing "The thing"   # mints ft-the-thing
agentic-sdlc pm new story ft-the-thing works "it works"    # mints st-works
agentic-sdlc pm story building st-works                # one line written, one ledger row
agentic-sdlc pm add ft-the-thing st-works              # bind it, and sequence it there
agentic-sdlc pm status                                 # the tree, in its declared order
make check                                             # check all: doc + shell + pm + …
agentic-sdlc close story 0.1/the-thing/works           # its checks, then `done` — or an error
```

A belt's output is one line per check, then one line saying what happened:

```
[story] ok: story-exists — pm/roadmap/stories/works.md
[story] ok: story-verified — `make sdlc ARGS='verify --story'` exited 0 — the story rung [verify] names
[story] error: committed: 2 uncommitted path(s) outside pm/roadmap/: src/a.py, src/b.py — commit by explicit pathspec; this belt never commits
[story] error: evidence-written: … carries no `done:` line — step 6 of pm-execution.md
[story] error — 2 check(s) false; nothing written
```

Fix what it named and run it again; every check is a read of the tree, so nothing is carried
between runs. All true → the one write and `next:` lines naming what is yours to do.

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
| `pm <kind> <status> <id> [<answer>…]` | **One ARRIVAL.** Writes one `status:` line — any state in `[pm.states.<kind>]`, anything else is exit 2 — plus a `status` row, a `disposition` row and a `rung.leave` event. On **stderr**, all derived and never a refusal: `next:` (the belt that closes it and the checks it will ask), `have:` (the installed files `[pm.arrive.<kind>.<state>] have` binds to this state — a declared one that is ABSENT is a named line), the FORK that state declares with **both answers already typed as commands you can paste**, `ready:` when the write made a PARENT ready, and one census of the tree's open work. An `<answer>` is whichever flag `[pm.arrive.…] answers` declares; it is recorded as a claim and never verified, a flag the state does not declare is refused naming the ones it does, and a bare move still writes and records `none` — which puts the grain on the census until somebody answers. **There is no transition table**: the unit is the state arrived at, never the pair, so `building -> planning` is an arrival at `planning` and asks `planning`'s question. `pm feature <done-state> <id> --review-record <path>` stamps `reviewed:` too; a path naming no file is refused whole |
| `pm new`, `pm init`, `pm retire`, `pm set`, `pm rename` | The other writes: scaffold a grain, stand up a tree, retire a milestone, set one frontmatter field. **`pm set` writes the SHAPE `check pm` grades**: a list-shaped field (`depends_on`, `consumed_by`) lands as the inline list `["a", "b"]` whatever form the value arrived in, a shape the gate's parser cannot read is refused at exit 2 with nothing written, and `order` is refused by name pointing at `pm add`/`pm remove`, because it is a BLOCK list. `pm new <kind> <slug>` mints **`<kind-prefix>-<slug>`** — the same id `tools/dev/pm_migrate.py` mints, one path for both — and the parent argument writes the child's BINDING, never a piece of the id. A milestone's VERSION is the same shape of fact: `pm new milestone <slug> <name...> --version <ver>` stamps `version:` and leaves the id a slug, and a milestone with no version is backlog rather than a finding. `pm retire <id> [<summary...>]` keeps the milestone's id on the plan and files a `retire` row in `<roadmap>/ledger.jsonl` holding its version, name and summary, which `pm roadmap` prints; `pm retire <id> --version <v> --name <name> [<summary...>]` backfills that row, marked `backfilled`, for a milestone no grain claims any more — one pruned before 0.5.0. `pm new bug <milestone> <slug> [<name...>]` stamps `name:`; without one the bug is still created and a `next:` line names the empty field. **`pm move` is gone (0.4.0)** — re-parenting is `pm set <id> feature <fid>`, one line, and the id never changes. `pm rename <old> <new>` is the one path that still rewrites refs: the grain's `id:` and every inbound reference (`depends_on`, `consumed_by`, `reviewed`, `caused_by`, `caught_in`, `fix_milestone`, the bindings, every `order` entry), matched whole-token, in one pass — **whole or not at all**, and one reference it cannot rewrite means nothing is written |
| `pm config --seed` | Prints the seed `devkit.toml` this pinned version ships — every gate key commented at the default the code actually holds, and the two declarations spelled out with their arguments. Writes nothing. `init` serves a new repo once; this serves every bump after it |
| `pm status`, `pm list`, `pm get`, `pm validate`, `pm vocabulary`, `pm ready-for`, `pm roadmap` | Reads. `ready-for story\|feature\|milestone\|tag <id>` is a belt's entry condition as an exit code, naming every blocker and never a tally. **`story` is the inner loop's edge**: it asks the story belt's own `[story] steps` narrowed to what the registry declares decidable before the work, and NAMES every check it did not ask with why. There is no `adopt` rung — every adopt check is either the work the bump does or one that runs a command, so the derived condition is empty; the refusal says so rather than reading as a typo. Emits `rung.enter` where `[emit]` declares a sink, and nothing where a tree declares none |
| `pm ledger record\|show\|report` | The ledger — telemetry: one JSONL row per status flip, decision, dispatch, session and gate run, carrying tokens, tool calls and wall-clock. `report` adds them up per grain (spend, cost, how long something took) and never exits non-zero on a number; **name more than one milestone and it compares them** — every block gets one row per milestone and a `delta` row, `last - first`, marked `*` where the census under it moved, and `--json` is one joined document rather than a nested report per milestone to join by hand. `--help` names every block it prints with that block's columns in order. **Two homes**: one `ledger.jsonl` per milestone for rows naming a grain, and `<roadmap>/ledger.jsonl` for the rest — `gate` and `test` rows, and a session nobody could attribute. `show` and `report` both read both. A row names its grain from `--grain` (the couriers pass **`GDK_LEDGER_GRAIN`** from their environment — **you export it**; nothing here does), else from the one story in progress, else not at all |
| `pm ledger stamp start\|stop <grain> [--issue <id>]... [--agent <type>] [--tokens N] [--outcome O]` | Stamp your own work: one `stamp` row per edge in the grain's milestone ledger. `--issue` repeats and is a first-class field; `--agent` is refused off the agent roster (exit 2); `--tokens` and `--outcome` (`landed`, `superseded`, `stopped:<reason>`) go on `stop`. A stop with no open start, or a start over an open one, is refused (exit 1) and writes nothing. `ledger show <grain>` prints each start/stop pair as ONE line: start, stop, duration, issue, agent, tokens, outcome. `dispatch --grain` renders a `GDK-STAMP` line into the prompt, and `ledger record --from-transcript` copies grain and issue back from it, so a concurrent dispatch attributes itself with no exported variable. Every row the ledger appends also carries the checkout's `branch`, read from `.git/HEAD` as text |
| `pm decide <id> <title…>` | Appends one dated heading to that grain's decisions log, which sits beside it as `<stem>-decisions.md` |
| `pm new handoff <milestone-id>` | Mints the milestone's `handoff.md` from the template. Never auto-minted by `pm new milestone`, so an absent one is a signal `check pm` warns on; never clobbers what is there |
| `pm add <parent-id> <child-id> [--position N\|--before <id>\|--after <id>]` | **Binds AND sequences**, in one pair of writes: the child's own field names the parent, the parent's `order:` list says where. Exactly `set` plus a list insert, and nothing else. Neither argument names a kind — each id resolves to the grain that declares one, and `[pm.contains]` says whether that pair is allowed, so ONE verb serves root → milestones, milestone → features and bugs, feature → stories. Bare, it appends. Off the mapping it refuses naming both kinds and writes nothing. `order` is OPTIONAL per container: a bound child nobody sequenced is a counted line, never a finding |
| `pm remove <parent-id> <child-id>` | Unbinds and unsequences together. `pm set <id> <field> ""` still unbinds alone — which leaves the parent sequencing a child it no longer holds, the DANGLING entry `check pm` reports |
| `pm next` | The first entry in `order` that has not shipped, with the version its milestone declares |
| `pm install-skills` | Writes `.claude/rules/pm-execution.md`, `.claude/skills/pm-operations/SKILL.md`, `.claude/skills/handoff/SKILL.md`, and the planning pair `.claude/skills/writing-plans/SKILL.md` (plan only when needed) and `.claude/skills/executing-plans/SKILL.md` (file and continue), each of those two with a `## Project config` block the install keeps |
| `check doc \| shell \| grain-shape \| pm \| hooks \| repo-hygiene \| budget` | The gates. Pure text over git, markdown and shell; each prints a census of what it scanned and one verdict line. `check all` runs `[checks] all` (stock: `doc`, `shell`, `grain-shape`). `check <gate> --help` is that gate's contract |
| `gates-extra` | Not a gate: prints `[gates] extra`, one make target per line, for `Makefile.devkit`'s `check` |
| `verify --story \| --feature \| --milestone \| --plan \| --check` `[--no-cache]` | The three rungs, each the make target `[verify] <rung>` names — `story = "make unit"`, `feature = "make test"`, `milestone = "make milestone"`; a rung not declared is exit 2. A rung records its verdict against the tree state it ran on (HEAD plus a digest over every file git lists, tracked and untracked, a submodule's own checkout included) and a run over a byte-identical tree prints `[verify:cache] REUSED …` with that run's age, census, cost and what it did not re-measure, and exits with its code, instead of running the target; `--no-cache` runs it anyway. `--plan` prints all three with their measured cost and runs nothing; `--check` holds the three targets to the Makefile |
| `lesson record --grain <id> --rule <id> --source <path> "<text>"`, `lesson show [--grain <id> \| --rule <id>]` | **Capture, and only capture.** One append-only ledger row naming the grain it came from, the rule or check it is about, and the record it was derived from — routed by the grain like every other row. The row POINTS at its source and never restates it: a `--source` naming no file, or one outside this checkout, is refused and nothing lands. `show` prints one tab-separated row per lesson **in the order they were recorded**, columns named in `--help`; nothing is ranked, scored or weighed, and composition is the shell's job. The belts read them back where you stand — against the grain at a move, against a check's name beside that check's verdict |
| `close story <id>`, `close feature <id>` | The inner belts: checks, then the grain's status set to the first state of its kind's `done` list, or nothing |
| `changelog [<grain-id>] [--json]` | The consumer-visible sentence each grain earned, rendered. `changelog:` is a FIELD on every grain kind and this is the view: it collects `<grain-id>` and everything beneath it **in the `order:` each parent declares**, read whole across kinds so a milestone's interleaved bugs and features come out in the sequence the work shipped. `none` is an ANSWER — the grain earned no consumer-visible line — and prints nothing; an EMPTY field has answered nothing and `check pm` D12 names it. Columns in order: `id kind status changelog`. Writes no file: **`CHANGELOG.md` is retired (0.6.0)**, the way `ROADMAP.md` was in 0.3.0, and for the same reason — a hand-maintained second copy nothing could check against the tree. Redirect this if you want a file |
| `cite [--sites]` | **The rule-citation census: how many times each `rule <n>` is cited in your tree, and where.** The number a brief quotes, as a command's output — this package's own 0.6.0 brief asserted *"roughly 600 citations, rule 4 alone 194"* against a tree holding 1,107, and nobody could ask, so the wrong number was quoted forward through three milestones. The universe is `git ls-files` from the repo root, so a venv, a cache and a nested worktree are out without a roster to keep current; a tracked SYMLINK is skipped rather than followed, because it may leave the checkout. Columns in order: `rule citations files`, and with `--sites` one row per citation, `rule path line text`. **Rows on stdout, the census line on stderr**, so a pipe carries rows only; there is no `--rule` flag, because the rule is the first column and one rule is a grep. The grammar's whitespace may be a LINE BREAK, so a wrapped `hard rule 4` counts where a line-based grep loses it — six of this repo's own do. It reports and never grades: a rising count is what a rule being USED looks like, and a census of ZERO files is exit 1 naming what it scanned |
| `dispatch [--grain <id>] [--role <name>] [--mode serial\|parallel]` | The contract preamble a dispatched agent needs **before its first tool call**. What it RENDERS is read from the same declaration the verb it describes reads — the ladder from `[verify]`, the gate roster from `[checks]`, the state vocabulary from `[pm.states.*]` — so none of it is retyped and none can drift. `[dispatch] contracts` are named as reference, never copied — CLAUDE.md is named as already loaded — and the builder's git and scope rules are inlined, so a builder starts building instead of reading. A milestone's `mode:` (or `--mode`) picks the mode; parallel renders the agent-owned worktree loop on the milestone's `branch:`. A declared path that resolves to nothing is exit 2. `[dispatch]` is a DECLARATION — nothing stands behind it and the reader refuses by name when it is absent. With `--grain` it also prints the `GDK_LEDGER_GRAIN` export and the `pm ledger record --grain <id>` line that files what the dispatch cost, because the moment a dispatch begins is the only moment anyone knows the grain. **It renders; it never spawns** — the two commands are yours to run |
| `release <version>` | The outer belt: tree clean, on the milestone branch, **the milestone itself and every closed grain answered the changelog question** (a sentence or `none` — it counted bullets in a file until 0.6.0, which passed a release of forty grains on one bullet), features done, findings dispositioned, version sites in sync, gate green → the milestone's status. Push, PR, merge and tag are printed as `next:` — never performed |
| `adopt <version>` | Checks only, nothing written: pin bumped, installables current — except the files `[adopt] ours` claims, which are named and counted on every run — config accepted, hooks armed, targets resolve, this package's `check all` and `pm validate` green — and `checks-pass` names every gate outside the roster and every `[gates] extra` target it did not run, beside the `[adopt.commands] checks-pass` key that would run them. Runs wherever the project tracks the bump (a milestone, a feature, a story, or nowhere); it sets no status and files no row of its own |
| `init` | Everything below, in order, plus the files nothing else writes |
| `install-ci` | `.github/workflows/`: `verify.yml` (arms the hooks, runs `make milestone`), `semver-gate.yml`, `auto-tag.yml` |
| `install-agents` | `.claude/agents/`: the review/build contract (`verification-reviewer.md`, `verification-builder.md`) and the base roster — architect, po, developer, reviewer, milestone-reviewer, simplifier, test-writer, tech-writer, doc-hygiene, pm-operator — each pointing at `make sdlc ARGS='dispatch …'` for the ladder, gate roster and vocabulary rather than carrying a hand-edited copy, with the judgement calls the tool cannot derive left yours after install |
| `install-hooks` | `tools/hooks/` (commit-pathspec, stop-gate, write-confine, two ledger couriers, `pre-push`, `prepare-commit-msg`), `tools/dev/agent-worktree.sh` and `tools/setup-hooks.sh`, which arms them. Names `.claude/settings.json` and prints its entries with ABSOLUTE, shell-quoted script paths; `--write-settings` writes that file when nothing is in the way, and never merges into or replaces one that exists. An absolute path names one machine, so a shared checkout puts the block in the gitignored `.claude/settings.local.json` — `check pm` and `adopt` read both. The couriers take their tree from **`GDK_LEDGER_ROOT`** when the session cwd is not inside it |
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

[repo_hygiene]
mainline  = "origin/main"
protected = "^(main|staging)$"

[gates]
extra = ["my-scan"]                           # MAKE TARGETS your own makefile defines, run by
                                              # `make check` after the devkit gates. A devkit GATE
                                              # name here is exit 2: gates go in [checks] all

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

[pm]
pressure    = true                            # the fork, the READY crossing and the open-work
                                              #   census, on stderr; off in one line
wip         = 0                               # YOUR work-in-progress limit; 0 declares none, and
                                              #   exceeding it is a reported line, never a refusal

[tests]
budget = { unit = 20, integration = 130 }     # `check budget`: seconds per tier, from the ledger
cases  = { unit = 1250, integration = 800 }   # and a size ceiling per tier

[verify]
story     = "make unit"                       # the make TARGET each rung runs
feature   = "make test"
milestone = "make milestone"

[release]                                     # also [adopt], [story], [feature]:
steps = ["tree-clean", "gate"]                #   the check list, when not the shipped default
skippable = ["review-recorded"]               #   which checks `--skip <check> "<why>"` may answer;
                                              #   STOCK IS EMPTY, so nothing is skippable until you say so
[release.commands]
gate = "make milestone"                       # the command a named check runs
prove-artifact = "uvx --from git+…@v{version} agentic-sdlc --version"
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

**Your Makefile is two lines plus what is yours.** The pin lives in your file, so a bump is a
one-line diff:

```make
DEVKIT_VERSION := vX.Y.Z
include Makefile.devkit

my-scan: ## a gate this project owns
	@bash tools/dev/checks/my_scan.sh
```

**The stock wiring never puts `agentic-sdlc` on PATH; `make` reaches it at your pin.**
`make sdlc ARGS='close story <id>'` runs any verb and `make pm ARGS='story building <id>'` any `pm`
verb, and every command the CLI prints for you to run is spelled that way. `ARGS` is parsed by a
second shell, so put free text in single quotes, as the printed lines do:
`make pm ARGS='set <id> changelog '"'"'costs $5'"'"''`, and each `'` INSIDE that free text is typed `'"'"'"'"'"'"'"'"'` (it has to survive both shells). Through make, any nonzero exit is make's
2, and the verb's own code is the N in make's `Error N` line.

`Makefile.devkit` is devkit-owned: `help`, `pm`, `sdlc`, `check`, `precommit`, `milestone`. Your build and
test tiers arrive through `Makefile.tiers`, a file you (or a language kit) write beside it: it
defines the tier targets and declares which compositions they join with `GDK_PRECOMMIT_TIERS` and
`GDK_MILESTONE_TIERS`. With no tier file, `precommit` and `milestone` are `check` alone and say so.
Your own static gates join `check` through `[gates] extra`, never through a fork of the include.

**The two lists next to each other are two namespaces.** `[checks] all` names **gates this package
ships** (`agentic-sdlc check <name>`); `[gates] extra` names **make targets your own makefile
defines**. `make check` runs the first list, then the second. A gate name in `[gates] extra` is
refused at exit 2 and told which key runs it, because make's own answer —
`No rule to make target 'budget'` — arrives three layers below the config that caused it.  <!-- doc-scan:allow -->

Every gate prints ONE verdict line naming its transcript under `.gate-reports/`; `VERBOSE=1`
streams it. `make precommit` belongs in your per-change loop; `make milestone` is the full gate and
what the installed CI runs; `check repo-hygiene` belongs at milestone close, because it fetches.

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
make unit        # the inner loop: no subprocess, one process
make precommit   # check + unit — the per-change gate
make test        # both tiers on the floor interpreter — what a feature close runs
make milestone   # check + matrix + budget — the full gate, and what CI runs
```

`make matrix` runs the whole suite on `PY_FLOOR` and the `-m "not shell"` slice on every other
interpreter in `PY_MATRIX`; `make fuzz` runs the seeded harnesses alone. Nothing here reads a path
outside its own checkout or names a project that consumes it: `tests/fixtures/` holds purpose-built
repos, hook payloads and transcripts, versioned with the code that reads them. The operating
contract for agents working here is [`SDLC.md`](SDLC.md); the hard rules are [`CLAUDE.md`](CLAUDE.md).

## Requirements

Python 3.11+ (stdlib only) and git. `shellcheck` optional — without it `check shell` soft-skips.

## License

MIT — see [LICENSE](LICENSE).
