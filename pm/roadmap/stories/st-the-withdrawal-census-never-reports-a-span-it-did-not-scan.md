---
id: st-the-withdrawal-census-never-reports-a-span-it-did-not-scan
kind: story
feature: ft-install-force-keeps-what-the-project-owns
milestone: "ms-a-consumer-can-take-the-bump"
name: the withdrawal census never reports a span it did not scan
status: building
owner: agent
depends_on: []
changelog: The withdrawal report no longer says "withdrawn nothing" when the pin already names the running version: it says it compared nothing, names where the floor came from, and `--since <version>` sets the floor — pass the pin you are leaving.
---

# the withdrawal census never reports a span it did not scan

Issues: #21 #28 (same root cause; #28 adds that through `Makefile.devkit`'s `uvx --from …@$(DEVKIT_VERSION)` the
running version IS the pin, so the floor always equals the ceiling).

Every installer ends with *"install-X has withdrawn no make target, verb flag or file between <from>
and <to>"*. `<from>` is `installed_stamp()` (`install.py:666`), the working-tree Makefile pin. The
adopt belt requires the pin to be bumped first, so on the bump the census exists for,
`retired_since()` (`:686-705`) keeps rows with `floor < key < ceiling` over an empty interval and
prints `NOTHING_WITHDRAWN` (`:655`). The 0.6.0 row, `Retirement('0.6.0', 'install-agents',
files=('.claude/agents/changelog-writer.md',))`, is exactly the one it should have printed.

**This is rule 4's first sin: a census that cannot fail in the order the belt demands.**

## Acceptance criteria

1. When floor == ceiling, the line says nothing was compared and how to compare something (run it
   before bumping, or `--since <version>`). It never says "withdrawn nothing".
2. `--since <version>` sets the floor explicitly, and a malformed version exits 2.
3. With `--since v0.4.0` run from 0.8.0, `install-agents` names `changelog-writer.md` as withdrawn in 0.6.0.
4. Not chosen by the tool on its own: reading `HEAD:Makefile` when the working tree differs. It is
   only acceptable if the line says which pin it read and where from. Otherwise it is inferring the
   span (rule 9). The builder picks, and the close says which.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `retired_since` / the report with floor == ceiling. Must fail at HEAD | new, tests/test_install.py |
| 2, 3 | unit | the report with an explicit floor over the real `RETIREMENTS` table | amend the above |

## Semver

Minor: a new line shape and a new flag.

## Out of scope

A version stamp in installed files. Their GENERATED headers carry no number, and adding one is
another byte-current surface.
