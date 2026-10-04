# Changelog

## 3.0.0 (2026-10-04)

agentic-sdlc is now a repo of 28 files (plus tests) with 2 jobs: which agent and which model for
which work, and hooks and CI checks that keep agents safe and repos lean. It tracks no work.

Added:
- `AGENTS-AND-MODELS.md`: the model guide (Sonnet default, Opus list, developer step-up rule, Haiku for bulk lookups, effort cap `high`, Claude or Codex).
- Claude Code plugin `agentic-sdlc`: 6 agents with their model set, skill `agents-and-models`, and 4 POSIX sh hooks (`git-denylist` on, `context-budget` on and warn-only, `commit-pathspec` and `write-confine` opt-in by env var).
- Codex adapter: `codex/AGENTS.md` and a 1-paste install in `codex/README.md`.
- 3 reusable workflows: `context-budget`, `test-budget` (warns only), `issue-link`.

Removed (all of 2.x):
- The PM tree (`pm/`, 504 files), the ledger and every `make pm` / `make sdlc` verb.
- The Python package (`src/agentic_sdlc`), its test suite, `pyproject.toml`, `uv.lock` and the wheel release flow.
- `devkit.toml`, `Makefile`, `Makefile.devkit`, `Makefile.tiers` and the gate framework (it moves to godot-devkit).
- `tools/`, the ledger hooks, the git `pre-push` and `prepare-commit-msg` hooks.
- `SDLC.md`, `improvements.md`, `docs/reviews/`, `docs/design/`, `docs/research/`.
- The workflows `verify`, `auto-tag`, `release` and `semver-gate`.
- The repo's own `.claude/agents`, `.claude/rules` and 6 PM skills.

Upgrade from 2.x: remove the `agentic-sdlc` pin and the PM tree, then install the plugin.
