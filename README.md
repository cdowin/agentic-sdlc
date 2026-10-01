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
4. **The integrator runs `make sdlc ARGS='integrate <slug>...'` once per batch**: it merges each lane with
   `--no-ff`, runs one proof over the batch, fast-forwards the milestone branch and writes `done`
   on each merged story.
5. **`release <version>`** writes the milestone `done`. CI runs the full tiers once, on the
   release PR.

**Validate once:** a PASS is a receipt keyed on the tree, and nothing re-runs a gate on a tree
that has one. Hooks refuse only acts that cannot be undone or that harm another tree; they never
run a gate. [`SDLC.md`](SDLC.md) is the whole loop. The
[DeepWiki overview](https://deepwiki.com/cdowin/agentic-sdlc/1-overview) is a generated map of
the code; it can lag the tree.

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
the hook corpus (armed), the agent roster, the CI workflows, a `CLAUDE.md` skeleton and an empty
PM tree — in order, idempotently. The devkit-owned files are overwritten by `--force`;
`devkit.toml`, `Makefile`, `pyproject.toml`, `CLAUDE.md` and the tree are yours from the first
write and never touched again. `make` runs `.venv/bin/agentic-sdlc`, runs `uv sync --frozen` first
when it is missing or older than `uv.lock`, and exits 2 with the `uv add` line when `uv.lock` does
not name the kit.

**Adopting a bump:** `uv add --dev agentic-sdlc==X.Y.Z` (or merge a Renovate/Dependabot PR), then
take `Makefile.devkit` first with `uv run agentic-sdlc install-gates --force`, because every other
command goes through its targets. Read the release notes (`agentic-sdlc changelog <milestone-id>`
on the source tree; `agentic-sdlc pm roadmap` maps versions to milestone ids). Run
`make sdlc ARGS='install-agents --diff'` and each other `install-*` to see what changed, take what
you want, re-run `make pm ARGS=init` once, and run `make sdlc ARGS='adopt <version>'` to read the
result.

## The ladder — one verb, one scope

Nothing runs a rung wider than the thing you changed, and nothing proves the same tree twice.

| Who | When | Run |
|---|---|---|
| anyone | after a PM-tree or doc edit | `make check` |
| builder | after each edit, and before the commit | the spot check, `[verify] spot`: lint plus one unit slice, under 30 s |
| integrator | once per batch of lanes | `make sdlc ARGS='integrate <slug>...'`: merge, ONE proof, `done` on each merged story |
| architect | the milestone | `make sdlc ARGS='release <version>'`: status and version sites; CI runs `make milestone` once, on the release PR |
| anyone | bumping the devkit pin | `make sdlc ARGS='adopt <version>'` — the adoption, never your own gates |

`make sdlc ARGS='verify --plan'` prints each `verify` rung with the cost it last took, read from
your ledger. Ask it instead of guessing.

**A PASS is a receipt.** A rung records its verdict against the state of the tree it ran on, so
asking the same rung about the same tree twice costs one run and one read. The state leaves out
each grain's `status:` line and the ledger rows, so a status write after a green run is a read. A
project whose rung target READS statuses sets `[verify] reuse_ignores_status = false`. The reuse
is always printed, naming the run it came from and its age; one other byte in the working tree,
tracked or untracked, and it re-runs. `--no-cache` re-runs unconditionally.

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

`release` prints one line per check — `ok: <check> — <detail>` or `error: <check>: <why>` — then
the one write and `next:` lines, or nothing written. Fix what it named and run it again; every
check is a read of the tree, so nothing is carried between runs.

## Verbs

`agentic-sdlc --help` and `agentic-sdlc pm --help` are the live rosters, and each verb's `--help`
is its contract. This table is the index.

| Verb | Reads / writes |
|---|---|
| `pm <kind> <status> <id>` | **One status write**: one `status:` line, any state in `[pm.states.<kind>]`, and one ledger row when the grain moved. A close is a write into the `done` category; `pm story` and `pm bug` take several ids |
| `pm new`, `pm init`, `pm set`, `pm rename`, `pm retire` | The other writes. `pm new <kind>` mints `<kind-prefix>-<slug>` bound to its parent; `pm set` writes one frontmatter field; `pm rename` rewrites an id and every reference to it, whole or not at all; `pm retire` removes a milestone's grains and keeps one `retire` row |
| `pm add`, `pm remove` | Bind and sequence a child under a parent, or undo both. `[pm] contains` says which kinds hold which |
| `pm status`, `pm list`, `pm get`, `pm validate`, `pm vocabulary`, `pm next`, `pm roadmap` | Reads. Each names its columns in `--help`, so a pipe can filter them |
| `pm config --seed`, `pm templates` | Print the seed `devkit.toml` this pin ships; copy the grain templates out to edit |
| `pm ledger record\|show\|report\|stamp` | The ledger: one JSONL row per status write, decision, dispatch, session and gate run. `report` adds them up per grain and compares milestones |
| `pm decide <id> <title…>` | Appends one dated heading to the grain's `<stem>-decisions.md` |
| `pm new handoff <milestone-id>`, `pm new reconcile <milestone-id>` | Mint the milestone's handoff, or its forward-reconcile record. `check pm` warns when one is due and absent |
| `pm install-skills` | Writes `.claude/rules/pm-execution.md` and the skills under `.claude/skills/` |
| `integrate <slug>...` | Merges each lane with `--no-ff` into one batch worktree (after `[integrate] prepare`, once, when declared), runs `[integrate] per_merge` after each merge and `[integrate] proof` once, then writes `done` on each merged story and fast-forwards the base. On red it names the lane and closes nothing; run it again to resume |
| `verify --spot\|--milestone\|--plan\|--check` | Runs the make target `[verify] <rung>` names, and reuses a recorded verdict on a byte-identical tree; a miss prints a `changed:`, `added:` or `removed:` line per input that moved since the last PASS. `--plan` prints each rung's last cost; `--check` holds the targets to the Makefile |
| `check doc \| shell \| grain-shape \| pm \| repo-hygiene` | The gates: pure text, a census, one verdict line. `check all` runs `[checks] all` and reuses a PASS while its inputs are unchanged |
| `gates-extra [--inputs \| --run <target>]` | Prints `[gates] extra`, one make target per line, for `Makefile.devkit`'s `check` |
| `release <version>` | Five checks, then the milestone's first `done` state, or nothing. Runs no gate; `--force` writes anyway and files a `deviation` row. Push, PR, merge and tag are printed as `next:` |
| `adopt <version>` | Three checks after a pin bump, and nothing written: pin, installables, config. It also prints a `not taken:` note for an installer with no file on disk (exit unchanged), an `absent:` line per missing file of a taken installer, an `unarmed:` line for hooks `tools/setup-hooks.sh` never armed as `git config` reads them, and a finding per `[dispatch]` contract that is missing or outside `[doc]` scope. `[adopt] ours` names the installed files the project owns |
| `dispatch [--grain <id>] [--role <name>] [--reconcile <milestone-id>]` | Renders the contract preamble a dispatched agent needs, read from `devkit.toml`. It spawns nothing and refuses no dispatch |
| `changelog [<grain-id>] [--json]` | Renders each grain's `changelog:` field in `order:`. There is no `CHANGELOG.md` (retired in 0.6.0) |
| `init` | Everything below, in order, plus the files nothing else writes. Its last lines are the loop, in the tree's declared states |
| `install-ci` | `.github/workflows/`: `verify.yml` (runs `make milestone` once per pull request into `main`), `semver-gate.yml`, `auto-tag.yml`. `--ruleset branch\|tag` prints one GitHub ruleset as JSON |
| `install-agents` | `.claude/agents/`: architect, developer, reviewer, tech-writer. A closing `## Project` section is yours, and `--force` keeps it |
| `install-hooks` | `tools/hooks/` (`cc-git-denylist`, `cc-write-confine`, two ledger couriers, `pre-push`, `prepare-commit-msg`), `tools/dev/agent-worktree.sh` and `tools/setup-hooks.sh`, which arms them. `--write-settings` writes `.claude/settings.json` when none exists |
| `install-gates` | `Makefile.devkit` (`help`, `pm`, `sdlc`, `check`, `precommit`, `milestone`) and `tools/dev/gdk_gate.sh`, the one-verdict-line gate library |
| `version` | This package's version |

Every installer writes a file once. A destination that differs is refused by path (move it aside,
or `--force`); `--diff` prints what would change and writes nothing; a difference confined to a
file's project-config block — a hook's `project config` header, an agent brief's ```` ```text ````
fence — is reported as one and is current. **`--force` keeps what is yours**: that block is carried
into the new body line for line, and a file `[adopt] ours` claims is left alone and named, by
`pm install-skills` too. `install-* --force <path>` takes one destination, claimed or not.

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
  DRIFT  feature ft-the-thing is 'done' (done) but story st-works is 'building' (in_progress) — … (D11)  [pm/roadmap/stories/works.md]
  WARN   feature ft-other is todo over 2 story/ies in done: …
```

The tool refuses facts about the **input** — a state in no category, a config value of the wrong
shape, a path that is not there — at exit 2. It reports facts about the **tree** and carries on;
whether an open child should stop you is your question, and `--force` is the answer on the record.

## `devkit.toml`

At the repo root. Every GATE key has a stock default, so a repo with no file runs every gate
byte-identically to one declaring them. The declarations have none, because they are yours:
`[pm.states.<kind>]`, which `pm init` writes and without which every work-moving verb is refused
by name, and `[verify]`, `[integrate]` and `[dispatch]`, whose values only your project can name.
`agentic-sdlc pm config --seed` prints the whole seed as your pinned version ships it — every gate
key commented at its real default — which is what to read on a bump. These are the keys the tool
reads:

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
checks = ["D1", "D2", "D4", "D5", "D6",       # the stock roster; a declared list REPLACES
          "D11", "D12", "U1",                 # it, and `check pm` names any stock rule it
          "V1", "V4", "V5", "V7"]             # omits. Opt-in: D9 D10 R1-R6 U2-U4
                                              # (`pm vocabulary` names each)
version_file    = "pyproject.toml"            # R5 and `version-sync`: where the version lives
version_pattern = '^version = "(.*)"$'
version_at      = "start"                     # R5: "start" (bump-at-START) or "ship" (at close)

[pm.states.story]                             # one table per kind: milestone, feature, story, bug
todo        = ["planning", "ready"]
in_progress = ["building"]
done        = ["done", "obe"]                 # `integrate` and `release` write the FIRST of these

[pm.templates.feature]                        # one table per kind. `pm new` appends one `## `
extra_sections = ["Patterns"]                 #   heading per name to the template it reads

[pm.required.story]                           # one table per kind; nothing behind it. `pm new`
lines = ["Destination:", "Scenarios:"]        #   writes each prefix; `check pm` WARNs on one
                                              #   missing or empty

[verify]
spot      = "make unit"                       # the builder's one command
milestone = "make milestone"                  # CI's full tiers, on the release PR
static    = "make check"                      # asked before a milestone reuse (stock)
[verify.inputs]
spot = ["src", "tests"]                       # key a rung on the paths its target reads

[integrate]
per_merge = []                                # make targets after each merge
proof     = ["check", "unit"]                 # make targets run once over the batch
prepare   = []                                # optional: run once in a new batch, before the first merge

[dispatch]
project   = "<one line: what this is, and its stack>"
contracts = ["CLAUDE.md", ".claude/rules/pm-execution.md"]

[release.version_files]                       # a TABLE: one "<path>" = '<regex>' row per site
"pyproject.toml" = '^version = "(.*)"$'       # `version-sync` reads every row
"src/pkg/__init__.py" = "^__version__ = '(.*)'$"   # a second site, if you carry one

[adopt]
ours = [".github/workflows/verify.yml"]        # installed files this project OWNS: not graded, named every run
```

`make pm ARGS=vocabulary` prints your declared states with their categories and the rule ids
`[pm] checks` may name — read it after a pin bump. A key this version no longer reads is named at
exit 2 with its replacement, never silently ignored; `adopt` names every one.

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
like any other — `pm next` says what is next, and `pm roadmap` prints the whole sequence.

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
`make sdlc ARGS='verify --spot'` runs any verb and `make pm ARGS='story building <id>'` any `pm`
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
exits the worst code any gate gave. A gate name in `[gates] extra` is refused at exit 2 and told
which key runs it. A target that `[gates.inputs]` keys on the paths it reads is reused while they
are unchanged, the way `check all` reuses a devkit gate; a target with no entry runs every time.

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
make milestone   # check + test + matrix — the full gate CI runs once
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
