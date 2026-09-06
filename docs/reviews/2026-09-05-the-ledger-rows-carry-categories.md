# Feature review — `0.2.0/the-ledger-rows-carry-categories` — SHIP-WITH-FIXES

Feature-level pass over `82ea7ac`, branch `milestone/0.2.0-the-conveyor`, run 2026-09-05.
Adversarial by execution: every claim below was produced by building scratch trees in
`tempfile` and reading what `_tree_snapshot`, `named_grains` and `pm ledger report` actually
returned. Nothing here was concluded from reading the diff.

**Measured against the working tree, not against `82ea7ac` in isolation.** Four commits
landed on these files after it — `1e01518` (each kind seeds only the states its belt writes),
`2cb2be9`, `ef174b9`, `b3acf5e` — and one of them makes finding **L1** reachable on the stock
seed. Reviewing the commit as frozen would have missed it.

`report.py`'s section-3 `after_review` column is being deleted concurrently in a worktree and
is **not reviewed here**.

**All four ship criteria hold under measurement.** One MAJOR: the dispatch-side twin of this
feature's own disclosure rule is missing — a row that names a grain in a frozen key the
current declaration cannot spell is dropped from attribution with no disclosure at all, while
the status-side (`unplaced_s`) and the old-shape side (`legacy`) both disclose.

## The blocker

### L1 — a grain in an undeclared word is dropped from attribution with NO disclosure — MAJOR

`src/agentic_sdlc/repo/pm/report.py:841` —
`buckets_by_kind = LEGACY_BUCKETS if is_legacy(row) else CATEGORY_BUCKETS`.

A NEW-shape row carries both key families, so `is_legacy` is False (`report.py:854-862`) and
the row is read through `CATEGORY_BUCKETS` (`report.py:109-112`) alone. When a grain sits at a
word the current declaration does not name, the category key is empty and the frozen key — still
written, still on the row — names it. The reader ignores it and nothing says so.

Reachable on the **stock seed** since `1e01518` dropped `reviewing` from the story kind. A
story at `reviewing` is exactly the tree a vocabulary migration produces, and it is the tree
this milestone exists to create.

Measured, `tests/support/pm.tree(story_statuses=('reviewing',))`, stock config:

```
story seed states: {'todo': ('planning','ready'), 'in_progress': ('building',),
                    'done': ('done','obe')}

snapshot: {"features_building":["0.1/alpha"],"features_in_progress":["0.1/alpha"],
           "features_review":[],"milestones_building":["0.1"],
           "milestones_in_progress":["0.1"],"stories_in_progress":[],
           "stories_review":["0.1/alpha/s0"],"stories_wip":[]}

is_legacy   : False
named (new) : ['0.1/alpha']          <- the story is NOT named
named (old) : ['0.1/alpha', '0.1/alpha/s0']   <- the pre-82ea7ac reader named it
```

and the report over one dispatch row carrying that snapshot:

```
-- story (1)
grain         size  dispatches  in  out  cache_create  cache_read  tool_calls  duration_s  todo  in_progress  done  total_s
0.1/alpha/s0                 0   -    -             -           -           -           -     -            -     -        -

-- rows naming no grain (0)

json legacy      : {"rows": 0, "unattributed": 0}
json unattributed: 0
```

`check pm` on the same tree: `exit 1`, `DRIFT  story 0.1/alpha/s0: status 'reviewing' not in
(planning ready building done obe)`.

**Why this is a finding and not the honest answer.** The number is defensible — under the
current declaration nothing was in progress for that story. What is not defensible is the
SILENCE. This feature supplies the disclosure everywhere else it drops information:

- a STATUS stint in an undeclared word → `unplaced_s`, plus
  `spent time in a state this declaration does not name — seconds in no category column,
  not zero` (`report.py:129-130`, `1100-1103`);
- an OLD-SHAPE dispatch row it cannot read → `legacy`, plus
  `N of these predate category keys and name no grain` (`report.py:127-128`, `1109-1111`).

The DISPATCH-side twin — *"this row named a grain in a key your declaration cannot spell"* —
has neither. The story prints `dispatches 0` and dashes across, which is the shape D7's own
ruling calls out: *"never silently counted as empty"*. It is also a behaviour regression
against the pre-`82ea7ac` reader for exactly this tree (see the differential above), and the
regression is invisible: the report simply counts less.

Not a BLOCKER, for two reasons stated so the grade can be argued with: `check pm` already
fails such a tree loudly at exit 1 before a commit, and the drop is bounded to grains whose
status is undeclared. What is missing is a line, not a number.

The shape of a fix: count rows whose frozen keys name a grain the category keys do not, and
disclose them under the spend table the way `legacy` and `unplaced_s` already are.

## The criteria, each judged with its measurement

### Criterion 1 — category keys beside the frozen ones, and the frozen pair deprecated — MET

**Snapshot, renamed vocabulary.** A tree declaring `icebox/queued | forging/inspecting |
shipped/dropped` for every kind — no `building`, no `reviewing` anywhere:

```
{"features_building": [], "features_in_progress": ["0.1/alpha"], "features_review": [],
 "milestones_building": [], "milestones_in_progress": ["0.1"],
 "stories_in_progress": ["0.1/alpha/s0"], "stories_review": [], "stories_wip": []}

frozen all empty        : True
category all full       : True
every frozen key present: True
```

Not only the helper — through the CLI, so the row that LANDS is what was checked:
`pm ledger record --event SubagentStop --from-transcript …` → exit 0, and the appended row's
`tree` carries all eight keys in the shape above.

**Deprecated where the row shape is documented.** Every site that documents the shape,
enumerated by grep over `*.md` / `*.py` / `*.toml` outside `tests/`:
`src/agentic_sdlc/repo/pm/cli.py:1641-1651` (`_tree_snapshot`), `ledger.py:625-635`
(`usage_row`), `CHANGELOG.md:324-350`. All three carry DEPRECATED with removal at the next
major. There is no fourth site — no README table, no `docs/` page, no `--help` text lists the
`tree` keys — so nothing is silently kept.

`tests/test_pm_flow.py:486-488` names `('pm.cli', '_tree_snapshot')` as D7's dated exception in
the seed-word census, and `:609` asserts it is there. The docstring's claim reproduces.

### Criterion 2 — an old row is readable, or disclosed as unreadable — MET

The vendored fixture `tests/fixtures/ledger-old-shape/ledger.jsonl` (5 rows, 3 dispatches)
through `pm ledger report 0.1`:

```
-- story (1)
grain         size  dispatches   in   out  …  todo  in_progress  done  total_s
0.1/alpha/s0                 1  100  2000  …     -          600     -     1800
   0.1/alpha/s0 spent time in a state this declaration does not name — seconds in no category column, not zero: 1200 s

-- rows naming no grain (2)
dispatches  in   out  cache_create  cache_read  tool_calls  duration_s
         2  70  1000             -           -           4         180
   2 of these predate category keys and name no grain — unreadable under a renamed vocabulary, and not counted as empty
```

and `--json`:

```
legacy      : {"rows": 3, "unattributed": 2}
unattributed: {"dispatches": 2, "usage": {"input": 70, "output": 1000,
               "cache_creation": null, "cache_read": null},
               "tool_calls": 4, "duration_s": 180}
s0 states   : {"todo": null, "in_progress": 600, "done": null}
s0 unplaced : 1200
```

Disclosed in text AND in `--json`. Never a zero: the two unreadable rows are a census of 2 with
their own sums, not an absence; `done` and `todo` are `null` → `-`, not `0`.

The arithmetic re-derives from the rows: `building` 10:00→10:10 = 600 s in `in_progress`;
`review` 10:10→10:30 = 1200 s in a word the seed does not declare → `unplaced_s`;
`total_s` 10:00→10:30 = 1800 = 600 + 1200.

**The boundary discriminates, which the fixture alone does not prove.** Adding one NEW-shape
row that also names nothing (an idle tree) to the same ledger:

```
legacy      : {"rows": 3, "unattributed": 2}
unattributed: 3 dispatch rows
-- rows naming no grain (3)
   2 of these predate category keys and name no grain — …
```

3 unattributed, 2 legacy. The new row is not miscounted as old.

**`tree: {}` vs no `tree` at all**, the two shapes `is_legacy` distinguishes by docstring:
`{"rows": 1, "unattributed": 1}` over the pair, and `rows naming no grain (2)`. The docstring's
claim reproduces.

**The legacy reader is byte-identical to the reader it replaces.** `report.LEGACY_BUCKETS`
(`report.py:120-123`) equals `git show 82ea7ac^:…/report.py`'s `DISPATCH_BUCKETS`, character
for character. Each of the five frozen buckets exercised one at a time, old reader vs new,
against a transcription of the pre-commit code:

```
stories_wip          legacy=True  now=['0.1/alpha','0.1/alpha/s0'] then=same MATCH=True
stories_review       legacy=True  now=['0.1/alpha','0.1/alpha/s0'] then=same MATCH=True
features_building    legacy=True  now=['0.1/alpha']                then=same MATCH=True
features_review      legacy=True  now=['0.1/alpha']                then=same MATCH=True
milestones_building  legacy=True  now=[]                           then=same MATCH=True
```

The fixture only exercises `stories_wip`; the other four are proven here and nowhere in the
suite.

**No regression on the seam for declared states.** For every (feature status, story status)
pair the stock seed declares — 30 pairs — the tree was built, `_tree_snapshot` run, and the
NEW reader compared against the OLD one over the row that lands: **0 mismatches.** The
mismatch class that does exist is L1, and it is outside the declaration.

### Criterion 3 — dwell columns per CATEGORY, three not twelve — MET

A project declaring twelve states per kind (`icebox triaged groomed queued | forging paused
inspecting reworking | shipped dropped superseded absorbed`), with a story walked through eight
of them one hour apart:

```
grain         size  dispatches  …  duration_s   todo  in_progress  done  total_s
0.1/alpha/s0                 0  …           -  10800        14400     -    25200

column count: 13 | dwell columns: ['todo','in_progress','done'] | project words leaked: []
state_columns(cfg, "story") = ('todo', 'in_progress', 'done')
json states: {"todo": 10800, "in_progress": 14400, "done": null} unplaced: None total_s: 25200
```

Three columns, both tables, no project word in a header. The sums re-derive: `triaged` +
`groomed` + `queued` = 3 × 3600 = 10800 todo; `forging` + `paused` + `inspecting` +
`reworking` = 4 × 3600 = 14400 in_progress; `shipped` is the last row so its clock is running
and `done` is `-`, not `0`; `total_s` 10:00→17:00 = 25200.

### Criterion 4 — a test reads a vendored old-shape fixture — MET

`tests/test_pm_ledger_report.py:448` reads `tests/fixtures/ledger-old-shape/ledger.jsonl` and
asserts both halves — the readable row attributed (`dispatches == 1`, `output == 2000`) and
the boundary disclosed (`legacy == {'rows': 3, 'unattributed': 2}`, the `-- rows naming no
grain (2)` heading and the full disclosure sentence). Its twin at `:494` asserts the line does
NOT appear for a current-shape ledger and that `legacy` is `{"rows": 0, "unattributed": 0}` —
a number, never an absent key. Vendored under `tests/fixtures/`, hard rule 8 satisfied, and
the fixture's README states what each of its five rows is for.

Both claims re-measured independently here and both reproduce, including on the two paths the
tests do not take: `legacy` over a ledger with no boundary is `{"rows": 0, "unattributed": 0}`,
and over a milestone with **no ledger file at all** the report prints
`[ledger:report] 0.1 — no ledger` at exit 0 with the same zeros in `--json` — the CHANGELOG's
"zeros when there is no boundary" claim, reproduced on both paths.

## Rule 6 — every row key that existed before `82ea7ac` still exists

Grepped the row writers before and after:

| surface | before `82ea7ac` | after |
|---|---|---|
| `ledger.ROW_KEYS` | 16 keys | identical, 16 keys |
| `_tree_snapshot` frozen buckets | `milestones_building` `features_building` `features_review` `stories_wip` `stories_review` | all five, still written, still matched by the same seed words |
| `report` attribution buckets | `DISPATCH_BUCKETS` | same tuple, renamed `LEGACY_BUCKETS`, still read for old rows |

Nothing was removed from the row. What DID change is output format, and it is a minor bump at
least under rule 6/7: the spend table's per-word dwell columns became three per-category ones,
`--json`'s `states` re-keyed from state words to categories, and `unplaced_s` and `legacy` are
new keys. `CHANGELOG.md:324-350` states all of it, including *"The old per-word columns are
gone"*. The version is unbumped, which is this repo's bump-at-close posture (CLAUDE.md,
D8 off) and not a finding.

## Rule 9 — nothing here decides what a category MEANS

Every category question in the change routes to the project's declaration or to `model`'s
closed set, and each was traced to its source:

- `_tree_snapshot`'s `in_progress()` (`cli.py:1667-1668`) → `model.category_of` → `flow_of`.
- `report.category_seconds` (`report.py:890-905`) → `model.category_of`, and `None` is
  **disclosed** as `unplaced`, never folded into a column by guess.
- `report.state_columns` (`report.py:866-887`) returns `model.CATEGORIES` — the closed
  three-name set `model` validates every declaration against, not an opinion about a word.
- `LEGACY_BUCKETS` reads old rows AS WRITTEN and explicitly never through the current
  declaration, which is D7's second rejected alternative held to.

The one seed-word comparison that remains is the frozen keys' `mstat == model.BUILDING` /
`fstat == model.REVIEWING` in `_tree_snapshot` — the dated, deprecated D7 exception, and it is
named as such in `tests/test_pm_flow.py:486-488`.

## The rest of the findings

### L2 — the disclosure note over-claims for a row that named a grain elsewhere — MINOR

`report.py:127-128`. An OLD-SHAPE row whose `stories_wip` names a story from a **different**
milestone is counted in `legacy.unattributed` and gets the line
`unreadable under a renamed vocabulary`. Measured:

```
['-- rows naming no grain (1)',
 '   1 of these predate category keys and name no grain — unreadable under a
    renamed vocabulary, and not counted as empty']
legacy: {"rows": 1, "unattributed": 1}
```

That row was perfectly readable and named a real grain — it simply named one outside this
milestone. `spend_data`'s own comment (`report.py:966-971`) says the class is *"EITHER a
dispatch over an idle tree OR a dispatch over a tree whose words that shape could not spell"*;
this is a third case neither names. The error is in the safe direction (over-disclosing, not
under-), so MINOR — but the sentence asserts something false about that row.

### L3 — `report.LEGACY_KEYS` is defined and never read — NIT

`report.py:124`. Introduced by `82ea7ac` beside `CATEGORY_KEYS`, which `is_legacy` does read.
`grep -rn LEGACY_KEYS src tests` returns exactly the definition line. Dead constant.

### L4 — `state_columns(cfg, kind)` ignores both parameters — NIT

`report.py:866`. The body is `return model.CATEGORIES`. Defensible as a call-site shape that
survives a future per-kind answer, and the docstring says so in effect — but a reader has to
open the body to learn that neither argument is consulted.

### L5 — the feature carries no stories, so no `## How this is proven` table — QUESTION

`pm/roadmap/0.2.0-the-conveyor/features/the-ledger-rows-carry-categories/` holds `feature.md`
and nothing else. The reviewer contract asks whether the story's proof table matches what
landed; there is no story and no table, so the four added test cases were held against the
ship criteria instead. Six of this milestone's sixteen features are the same shape, so this is
the milestone's pattern rather than a deviation for this feature — raised as a QUESTION, for
whoever owns that pattern.

## The tests this change added

Four cases, none of them spawning: `pytest tests/test_pm_ledger_report.py
tests/test_pm_ledger_record.py --collect-only -m shell` collects **0 of 63** — every one is a
function call or a `tempfile` tree, which is rule 10's cheapest tier that can fail. The three
touched modules run in **0.66 s** for 90 cases.

Each earns its place against the "if this were deleted, what would it cost" test:

- `test_a_renamed_vocabulary_fills_the_category_keys_and_empties_the_frozen` gates criterion 1;
  no existing case declares a vocabulary the frozen keys cannot spell, and without it the
  feature's headline claim is unproven.
- `test_an_old_shape_ledger_is_read_where_it_can_be_and_disclosed_where_not` gates criteria 2
  and 4 over a data shape this package no longer writes — a vendored fixture is the only way to
  produce it, and its docstring says why it is not an amendment to the seeded golden.
- `test_a_current_shape_ledger_discloses_no_boundary` is the discrimination half; without it
  the disclosure could fire on every ledger and the first test would still pass.
- The `snapshot()` mirror in `tests/support/pm.py` keeps the two families agreeing the way the
  writer produces them. Worth naming: because it mirrors, no committed case reads a row where
  the two families DISAGREE — which is the gap L1 lives in.

`make check` 5/5 PASS (2.8 s), `make unit` 706 passed / 2 skipped / 505 subtests (9.3 s),
`make test` 1095 passed / 2 skipped / 557 subtests (55.0 s) — all my runs, on the working tree.

## What I did NOT verify

- **`pm ledger report --from <rev>`** over an old-shape ledger. `GitSource` is shared code and
  the attribution path is identical, but no run through git was made — the whole review is
  in-process and `tempfile`-based.
- **`pm ledger show`.** `ledger.row_names` scans every `tree` value, so a new row names a grain
  in both families; I reasoned that set membership makes double-counting impossible and did
  **not** run `show` to confirm it.
- **Section 3's `after_review` column** and everything downstream of it — being deleted
  concurrently, excluded by instruction.
- **Sections 2, 4, 5 and 6** of `pm ledger report`. They do not read `tree`, so they are
  outside this feature's surface; their output appeared in my runs and was not inspected.
- **A consumer install.** No `install-*` verb was run into a temp repo; the row-shape
  documentation census is over this checkout's source, which is where the deprecation would
  have to be.
- **CRLF, non-UTF-8 and torn-tail ledgers** under the new keys. `append_row` and `read_rows`
  are untouched by `82ea7ac`, so I scoped them out rather than re-proving them.
- **`82ea7ac` as frozen.** Everything measured is the working tree at `2cccde2`. Four later
  commits touch these files; L1 is reachable only because of one of them, and a
  commit-as-frozen review would have returned clean.
- **Whether L1 bites this repo today.** `make check` is green here, so no grain currently sits
  at an undeclared word — the finding is about a consumer mid-migration, not about this tree.

Reviewer's token cost: ~210k.

```text
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| L1 | MAJOR | open: needs a disclosure line, not a number — see the shape-of-a-fix note |
| L2 | MINOR | open |
| L3 | NIT | open |
| L4 | NIT | open |
| L5 | QUESTION | open: the milestone's pattern, not this feature's choice |
```
