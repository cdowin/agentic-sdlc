# CLAUDE.md — agentic-sdlc

**Repo discipline, consumed as a pinned-tag Python package**: the static gates (`check doc`,
`check shell`, `check repo-hygiene`, `check pm`, `check hooks`), `pm` — a
markdown-and-frontmatter project tracker with a ledger — and the `install-*` verbs that write a
project's standard target set, runners, hook corpus, agent roster and CI. Extracted from
`godot-devkit` at 0.2.0; the scene half stayed there.

Consumed by repos that pin `DEVKIT_VERSION` in their Makefile and route gates through `uvx`.
Which repos those are is none of this package's business (hard rule 8). Public repo, MIT. **Every
change here lands in other projects' commit gates — treat the CLI as a published API.**

**The goal, the northstar, and the reasoning behind the rules below live in [`README.md`](README.md).** Read it once before your first change here; this file is the enforceable form, not a second copy of it. One line worth carrying in your head: *anything a project checks or scaffolds by hand should be one deterministic command that touches nothing else — and provable without reading the tree.* Two audiences, humans and LLMs; for the latter the deliverables are a stable verb vocabulary, determinism, and token reduction.

## Hard rules

1. **Stdlib only, forever.** No runtime dependencies. Python 3.11+ (`tomllib`). A consumer's pre-push hook must never break because of a transitive dep.
2. **Pure text — boots nothing.** No tool starts an engine, runs a build or an import, or depends on generated cache state. Every gate reads git, markdown and shell as text, so it is safe anywhere, anytime, in parallel. This rule used to carry an exit clause for the other half — *"the `repo/` family does not touch a scene at all: it is here because this is the pinned-tag channel its consumers already share… **if that stops being true, it leaves**"*. **It was exercised in 0.2.0, in the other direction: the scene half left and the repo family kept the channel.** The one-way layout is what made that a whole extraction rather than a negotiation, and it stays that way for whatever arrives next.
3. **A write verb touches only what it was asked to touch.** `pm` rewrites ONE frontmatter line and preserves every other byte, including the file's line endings; an installer writes a whole file or refuses by path. A verb that cannot guarantee a correct result **refuses and says why** — it never edits partially and never reformats adjacent lines. Writes are idempotent: the same command twice is a no-op the second time.
4. **Two cardinal sins, one shape.** Read side: a gate that misses real drift and prints PASS. Write side: a diff that looks legitimate and is not. Both are worse than a crash because both destroy the signal a consumer relies on. When scoping/globbing/excluding, prove the file census matches intent (count what you scanned; a gate scanning 0 files must say so, loudly). Loud failure is a feature — an LLM can recover from an error and cannot recover from a lie.
5. **Config over forks.** Per-project variation goes in the consumer's `devkit.toml` section — never "edit the tool". **A GATE ships stock defaults**: a repo with no `devkit.toml` runs every gate byte-identically to one declaring them. **A WORKFLOW does not.** States, transitions and flow are the project's declaration of how it works; `init` writes them, every run reads them, and a tree without them is refused by name. The no-config half was written in this package's first CLAUDE.md, beside a rule reading *"the only writes ever performed are stdout/stderr"* — it is a linter's property, and a default nobody can see is the engine's opinion wearing the project's clothes.
6. **Exit codes are contract:** 0 pass, 1 findings, 2 usage error. Output line shapes (`  DRIFT  …`, `[check:x] PASS — …`) are grepped by consumers — changing them is a **minor** bump at least.
7. **Semver, enforced by habit:** patch = fix with identical interface; minor = new subcommand/flag/config key or output-format change; major = anything a consumer Makefile/hook must edit to survive. `__version__` in `src/agentic_sdlc/__init__.py` and `version` in `pyproject.toml` move together, always.
8. **This package knows nothing about its consumers.** No file here names a consuming project, reads a path outside this checkout, or gates on another repo's content or working state. Fixtures live in `tests/fixtures/`, committed and versioned — a check that needs realistic data VENDORS that data here. A consumer proves its own integration when it bumps its pin; that is the consumer's gate and it runs in the consumer's repo. A release gate that can be reddened by somebody else's uncommitted work is not a gate. Worked examples in prose name a SHAPE ("a project whose `check` carries extra gates"), never a repo.
9. **Express, never infer.** This package gives a project the means to declare its grains, its states, its transitions and its flow — to create work, move it, and ask where it is. **It never decides what a move MEANS, whether it was right, or what should happen next.** Expressing the flow is the product; inferring from it is a different product, and it belongs to whatever is running the flow — an agent with a dispatch, a reviewer, a person who can be asked.

   The edge is one question: **is this reading what the project declared, or deciding what the project should do?** Refusing a malformed declaration is reading — a state in no category, a transition to an undeclared state, a move the table forbids, a config value of the wrong shape: exit 2, always. Reporting a fact about the tree is reading — *"3 stories not in `done`: s1 is building"*. **Blocking on that fact is deciding**, and it asserts an answer to a question this package cannot ask: descoped? a hotfix? deliberate? It warns, it names, it proceeds, and the caller decides.

   A tool that refuses gets worked around invisibly, and then the protocol teaches nothing. `check <gate>` is the thing that FAILS a contradictory tree, in CI and pre-push, with an exit-code contract for exactly that. **`pm` moves and reports; `check` gates.** Conflating them is how the conveyor inherited a job it should never have had (0.2.0; `docs/design/state-categories.md` §7).


10. **Test what BITES, the cheapest way that can actually fail.** We test to be useful, not to say we have tests. A test earns its place by gating something that would cost real time if it broke: a load-bearing module (`src/agentic_sdlc/core/walk.py`, `src/agentic_sdlc/core/config.py`, `src/agentic_sdlc/repo/pm/model.py`, `src/agentic_sdlc/repo/conveyor/driver.py`), a path a consumer runs dozens of times a day, or one of rule 4's two cardinal sins — a gate printing PASS over what it did not measure, a write that looks legitimate and is not. **100% coverage is not the goal and never was**; coverage that bites is. The question for any case: *if this were deleted and the thing it guards broke, what would that cost?* "The next run catches it anyway" means delete. Iteration and learning beat perfect engineering — which is only safe because the things that bite are gated hard. A test that spawns a process to check a pure function is an integration test by accident, and the suite pays for it forever. Default to a function call; a temp tree when the code reads files; a real repository, `make` or installed hook ONLY when the thing under test is one — and then say so, by reaching for the builder that spawns rather than passing a flag to one that might. **And prove it ONCE.** Before a new test, name the one that already covers this or the one that can be amended to; a new case is warranted only when neither exists. A rule proven at three altitudes is two altitudes of cost for no altitude of coverage. **A tier that got slower is a finding**: it degrades a human's patience instead of a boolean, so no other gate will ever notice. This rule is the counterweight rule 4 never had — rule 4 says a gate must not print PASS over what it did not measure, and for two releases every judgement call resolved toward "more real" because nothing argued the other way. Measured 2026-09-05: 1842 tests, 240 s of wall clock with 150 s of CPU inside it, and `make precommit` running all of it after every edit — arrived at one honest fixture at a time, with every gate green the whole way down.
## Where things live

One family and a shared floor. The rule, not the inventory — `ls src/agentic_sdlc`
is the inventory, and it cannot go stale:

- **`core/`** — infrastructure that knows about no family at all. `project.py` finds the
  repo and loads config; `config.py` decides what a config VALUE may be. Nothing here
  may import from `repo/`.
- **`repo/`** — the discipline itself: the `pm` tracker, the gates that read markdown,
  shell and git, and the `install-*` verbs with the files they write. It may import
  `core/`, never the reverse. That one-way edge is what let the other family leave
  whole (rule 2) — check it before you add an import, because nothing else will.

A module that fits neither is a signal worth raising, not a placement problem
to solve quietly. Tool modules own their behavior and expose `main(argv)` or `run()`;
`cli.py` only routes.

- **New check** = module in `repo/checks/` + a key in `cli.py`'s `KNOWN_GATES` +
  README table row + CHANGELOG line. `_check_module` DERIVES the import path from the
  name, so there is no second list to update — and `tests/test_gate_roster.py` asserts
  the roster equals what dispatches, because eight phantom gate names survived an
  extraction that touched every other surface in that file.
- **New verb** = module + `cli.py` route + README table row + CHANGELOG line. A verb
  that WRITES additionally needs an explicit refusal path with a test proving it
  declines rather than mangles, and an idempotence test.
- **New test** = **first, the search.** Name the test that already covers this,
  or the one that could be AMENDED to. A new case is warranted only when
  neither exists, and *"I could not find one"* is an answer that has to have
  been looked for. Then: the cheapest tier that can fail (rule 10) — a function
  call before a temp tree, a temp tree before a process — and a row in the
  story's `## How this is proven` table saying which. **The default is that a
  new test is NOT warranted**: this suite reached 1,478 functions over 7,241
  statements of source, one per 4.9, because every individual addition was
  reasonable and nothing asked about the total.
- **Every config value goes through `src/agentic_sdlc/core/config.py`.** Never `tuple(cfg.get(...))` —
  a bare string is iterable, and that is how seven gates shipped a silent PASS over an
  empty census in v0.9.0.

## How we work

- **The agent SDLC** — milestone branching, the dispatch loop, the model mix, and the roster `install-agents` ships — is [`SDLC.md`](SDLC.md), at the root because it is the operating contract, not auxiliary documentation.
- **The README carries the why; this file carries the enforceable form.** If a change
  makes you want to edit this file, ask first whether it changed *doctrine* or merely
  *contents*. Contents belong in the tree, in `--help`, or in the README. A CLAUDE.md
  that has to be edited whenever code moves is a manifest, and it will lie.
- **The committed fixtures ARE the fixtures.** `tests/fixtures/` holds purpose-built
  repos, hook payloads and transcripts, versioned with the code that reads them; every
  verb and every gate is proven against those. A check that wants more realistic data
  vendors more data here (rule 8) — it never reaches for a tree outside this checkout,
  which would answer differently on every machine.
- **Verify against source, never a cached wheel.** `uvx --from <path>` caches by
  version, so an unchanged version number serves stale code and a fixed bug still
  reproduces. Use `PYTHONPATH=src python3 -m agentic_sdlc.cli …`.
- **A review is part of a release, not a courtesy.** Every minor bump in this package
  so far has had a pre-release review return NOT RELEASE-SAFE, and each time the
  blocker was a false PASS that would have shipped a permanently-green gate.

### Reporting to Chris

**Every decision he needs to make goes in a numbered `NEEDS YOU` list at the TOP**, so
he can answer "1 yes, 2 delete" without scrolling. Each item is a decision, not an
observation, and it carries the thing being decided **in the message** — a path, a
commit hash, or the content itself. Never "there are three open questions" — name them
A, B, C. When nothing needs him, say "nothing needs you" explicitly.

- **Gate output only when it FAILED, or when you ran it yourself** — one line
  ("157/157, my run"), never a pasted PASS block. A wall of green tells him nothing.
- **Numbers, not adjectives.** "228 files, census unchanged", not "verified thoroughly".
- **Say what you did NOT verify.** A claim with an unstated gap is worse than a gap.

## Verification loop

**Run `make precommit` after a change and `make milestone` before a release. Never
hand-roll an incantation.** `precommit` is the NARROW rung — gates, the hook
self-tests, and the unit tier: no subprocess, one process, seconds. The
integration tier (`make integration`) runs at the close through
`verify --feature`, and `milestone` runs everything on every interpreter. It
was not always split: `precommit` ran the whole suite after every edit, which is
the same 170x this package exists to end, in the file that names it. `make help` lists every target. If the check you need is not
a target, **add the target**, then run it — apparatus that lives in one agent's context
is apparatus that gets rebuilt.

**`make milestone` runs the matrix, and the matrix proves PYTHON on every interpreter —
bash once.** `PY_FLOOR` runs the whole suite; the other interpreters in `PY_MATRIX` run
`-m "not shell"`. A spawn is not something a Python version changes, so replaying it four
times buys minutes and no information.

**That `shell` mark is the TIER**, and it is what `make unit` / `make integration` select
on. It was derived for the matrix and had no target for years, so the fast half was
unreachable from the command line. The suite's wall clock was ~85% subprocess, and that
number sat in this file as a justification for skipping interpreters rather than as the
defect it was — which is rule 10, and why rule 10 exists. The `shell` mark is DERIVED
per module in `tests/conftest.py` from what the source does, never hand-applied (a
hand-written one is a collection refusal). A `PY_FLOOR` outside `PY_MATRIX` is refused
by name before the first interpreter starts: a matrix with no full pass would print PASS
over a suite nothing ran. `make test` is unaffected — it runs everything.

**Every gate prints ONE verdict line naming its full transcript under .gate-reports/;
`VERBOSE=1` streams the whole thing.** A new target routes through the shipped
`gdk_gate_capture` / `gdk_gate_verdict` (installables/gdk_gate.sh, sourced from
source — this package is its own first consumer) like the rest; never ask an agent to
grep a gate's output for its result. Enforced by `tests/test_makefile_gates.py`.

- Behavior gate: `make gates` — `agentic-sdlc check all` over this repo's own tree,
  which is a real project with a real PM tree and a real hook corpus. Self-hosting is
  the behavior proof: every check runs against something committed here.
- Differential + replay harnesses: `make fuzz`. Seeded, so a divergence reproduces
  exactly rather than being re-derived; `make test` runs them too.
- **A write verb under test writes to scratch, never to a fixture in place.** Copy the
  file (or the tree) to a `tempfile` first; a fixture that a test run mutates is a
  fixture that grades the next run against the last one's output.
- A gate-semantics change additionally needs a deliberately-broken probe: introduce the drift class in a scratch copy of a fixture repo and confirm the gate FAILS (rule 4). Prove the **config** path too: a bad value for that gate's section must exit 2, and a zero-file census must FAIL rather than pass.
- **Never verify through `uvx --from <path>`.** uv caches the built wheel by version, so an unchanged
  version number serves stale code and a fixed bug still reproduces. Run `PYTHONPATH=src python3 -m
  agentic_sdlc.cli …`, or `uv cache clean agentic-sdlc` first.

## Self-hosting

This package runs its own tooling on its own tree, and that is a gate, not a demo.

- `pm/roadmap/` is a real PM tree scaffolded by `pm new`, and `devkit.toml` turns on **every** rule this package ships except D8 (which encodes bump-at-START; we bump at close). Both `agentic-sdlc check all` and `agentic-sdlc check pm` must exit 0 here.
- Work follows the milestone-branch flow — [`SDLC.md`](SDLC.md) §1 — the same as its consumers: `main` is merge-commit-only, at close. D9 + D10 in `[pm] checks` are what hold this tree to it.
- CI is `.github/workflows/verify.yml`, whose one job runs `make milestone` — the same target the local full gate is. The same target is not the same ANSWER: a gate that reads repo-LOCAL state answers differently in a checkout, and `core.hooksPath` is the measured case (nothing tracked carries it, so `check hooks` was UNARMED on every CI run while every developer's tree was armed). Whatever the gate needs and the checkout lacks is a step ahead of it, guarded on a tracked file that only exists where the tool is wanted — the arming script behind `hashFiles('tools/setup-hooks.sh')` is the shipped example, and a build toolchain a consumer's gate needs is a step the consumer adds after the write. It is INSTALLED by `install-ci`, not hand-written: edit `src/agentic_sdlc/repo/installables/ci-verify.yml` and re-install.
- The review + build contract under `.claude/agents/verification-*.md` is INSTALLED by `install-agents`, not hand-written — edit the source under `src/agentic_sdlc/repo/installables/` and re-install. A test asserts this repo's copies stay byte-current, and another asserts they pass `check doc` in a fresh consumer, because a contract that reddens the gates it arrives beside gets deleted by the first person who runs them.
- `install-hooks` IS self-hosted since 0.23.0: `tools/hooks/`, `tools/setup-hooks.sh` and `tools/dev/agent-worktree.sh` are the installer's output, and `.claude/settings.json` carries the entries it prints — the two ledger couriers `"async": true`, feeding `pm/roadmap/<building>/ledger.jsonl` through this Makefile's `pm` target. The `project config` headers are this repo's (static gate `make gates`, the hook self-tests standing in for a unit slice, base `main`); `make hooks-self-test` replays the corpora the installed hooks ship and is in `precommit` — loud on a census of zero, because a corpus list that empties out and passes is the one failure that gate must never have. `bash tools/setup-hooks.sh` arms the git hooks — it writes `core.hooksPath`, which a worktree shares with the main checkout. The installables are still proven by installing them into a temp repo and RUNNING them against real hook payloads.
- **`CHANGELOG.md` is hand-maintained**, like every other project's. A consumer-visible change goes into its `## Unreleased` section as a bullet as the work lands, and the release skill retitles that section to the tag. Rationale with a rejected alternative is a decision — `pm decide` opens the heading — not a release note.
- If a rule fails when pointed at this repo, the finding gets fixed. Turning the rule off is only right when the rule encodes a flow this package does not run, and that goes in `decisions.md` with what was rejected.

## Releases

Use the `/release` skill — it owns the bump/tag/push sequence and the consumer-pin reminder. Never tag by hand; never let `__init__.py` and `pyproject.toml` versions diverge.
