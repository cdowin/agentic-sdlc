---
id: 0.2.0/the-code-knows-entry-and-exit
milestone: "0.2.0"
name: The code knows entry and exit; the config knows every state between
status: building
reviewed: docs/reviews/2026-09-06-the-code-knows-entry-and-exit.md
phase: 9
depends_on: ["0.2.0/every-question-is-asked-of-a-category", "0.2.0/the-ledger-rows-carry-categories", "0.2.0/the-inner-levels-are-belts-too", "0.2.0/the-belt-reports-and-finishes", "0.2.0/the-project-declares-its-flow"]
consumed_by: []
---

# The code knows entry and exit; the config knows every state between

**Chris, 2026-09-05:** *"The code itself is just a state transition machine. It just knows an
entry and an exit state. The config defines planning, ready, packaging, etc. and maps those to
todo, in progress, or done. The CLI reflects back what is configured."* *"This tool is a
reader/writer. It reads/writes the same things, in the same places, over and over. It echoes
state back — it doesn't DO anything."* *"Open up a milestone, stamp stamp stamp to done."*
0.2.0 is the whole MVP — no 0.3.0, no deferrals, no open bugs.

The same ladder at every level: **plan → ready → build → test → review → done.** A stamp is one
command. A belt is the config's entry conditions printed as checks, then one write or a clean
error (D12). A tree whose levels disagree gets a warning line, not a failure and not an action.

## Ship criterion

1. Each kind declares its own states, each in exactly one category, and `pm vocabulary` echoes
   them; the `[pm.transitions]` key and its reader are gone (a belt writes the first `done`
   state of its kind, nothing else needs a table).
2. `ready` is stamped by `pm <kind> ready <id>` and nothing else; `check pm` WARNS, exit code
   unchanged, when a grain at or past `ready` has an empty criteria section, a feature has no
   stories, or a milestone has an unphased feature or no `branch:`.
3. Every cross-level disagreement (D2, D3, D5, D6) is a `  WARN  ` line naming both grains,
   counted in the summary, never a finding, never an exit code, never an action.
4. Every belt is D12: all its checks run and print; all true → the one status write; any false →
   `error:` lines naming each, exit 1, no write; `--force` writes and the ledger row names the
   false checks. No belt bumps, retitles, pushes, tags or moves any other grain. `close feature`
   accepts a story in ANY state of the `done` category. `docs/sdlc-protocol.md` renders from the
   check lists and says what the caller does after each belt.
5. `pm ready-for milestone` names every open bug whose `fix_milestone` is the milestone, and
   `release`'s check list includes it.
6. The three bugs open against 0.2.0 are `closed`, and no bug names another milestone.
7. Every record under `docs/reviews/` naming 0.2.0 has no finding at `open`.
8. 0.2.0's stories, features and the milestone close through the belts, and the ledger's status
   rows say so.

## Proof budget

One test per criterion at the cheapest tier that can fail; the belt cases replace, not join,
`tests/test_conveyor_*.py` — a conveyor a third the size keeps a third of the tests.
