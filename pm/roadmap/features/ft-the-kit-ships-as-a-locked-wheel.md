---
id: ft-the-kit-ships-as-a-locked-wheel
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: the kit ships as a locked wheel
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the kit ships as a locked wheel

Issue: #101. Consumers pin a tag and run `uvx --from "git+https://…@vX.Y.Z" agentic-sdlc`: every
machine and CI run builds from source, nothing is hash-locked, a moved tag changes bits
silently, dependency bots cannot see the pin, and each call pays ~0.8-0.95s of resolution
(measured 2026-09-30). The PyPI name is taken.

## Decided (do not re-plan)

- **Index: a public static PEP 503 index on this repo's GitHub Pages** (`gh-pages` branch),
  URL `https://cdowin.github.io/agentic-sdlc/simple/`. No token anywhere. Chris decided public:
  the repo is public MIT.
- **Build once per tag.** A workflow in THIS repo (`.github/workflows/release.yml`, this repo's
  own file, not an installable) runs on each `v*` tag: `uv build`, then adds the wheel and sdist
  to `gh-pages` under `simple/agentic-sdlc/` and regenerates the two index pages (root and
  project) with `sha256` fragments. A file for a version already in the index is REFUSED (the
  job fails naming it): a wheel is immutable. `auto-tag.yml`'s `RELEASE_WORKFLOW` names it if
  that is how the tag hands off. Stdlib-only index writer (a small script under `tools/`), no
  third-party action for the index.
- **Consume by version, locked.** The consumer shape is `[dependency-groups] dev =
  ["agentic-sdlc==X.Y.Z"]` + `[[tool.uv.index]] name = "agentic-sdlc", url = …, explicit = true`
  + `[tool.uv.sources] agentic-sdlc = { index = "agentic-sdlc" }`. `init` writes it for a new
  project that has (or gets) a `pyproject.toml`; a project with none keeps the git pin.
- **The lock is the only path (Chris decided 2026-09-30; a MAJOR, rule 7: the release is
  1.0.0).** `DEVKIT_VERSION` and `uvx --from git+` leave stock `Makefile.devkit`. `DEVKIT` is
  `.venv/bin/agentic-sdlc`, synced by `uv sync` when missing. A tree whose `uv.lock` does not
  name agentic-sdlc gets make's exit 2 BY NAME, printing the one command that fixes it:
  `uv add --dev agentic-sdlc==<X.Y.Z> --index agentic-sdlc=<url>` (check what `uv add --index`
  writes; if it cannot write `explicit = true` and the source pin, print the pyproject block too).
- **A project with no `pyproject.toml` gets a tooling-only one.** `init` writes a minimal
  `pyproject.toml` (`[project]` name/version/requires-python, `[tool.uv] package = false`) when
  none exists — an installer writes a whole file or refuses by path (rule 3); it never edits an
  existing pyproject. A non-Python consumer (a Godot game) is the case this serves.
- **Migration is printed, not performed.** `adopt 1.0.0` run from the git pin (the last time
  anyone runs `uvx --from git+`) has a check that names the move: the `uv add` line, then
  `install-gates --force` for the new `Makefile.devkit`. The adopt belt stays checks-only.
- **The verbs learn the shape.** `adopt <version>`'s `pin-bumped` reads the locked version when
  the lock names the kit; `install-*` and any doctor/preflight read of the pin read both. CI:
  the stock `ci-verify.yml` runs `uv sync --frozen` when a `uv.lock` names the kit.
- **Docs:** README install section and the adopt path (`uv add --dev agentic-sdlc==X.Y.Z`, or a
  Renovate/Dependabot PR, then `adopt`).
- This supersedes the local-install item once planned in `ft-the-static-gate-takes-seconds`.

## Ship criterion

- A scratch consumer with the pyproject block and a local file index (a `file://` index built
  by the index script from `uv build` output) runs `uv sync`, and `make check` calls
  `.venv/bin/agentic-sdlc`, with no `uvx` in the run.
- A tree with no lock naming the kit: `make check` exits 2 and prints the `uv add` line.
- `adopt 1.0.0` from a git-pinned consumer names the migration steps.
- The index script refuses a version already present; rerun on the same set is a no-op.
- The real publish runs at this milestone's tag (the orchestrator enables Pages and watches it).

## Proof budget

  cases: ~5 — DEVKIT resolution and the by-name refusal, the index script (write, refuse, idempotent), adopt reading the lock
  tier: unit for the script and resolution text; one integration case for the scratch consumer
  lands in: tests for the index script, Makefile.devkit, conveyor adopt
  what already covers this: pin-bumped reads DEVKIT_VERSION; nothing reads a lock.
