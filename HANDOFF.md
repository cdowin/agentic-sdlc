# Handoff — two kits, one release, fresh pins

**Written 2026-09-04.** The end state Chris asked for: *"Two repos. Fully released 24, fresh pins. All
committed/pushed and ready for handoff to a fresh agent."*

Four repos, checked out side by side in one workspace directory:
`godot-devkit`, `agentic-sdlc`, `consumer_a`, `consumer_b`.

<!-- rule-8: migration document. This file names the four repos on purpose — it is the
     record of a migration BETWEEN them, and a plan that cannot say which repo a step
     happens in is not a plan. It is exempt from the CONSUMER-NAME clause of the rule-8
     gate and from nothing else; the exemption is one exact path, declared in
     tests/test_consumer_independence.py (MIGRATION_DOC) and again here, so it cannot be
     taken without editing both sides. When the migration lands, delete this file AND
     that entry — the gate fails if the entry outlives the file, or the file stops
     needing it. Nothing in src/, tools/, .github/ or an installable may name a repo,
     and this exemption cannot reach any of them: it is a single top-level .md. -->

## Where things stand

- **godot-devkit** — branch `milestone/0.24.0-gate-cost`, four features `done`, milestone at `reviewing`,
  every release-review finding landed (`136d78c`). **Not yet gated, accepted, packaged, or tagged.**
- **agentic-sdlc** — seeded, imports clean, **1,388 tests pass and 9 fail**. Not canonical yet.
- **consumer_a** — pinned `DEVKIT_VERSION := v0.23.0`. Must not bump until the tag exists.
- **consumer_b** — pinned v0.23.0. **No longer blocks anything.** Its one D5 drift only ever reddened
  `make smoke`, which is deleted, so `make milestone` now reads no consumer at all.

## Phase 1 — release 0.24.0, in `godot-devkit`

**The order was wrong until today and the fix is the point.** The full gate is the LAST thing before
done — review, land fixes, *then* gate (`SDLC.md` § Close protocol, `.claude/skills/release/SKILL.md`).

1. `make milestone` — ONCE, on the final tree. ~3:10. Self-contained; no consumer needed.
2. `pm milestone accepted 0.24.0`
3. `pm milestone packaging 0.24.0`, then retitle `## Unreleased` → `## v0.24.0 — <date>` and open a fresh
   empty `## Unreleased` above it.
4. Commit `release: v0.24.0 — …`
5. `pm milestone done 0.24.0` — the last PM action, and the first one that is true when written.
6. Push, PR to `main`, CI green, **merge as a merge commit**. Never push `main`; the pre-push hook blocks it.
7. On `main` at the merge commit: `git tag v0.24.0 && git push origin v0.24.0` — the TAG ref only.
8. Prove it: `uv cache clean godot-devkit`, then
   `uvx --from "git+https://github.com/cdowin/godot-devkit@v0.24.0" godot-devkit --version` → `0.24.0`.

## Phase 2 — `agentic-sdlc` becomes canonical

> *"finish pulling in whatever changes that made, that way agentic-sdlc is now the canonical. It should
> install its own work on itself so it has the full set of practices/patterns."*

9. **Re-sync from the tag.** The seed was taken at `f25243b`; **`136d78c` and anything after are not here
   yet.** `git archive v0.24.0`, re-apply the seed commit's exclusions, re-run the
   `godot_devkit` → `agentic_sdlc` rename.
10. **Fix the 9 known failures** — measured, listed so nobody re-derives them:
    `test_boundaries.py` ×2 (layer/import allowlists still naming the removed half),
    `test_fuzz_inputs.py` ×3 (scene/retarget corpus cases plus the "every hostile class is exercised"
    census), `test_makefile_gates.py` ×3, `test_shell_mark.py::Census` ×1 (module census shrank).
11. **Strip the removed half from prose.** `cli.py`'s `__doc__` still documents 14 verbs that are gone;
    `devkit.toml`, `README.md` and `Makefile` still name Godot gates.
12. **Decide the history.** Chris on the plain copy: *"not having history is a bit of a boon because we
    have so much pollution from the consumer_b and consumer_a consumer smoke checks."* `pm/` and `CHANGELOG.md`
    are godot-devkit's verbatim right now. Prune to what this kit shipped, or start clean and leave the
    old tree in godot-devkit as reference.
13. **Self-install — the point of the exercise.** `install-hooks`, `install-agents`, `install-skills`,
    `install-runners`, `install-ci`, one `pm init`, run BY this repo ON this repo, so it carries its own
    practices instead of describing them.
14. **Decide the version lineage.** It currently inherits `0.24.0`, which is another artifact's number.
    Restart at 0.1.0, or continue deliberately.
15. Green: `make gates`, `make test`, `make milestone`.

## Phase 3 — `godot-devkit` sheds the agentic half

**Blocked on one unanswered question** (`godot-devkit/docs/design/two-kits.md`):

> **Can `[checks] all` compose a check from another package?** The whole split rests on it: the agentic
> kit provides the runner, the Godot utilities provide Godot gates, a consumer's `devkit.toml` composes
> both. Nothing has ever registered a check from outside the package. **Answer it before deleting
> anything.** If it cannot, each half grows its own runner — a second name for the same fact, which needs
> arguing rather than assuming.

16. Delete `src/godot_devkit/repo/`; keep `godot/`; keep `core/` **duplicated on purpose**. Chris ruled
    it, and named the trigger to revisit: if both kits stay config-forward and the shared surface grows,
    the answer becomes a published shared config utility — not a private third package, and never a
    dependency edge between the kits.
17. Its CLI keeps the Godot verbs only.
18. Green, then release as its own next version.

## Phase 4 — fresh pins on both consumers

**Never bump a pin before the tag exists.** M48 caught the reverse once.

19. **consumer_a** — bump `DEVKIT_VERSION` to `v0.24.0`; `install-ci --diff` then decide **PER FILE**
    (`--force` is whole-set and would overwrite a deliberately-grown `auto-tag.yml` path filter);
    `install-hooks`; `install-runners --force`; `pm install-skills`; `install-agents`; one `pm init`.
    Run `godot-devkit check pm` **by hand once** and read its NOTE — `make check` will not show it.
    Migrating `status:` lines is OPTIONAL in 0.24.0 and REQUIRED before 0.25.0.
20. **consumer_b** — the same. Its deliberate two-job sharded `verify.yml` is 177 lines from the installable;
    `--force` there would destroy it.
21. Later, once phase 2 lands: both consumers gain `agentic-sdlc` as a second pin.

## Open questions

| # | question | blocks |
|---|---|---|
| 1 | Can `[checks] all` compose a check from another package? | phase 3 |
| 2 | `agentic-sdlc` version lineage — restart or continue? | phase 2 |
| 3 | What of godot-devkit's `pm/` and `CHANGELOG` history moves here? | phase 2 |
| 4 | consumer_b's D5 drift (`dossier-script-split` story at `review` under a `planning` feature) | nothing. Fix at leisure. |

## Things that will bite

- **`tests/support/__init__.py` does `sys.path.insert(0, REPO_ROOT/'src')`**, so `PYTHONPATH=<old> pytest`
  silently runs the WORKTREE source and reports a false PASS. Filed as
  `bugs/fails-against-head-is-unprovable-by-the-obvious-spelling`. Use `git archive HEAD | tar -x`.
- **A gate reading a half-deleted tree can produce a confident WRONG verdict**, not just a crash. Measured:
  `behavior-fan-scan` in consumer_a called three live allowlist entries stale while `awk` could not open a
  peer's deleted files, and nearly cost three legitimate guards. Stage deletions before believing a scan.
- **`git commit -- <path>` silently omits NEW files.** `git add` them explicitly first.
- The self-hosted `pre-push` blocks a direct push to `main`; a release is a PR merge plus a tag.
- **Write-confinement**: agent edits are confined to the session's own repo, and the guard reads its grant
  file relative to ITS OWN location — which is the session's project dir, not the repo you happen to be
  editing. A cross-repo grant goes in that repo's `tools/hooks/extra-write-roots.local` (gitignored; it
  holds absolute machine paths). **It is gitignored, so it has no backup — read before you write to it.**
