# Feature review — `0.2.0/the-extraction-finishes`

Feature-level pass (SDLC.md §0) over the commit range its four stories name in their `## Close`
blocks: `268fa44`, `69df2df`, `650dc45`. Branch `milestone/0.2.0-the-conveyor`, run 2026-09-05.

This is **not** a re-run of `docs/reviews/2026-09-05-0.2.0-release-review.md`. That pass owns M4
(`shell.py:35`'s `rglob` reddening `test_boundaries.py`), which is the only finding it filed
against this feature's range; it is not re-filed here. What follows is the cross-story question
that pass could not ask: four stories all edited `cli.py` and its census tests, and this asks
whether the censuses they installed close in both directions.

**Verdict: SHIP-WITH-FIXES.** The defect the feature was written to kill is dead and proven
dead by execution. Three of the four censuses it shipped are one-directional, and one live verb
is already sitting in the gap.

---

## What holds

The headline is real and was re-derived, not read:

- **`KNOWN_GATES` is six names and every one dispatches.** `uid`, `tres`, `props`, `defaults`,
  `rng`, `tres-comment`, `unit-disk`, `test-shape` are gone from the dict and from
  `_unknown_check`'s message. `_check_module` DERIVES the import path from the name, so the
  `if` chain that was the second roster no longer exists — the dict is the only list.
- **`check all` on this repo, my run:** `doc` PASS, `grain-shape` PASS (48 documents),
  `pm` PASS, `shell` PASS, `hooks` PASS. `agentic-sdlc install-runners` correctly answers
  `unknown command` at exit 2 (which is also finding E1, below — the README still tells a
  consumer to run it).
- **The wheel is clean, built and unzipped rather than inferred.** `uv build --wheel`:
  **84 entries**, top level under `agentic_sdlc/` is `__init__.py`, `cli.py`, `core/`, `repo/`.
  No `data/`, no `classdb.json`, no `.tscn`, no `.tres`. The Close block in story 03 says 84;
  `tests/test_wheel_payload.py`'s docstring says 85. The Close block is the accurate one.
- **`--help` no longer advertises the fourteen scene verbs.** Parsed back out of the docstring:
  `adopt check close gates-extra init install-agents install-ci install-gates install-hooks
  install-sdlc pm release verify` — thirteen, all routed.
- **The sweep list in `feature.md` was completed.** `pyproject.toml`'s `description` and
  `keywords` describe this package; `devkit.toml` carries no `[uid]`/`[tres]`/`[props]`;
  `RETARGET_FLAG` and `tests/support.temp_repo` are gone with the census entry that held the
  latter alive updated in the same change (`tests/test_shell_mark.py:77` documents the removal);
  `FIXABLE_CHECKS` is an empty `frozenset` with the plumbing and its refusal test kept, argued
  in place. `tests/fixtures/kitchen_sink.tscn` and `tilemap.tscn` are deleted.
- **The ruling the feature said it needed was made and executed elsewhere in the milestone.**
  `cc-godot-sandbox.sh` left; `model.py`'s D8 `version_file` default is `pyproject.toml`
  (`model.py:213`, `:284`).

## Findings

### E1 — MINOR — README's installer table still describes the half that left

`README.md:166` (`install-ci`) opens *"The four workflows a Godot project runs on a push"* and
documents `uid-guard.yml`; `install-ci` installs three workflows now and `ci-uid-guard.yml` is
deleted from `installables/`. `README.md:168` (`install-hooks`) lists `cc-godot-sandbox.sh` and
`checks/doctor.sh` as things the verb writes, and instructs the reader to *"wire `bash
tools/hooks/cc-godot-sandbox.sh --self-test` into your static gate"*. Neither file ships. I ran
`install-hooks` into a scratch repo: seven files, none of them either one.

Story 04's Close claims the first surfaces describe this package, and `69df2df` did rewrite
README (-261/+137). The installer table is the largest first surface in it and three of its rows
still describe the other kit. The `install-runners` row is filed separately, against the feature
that renamed the verb (`the-middle-tier-splits`, T3), because that is one edit with one owner.

Nothing gates this: `[doc] scope` is `CLAUDE.md` + `.claude/rules/*.md` + `.claude/agents/*.md`,
and README is deliberately outside it.

### E2 — MINOR — `version` is routed, works, and is documented nowhere

`cli.py:368` routes `-V`, `--version` and `version`. `PYTHONPATH=src python3 -m
agentic_sdlc.cli version` → `agentic-sdlc 0.1.0`, exit 0. The docstring never names it.

`tests/test_cli_surface.py` claims both directions and cannot see this one:
`routed_verbs()` returns `{'pm','init','gates-extra','check','verify'}` plus the two rosters it
asks (`install_commands()`, `conveyor_verbs()`). The five singletons are hand-written — the file's
own docstring calls a hand-written roster *"the same defect one layer down"* — and `version` is a
sixth branch that is in neither set, so `documented - routed` and `routed - documented` are both
empty over a verb that ships. The direction the docstring names as *"the direction that goes
wrong next: a verb nobody can discover"* is unasserted for exactly the branches `main()` writes
longhand.

### E3 — MINOR — `roster == dispatchable` is asserted in one direction only

The story is titled `roster-equals-dispatchable`. `tests/test_gate_roster.py` proves
roster → module (`test_every_declared_gate_resolves_to_a_module`, `test_every_resolved_module_
exposes_run`) and proves that a name outside the roster resolves to nothing. It never proves
module → roster: nothing enumerates `src/agentic_sdlc/repo/checks/*.py` and asserts that set
equals `KNOWN_GATES`. Grepped: `tests/test_gate_roster.py` is the only file in `tests/` that
mentions `KNOWN_GATES` at all.

Today the two sets match (six modules, six keys), so this is latent. It is the step CLAUDE.md's
own recipe puts a gate on — *"New check = module in `repo/checks/` + a key in `cli.py`'s
`KNOWN_GATES`"* — and the failure it admits is a gate authored, reviewed, shipped in the wheel
and never run in any consumer. That is `the-kit-owns`' thesis (*a guard nobody wired is not
there*) arriving through the roster instead of through a Makefile. The prune was the small half;
the census is the deliverable, and half a census is what let eight names live for two releases.

### E4 — NIT — the wheel-payload exemption matches a directory name anywhere in the path

`tests/test_wheel_payload.py:46` — `if set(rel.parts) & set(DELIBERATE_PAYLOAD): continue`. The
three exempt names are matched against **every** component of the path, not against the first, so
any new blob under a directory named `installables`, `templates` or `guidance` at any depth is
exempt: `src/agentic_sdlc/data/templates/classdb.json` re-ships green. `test_the_godot_payload_
is_gone_and_named` catches that one literal path (`data/` and `classdb.json` are named), and
nothing catches the next one.

Same file, same nit: the docstring says the wheel was proven at *"85 entries"*; the build at HEAD
is 84.

## Ship criteria

`feature.md` states no numbered ship criteria; these are its own stated deliverables, read as
criteria.

| # | deliverable | verdict |
|---|---|---|
| 1 | a stock consumer's `check all` no longer exits 2 | **met** — the milestone review re-derived this in a fresh `git init` with no `devkit.toml` (doc FAIL, shell FAIL, grain-shape PASS, EXIT=1); `tests/test_gate_roster.py::TestAStockConsumer` runs the same path |
| 2 | `roster == dispatchable` as a test, "the deliverable, not the pruning" | **caveat** — one direction only (E3) |
| 3 | `--help` names what ships | **caveat** — the fourteen scene verbs are gone and both directions are asserted for the two rosters, but `version` is routed and undocumented and the test cannot see it (E2) |
| 4 | the wheel carries only what has a reader | **met** — 84 entries, built and unzipped, no engine payload (E4 is about the guard's future, not this tree) |
| 5 | the first surfaces describe this package | **caveat** — `pyproject.toml`, `devkit.toml`, `CLAUDE.md` and README's prose are done; README's installer table is not (E1) |
| 6 | a ruling on `cc-godot-sandbox.sh` and D8's default rather than a sweep | **met** — the hook left, D8 defaults to `pyproject.toml` |

## Close-block claims checked against the tree

Every `## Close` line in the four stories was checked against `git show` for the commit it names.

- Story 01, 02 — **true**. `268fa44` carries `cli.py`, `tests/test_gate_roster.py`,
  `tests/test_cli_surface.py`.
- Story 03 — **one commit is wrong.** It says *"done: 268fa44 — data/classdb.json (129,490
  bytes, zero readers), RETARGET_FLAG, two orphan .tscn fixtures and support.temp_repo
  removed"*. `268fa44` deletes the two `.tscn` fixtures and rewrites `tests/support/__init__.py`;
  `src/agentic_sdlc/data/classdb.json` is deleted by **`69df2df`**, the next commit. Not filed as
  a finding — both commits are named in this feature's own range and the work is all present —
  but the evidence line points a future session at a commit that does not contain half of what it
  claims.
- Story 04 — **true as to what it names** (`69df2df` for README/CLAUDE.md/devkit.toml,
  `650dc45` for the `check shell` cause). The claim it does not make, and which E1 is about, is
  that README as a whole now describes this package.

One shape worth naming for the next level: `268fa44` is a single commit carrying three stories'
code changes plus twenty-three PM documents and a scope audit. Three `## Close` blocks therefore
name one hash and none of them is separable by it. That is why story 03's mis-attribution was
invisible until this pass.

## What I ran

- `uv run --python 3.11 --with pytest python -m pytest tests/test_gate_roster.py
  tests/test_cli_surface.py tests/test_wheel_payload.py tests/test_fresh_project.py
  tests/test_makefile_include.py tests/test_consumer_independence.py tests/test_grain_shape.py
  tests/test_check_hooks.py -q` → **152 passed, 1 skipped, 30.20 s**.
- `PYTHONPATH=src python3 -m agentic_sdlc.cli check all` on this repo → all five gates PASS.
- `PYTHONPATH=src python3 -m agentic_sdlc.cli check doc` → PASS, 0 unresolved claims.
- `PYTHONPATH=src python3 -m agentic_sdlc.cli version` / `--version` → `agentic-sdlc 0.1.0`,
  exit 0, and the verb appears in no `--help` line.
- `PYTHONPATH=src python3 -m agentic_sdlc.cli install-runners --diff` → `unknown command`.
- `uv build --wheel` into a scratch dir, then `zipfile.ZipFile(...).namelist()` → 84 entries,
  top level `__init__.py cli.py core repo`, no `data/`.
- `install-hooks` into a `tempfile` scratch repo → seven files written; no
  `cc-godot-sandbox.sh`, no `checks/doctor.sh`.
- Documented-verb list parsed back out of `cli.__doc__` and diffed against `main()`'s branches by
  hand.

## What I did NOT verify

- **`make milestone`, `make gates`, `make fuzz` and the interpreter matrix were not run.** Only
  the eight modules above, on 3.11.
- **The full suite was not re-run**, so M4's red (`tests/test_boundaries.py::OneWalk`) was not
  re-observed; it belongs to the milestone pass and its disposition there is `landed 4de8f9e`.
- **E3 was not proven by construction.** I did not add a seventh module under `repo/checks/` and
  watch the suite stay green; the claim rests on reading the two tests and grepping `tests/` for
  every reference to `KNOWN_GATES` (one file).
- **E4's bypass was not executed** — no `data/templates/` blob was planted and the suite re-run.
- **The README was not read end to end.** I read its installer and gate tables; drift elsewhere
  in a 240-line document is unmeasured.
- **The tree was live.** `check grain-shape` reported 46 PM documents at one point in this pass
  and 48 minutes later, so other builders were writing under `pm/roadmap/` throughout. Nothing
  above depends on a `pm/` count; the source and test files named were all read at HEAD with a
  clean `git status`.

Reviewer's token cost: ~100k for the three-feature pass, of which this record is one part.

```
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| E1 | MINOR | open: README.md:166,168 — the install-ci and install-hooks rows name workflows and hooks that no longer ship |
| E2 | MINOR | open: `version` is routed at cli.py:368 and named in no --help line; routed_verbs() cannot see it |
| E3 | MINOR | open: nothing asserts repo/checks/*.py is a subset of KNOWN_GATES |
| E4 | NIT | open: DELIBERATE_PAYLOAD matches any path component; docstring says 85 entries, the wheel has 84 |
```
