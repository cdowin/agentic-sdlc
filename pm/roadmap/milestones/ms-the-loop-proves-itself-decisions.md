Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-the-loop-proves-itself The loop proves itself — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-10-01 — No doctor verb: adopt grows instead

DeepWiki proposed `doctor`, one verb for the whole setup. 2.0.0 retired `preflight`, the same idea, because it "printed rows nobody acted on" (`cli.py::RETIRED_VERBS`). `adopt` already checks pin, installables and config. Its gaps are absences it skips; ft-adopt-names-what-is-absent closes them. Rejected: a new verb.

## D2 — 2026-10-01 — gdk_gate.sh stays bash and make stays the rung runner

Moving `gdk_gate.sh` verdict logic to Python and making make optional are both major bumps: `gdk_run_bounded` and the timeout API are consumer gate code, and `[verify]` rungs are make targets by design (rule 2: nothing invents an engine command). 2.0.0 just made every consumer change once. Rejected for 2.1.0; revisit only with a consumer asking.

## D3 — 2026-10-01 — Hooks keep their inline decisions

`cc-git-denylist.sh`, `cc-write-confine.sh` and `pre-push` decide in bash with inline `python3`. Rule 1 requires hooks to run on a consumer's bare `python3`, and 2.0.0 cut the hook corpus to guards that block irreversible acts. Moving them into the package would make a hook depend on the installed package. Rejected.

## D4 — 2026-10-01 — shellcheck_version keeps its empty default

DeepWiki proposed a real pin as the default. The code default `""` equals the seed's commented value (rule 5), and `""` is what lets `check shell` soft-skip on a machine with no shellcheck. A project that wants a pin sets one, as this repo does (`0.11.0`). Rejected.

## D5 — 2026-10-01 — improvements.md stays at the root

DeepWiki proposed moving `improvements.md` into the tree or `docs/design/`. Its header records why it sits at the root (a lesson about a migration cannot live inside the tree the migration rewrites), and ft-the-kit-says-one-loop keeps it as append-only history. Rejected.

## D6 — 2026-10-01 — Retired config keys need no new test

DeepWiki asked for a regression test that a retired key is named with its replacement. It exists: test_pm_gate.py, test_release.py, test_verify_main.py, test_adopt.py and test_verify_rules.py each cover their section. No new case.

## D7 — 2026-10-01 — No TOML writer dependency

`init` writes `devkit.toml` from a template (`installables/project-devkit.toml`), not from a TOML writer, so no writer is needed. Rule 1 stands. ruff goes in the dev group only (ft-python-has-a-lint-gate), which rule 1 does not cover.
