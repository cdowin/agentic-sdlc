---
id: 0.2.0/the-extraction-finishes/02-help-describes-what-ships
feature: 0.2.0/the-extraction-finishes
milestone: "0.2.0"
name: --help names only verbs this package routes
status: reviewing
owner:
depends_on: []
---

# --help names only verbs this package routes

`agentic-sdlc --help` — and the same text printed on any unknown command — lists what this
package can do, and every line of it resolves.

`cli.py:3–49` advertises ~14 verbs `main()` routes none of: `scene`, `scene-diff`, `refs`,
`orphans`, `autoloads`, `tiles`, and eight `scene` subverbs. `_usage()` prints that same
docstring on any typo, so a mistyped command hands the user a menu of nothing — which is worse
than a bare error, because it reads as documentation.

## Acceptance criteria

1. Every verb named in the module docstring is routed by `main()`, and a test proves the
   direction that actually fails: **for each verb the docstring names, `main([verb, '--help'])`
   does not print "unknown command"**. Parsing the docstring for verb names is the point — a
   hand-written list in the test is the same defect one layer up.
2. The docstring's remaining sections are the four families that ship: `pm`, `init`,
   `install-*`, `check`/`gates-extra`.
3. `--version` and the two help paths still exit as they do today (`0` for help asked for, `2`
   for usage refused). Do not change exit codes — rule 6 makes those a contract.

## Out of scope

- `KNOWN_GATES` and `_check_module` — story 01. Serialized with this one; the same file.
- Writing NEW verbs to satisfy the docstring. The docstring shrinks to the code, never the
  reverse.

## Files
Touch: `src/agentic_sdlc/cli.py` (docstring only), `tests/`.
Stay out of: everything story 01 touches in the same file — land 01 first.
