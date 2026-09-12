# CLAUDE.md — agentic-sdlc

**A reader/writer over a PM tree, shipped as a pinned-tag Python package.** `pm` writes one
status; `check` reads the same files and echoes findings and warnings; a belt (`close story`,
`close feature`, `release`, `adopt`) is its checks, then one write or a clean error, and `--force`
writes anyway on the record (D12). Consumers pin `DEVKIT_VERSION` in a Makefile and run it through
`uvx`; every change here lands in their commit gates — **treat the CLI as a published API.**
Public repo, MIT.

**The README carries the why; this file is the enforceable form.** The northstar, in Chris's
words: *a simple local Jira — it creates the work, moves it, expresses what the states and the
flow are, and infers nothing. It just echoes state back.*

## Hard rules

**The numbers are an API: source, tests and hooks cite them, so this list is append-only.** A rule
is trimmed inside itself, never renumbered or reordered; a new rule takes the next number.

1. **Stdlib only, forever.** No runtime dependencies; Python 3.11+ (`tomllib`). The reason is
   the HOOK CORPUS: `tools/hooks/` parses its payload with bare `python3 -c`, a consumer's system
   interpreter with no managed environment, so a transitive dependency there is a broken commit
   on someone else's machine. The package's own runtime resolves through `uvx`/`uv run` and is
   not exposed to that — the rule still binds it, and what actually blocks the tempting libraries
   is **rule 3** (byte-exact preservation) and **rule 6** (line shapes), not this one. Recorded
   with the audit at `ms-the-rule-reaches-the-work` D4.
2. **Pure text — boots nothing.** Every verb reads git, markdown and shell as text; nothing starts
   a build, an import or a cache. Safe anywhere, any time, in parallel.
3. **A write touches only what it was asked to touch.** `pm` rewrites ONE frontmatter line and
   preserves every other byte, line endings included; an installer writes a whole file or refuses
   by path. A verb that cannot guarantee a correct result refuses and says why. Writes are
   idempotent: the same command twice is a no-op the second time.
4. **Two cardinal sins, one shape.** A gate that misses drift and prints PASS; a write that looks
   legitimate and is not. Both are worse than a crash. Prove the census matches intent — a gate
   scanning 0 files FAILS and says so. An LLM recovers from an error and cannot recover from a lie.
5. **Config over forks, and the byte-identical guarantee is GATES-ONLY.** Per-project variation
   is the consumer's `devkit.toml`, never an edit to the tool. A GATE key has a stock default
   behind it, so a repo with no `devkit.toml` runs every gate byte-identically to one declaring
   them — and the seed carries that key COMMENTED at exactly the value the code holds, which
   `tests/test_config_seed.py` compares key by key and fails on by name. A WORKFLOW key has
   nothing behind it: `[pm.states.*]` and `[verify]` are the project's own declaration, spelled
   out with their argument, and each reader refuses BY NAME when its section is absent. So the
   FILE is not optional even though every gate key in it is — a tree with no `[pm.states.*]` has
   no working `pm` at all. `pm config --seed` prints the seed the pinned tool ships, which is what
   a BUMP reads; `init` serves a new repo once.
6. **Exit codes are contract:** 0 pass, 1 findings, 2 usage or config error. Output line shapes
   are grepped by consumers; changing one is a **minor** bump at least.
7. **Semver, enforced by habit:** patch = same interface; minor = a new verb, flag, config key or
   output shape; major = a consumer Makefile or hook must change to survive. `__version__` in
   `src/agentic_sdlc/__init__.py` and `version` in `pyproject.toml` move together, always.
8. **This package knows nothing about its consumers.** No file names a consuming project, reads a
   path outside this checkout, or gates on another repo's state. Realistic data is VENDORED under
   `tests/fixtures/`. A worked example names a shape, never a repo.
9. **Express, never infer.** The tool lets a project declare its grains, states and flow; create
   work, move it, and ask where it is. It never decides what a move MEANS or what should happen
   next. The edge is one question: *is this reading what the project declared, or deciding what
   the project should do?* A malformed declaration — a state in no category, a value of the wrong
   shape — is refused at exit 2: reading. A fact about the tree — *"3 stories not in `done`"* —
   is reported and the caller decides. **`pm` moves and reports; `check` gates; a belt checks,
   then writes one status or refuses; `--force` is the deviation, recorded in the ledger.**
10. **Test what BITES, the cheapest way that can fail.** A test earns its place by gating
    something that would cost real time if it broke: a load-bearing module, a path consumers run
    daily, or one of rule 4's sins. A function call before a temp tree, a temp tree before a
    process. **Prove it once**: before a new case, name the one that already covers this or can
    be amended to; a new case is warranted only when neither exists. A tier that got slower is a
    finding.
11. **Absence is a finding, and a capability advertises itself where you stand.** The operator
    here is usually an LLM with no memory of last week, and its failure mode is not getting things
    wrong — it is **not knowing they exist**. So: something the tree needs and does not have gets a
    NAMED line, never silence (a milestone past `todo` with no handoff; a grain with no binding; a
    courier wired to write and writing nothing). And a capability this package HAS is named in the
    surface someone is standing in when they need it — a column on the read verb, a word in
    `--help`, a line in the rule that auto-loads, a description on the skill. Rule 4 forbids the
    tool LYING; this one forbids it staying quiet. **The test: could someone hand-roll a thing this
    package already does, and would anything have stopped them?** Fix at the cheapest layer — a
    word, a column, a warning, a caller — never a new capability. Tree absences join `check pm`'s
    WARN family; `verify --plan` printing `unknown` rather than a guess is the same rule.

    **And the same rule, as a move you make rather than a property the code has — because a
    constraint only fires once you are already inside the mistake.** Before you write a script to
    measure this tree, or paste a prompt, ASK IT: `pm ledger report` (units, spend by agent,
    time per state; `--tree` for gate cost), `pm list` (any grain, as lines), `check <gate>`, `agentic-sdlc dispatch
    --grain <id>` (the contract a subagent needs). `TestACapabilityIsCitedWhereItsOperatorStands`
    holds the other direction: every verb the routers declare is cited in a surface an operator
    reads.

    **Read verbs emit LINES; composition is the shell's job.** The rule's read side, and the
    reason it has one: a read verb that omits a field people filter on does not just inconvenience
    them, **it teaches them the tool cannot do it**. `pm list` withheld the name, so
    `pm list | grep` returned nothing and the answer proposed was a new `--grep` flag. So: every
    read verb names its columns in order in `--help`, and if you cannot pipe something the missing
    thing is a **column**, never a verb. Existing filter flags stay — removing them breaks
    consumers for a purity nobody asked for — and the rule governs the next one. **A capability
    nobody can find is a capability you do not have**; when a request is met by hand-rolling
    something this package already does, the defect is the surface, not the requester.

## Where things live

`ls src/agentic_sdlc` is the inventory; this is the rule:

- **`src/agentic_sdlc/core/`** knows no family: `project.py` finds the repo and loads config,
  `config.py` decides what a config VALUE may be. It imports nothing from `repo/`.
  **It also holds THE PRIMITIVES, each the one place this package does one thing** — `walk.py`
  enumerates, `apply.py` mutates, `frontmatter.py` reads and writes a frontmatter block, `spawn.py`
  starts a process. Reach for one before writing the operation; `tests/test_boundaries.py` holds
  each with an exact allowlist and an empty offender list, so a second implementation fails by path.
- **`src/agentic_sdlc/repo/`** is the tool — the `pm` tracker, the checks, the belts, `verify`,
  and `install.py` with the files it writes under `installables/`. It imports `core/`, never the
  reverse. The router is `src/agentic_sdlc/cli.py`, a SIBLING of both: it only routes, and each
  verb module owns its behaviour and its `--help` docstring.
- **New check** = module in `src/agentic_sdlc/repo/checks/` + `KNOWN_GATES` in
  `src/agentic_sdlc/cli.py` + a
  README row + the grain's `changelog:`. **New verb** = module + route + README row + `changelog:`;
  a verb that WRITES also needs a refusal path with a test, and an idempotence test. **New test** =
  first the search (rule 10), then the cheapest tier, then a row in the story's
  `## How this is proven` table.
- **Every config value goes through `src/agentic_sdlc/core/config.py`.** Never
  `tuple(cfg.get(...))` — a bare string is iterable.
- **The committed fixtures ARE the fixtures.** `tests/fixtures/` holds purpose-built repos, hook
  payloads and transcripts, versioned with the code that reads them. `unit` / `integration` /
  `test` select on the `shell` mark, DERIVED in `tests/conftest.py` from whether a module's
  source spawns; a hand-written mark is a collection refusal.
- **`changelog:` is a field on the grain**, one consumer-visible sentence or the word `none`;
  `agentic-sdlc changelog <id>` renders them in `order:`. `CHANGELOG.md` is retired (0.6.0).
  Rationale with a rejected alternative is `pm decide`, not a release note.

## The ladder

Never hand-roll an incantation, and never run a rung wider than the thing you changed.
`make help` is the target list; if the check you need is not a target, add one to `Makefile.tiers`.

| you changed | run |
|---|---|
| the PM tree, or a doc | `make check` |
| code, inner loop | `agentic-sdlc verify --story` — `make unit`, the `[verify] story` target |
| code, before a commit | `make precommit` |
| closing a story | `agentic-sdlc close story <id>` |
| closing a feature | `agentic-sdlc close feature <id>` — `make test` is `[verify] feature` |
| closing a milestone | `agentic-sdlc release <version>` — its `gate` check is `make milestone` |

`agentic-sdlc verify --plan` prints each rung with the cost it last took, from the ledger — ask it
rather than guessing. **Never `pytest tests/<module>.py`** — selecting by path collects the module's
spawning tier too, and those cases run `make` against this repo; `make unit` (or `-m "not shell"`)
is the rung. Outside that tier a spawn now fails the test by nodeid, because prose did not hold it.
A gate-semantics change needs a deliberately-broken probe: plant the drift
class in a scratch copy of a fixture and confirm the gate FAILS; a bad config value exits 2; a
zero-file census FAILS. A write verb under test writes to scratch, never to a fixture in place.

**The CLI from this tree is `uv run -q agentic-sdlc …`** (`make pm ARGS="…"` is the same thing):
the working tree installed on itself, re-synced every call. Never `uvx --from <path>` — uv caches
a built wheel by version, so an unchanged version number serves stale code.

## Self-hosting

This package runs its own tooling on its own tree, and that is a gate, not a demo.

- `pm/roadmap/` is a real PM tree, and `devkit.toml` turns on every rule this package ships
  except D8 (it encodes bump-at-start; we bump at close). `make check` must exit 0 here. Work
  follows [`SDLC.md`](SDLC.md): a milestone branch, `main` merge-commit-only at close.
- **Every installer's output is installed here, byte-current with its source, or legitimately
  absent.** `Makefile.devkit` + `tools/dev/gdk_gate.sh` (`install-gates`);
  `.github/workflows/verify.yml` (`install-ci`); `tools/hooks/`, `tools/dev/agent-worktree.sh`
  and `tools/setup-hooks.sh` (`install-hooks`, with `.claude/settings.json` carrying the entries
  it prints); the verification pair under `.claude/agents/` (`install-agents`);
  `.claude/rules/pm-execution.md` + `.claude/skills/pm-operations/SKILL.md`
  (`pm install-skills`); `docs/sdlc-protocol.md` (`install-sdlc`). Edit the source under
  `src/agentic_sdlc/repo/installables/` or `src/agentic_sdlc/repo/pm/guidance/` and re-install
  with `--force`; a copy edited in place is the invisible fork these verbs exist to prevent, and
  `tests/test_install.py` fails it. The hooks' `project config` headers are this repo's, and a
  header-only difference is allowed. `bash tools/setup-hooks.sh` arms them.
- CI runs `make milestone` — the same target as the local full gate — after an arming step
  guarded on `tools/setup-hooks.sh`, because a fresh checkout is not armed.
- If a rule fails when pointed at this repo, the finding gets fixed. Turning a rule off is only
  right when it encodes a flow this package does not run, recorded with `pm decide`.
- **Releases** go through the `/release` skill: `agentic-sdlc release <version>` on this tree,
  then its `next:` lines by hand. Never tag by hand (rule 7 holds the two version sites).

## Reporting to Chris

**Every decision he needs to make goes in a numbered `NEEDS YOU` list at the TOP**, each item a
decision — not an observation — carrying the thing being decided in the message: a path, a hash,
the content itself. When nothing needs him, say "nothing needs you".

- **Gate output only when it FAILED, or when you ran it yourself** — one line, never a pasted
  PASS block.
- **Numbers, not adjectives.** "228 files, census unchanged", not "verified thoroughly".
- **Say what you did NOT verify.** A claim with an unstated gap is worse than a gap.
