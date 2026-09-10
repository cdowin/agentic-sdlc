---
id: st-every-census-this-milestone-argues-from-is-a-command
kind: story
feature: ft-the-suite-is-measured-like-the-source
milestone: "ms-nothing-is-hand-rolled"
name: every census this milestone argues from is a command
status: planning
owner:
depends_on: []
changelog:
---

# every census this milestone argues from is a command

Every number this milestone's brief and its two feature files argue from is a number a command
produces, or it is deleted. Nothing here is quoted from a `python3 -` somebody ran once.

The reason is filed as a bug in this milestone. `bg-the-brief-undercounts-the-coupling-it-argues-from`
found `ms-the-rule-reaches-the-work` asserting *"roughly 600"* hard-rule citations with *"rule 4
alone 194"* against a tree holding 1,107 and 314 — off by 2x, in the direction that made the
constraint look cheaper than it was, quoted forward through three milestones. **Measured again
2026-09-10 the tree says 1,153 citations across 499 tracked files, `rule 4` alone 325.** The number
moved by 46 in two days, which is the argument: a hand-rolled measurement is wrong the moment it is
written down.

## Scope, and the reconciliation this story owes

The bug's Fix section points at `ft-a-hand-rolled-command-is-a-missing-verb`, which owns the RULE and
eight candidate censuses. **That feature is in the pool with no milestone**, deferred with the rest of
the conveyor work. This story is the scoped slice: the censuses THIS milestone argues from, and
nothing else. The pooled feature keeps the rule and the other candidates, and the reconciliation is
written into the bug's close so the pointer does not dangle.

## The candidates, measured 2026-09-10, each needing a verdict

Not a mandate to ship four verbs. **A verb whose only caller was one session is worse than the
`python3 -` that produced it**, because it ships, it is documented, it is tested, and it is a
published API. A written reason why not is a legitimate, expected outcome for most rows.

    hard-rule citations   1,153 across 499 files; rule 4 alone 325.   bg- names it; it is
                          quoted in an always-loaded doc              the one that must become askable
    prose/code per root   src 4,503/14,281 = 0.3153 (0.6.0/D7 applied);
                          tests 10,830/20,604 = 0.5256                only test_prose_census.py knows it
    AST-shaped guards     12 modules, 7,781 lines, 22% of tests/;
                          34 guards, 18 covered, 16 named             st-a-source-shaped-guard argues from it
    the test-case count   three numbers all called "the count":
                          1,253 static `test_*` functions,
                          1,566 collected by `make test`,
                          1,136 by `make unit`, ceiling 1,140/430     they disagree and nothing says so

## Gotchas

1. **The three case counts are different questions and any surface here must say WHICH it reports.**
   Static function count, pytest collection (parametrize and subTest expand), and the `[tests] cases`
   ceiling are 1,253 / 1,566 / 1,140. A census reporting one of them as "the count" is rule 4's read
   side.
2. **Boots nothing (rule 2).** A census reads git, markdown and Python as TEXT. The moment a
   candidate needs to RUN something it is a make target declared in `[verify]`, not a verb — and a
   verb that spawns ends "safe from a git hook" for every verb, because a caller can no longer tell
   which ones are safe.
3. **Rule 11's read side binds any new read verb**: it names its columns IN ORDER in `--help`, and if
   something cannot be piped the missing thing is a COLUMN, never a filter flag.
   `test_cli_surface.py::test_every_read_verb_names_its_columns` (line 609) is the floor and
   `READ_VERBS_NAMING_COLUMNS = 7` (line 66) is what it rises from; `test_no_filter_flag_was_added`
   (line 536) is the other half.
4. **A new verb's full cost, per CLAUDE.md**: a module, a route in `src/agentic_sdlc/cli.py`, a
   README row, and the grain's `changelog:` — written with `pm set`, never by hand. None of these
   write, so no refusal path and no idempotence test is owed; say so rather than leaving it unstated.
5. **A builder does not edit shared docs.** The corrected citation number goes into `CLAUDE.md`-scope
   prose and into `ms-the-rule-reaches-the-work`; both come back as PROPOSED text. `pm/roadmap/` is
   the orchestrator's, and so is closing the bug.
6. **`check doc` gates path and target claims in `[doc] scope`**, which is `CLAUDE.md`, `README.md`,
   `SDLC.md`, `docs/*.md`, the rules, the agents and the skills — one level, so `docs/research/*.md`
   is NOT in scope and this story does not put it there.
7. **`[tests] cases` unit is at 1,136 of a declared 1,140.** A new verb brings cases; the ceiling
   moves in `devkit.toml` with the argument in the shape its comment already uses.
8. **A census that scans zero files must FAIL and say so** (rule 4). Every surface here carries its
   own floor, the way `_sources()` and `_roster()` do.

## Files this story may touch

- `src/agentic_sdlc/cli.py` — the route and the `--help` line, only if a verb is the answer.
- a new module under `src/agentic_sdlc/repo/` per verb shipped.
- `tests/test_cli_surface.py` — the routed/documented census and the column declarations.
- `README.md` and `ms-the-rule-reaches-the-work` are **PROPOSED text in the report**, not edits.

## Files it must stay out of

`pm/roadmap/**`. `devkit.toml`'s `[pm.*]` sections. `tests/test_prose_census.py` and
`tests/test_guard_corpus.py` — the two sibling stories own them, and a verb that duplicates their
reader is a second scoreboard for the number it was meant to single-source.

## Acceptance criteria

1. Every number quoted in `ms-nothing-is-hand-rolled.md`, `ft-the-module-says-what-it-does.md` and
   `ft-the-suite-is-measured-like-the-source.md` is a command's output or is deleted. The list is
   enumerated in the close, with what each one reads.
2. The hard-rule citation census is askable, and `ms-the-rule-reaches-the-work`'s "roughly 600 /
   rule 4 alone 194" is corrected from its output as PROPOSED text.
   `bg-the-brief-undercounts-the-coupling-it-argues-from` closes on it.
3. Each of the four candidates gets a verdict: a verb, a flag on an existing verb, or a written
   reason why not — stated per row.
4. **No verb ships with zero callers outside its own test.** The caller is this milestone's own
   briefs, and the close names where each output was used.
5. Every new read verb names its columns in order in `--help` and adds no filter flag.
6. Nothing runs, imports or boots. Exit codes are 0 pass / 1 findings / 2 usage-or-config.
7. Every census carries a floor and FAILS on a census of zero, naming what it scanned.
8. The three test-case counts are disambiguated wherever any of them is reported.
9. The reconciliation with the pooled `ft-a-hand-rolled-command-is-a-missing-verb` is written down:
   what this story took, what stayed in the pool, and where the bug's Fix pointer now resolves.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 3, 9 | — | the enumerated list and the per-row verdict in the close, graded by the feature review | not a test — a document's claims are prose, and `[doc] scope` does not cover `pm/roadmap/` |
| 2 | unit | the citation census over a vendored fixture with a known count, plus a floor case over the real tree | new; a fixture rather than the live tree, because the live count moves every commit — that is the defect, not the gate |
| 4, 5 | integration | `test_cli_surface.py::test_every_routed_verb_is_documented` and `test_every_read_verb_names_its_columns` | existing — the router is read by AST, so an undocumented addition is caught for free |
| 6 | unit | `test_boundaries.py::OneSpawn` (from `st-spawning-has-one-seam`) and `LayersPointDownward`; the exit-code contract is `test_cli_surface.py`'s `_EXIT_CONTRACT` | existing |
| 7 | unit | a zero-file census, in the shape of `test_boundaries.py::TheCensusIsTheRealTree::test_a_moved_SRC_breaks_the_build_instead_of_passing` | new, patterned on an existing one |
| 8 | unit | the case count surface asserts which of the three it reports, over a fixture where all three differ | new — and if no surface reports a case count, this row is deleted rather than satisfied |

## Out of scope

A verb per afternoon. Eight hand-rolled commands is evidence, not a mandate; the other four rows stay
in the pool with `ft-a-hand-rolled-command-is-a-missing-verb`.

A metrics surface, a dashboard, a trend, or a number with an opinion attached. These are census
questions in the shape `check <gate>` already uses: a verdict line naming what was scanned.

Gating on any of these counts. A rising citation count is what a rule being USED looks like; what is
a defect is a document asserting a number nobody can reproduce.

The transcript harvester, the agent-kind census and the phase-declares-what-it-hands census — the
conveyor milestone.
