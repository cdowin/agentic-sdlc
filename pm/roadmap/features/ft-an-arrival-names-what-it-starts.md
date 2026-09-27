---
id: ft-an-arrival-names-what-it-starts
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: an arrival names what it starts
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# an arrival names what it starts

Three issues where a move starts something the operator learns about one command later: #68 (a
milestone claims a version the file does not hold), #69 (a story becomes dispatchable with a
destination its gate rejects), and #79 (a bucket review, which #66 recommends, holds a sibling
feature on the other feature's findings).

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
- **#66 moved** to `ft-the-loop-learns-what-the-fork-learned`, which owns every guidance-file
  edit this milestone. This lane holds the code only.
- **#79 — a verdict block names the feature it grades.** Chris, 2026-09-27 (D6). #66 tells the
  loop to share one reviewer across a bucket, so a shared record must not hold a sibling. A
  fenced verdict block may carry one `feature: <id>` line after its `verdict:` line;
  `verdict.parse` returns it on `Verdict` (empty when absent). A reader that closes feature F
  (`_passes` in `repo/conveyor/steps.py`, and `ready_for.py`'s record loop) keeps:
  every block when NO block in the file names a feature (today's behaviour, unchanged); else
  only the blocks naming F. A block naming an id that does not point `reviewed:` at this record
  is a plain false naming the id and the record — a typo must not hide a MAJOR (rule 4). A
  record with some blocks keyed and some not is a plain false too: the reader cannot tell whose
  the unkeyed block is. The reviewer agent and the skill show the `feature:` line; those edits
  belong to `ft-an-agent-keeps-its-project-half` and `ft-the-loop-learns-what-the-fork-learned`.

## Ship criterion

- `pm milestone <id> building` on a tree whose version file lags prints the `next:` line with both
  values.
- With `arrival_gates = { story = ["probe"] }` and a failing `probe`, flipping two stories to
  building in one call runs `probe` once and prints one WARN naming it; exit 0.
- One record with two keyed blocks, feature A `SHIP` and feature B `HOLD` with an open MAJOR:
  `close feature A` passes its findings check and `close feature B` refuses on B's MAJOR. A block
  keyed to an id not pointing at the record is refused by name.

## Proof budget

  cases: 5
  tier: unit, plus ONE shell case for the arrival spawn
  lands in: existing pm arrive / config seed / verdict / close-feature test modules
  what already covers this: search first (rule 10); amend before adding
