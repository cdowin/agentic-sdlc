# Handoff — two kits, one release SHIPPED, fresh pins

**Rewritten 2026-09-04, end of session.** Four repos, checked out side by side in one workspace
directory: `godot-devkit`, `agentic-sdlc`, `consumer_a`, `consumer_b`.

<!-- rule-8: migration document. This file names the four repos on purpose — it is the
     record of a migration BETWEEN them, and a plan that cannot say which repo a step
     happens in is not a plan. It is exempt from the CONSUMER-NAME clause of the rule-8
     gate and from nothing else; the exemption is one exact path, declared in
     tests/test_consumer_independence.py (MIGRATION_DOC) and again here, so it cannot be
     taken without editing both sides. When the migration lands, delete this file AND
     that entry — the gate fails if the entry outlives the file, or the file stops
     needing it. Nothing in src/, tools/, .github/ or an installable may name a repo,
     and this exemption cannot reach any of them: it is a single top-level .md. -->

## State — everything below is committed and pushed

| repo | branch | state |
|---|---|---|
| **godot-devkit** | `milestone/0.25.0-the-godot-kit-alone` | **v0.24.0 RELEASED** — merged, tagged, artifact proven from a cold cache. 0.25.0 planned, not started. |
| **agentic-sdlc** | `milestone/0.2.0-the-conveyor` | **0.1.0 merged to main**, suite green (1,430 pass / 1 skip / 348 subtests). 0.2.0 planned, not started. |
| **consumer_a** | `feat/0.90.3-game-polish` | **pinned v0.24.0**, `make check` exit 0, 37 status words migrated. |
| **consumer_b** | `chore/devkit-v0.24.0` | **pinned v0.24.0**, `check` + `precommit` exit 0, 25 migrated. **PR not opened.** |

## What is left, in order

### 1 — Open consumer_b's PR
The branch is pushed and nobody opened the PR. `main` there is release-only and auto-tags on push.

### 2 — agentic-sdlc 0.2.0 — four features, all planned and measured

- **`the-extraction-finishes`** — 0.1.0 is green and green is not clean. **A stock consumer's
  `check all` exits 2**: `KNOWN_GATES` names eight removed gates and three sit in the DEFAULT roster,
  so the path a new adopter takes is the broken one. The real defect is the **missing census** —
  nothing asserts the declared roster equals what actually dispatches. Also `--help` advertising ~14
  absent verbs, a 126 KB Godot ClassDB dump with zero readers shipping in the wheel, and
  `devkit.toml` / `pyproject.toml` / `CLAUDE.md` still describing the half that left.
- **`the-kit-owns-the-gates-that-scan-its-own-artifacts`** — 4 of a consumer's 20 gates scan artifacts
  this kit owns; the other 16 are that game's own architecture and stay. Evidence: the second consumer
  has no prose-cap gate at all, so a rule this kit defines is enforced in one tree of two by accident.
- **`every-gate-reports-its-cost`** — `gdk_gate` is the single funnel; instrument there and gates that
  do not exist yet are covered.
- **`the-release-is-a-conveyor`** + **`design-the-three-belts.md`** — one belt per grain, each widening
  verification by exactly one step. **A belt never runs a belt above it.**

### 3 — godot-devkit 0.25.0, blocked on ONE file

Delete `src/godot_devkit/repo/`, keep `godot/` and a duplicated `core/`, pin `agentic-sdlc`, ship
`install-runners`. Measured across the four install plans:

| plan | files | Godot |
|---|---|---|
| `install-ci` | 4 | 0 |
| `install-agents` | 13 | 0 |
| `install-hooks` | 11 | **1** — `cc-godot-sandbox.sh` |
| `install-runners` | 13 | **12** |

`install-runners` is a Godot verb, and its only non-Godot member is **`Makefile.devkit`** — which
carries the gate FRAMEWORK and the Godot target ROSTER in one file. **That is the entire middle tier
and the only design problem left in the split.**

**Hard ordering:** this repo cannot green until `agentic-sdlc` is pinnable. The moment `repo/` goes,
`pm`, `check pm` and `install-*` go with it, and this repo's own gates use them.

### 4 — Loose ends in the consumers

- **consumer_a:** `make doctor` FAILs on a stale uid index — 3 of 1199 tracked sidecars missing from
  `.godot/uid_cache.bin`. A genuinely new 0.24.0 check finding a real condition: the one that makes
  scenarios FAIL while printing PASS inside. Remedy `rm -rf .godot && make import-cache` re-serializes
  tracked files, so it wants its own commit. Nothing gates on it today.
- **consumer_b:** its `pm/README.md` convention was rewritten during the adoption — a no-build decision
  story now stays `ready` instead of jumping to `review`, because that documented shortcut is exactly
  what produced the tree's only D5 drift. **A convention change is the repo owner's to confirm.**

## Open questions

| # | question | blocks |
|---|---|---|
| 1 | How does `Makefile.devkit` split — framework here, Godot roster there? | godot-devkit 0.25.0 |
| 2 | Which command is "narrow" per project — designed in `design-the-three-belts.md`, not built | the story belt's economics |
| 3 | Does `cc-godot-sandbox.sh`'s corpus self-test follow it to godot-devkit? | tidy, not blocking |

## Things that will bite

- **A belt never runs a belt above it.** Measured: a full suite is 154 s, a single module 0.9 s —
  **170x**. Eleven story-layer fixes verified at milestone scope cost **31 minutes**; re-checking the
  same five modules at story scope cost **13 seconds**. **A dispatch naming only the wide command
  teaches the wide command as the inner loop.** Name both, with costs, and say which is which.
- **`tests/support/__init__.py` does `sys.path.insert(0, REPO_ROOT/'src')`**, so `PYTHONPATH=<old>
  pytest` silently runs the WORKTREE source and reports a **false PASS**. Use `git archive HEAD | tar -x`.
- **A gate reading a half-deleted tree produces a confident WRONG verdict**, not a crash. Measured:
  `behavior-fan-scan` called three live allowlist entries stale while `awk` could not open a peer's
  deleted files, and nearly cost three legitimate guards. **Stage deletions before believing a scan.**
- **`git commit -- <path>` silently omits NEW files.** `git add` them explicitly first.
- **A blanket rename sweeps files that legitimately name the thing being renamed.** It broke THIS
  document twice. Exclude migration docs from any `godot-devkit → agentic-sdlc` sweep.
- **`tools/hooks/extra-write-roots.local` is gitignored and has no backup.** Read before writing; one
  was clobbered this session and reconstructed from inference.
- The self-hosted `pre-push` blocks direct pushes to `main` in every repo here. A release is a PR merge
  plus a tag.
