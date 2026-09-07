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

Pin a tag so every machine and CI runs identical code:

```bash
uvx --from "git+https://github.com/cdowin/agentic-sdlc@v0.4.0" agentic-sdlc --version
```

Then, from inside a git repo:

```bash
uvx --from "git+https://github.com/cdowin/agentic-sdlc@v0.4.0" agentic-sdlc init
make help
```

`init` writes `devkit.toml` (with your flow declared), your two-line `Makefile`, `Makefile.devkit`,
the hook corpus (armed), the agent roster, the CI workflows, the rendered SDLC document, a
`CLAUDE.md` skeleton and an empty PM tree — in order, idempotently. The devkit-owned files are
overwritten by `--force`; `devkit.toml`, `Makefile`, `CLAUDE.md` and the tree are yours from the
first write and never touched again.

**Adopting a bump** is: bump `DEVKIT_VERSION` in your Makefile, read the CHANGELOG, run
`install-* --diff` to see what the release would change, take what you want, re-run `pm init`
once, and `agentic-sdlc adopt <version>` to read the result.

## The ladder — one verb, one scope

Nothing runs a rung wider than the thing you changed.

| You are | Run |
|---|---|
| editing the PM tree or a doc | `make check` |
| editing code, inner loop | `agentic-sdlc verify --story` — the make target `[verify] story` names, e.g. `make unit` |
| about to commit | `make precommit` — `check` + your `GDK_PRECOMMIT_TIERS` |
| closing a story | `agentic-sdlc close story <id>` |
| closing a feature | `agentic-sdlc close feature <id>` — its check runs what `[verify] feature` names |
| closing a milestone | `agentic-sdlc release <version>` — its `gate` check runs `make milestone` |
| bumping the devkit pin | `agentic-sdlc adopt <version>` — the adoption, never your own gates |

`agentic-sdlc verify --plan` prints the three `verify` rungs with the cost each one last took, read
from your ledger. Ask it instead of guessing.

## Quickstart

```bash
agentic-sdlc pm new milestone 0.1 first-light
agentic-sdlc pm new feature 0.1 the-thing
agentic-sdlc pm new story 0.1/the-thing works "the thing works"
agentic-sdlc pm story building 0.1/the-thing/works     # one line written, one ledger row
agentic-sdlc pm add 0.1/the-thing 0.1/the-thing/works  # bind it, and sequence it there
agentic-sdlc pm status                                 # the tree, in its declared order
make check                                             # check all: doc + shell + pm + …
agentic-sdlc close story 0.1/the-thing/works           # its checks, then `done` — or an error
```

A belt's output is one line per check, then one line saying what happened:

```
[story] ok: story-exists — pm/roadmap/stories/works.md
[story] ok: story-verified — `agentic-sdlc verify --story` exited 0 — the story rung [verify] names
[story] error: committed: 2 uncommitted path(s): src/a.py, src/b.py — commit by explicit pathspec; this belt never commits
[story] error: evidence-written: … carries no `done:` line — step 6 of pm-execution.md
[story] error — 2 check(s) false; nothing written
```

Fix what it named and run it again; every check is a read of the tree, so nothing is carried
between runs. All true → the one write and `next:` lines naming what is yours to do.

## Verbs

`agentic-sdlc --help` and `agentic-sdlc pm --help` are the live rosters; this is the same set.

| Verb | Reads / writes |
|---|---|
| `pm <kind> <status> <id>` | Writes one `status:` line — any state in `[pm.states.<kind>]`, anything else is exit 2 — and one ledger row. `pm feature <done-state> <id> --review-record <path>` stamps `reviewed:` too; a path naming no file is refused whole |
| `pm new`, `pm init`, `pm retire`, `pm set`, `pm rename` | The other writes: scaffold a grain, stand up a tree, retire a milestone (the version stays on the plan), set one frontmatter field. **`pm move` is gone (0.4.0)** — re-parenting is `pm set <id> feature <fid>`, one line, and the id never changes. `pm rename <old> <new>` is the one path that still rewrites refs: the grain's `id:` and every inbound reference (`depends_on`, `consumed_by`, `reviewed`, `caused_by`, `caught_in`, `fix_milestone`, the bindings, every `order` entry), matched whole-token, in one pass — **whole or not at all**, and one reference it cannot rewrite means nothing is written |
| `pm config --seed` | Prints the seed `devkit.toml` this pinned version ships — every gate key commented at the default the code actually holds, and the two declarations spelled out with their arguments. Writes nothing. `init` serves a new repo once; this serves every bump after it |
| `pm status`, `pm list`, `pm get`, `pm validate`, `pm vocabulary`, `pm ready-for`, `pm roadmap` | Reads. `ready-for feature\|milestone\|tag <id>` is a belt's entry condition as an exit code, naming every blocker |
| `pm ledger record\|show\|report` | The ledger — telemetry: one JSONL row per status flip, decision, dispatch, session and gate run, carrying tokens, tool calls and wall-clock. `report` adds them up per grain (spend, cost, how long something took) and never exits non-zero on a number. **Two homes**: one `ledger.jsonl` per milestone for rows naming a grain, and `<roadmap>/ledger.jsonl` for the rest — `gate` and `test` rows, and a session nobody could attribute. `show` and `report` both read both. A row names its grain from `--grain` (the couriers pass **`GDK_LEDGER_GRAIN`** from their environment — **you export it**; nothing here does), else from the one story in progress, else not at all |
| `pm decide <id> <title…>` | Appends one dated heading to that grain's decisions log, which sits beside it as `<stem>-decisions.md` |
| `pm new handoff <milestone-id>` | Mints the milestone's `handoff.md` from the template. Never auto-minted by `pm new milestone`, so an absent one is a signal `check pm` warns on; never clobbers what is there |
| `pm add <parent-id> <child-id> [--position N\|--before <id>\|--after <id>]` | **Binds AND sequences**, in one pair of writes: the child's own field names the parent, the parent's `order:` list says where. Exactly `set` plus a list insert, and nothing else. Neither argument names a kind — each id resolves to the grain that declares one, and `[pm.contains]` says whether that pair is allowed, so ONE verb serves root → milestones, milestone → features and bugs, feature → stories. Bare, it appends. Off the mapping it refuses naming both kinds and writes nothing. `order` is OPTIONAL per container: a bound child nobody sequenced is a counted line, never a finding |
| `pm remove <parent-id> <child-id>` | Unbinds and unsequences together. `pm set <id> <field> ""` still unbinds alone — which leaves the parent sequencing a child it no longer holds, the DANGLING entry `check pm` reports |
| `pm next` | The first entry in `order` that has not shipped, with the version its milestone declares |
| `pm install-skills` | Writes `.claude/rules/pm-execution.md`, `.claude/skills/pm-operations/SKILL.md` and `.claude/skills/handoff/SKILL.md` |
| `check doc \| shell \| grain-shape \| pm \| hooks \| repo-hygiene \| budget` | The gates. Pure text over git, markdown and shell; each prints a census of what it scanned and one verdict line. `check all` runs `[checks] all` (stock: `doc`, `shell`, `grain-shape`). `check <gate> --help` is that gate's contract |
| `gates-extra` | Not a gate: prints `[gates] extra`, one make target per line, for `Makefile.devkit`'s `check` |
| `verify --story \| --feature \| --milestone \| --plan \| --check` | The three rungs, each the make target `[verify] <rung>` names — `story = "make unit"`, `feature = "make test"`, `milestone = "make milestone"`; a rung not declared is exit 2. `--plan` prints all three with their measured cost and runs nothing; `--check` holds the three targets to the Makefile |
| `close story <id>`, `close feature <id>` | The inner belts: checks, then the grain's status set to the first state of its kind's `done` list, or nothing |
| `release <version>` | The outer belt: tree clean, on the milestone branch, changelog non-empty, features done, findings dispositioned, version sites in sync, gate green → the milestone's status. Retitle, push, PR, merge and tag are printed as `next:` — never performed |
| `adopt <version>` | Checks only, nothing written: pin bumped, installables current — except the files `[adopt] ours` claims, which are named and counted on every run — config accepted, hooks armed, targets resolve, this package's `check all` and `pm validate` green. Runs wherever the project tracks the bump (a milestone, a feature, a story, or nowhere); the milestone is only where a ledger row would land |
| `init` | Everything below, in order, plus the files nothing else writes |
| `install-ci` | `.github/workflows/`: `verify.yml` (arms the hooks, runs `make milestone`), `semver-gate.yml`, `auto-tag.yml` |
| `install-agents` | `.claude/agents/`: the review/build contract (`verification-reviewer.md`, `verification-builder.md`) and the base roster — architect, po, developer, reviewer, milestone-reviewer, simplifier, test-writer, tech-writer, changelog-writer, doc-hygiene, pm-operator — each with a Project config section that is yours after install |
| `install-hooks` | `tools/hooks/` (commit-pathspec, stop-gate, write-confine, two ledger couriers, `pre-push`, `prepare-commit-msg`), `tools/dev/agent-worktree.sh` and `tools/setup-hooks.sh`, which arms them. Prints the `.claude/settings.json` entries; never writes that file |
| `install-gates` | `Makefile.devkit` (`help`, `pm`, `check`, `precommit`, `milestone`) and `tools/dev/gdk_gate.sh`, the one-verdict-line gate library |
| `install-sdlc` | `docs/sdlc-protocol.md`, **rendered** from your `[story]` / `[feature]` / `[release]` / `[adopt]` check lists and the `done` state each belt writes |
| `version` | This package's version |

Every installer writes a file once. A destination that differs is refused by path (move it aside,
or `--force`); `--diff` prints what would change and writes nothing; a difference confined to a
hook's `project config` header is reported as one and needs no `--force`.

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
checks = ["D1", "D2", "D3", "D4", "D5", "D6", "U1", "U2",   # + D9 D10 R5, opt-in.
          "V1", "V4", "V5", "V7"]             # U2: the ledger couriers are wired and the
                                              # tree holds no row — recording that goes
                                              # nowhere, which is silent otherwise
version_file    = "pyproject.toml"            # R5 and `version-sync`: where the version lives
version_pattern = '^version = "(.*)"$'
version_at      = "start"                     # R5: which entry in `order` the version file
                                              # must match — "start" (the first not yet shipped,
                                              # bump-at-START) or "ship" (the last that has)

[pm.states.story]                             # one table per kind: milestone, feature, story, bug
todo        = ["planning", "ready"]
in_progress = ["building"]
done        = ["done", "obe"]                 # a belt writes the FIRST of these

[tests]
budget = { unit = 20, integration = 130 }     # `check budget`: seconds per tier, from the ledger
cases  = { unit = 1250, integration = 800 }   # and a size ceiling per tier

[verify]
story     = "make unit"                       # the make TARGET each rung runs
feature   = "make test"
milestone = "make milestone"

[release]                                     # also [adopt], [story], [feature]:
steps = ["tree-clean", "gate"]                #   the check list, when not the shipped default
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

`agentic-sdlc pm vocabulary` prints your declared states with their categories and the rule ids
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
one — `"start"`, the first not yet shipped, or `"ship"`, the last that has, for a project that
bumps in the release commit.

## Wiring

**Your Makefile is two lines plus what is yours.** The pin lives in your file, so a bump is a
one-line diff:

```make
DEVKIT_VERSION := v0.4.0
include Makefile.devkit

my-scan: ## a gate this project owns
	@bash tools/dev/checks/my_scan.sh
```

`Makefile.devkit` is devkit-owned: `help`, `pm`, `check`, `precommit`, `milestone`. Your build and
test tiers arrive through `Makefile.tiers`, a file you (or a language kit) write beside it: it
defines the tier targets and declares which compositions they join with `GDK_PRECOMMIT_TIERS` and
`GDK_MILESTONE_TIERS`. With no tier file, `precommit` and `milestone` are `check` alone and say so.
Your own static gates join `check` through `[gates] extra`, never through a fork of the include.

**The two lists next to each other are two namespaces.** `[checks] all` names **gates this package
ships** (`agentic-sdlc check <name>`); `[gates] extra` names **make targets your own makefile
defines**. `make check` runs the first list, then the second. A gate name in `[gates] extra` is
refused at exit 2 and told which key runs it, because make's own answer — `No rule to make target
'budget'` — arrives three layers below the config that caused it.

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
