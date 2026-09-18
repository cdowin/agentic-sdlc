---
id: ft-a-surface-says-what-it-means
kind: feature
milestone: "ms-the-filed-issues-are-answered"
name: a surface says what it means
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a surface says what it means

Four consumer issues where the tool knows a fact and the surface in front of the operator does not
say it. One lane, because #61 and #63 both edit the dispatch preamble.

## Decided (do not re-plan)

- **#60 — `make pm ARGS="…"` breaks on `(`, `'` and `,`.** The recipe in
  `src/agentic_sdlc/repo/installables/` (`Makefile.devkit`) must not put ARGS into shell text.
  Pass it through the ENVIRONMENT and let the CLI split it (`shlex.split`, stdlib). Parentheses and
  commas then pass through. An unbalanced quote is exit 2 with one line that says how to write the
  name, never a bash parse error. The `sdlc` recipe gets the same fix. Re-install here with
  `install-gates --force`.
- **#61 — a finding id over 32 characters.** The `close feature` check prints
  `refused: finding id over 32 characters (<n>): <id>` as a plain false check, never
  `unverifiable`. `dispatch --grain <feature>` renders the review-record grammar in the preamble:
  verdict line, header row, no separator row, id at most 32, the severity words, the disposition
  words (`landed <hash>`, `deferred: <id>`, `rejected: <why>`). Render it from the constants the
  check reads, never a second copy of them.
- **#63 — the preamble names no read verb.** `dispatch` (both `--grain` and `--role`) renders one
  block, "Read the tree through the kit", naming `changelog <milestone-id>`, `pm status <id>`,
  `pm list`, `pm ledger show|report`, `cite`. Each named verb must exist in the router; a test
  holds that.
- **#51 — semver-gate.yml ships `pyproject.toml`.** `install-ci` renders `VERSION_FILE` from
  `[pm] version_file`. It picks `VERSION_PATTERN` from a small table keyed on the file name
  (`pyproject.toml`, `Cargo.toml`, `package.json`, `project.godot` with `config/version="…"`,
  `VERSION`). An unknown name refuses by path and names the two env lines to write. `adopt` fails
  when the installed workflow's `VERSION_FILE` is not `[pm] version_file`.

## Ship criterion

- `make pm ARGS="new story ft-x s The HUD reads f(host), then g"` creates the grain.
- A 33-character finding id closes nothing and says the cap in plain words.
- The dispatch preamble names the read verbs and, for a feature, the record grammar.
- `install-ci` on a `project.godot` tree writes a gate that reads that file.

## Proof budget

  cases: 4-6
  tier: unit (function before temp tree), one make-spawn case for #60 if unit cannot reach it
  lands in: existing test modules for dispatch, close feature, install
  what already covers this: search first (rule 10); amend before adding
