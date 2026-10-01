# CLAUDE.md — agentic-sdlc

**A reader/writer over a PM tree, shipped as a pinned-tag Python package.** `pm` writes one
status; `check` reads the same files and echoes findings and warnings; `release` checks, then
writes one status or refuses. Consumers pin `agentic-sdlc==X.Y.Z` in `uv.lock` and run it from
`.venv`; every change here lands in their gates — **treat the CLI as a published API.** Public
repo, MIT.

**The README carries the why; this file is the enforceable form.** The northstar, in Chris's
words: *a simple local Jira — it creates the work, moves it, expresses what the states and the
flow are, and infers nothing. It just echoes state back.* The flow is [`SDLC.md`](SDLC.md).

## Hard rules

**The numbers are an API: source, tests and hooks cite them, so this list is append-only.** A rule
is trimmed inside itself, never renumbered or reordered; a new rule takes the next number.

1. **Stdlib only, forever.** No runtime dependencies; Python 3.11+ (`tomllib`). The hook corpus
   under `tools/hooks/` runs on a consumer's bare `python3`, so a dependency there breaks someone
   else's commit. Rules 3 and 6 are what block the tempting libraries.
2. **Pure text for inspection and state.** Readers and PM writes never start a build, import or
   cache. Only explicit `verify`, the release belt and the integrator's merge run declared gates,
   through the process primitive; nothing invents an engine command.
3. **A write touches only what it was asked to touch.** `pm` rewrites ONE frontmatter line and
   keeps every other byte, line endings included; an installer writes a whole file or refuses by
   path. A verb that cannot guarantee a correct result refuses and says why. Writes are
   idempotent.
4. **Two cardinal sins, one shape.** A gate that misses drift and prints PASS; a write that looks
   legitimate and is not. Both are worse than a crash. A gate scanning 0 files FAILS and says so.
   An LLM recovers from an error and cannot recover from a lie.
5. **Config over forks; the byte-identical guarantee is GATES-ONLY.** Per-project variation is
   the consumer's `devkit.toml`, never an edit to the tool. A GATE key has a stock default, and
   the seed carries it commented at exactly the value the code holds (`tests/test_config_seed.py`
   compares them). A WORKFLOW key (`[pm.states.*]`, `[verify]`) has no default: each reader
   refuses BY NAME when it is absent. `pm config --seed` prints the seed a bump reads.
6. **Exit codes are contract:** 0 pass, 1 findings, 2 usage or config error. Output line shapes
   are grepped by consumers; changing one is a **minor** bump at least.
7. **Semver, enforced by habit:** patch = same interface; minor = a new verb, flag, config key or
   output shape; major = a consumer Makefile or hook must change. `__version__` in
   `src/agentic_sdlc/__init__.py` and `version` in `pyproject.toml` move together, always.
8. **This package knows nothing about its consumers.** No file names a consuming project, reads a
   path outside this checkout, or gates on another repo's state. Realistic data is VENDORED under
   `tests/fixtures/`.
9. **Express, never infer.** A project declares its grains, states and flow; the tool creates
   work, moves it, and says where it is. It never decides what a move MEANS or what comes next. A
   malformed declaration is refused at exit 2; a fact about the tree is reported and the caller
   decides. `--force` is the deviation, recorded in the ledger.
10. **Test what BITES, the cheapest way that can fail.** A test earns its place by gating a
    load-bearing module, a path consumers run daily, or one of rule 4's sins. A function call
    before a temp tree, a temp tree before a process. Before a new case, name the one that covers
    this or can be amended. A tier that got slower is a finding.
11. **Absence is a finding, and a capability advertises itself where you stand.** Something the
    tree needs and lacks gets a NAMED line, never silence. A capability this package HAS is named
    where its operator stands: a column, a word in `--help`, a line in the auto-loaded rule.
    `TestACapabilityIsCitedWhereItsOperatorStands` holds it. Before you hand-roll a measurement,
    ASK the tree: `pm ledger report`, `pm list`, `check <gate>`, `agentic-sdlc dispatch --grain
    <id>`. **Read verbs emit LINES; composition is the shell's job:** a filter you cannot pipe is
    a missing **column**, never a new verb or flag.

## Where things live

- **`src/agentic_sdlc/core/`** knows no family and imports nothing from `repo/`. It holds THE
  PRIMITIVES, each the one place this package does one thing: `walk.py` enumerates, `apply.py`
  mutates, `frontmatter.py` reads and writes frontmatter, `spawn.py` starts a process.
  `tests/test_boundaries.py` fails a second implementation by path.
- **`src/agentic_sdlc/repo/`** is the tool: the `pm` tracker, the checks, `verify`, and
  `install.py` with its files under `installables/`. `src/agentic_sdlc/cli.py` only routes; each
  verb module owns its behaviour and its `--help`.
- **New check** = module in `src/agentic_sdlc/repo/checks/` + `KNOWN_GATES` + a README row.
  **New verb** = module + route + README row; a verb that WRITES also needs a refusal test and an
  idempotence test.
- **Every config value goes through `src/agentic_sdlc/core/config.py`.** Never
  `tuple(cfg.get(...))` — a bare string is iterable.
- **`tests/fixtures/` holds the fixtures.** `unit` / `integration` / `test` select on the `shell`
  mark, DERIVED in `tests/conftest.py` from whether a module spawns.
- **`changelog:` is a field on the grain**: one consumer-visible sentence or `none`. Rationale
  with a rejected alternative is `pm decide`.

## The ladder

Never run a rung wider than the thing you changed. `make help` is the target list.

| who | when | run |
|---|---|---|
| anyone | a PM-tree or doc edit | `make check` |
| builder | after each edit, and before the commit | the spot check, `[verify] spot`: `make unit` here |
| integrator | once per batch | `integrate <slug>...` (batch 2): merge, ONE proof, write `done` |
| architect | the milestone | `agentic-sdlc release <version>`: status and version sites; CI runs `make milestone` |

A PASS is a receipt keyed on the tree; nothing re-runs a gate on a tree that has one.
`agentic-sdlc verify --plan` prints each rung's last cost. **Never `pytest tests/<module>.py`**:
a path collects the spawning tier too. A gate-semantics change needs a broken probe: plant the
drift in a scratch copy of a fixture and see the gate FAIL. A write verb under test writes to
scratch, never to a fixture in place.

**The CLI from this tree is `uv run -q agentic-sdlc …`** (`make pm ARGS="…"` is the same). Never
`uvx --from <path>`: uv caches a built wheel by version and serves stale code.

## Self-hosting

- `pm/roadmap/` is a real PM tree; `devkit.toml` turns on every rule except D8 (we bump at close).
  `make check` must exit 0 here.
- **Every installer's output is installed here, byte-current with its source.** Edit the source
  under `src/agentic_sdlc/repo/installables/` or `src/agentic_sdlc/repo/pm/guidance/`, then
  re-install with `--force`. `tests/test_install.py` fails a copy edited in place.
- CI runs `make milestone`, once, on the release PR.
- A rule that fails on this repo gets fixed, not turned off — unless it encodes a flow this
  package does not run, recorded with `pm decide`.
- **Releases** go through the `/release` skill. Never tag by hand (rule 7 holds the two sites).

## Reporting to Chris

**Every decision he needs to make goes in a numbered `NEEDS YOU` list at the TOP**, each item a
decision — not an observation — carrying the thing being decided: a path, a hash, the content
itself. When nothing needs him, say "nothing needs you".

- **Gate output only when it FAILED, or when you ran it yourself** — one line, never a pasted
  PASS block.
- **Numbers, not adjectives.** "228 files, census unchanged", not "verified thoroughly".
- **Say what you did NOT verify.** A claim with an unstated gap is worse than a gap.
- **Write ASD-STE100 Simplified Technical English** in live replies, commit messages and PR
  bodies: short sentences, active voice, one instruction per sentence, one word for one meaning.
  Use the fewest words that do the job.
