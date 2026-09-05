---
id: 0.2.0/adopt-is-a-conveyor/02-adoption-verifies-the-adoption-not-the-game
feature: 0.2.0/adopt-is-a-conveyor
milestone: "0.2.0"
name: Adoption verifies the adoption, not the game
status: reviewing
owner:
depends_on: ["0.2.0/adopt-is-a-conveyor/01-adopt-walks-the-adoption"]
---

# Adoption verifies the adoption, not the game

`agentic-sdlc adopt` finishes in seconds on a consumer whose own gate set takes minutes,
because it runs **this package's** `check all` and never the consumer's `make check`. The
consumer's twenty gates verify the consumer's code against the consumer's rules, and a version
bump here cannot change their verdict. Running them during adoption re-verifies the game.

Measured on the live consumers and quoted in the feature file: `check all` is **2.6 s**,
`check pm` is **0.3 s**. That subtraction is the entire point of this feature, it is one line
of code, and it is exactly the kind of line that regresses back to `make check` the first time
someone "makes adoption more thorough". So it gets a test of its own that names the thing it
must not do.

## The three steps a human list keeps forgetting

- **`checks-pass`** — `agentic-sdlc check all` in this checkout. Not `make check`. Not
  `make precommit`. Not `[gates] extra`, which is by definition the *project's own* gates
  (`gates_extra.py`'s first paragraph).
- **`hooks-self-test`** — `install-hooks` rewrites guard scripts, and a guard that fails OPEN is
  not there. This package has already shipped a hook that was installed, executable, and
  stopping nothing; a config diff cannot show that, and no amount of reading can.
- **`runner-targets-resolve`** — `install-runners --force` rewrites `Makefile.devkit`, which
  defines the targets every later gate runs through. Broken there, every subsequent gate fails
  for the wrong reason and the operator debugs the wrong thing. `0.2.0/the-middle-tier-splits`
  makes this sharper, not softer: the composition moves into `Makefile.tiers` behind an
  `-include`, and **an `-include` of a missing file is silent by design**. A step that resolves
  the targets is the only thing standing between that silence and a green adoption over a gate
  set that is not there.

## The steps and their kinds

| step | kind | postcondition | notes |
|---|---|---|---|
| `pin-bumped` | judgement | `DEVKIT_VERSION` names the running version | story 01 |
| `installables-diffed` | automatic | each `install-*` verb's `--diff` has been produced for this run | it PRINTS; the artifact is the operator having seen it, so its `verify()` is that the run recorded the diff, not that a human read it |
| `installable-decisions-recorded` | judgement | every diffed file is either byte-current or named in the run's record with a decision | the `--force` is whole-set (`SKILL.md` step 8), so per-file is a human call |
| `config-updated` | judgement | no `devkit.toml` key the new version RETIRED is still declared | `config.section_declared` answers the "declared empty" half already |
| `hooks-self-test` | gate | the installed hooks' self-test exits 0 | the replay over the hooks THIS kit installs — per the audit's ruling, the Godot sandbox corpus is `godot-devkit`'s |
| `runner-targets-resolve` | gate | every target the framework composes from resolves in this repo's make | `make -n` on the composed targets; a missing `-include` file is a FAILURE here, never a silence |
| `checks-pass` | gate | `agentic-sdlc check all` exits 0 or 1 per the roster, and 2 is a failure | the subtraction |
| `pm-validates` | gate | `agentic-sdlc pm validate` exits 0 | the tree is still good against the new version |

## Refusal matrix — the step surface (SDLC.md §5)

| input | expected |
|---|---|
| a consumer with `[gates] extra` declared | `checks-pass` runs `check all` and NOT the extra targets; asserted by a command recorder |
| a consumer whose `make check` would fail | `adopt` still completes — the failure is the consumer's own gate and not this operation's business |
| a repo with no `Makefile.devkit` | `runner-targets-resolve` refuses naming the file; it does not install one |
| `Makefile.tiers` named by `GDK_TIERS_MK` and absent | **FAIL**, naming the file — never the `-include`'s silence |
| a hook installed but not executable | `hooks-self-test` FAILS; the "installed, executable, stopping nothing" case fails too, proven with a deliberately-neutered guard in a scratch copy |
| a `check all` roster that scans **0 files** | FAIL, loudly — rule 4's zero-census rule, restated at this layer |
| `check all` exits 2 (a config error) | the step FAILS and says so is a config error, distinct from findings |
| a PM tree with a dangling `reviewed:` pointer | `pm-validates` fails naming the path |
| a `devkit.toml` declaring a retired section, empty | `config-updated` names it — the "declared empty" case, which `config_section` alone cannot see |
| any step reading a path outside the repo root | impossible, asserted by story 01's recorder — restated here per step |

## Acceptance criteria

1. **The subtraction, named.** `tests/test_adopt_steps.py::test_checks_pass_never_runs_make`
   runs the full list in a scratch consumer whose `Makefile` has a `check` target that writes a
   sentinel file, and asserts the sentinel does not exist. It also asserts the recorded command
   is `check all` and contains neither `make` nor any target from `[gates] extra`. This is the
   one line of the feature that is easy to write correctly and easy to regress
   (`adopt-is-a-conveyor` ship criterion 2), so the test names it in the failure message.
2. `hooks-self-test` FAILS on a scratch copy of a fixture repo whose guard was neutered to exit
   0 unconditionally — a deliberately-broken probe, per CLAUDE.md § Verification loop, and the
   test must be watched failing before the step exists.
3. `runner-targets-resolve` FAILS when `Makefile.tiers` is named and absent, and names it.
   Watched failing against a step that only ran `make -n check`.
4. `checks-pass` treats exit 2 as a step failure with a different message from exit 1, and a
   zero-file census as a failure — asserted separately.
5. Every automatic and gate step is idempotent: the second run reports already-true and changes
   no bytes in the tree.
6. Every step's `verify()` catches a `do()` that did not take (the release feature's story 01
   contract, applied per step here).
7. Every row of the refusal matrix is a test, on scratch copies — never on a fixture in place.
8. The adopt list renders in `docs/sdlc-protocol.md` beside the release list, satisfying this
   feature's ship criterion 4. **The renderer is `the-release-is-a-conveyor/05`'s file**; this
   story only asserts the output contains all eight steps with their kinds.

## Files this story may touch

- `src/agentic_sdlc/repo/conveyor/adopt_steps.py` — NEW (all eight steps)
- `tests/test_adopt_steps.py` — NEW
- `tests/fixtures/` — a scratch consumer fixture carrying a `Makefile` with a sentinel `check`
  target, an installed-but-neutered guard, and a `Makefile.devkit` composing from a
  `Makefile.tiers` (vendored here, rule 8)

## Files this story must stay out of

`src/agentic_sdlc/repo/conveyor/adopt.py` and `src/agentic_sdlc/cli.py` (story 01), every file
owned by `the-release-is-a-conveyor` (`driver.py`, `state.py`, `config.py`,
`release_steps.py`, `skip.py`, `render.py`, `install.py`, `core/config.py`, `pm/ledger.py`),
`Makefile.devkit` and `installables/Makefile.devkit` (owned by `0.2.0/the-middle-tier-splits`,
phase 2 — this story READS the seam it left and must not move it).

## Out of scope

- Making the consumer's own gates faster, or scoping them. `verify --changed` is
  `0.2.0/the-story-belt-knows-what-verifies-this-edit`.
- Installing anything. `adopt` diffs and decides; the `install-*` verbs write.
- Any change to `check all`'s roster or to `[gates] extra`.
