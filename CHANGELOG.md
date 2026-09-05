# Changelog

## Unreleased

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
