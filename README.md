# agentic-sdlc

**A reader/writer over a PM tree.** The tree is markdown grains with YAML frontmatter under
`pm/roadmap/` — milestone → feature → story, and bugs — and the tool reads and writes the same
files, in the same places, over and over. It echoes state back; it does not *do* anything.

- **`pm` writes one status.** `agentic-sdlc pm story building <id>` rewrites one `status:` line,
  preserves every other byte, and appends one timestamped row to the milestone's ledger.
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
uvx --from "git+https://github.com/cdowin/agentic-sdlc@v0.2.0" agentic-sdlc --version
```

Then, from inside a git repo:

```bash
uvx --from "git+https://github.com/cdowin/agentic-sdlc@v0.2.0" agentic-sdlc init
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
| editing code, inner loop | `agentic-sdlc verify --story` — the changed paths decide |
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
agentic-sdlc pm status                                 # the tree, grouped by phase
make check                                             # check all: doc + shell + pm + …
agentic-sdlc close story 0.1/the-thing/works           # its checks, then `done` — or an error
```

A belt's output is one line per check, then one line saying what happened:

```
[story] ok: story-exists — pm/roadmap/0.1-first-light/features/the-thing/stories/works.md
[story] ok: narrow-verified — `agentic-sdlc verify --story` exited 0
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
| `pm new`, `pm init`, `pm move`, `pm retire`, `pm set` | The other writes: scaffold a grain, stand up a tree, re-parent a story, retire a milestone into `ROADMAP.md`, set one frontmatter field |
| `pm status`, `pm list`, `pm get`, `pm validate`, `pm vocabulary`, `pm ready-for` | Reads. `ready-for feature\|milestone\|tag <id>` is a belt's entry condition as an exit code, naming every blocker |
| `pm ledger record\|show\|report` | The ledger: one JSONL row per status flip, decision and dispatch; `report` adds them up per grain and never exits non-zero on a number |
| `pm decide <id> <title…>` | Appends one dated heading to that grain's `decisions.md` |
| `pm install-skills` | Writes `.claude/rules/pm-execution.md` and `.claude/skills/pm-operations/SKILL.md` |
| `check doc \| shell \| grain-shape \| pm \| hooks \| repo-hygiene \| budget` | The gates. Pure text over git, markdown and shell; each prints a census of what it scanned and one verdict line. `check all` runs `[checks] all` (stock: `doc`, `shell`, `grain-shape`). `check <gate> --help` is that gate's contract |
| `gates-extra` | Not a gate: prints `[gates] extra`, one make target per line, for `Makefile.devkit`'s `check` |
| `verify --story \| --feature \| --milestone \| --plan \| --check` | The three rungs. `--story` runs the `[[verify.narrow]]` rules the changed paths match; the other two run the make target `[verify]` names; `--plan` prints all three with measured costs and runs nothing; `--check` validates `[verify]` against the tree |
| `close story <id>`, `close feature <id>` | The inner belts: checks, then the grain's status set to the first state of its kind's `done` list, or nothing |
| `release <version>` | The outer belt: tree clean, on the milestone branch, changelog non-empty, features done, findings dispositioned, version sites in sync, gate green → the milestone's status. Retitle, push, PR, merge and tag are printed as `next:` — never performed |
| `adopt <version>` | Checks only, nothing written: pin bumped, installables current, config accepted, hooks armed, targets resolve, this package's `check all` and `pm validate` green |
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
  DRIFT  feature 0.1/the-thing is done w/o review record  [pm/roadmap/…/feature.md]
  WARN   feature 0.1/other is todo over 2 story/ies in done: …
```

The tool refuses facts about the **input** — a state in no category, a config value of the wrong
shape, a review record that is not there — at exit 2. It reports facts about the **tree** and
carries on; whether an open child should stop you is your question, and `--force` is the answer
on the record.

## `devkit.toml`

At the repo root. Every gate has stock defaults, so a repo with no file runs byte-identically to
one declaring them; the flow (`[pm.states.<kind>]`) has none, because it is yours — `pm init`
writes it and a tree without it is refused by name. These are the keys the tool reads:

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
extra = ["my-scan"]                           # your own gate targets, run by `make check`

[pm]
roadmap_dir  = "pm/roadmap"
template_dir = "pm/templates"                 # `pm templates` copies the stock ones here
review_dir   = "docs/reviews"
story_ordinal_prefix = false                  # stories/NN-<slug>.md keeps NN in the file, not the id
checks = ["D1", "D2", "D3", "D4", "D5", "D6", "V1", "V2", "V3", "V4", "V5"]  # + D8 D9 D10 V6, opt-in
version_file    = "pyproject.toml"            # D8 and `version-sync`: where the version lives
version_pattern = '^version = "(.*)"$'

[pm.states.story]                             # one table per kind: milestone, feature, story, bug
todo        = ["planning", "ready"]
in_progress = ["building"]
done        = ["done", "obe"]                 # a belt writes the FIRST of these

[tests]
budget = { unit = 20, integration = 130 }     # `check budget`: seconds per tier, from the ledger
cases  = { unit = 1250, integration = 800 }   # and a size ceiling per tier

[verify]
feature   = "make test"                       # the make TARGET each rung runs
milestone = "make milestone"

[[verify.narrow]]                             # the story rung: first matching rule per path
paths = "src/<name>.py"
run   = "pytest tests/test_<name>.py -q"

[release]                                     # also [adopt], [story], [feature]:
steps = ["tree-clean", "gate"]                #   the check list, when not the shipped default
[release.commands]
gate = "make milestone"                       # the command a named check runs
prove-artifact = "uvx --from git+…@v{version} agentic-sdlc --version"
[release.version_files]                       # every site `version-sync` reads
"pyproject.toml" = '^version = "(.*)"$'
[adopt]
runner_targets = ["precommit", "milestone"]   # what `runner-targets-resolve` asks `make -n` about
```

`agentic-sdlc pm vocabulary` prints your declared states with their categories and the rule ids
`[pm] checks` may name — read it after a pin bump. A key this version no longer reads is named at
exit 2, never silently ignored.

## Wiring

**Your Makefile is two lines plus what is yours.** The pin lives in your file, so a bump is a
one-line diff:

```make
DEVKIT_VERSION := v0.2.0
include Makefile.devkit

my-scan: ## a gate this project owns
	@bash tools/dev/checks/my_scan.sh
```

`Makefile.devkit` is devkit-owned: `help`, `pm`, `check`, `precommit`, `milestone`. Your build and
test tiers arrive through `Makefile.tiers`, a file you (or a language kit) write beside it: it
defines the tier targets and declares which compositions they join with `GDK_PRECOMMIT_TIERS` and
`GDK_MILESTONE_TIERS`. With no tier file, `precommit` and `milestone` are `check` alone and say so.
Your own static gates join `check` through `[gates] extra`, never through a fork of the include.

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
