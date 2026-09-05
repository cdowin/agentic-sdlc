# Feature review — `0.2.0/the-middle-tier-splits`

Feature-level pass (SDLC.md §0) over the commit range its three stories name in their `## Close`
blocks: `b9cf082`, `f504ab5`. Branch `milestone/0.2.0-the-conveyor`, run 2026-09-05.

Not a re-run of `docs/reviews/2026-09-05-0.2.0-release-review.md`. That pass filed nothing
against this range. The cross-story question it could not ask: story 01 built the tier seam,
story 02 built the guard on it, story 03 emptied the roster the seam replaced — and the guard
story 02 shipped is scoped to the failure story 01 was worried about rather than to the one make
actually produces.

**Verdict: HOLD.** Criterion 2 — *"a tier name that resolves to no target is a **loud** failure,
not a silently-shorter gate"* — is met for the shape the feature designed against and fails, at
exit 0 with no output, for the shape a real consumer hits first.

---

## What holds

- **Criterion 1 is met.** `Makefile.devkit` is 249 lines and names no language target.
  `tests/test_consumer_independence.py` grew the operative-token clause (`ENGINE_ARTIFACTS`,
  scanned across `src/`, `tools/`, `.github/`) and its `ENGINE_TOMBSTONES` dict ships **empty** —
  the assertion story 03's Close claims, and it is true: `ENGINE_TOMBSTONES: dict[str, str] = {}`
  at `tests/test_consumer_independence.py:134`. Banning tokens rather than the word is the right
  call and it is the reason the dict can be empty.
- **Criterion 3 is met and I ran it.** In a scratch consumer with no `Makefile.tiers`,
  `make -n precommit` emits, first, ahead of the gate:
  `[TIERS] GDK_PRECOMMIT_TIERS is empty — this gate is 'check' alone; Makefile.tiers is not
  present`. The distinction between *absent file* and *file present declaring no tier* is carried
  in that one line by `$(if $(wildcard …))`. A pure-SDLC consumer is a supported shape and says
  so.
- **Criterion 2's first half is met.** `GDK_PRECOMMIT_TIERS := parse nosuchtier` stops at parse
  time: `Makefile.devkit:222: *** GDK_PRECOMMIT_TIERS names a tier no makefile defines:
  [nosuchtier] … Stop.`, exit 2, before `.gate-reports/` exists. The typo'd-`GDK_TIERS_MK` shape
  is caught by the sibling guard at `:212`. Both were run.
- **The `MAKEFILE_LIST` scan does not false-positive on a tier defined in the consumer's own root
  Makefile after the `include`** — awk reads the whole file, not the lines make has consumed. Ran
  it; `roottier` resolved.
- **Criterion 4 is met.** `tests/test_makefile_include.py` covers tiers-absent and tiers-present
  with two targets each, plus `--warn-undefined-variables` on both paths, plus the two refusals.
  59 tests, all green in my run.
- **`install-runners` → `install-gates` is real** and the rename is argued in `install.py:46`
  rather than merely done.

## Findings

### T1 — BLOCKER — a declared tier can be silently skipped, and criterion 2's guard cannot see it

`src/agentic_sdlc/repo/installables/Makefile.devkit:218-227`, and it is a **measured exit 0**.

The orphan guard asks one question: is this tier name defined as a target somewhere in
`MAKEFILE_LIST`? Make asks a different one at run time: is this prerequisite **out of date**? A
target that is defined and whose name matches an existing file or directory, with no `.PHONY`, is
up to date, so make runs its recipe **not at all and says nothing**.

Scratch consumer, `tempfile`, `DEVKIT_VERSION := v0.2.0`, `Makefile.tiers`:

```make
GDK_PRECOMMIT_TIERS := parse test
parse: ; @echo "TIER parse ran"
test:  ; @echo "TIER test ran"
```

with a directory `test/` present (and no `.PHONY`, which is the whole of the defect):

```
$ make precommit
stub check ran
TIER parse ran
$ echo $?
0
```

`test` is in the declared tier list, `test` is a defined target, `test` did not run, exit is 0,
and **no line anywhere says a gate was skipped** — not the orphan guard (the target exists), not
the `[TIERS]` announcement (the list is non-empty), not make (a satisfied prerequisite is
silent). That is criterion 2's own sentence inverted: *"a gate list that quietly gets shorter is
the one failure a gate must never have"*, and *"a one-gate run that reads as a five-gate run is
rule 4 wearing a Makefile"* (`b9cf082`'s message).

This is not exotic. `test`, `docs`, `bin`, `lint`, `build` and `tools` are all plausible tier
names and all plausible directory names, and a language kit's `install-gates`-equivalent writes
the tier file for the consumer — so the consumer never sees the `.PHONY` line it depends on.

The requirement exists and is documentation only: lines 34-37, *"THE TIER FILE DECLARES ITS OWN
`.PHONY`. The `.PHONY` below can only list its own"*. Nothing enforces it. Every tier case in
`tests/test_makefile_include.py` uses `kit-`-prefixed names **with** `.PHONY: kit-parse …`
declared (lines 91, 435, 445, 458, 472), so no test can hit this; `test_phony_lists_exactly_what_
this_file_defines` (:508) guards the framework's own list and says so.

The framework's own compositions are safe — `.PHONY: help pm check precommit milestone …` at
:150 — so the exposure is exactly the tier seam this feature introduced.

Two shapes of fix, both cheap and both at parse time, where the rest of the guard already lives:
add each declared tier to `.PHONY` from `GDK_*_TIERS` (make accepts `.PHONY: $(GDK_PRECOMMIT_TIERS)
$(GDK_MILESTONE_TIERS)`, which costs nothing and needs no cooperation from the tier file), or
`$(error)` when `$(wildcard <tier>)` is non-empty for a declared tier name.

### T2 — MINOR — `CLAUDE.md:106` names an installable that does not exist

> *"A new target routes through the shipped `gdk_gate_capture` / `gdk_gate_verdict`
> (installables/gdk_runners.sh, sourced from source — this package is its own first consumer)"*

`src/agentic_sdlc/repo/installables/gdk_runners.sh` does not exist; the file is `gdk_gate.sh`.
`b9cf082` edited `CLAUDE.md` and this line was not among the four it changed, and `b9cf082`'s own
message says *"following the gdk_gate.sh rename was right"* — so the rename was in hand.

`check doc` PASSes over it: `[check:doc] PASS — 5 doc(s), 18 fenced line(s) skipped, 2
.claude/skills/ entr(ies), 0 unresolved claims`. Not a gate defect — `check_backtick_paths`
(`doc.py:187-202`) only reads backtick-wrapped spans, which is its documented subset, and this
path is bare prose inside a parenthesis. It is a defect in the one file that is loaded into every
session in this repo, pointing a future agent at a file that is not there.

### T3 — MINOR — README documents `install-runners`, a verb this feature removed

`README.md:169` is a full installer-table row for `install-runners`, describing
`tools/dev/gdk_runners.sh` and the runner set (`parse.sh`, `lint.sh`, `warnings.sh`, `unit.sh`,
`scenario.sh`, `capture.sh`, `compile_sweep.gd`, `hermetic_run_scan.sh`) — none of which ships.
The verb is gone:

```
$ PYTHONPATH=src python3 -m agentic_sdlc.cli install-runners --diff
agentic-sdlc: unknown command 'install-runners'
```

`install-gates` appears nowhere in README. `CHANGELOG.md:46` records the rename correctly, so the
fact was known and one of the two surfaces was updated.

CLAUDE.md's own recipe is *"New verb = module + `cli.py` route + README table row + CHANGELOG
line"*, and nothing asserts the README table against `install_commands()` the way
`tests/test_cli_surface.py` asserts the `--help` docstring against `main()`. This is the same
one-directional-census shape filed as E3 in
`docs/reviews/2026-09-05-the-extraction-finishes.md`, arriving through a different door.

(README rows 166 and 168 are stale for a different reason and are filed as E1 in that record, not
here — one edit, one owner.)

### T4 — MINOR — story 03's `## Close` credits two commits that do not contain the change

> *"done: b9cf082 f504ab5 — install-runners became install-gates; gdk_runners.sh split 881->405
> with gdk_gate_capture moved byte-for-byte"*

`git show --name-status` for both commits: neither touches `gdk_runners.sh` or `gdk_gate.sh`. The
split and rename are **`8f4e9c1`** (`fix(0.2.0/bugs): the deprecation window closes …`), which
deletes `gdk_runners.sh` and adds `gdk_gate.sh` alongside nine other engine installables;
`gdk_gate.sh` then grows in `6e9388d` and `cc0569d`. The `install-runners → install-gates` half of
the same sentence **is** in `b9cf082`, along with `install-ci` dropping `uid-guard.yml` and
`install-hooks` dropping the two Godot files.

The close evidence is what a future session trusts, and half of this line sends it to two commits
that contain none of it.

## Ship criteria

| # | criterion | verdict |
|---|---|---|
| 1 | `Makefile.devkit` names no Godot target; `test_consumer_independence.py` grows the assertion | **met** — 249 lines, no language target, operative-token ban, empty tombstone dict |
| 2 | compositions come from `GDK_*_TIERS`; a tier name resolving to no target is loud | **not met** — loud for an undefined name, silent at exit 0 for a defined name shadowed by a file or directory (T1) |
| 3 | with no `Makefile.tiers`, `make precommit` runs `check` alone and says so | **met** — ran it; the `[TIERS]` line distinguishes absent-file from declares-nothing |
| 4 | `tests/test_makefile_include.py` proves both shapes | **met** as written — and every tier case in it declares `.PHONY`, which is why T1 is invisible to it |

`feature.md`'s risk 1 named the mitigation as *"an empty tier list is fine, a NAMED tier that does
not resolve is not."* That mitigation shipped exactly as designed. T1 is the third shape neither
the risk nor the criterion anticipated: a named tier that **does** resolve, to nothing that runs.

## What I ran

- Scratch consumer in `tempfile`: `Makefile.devkit` copied out of `installables/`, a two-line root
  `Makefile`, five tier configurations. Results above, all reproduced from the shipped file.
  - no tier file → `[TIERS] … is not present`, dry run clean.
  - `parse nosuchtier` → `Makefile.devkit:222 *** … Stop.`, **exit 2**.
  - `parse test` + `test/` directory, no `.PHONY` → **exit 0, `test` never ran, nothing said**.
  - tier target defined in the root `Makefile` after the `include` → resolves, no false error.
  - missing `DEVKIT_VERSION` → `Makefile.devkit:79 *** … Stop.` ahead of every tier check.
- `uv run --python 3.11 --with pytest python -m pytest tests/test_makefile_include.py
  tests/test_consumer_independence.py … -q` (eight modules) → **152 passed, 1 skipped, 30.20 s**.
- `PYTHONPATH=src python3 -m agentic_sdlc.cli check doc` → PASS, 0 unresolved claims, over the
  dead path at `CLAUDE.md:106`.
- `PYTHONPATH=src python3 -m agentic_sdlc.cli install-runners --diff` → `unknown command`.
- `git show --name-status -M` for `b9cf082`, `f504ab5`, `8f4e9c1`, `6e9388d`;
  `git log --follow` on `gdk_gate.sh` and `git log --all` on `gdk_runners.sh`.
- `grep -rn install-runners` across the tree excluding `.git`.

## What I did NOT verify

- **No gate actually executed inside the scratch consumer.** `check` was stubbed, because the
  real recipe resolves `uvx --from git+https://github.com/cdowin/agentic-sdlc@v0.2.0` — a network
  fetch of a tag that does not exist yet. T1 is proven at the make level: the prerequisite did not
  run. The behaviour of `gdk_gate_capture` inside a tier was not exercised.
- **GNU make 3.81 only** (macOS system make). The shadowing behaviour is POSIX and I expect it
  identical on 4.x, but it was not run there, and `--warn-undefined-variables` interacts
  differently across versions.
- **`install-gates` output was not diffed** against `installables/` in a consumer, and
  `install-ci` / `install-agents` outputs were not inspected at all; `f504ab5`'s eighteen
  installable edits were read as a file list, not reviewed line by line.
- **The `ci-verify.yml` rewrite in `b9cf082` (103 lines) was not run.** No CI run was observed.
- **T1's fix was not applied or tested.** I state two shapes; neither was written.
- **The `.claude/agents/` copies were not diffed byte-for-byte** against the installables
  `f504ab5` edited; `tests/test_install.py` asserts it and passed in my run, which is the only
  evidence I have for it.
- The tree was live during this pass (other builders writing under `pm/roadmap/`), but every file
  named above was read at HEAD with a clean `git status`.

Reviewer's token cost: ~95k.

```
verdict: HOLD
| id | severity | disposition |
| T1 | BLOCKER | open: Makefile.devkit:218-227 — a declared tier shadowed by a same-named file or directory is skipped at exit 0 with no output |
| T2 | MINOR | open: CLAUDE.md:106 names installables/gdk_runners.sh, which does not exist |
| T3 | MINOR | open: README.md:169 documents install-runners, which now exits 2; install-gates is undocumented |
| T4 | MINOR | open: story 03's Close credits b9cf082/f504ab5 with the gdk_runners.sh split, which is in 8f4e9c1 |
```
