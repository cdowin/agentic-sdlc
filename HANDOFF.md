# Handoff — 0.2.0 the conveyor

**Written 2026-09-05, end of a long session. 19 commits on
`milestone/0.2.0-the-conveyor` since `815de59`.**

Read this, then `pm/roadmap/0.2.0-the-conveyor/milestone.md`, then
`decisions.md` (D1-D10). Everything else is derivable.

---

## HOW TO WORK HERE — read this before you run anything

**The single most expensive mistake in this repo is running a rung wider than
the thing you changed.** It is the failure the whole milestone exists to end,
and the last session made it four times by hand inside the feature that fixes
it. The ladder, with MEASURED costs:

| you changed | run | cost |
|---|---|---|
| the PM tree, or a doc | `make gates` | **~2 s** |
| code, inner loop | `agentic-sdlc verify --story` | seconds |
| code, before a commit | `make precommit` | **~10 s** |
| closing a feature | `agentic-sdlc verify --feature` | **~36 s** |
| closing a milestone | `make milestone` | minutes |

**Writing to the PM tree is `pm new`, an edit, `make gates`, a commit.** Two
seconds. A planning step that costs a suite is one people batch up and stop
doing.

**A story is build → unit → done, repeated.** `agentic-sdlc verify --plan`
prints every rung with the cost it actually took, from the ledger. Ask it rather
than guessing.

Run the CLI as `PYTHONPATH=src python3 -m agentic_sdlc.cli …` —
**never `uvx --from`**, which caches by version and serves stale code.

---

## Where the milestone is

Eight phases. 1-4 built and reviewed; 5-8 are the rebuild.

| phase | feature | state |
|---|---|---|
| 1 | `the-extraction-finishes` | reviewing |
| 2 | `the-middle-tier-splits`, `the-kit-owns-the-gates…` | reviewing / building |
| 3 | `every-gate-reports-its-cost`, `the-belts-refuse-to-advance`, `the-story-belt…` | building |
| 4 | `the-release-is-a-conveyor`, `adopt-is-a-conveyor` | building / reviewing |
| **5** | **`the-belt-reports-and-finishes`** → then `the-inner-levels-are-belts-too` | driver DONE, inner belts NOT BUILT |
| **6** | `the-project-declares-its-flow` **done**; `the-suite-is-cheap…` **done** | |
| **7** | `every-question-is-asked-of-a-category`, `the-proof-is-named-in-the-criterion` | **NEXT** |
| 8 | `the-ledger-rows-carry-categories` | blocked on 7 |

### Findings: 36 open at session start → **2**

`I2` (26 stories parked at `reviewing`; they close once the inner belts land)
and `R4` (owned by phase 7, which deletes the line it is against). **Seven of
the thirty-two were stale** — already fixed, never re-dispositioned. Verify by
measurement before trusting any disposition in `docs/reviews/`.

---

## What is DONE, and the rulings behind it

Decisions D1-D10 in `pm/roadmap/0.2.0-the-conveyor/decisions.md` carry the
reasoning and the rejected alternatives. The load-bearing ones:

- **D8 — everything is a check.** No belt step halts. `_walk` records every
  answer and returns a scoreboard; `release` over a red `make gates` reaches
  `tag`. `--skip` is gone; the ledger row it wrote is now written by the machine
  for every not-true step.
- **D7 — the ledger keeps its frozen keys** and gains category keys beside them.
- **D5 — D8/D9/D10 report over every `in_progress` milestone**, because "the
  building milestone" is not expressible under three categories.
- **D6 — the engine's two verbs exist.** `move` and `holds` in `model.py`. They
  had never been built; the census is phase 7's acceptance test.
- **D9 — a composition rung has no gate slot**, so `verify --plan` says
  `unknown` for the wide rungs. Filed: `0.2.0/bugs/a-composition-has-no-slot`.
- **D10 — the test tier is the ladder's bottom rung**, and a tier over its
  ceiling is a gate failure.

**Phase 6 landed the northstar's core:** three categories, `[pm.states.<kind>]`
and `[pm.transitions.<kind>]` declared per project, no runtime fallback,
`pm vocabulary` as the pin-bump verb, and a live seed.

**The suite went 240 s → 36 s** and `make precommit` 240 s → 10 s, with the pass
count going UP. Hard rule 10 is the counterweight rule 4 never had.

---

## NEXT, in order

1. **Finish phase A/B of `the-proof-is-named-in-the-criterion`** — cut the suite
   to what BITES. Phase C (the prevention) is already landed: templates, rule
   10, the roster, `check budget`'s time AND case ceilings. The feature record
   carries the "does it bite" table; use it as the criterion, not "which are
   duplicates".
2. **Phase 5's inner belts** (`the-inner-levels-are-belts-too`). It is unbuilt
   and its record specifies belts that REFUSE — read its banner first; D8 means
   they report. Closing it closes I2.
3. **Phase 7** (`every-question-is-asked-of-a-category`) — the behaviour change.
   Route the census through `holds`. **Every fixture tree already declares a
   flow**, so this lands as a behaviour change rather than 400 fixture edits.
4. **Phase 8**, then close the tree through the belts, review, and release
   0.2.0 through `agentic-sdlc release 0.2.0` (criterion 10 — a conveyor whose
   first release is done by hand has not been tested).

---

## Gotchas that cost the last session real time

- **`repo_root()` no longer spawns git** — it walks up for `.git`. A test tree
  only needs `(root/'.git').mkdir()`. `support.pm.tree` marks; `support.pm.git_tree`
  initialises, and reaching for the second is what marks a module integration.
- **`pytestmark` is one name.** Two assignments silently replace each other; use
  a list.
- **`check budget` must NOT go in `[checks] all`.** It grades the last recorded
  run, and `check all` runs inside a test that spawns `make gates` against this
  tree — nine tests went red over unrelated timing. It lives in `make milestone`.
- **A `[verify]` rung that names a make target whose meaning changed is a silent
  hole.** `feature = "make precommit"` stopped meaning "integration" the moment
  `precommit` became narrow, and a feature closed running no integration for an
  hour.
- **Dispositions have a grammar** — `landed <hash>`, `rejected: <why>`,
  `deferred: <grain-id>`, `open`, `open: <note>`. Prose after the hash makes
  `pm ready-for tag` refuse the record.
- **The scene half is gone.** Anything naming Godot in `src/` is drift (rule 8).
