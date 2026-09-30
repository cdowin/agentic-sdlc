---
id: ft-ci-runs-what-the-laptop-runs
kind: feature
milestone: "ms-the-mistake-surfaces-where-it-is-made"
name: ci runs what the laptop runs
status: done
reviewed: docs/reviews/2026-09-29-0.17.0-hooks-and-ci.md
depends_on: []
consumed_by: []
changelog: `install-ci` writes actions/checkout@v7, astral-sh/setup-uv@v10.2.0 (setup-uv publishes no major tag) and actions/upload-artifact@v7 (Node 24; setup-uv v10 turns its cache off on pull_request events), and the new gate key `[shell] shellcheck_version` pins the shellcheck `check shell` may run — another version or none fails, naming both — which the stock verify.yml installs, read through `check shell --pin`.
---

# ci runs what the laptop runs

Issues: #89, #90.

A local pass must mean a CI pass. `check shell` passed on local shellcheck 0.11.0 and failed on
the runner's apt shellcheck for nine days. `install-ci` writes actions on the deprecated Node 20
runtime, and consumers cannot bump the kit-owned files without failing `installables-current`.

## Decided (do not re-plan)

- **Bump the action majors** in `src/agentic_sdlc/repo/installables/ci-*.yml`: `actions/checkout`,
  `astral-sh/setup-uv`, `actions/upload-artifact` to their current majors. Confirm each with
  `gh api repos/<owner>/<repo>/releases/latest` before writing (the issue says v7, v10, v7 on
  2026-09-28). setup-uv's cache-off-on-PR default is accepted; say so in the changelog.
  Re-install this repo's workflows with `install-ci --force`.
- **No check for deprecated action runtimes.** It would need a table of deprecations that goes
  stale; `adopt`'s `installables-current` already carries the bump to consumers.
- **`[shell] shellcheck_version`, a new GATE key**, stock `""` (any version: today's behaviour,
  byte-identical, rule 5). When set, `check shell` FAILS (exit 1) if `shellcheck --version`
  differs, naming both versions; a missing shellcheck with a pin set FAILS rather than SKIPs
  (a pinned gate that skips is a PASS that looked). Every `check shell` verdict line names the
  shellcheck version it ran (rule 11). Seed carries the key commented at `""`.
- **The stock `ci-verify.yml` installs the pinned version** when the key is set, from the
  shellcheck GitHub release tarball, before the gate; with the key unset it keeps today's step.
  How the workflow reads the key is the developer's call, through an existing read verb if one
  fits (`pm config` or similar); never a second parser in YAML.
- This repo sets the key to the version installed here and `make milestone` stays green.

## Ship criterion

- A fresh `install-ci` writes no Node 20 action.
- With the pin set to a version other than the local one, `check shell` exits 1 naming both.
- Unset, `check shell` output differs from 0.16.0 only by the version clause.

## Proof budget

  cases: 3 unit cases in the check-shell module (mismatch, missing-with-pin, version clause); seed test moves
  tier: unit (fake `shellcheck` on PATH is a spawn → integration if it must run one)
  lands in: tests for repo/checks/shell.py, tests/test_config_seed.py
  what already covers this: the soft-skip and zero-census cases; no version is read today.
