---
id: ft-an-arrival-names-what-it-starts
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: an arrival names what it starts
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# an arrival names what it starts

Three issues where a move starts something the operator learns about one command later: #68 (a
milestone claims a version the file does not hold), #69 (a story becomes dispatchable with a
destination its gate rejects), #66 (the loop holds every feature open until one milestone review).

## Decided (do not re-plan)

- **#68 — the milestone arrival names the version edit.** Do NOT stamp the version file: `pm`
  rewrites one frontmatter line (rule 3). When a milestone arrives at a building-category state,
  `[pm] version_at = "start"`, and the version in `[pm] version_file` is not the milestone's
  `version:`, `_arrived` prints one extra `next:` line naming the file, the value it holds and the
  value R5 will demand: `next: set <file> version <held> -> <want> — R5 DRIFT until it does`. Read
  the version with the same reader R5 uses (`inventory.graded_release`), never a second parser.
  `version_at = "ship"` prints nothing new.
- **#69 — a story arrival runs the gates the project declares for it.** New GATE key
  `[pm] arrival_gates`, a table of `<kind> = [<make target>, …]`, stock empty (seeded commented at
  that value, rule 5; through `core/config.py`). After a story (or bug) arrives at a state whose
  category is `building` or `ready`, `pm` runs each declared target once for the whole invocation
  with `GRAIN=<id>[,<id>…]` in the environment (spawned through `core/spawn.py`), and prints each
  failing target by name as a `WARN` line with its last output line. The write stands and the exit
  stays 0: `pm` moves and reports; refusing would make it a belt (rule 9). No `arrival_gates`
  declared prints nothing. The capability is named in `pm story --help` and the seed (rule 11).
- **#66 — a feature closes when it lands; review is a judgment.** 0.14.0 (#49) already moved
  review to one pass per lane as it merges. The rest is skill text, in
  `repo/pm/guidance/run-the-sdlc.md` step 8, re-installed with `pm install-skills --force`:
  close a lane's stories and its feature the same day it merges; review is a per-feature
  judgment, and related landed features may share one reviewer (a bucket of two or three); a
  feature the orchestrator does not send to review gets an orchestrator-written record (one line
  on what was read, plus the fenced verdict block with no findings) as its `reviewed:` target,
  which `close feature` already accepts. Show that minimal record in the skill.
  Also step 10: run `make sdlc ARGS='verify --milestone'` before `release`, because `release`
  reuses a green one on the same tree (`ft-a-gate-reads-what-this-run-did`, #74).

## Ship criterion

- `pm milestone <id> building` on a tree whose version file lags prints the `next:` line with both
  values.
- With `arrival_gates = { story = ["probe"] }` and a failing `probe`, flipping two stories to
  building in one call runs `probe` once and prints one WARN naming it; exit 0.
- The installed skill says close-as-it-lands, review-by-judgment, and shows the minimal record.

## Proof budget

  cases: 4
  tier: unit, plus ONE shell case for the arrival spawn
  lands in: existing pm arrive / config seed / install test modules
  what already covers this: search first (rule 10); amend before adding
