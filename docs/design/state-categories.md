# The engine should have no opinion about the words

**Written 2026-09-05, from Chris's reading of the SDLC.**

> *"This tool, all the grammar and the states, it actually really shouldn't have an opinion about
> those. It should just provide the engine and the machinery. And all the states should be
> configurable. … What it's really looking for is: is everything in the macro completed column."*

This document is the case for that plus the design; it shipped in 0.2.0, and §5 keeps the record.

## 1. The tool currently has an opinion, in thirty-two places

`grep` over `src/agentic_sdlc`, 2026-09-05: 32 reads of a hardcoded state word, plus bare `'done'`
literals in `pm/cli.py`.

| where | what it hardcodes |
|---|---|
| `model.py:75-76` | `BUILDING = 'building'`, `REVIEWING = 'reviewing'` |
| `model.py:80` | `STALLED_IF_ALL_STORIES_DONE = LIFECYCLE[:LIFECYCLE.index(REVIEWING)]` |
| `model.py:1030-1042` | *"is `status` at or past `BUILDING`"* — D5's whole question |
| `ledger.py:589` | `TERMINAL_STATE = 'done'` |
| `ready_for.py:135` | `DONE = model.LIFECYCLE[-1]` |
| `pm/cli.py` ×12 | `model.REVIEWING` and `'done'` in the feature/story close paths |

`[pm] story_states` is configurable, but every question is asked by NAME, so a project that
renames `building` gets a D5 that cannot place it and silently stops asking.

## 2. Today proved it, twice, in one session

`pm ready-for feature` first asked for every story at `reviewing`, then at `done`; both are wrong
the same way, because the question is *"is every story finished"* and no single word answers it
for another vocabulary. The `done` spelling also made a story abandoned at `obe` / `wontfix` /
`duplicate` block its feature forever.

## 3. What mature trackers do, and they converge

- **Jira**: three hardcoded status *categories* over an unlimited user-defined status set, each
  status in exactly one category; `status = Done` vs `statusCategory = Done` is a documented trap.
- **Azure DevOps**: `Proposed`, `In Progress`, `Resolved`, `Completed`, plus `Removed` (hidden).
- **Linear**: `Backlog`, `Planned`, `Started`, `Completed`, `Canceled`.

All agree the category set is CLOSED and small and the state set is OPEN; they split on where
"we stopped doing it" lives (Jira: a `resolution` field; the others: a category). §4 takes Jira's.

## 4. The design

### Three categories, and they are a HARD opinion

Chris, 2026-09-05: *"Your work can only fall within those three categories. We could invent more,
but I don't think we should."*

```
todo         not started
in_progress  started, not finished
done         finished
```

### The fourth category this document proposed, and why it was wrong

The first draft had a `dropped` category for abandoned work; shipped-vs-abandoned is an OUTCOME,
a different axis from progress, and folding it in gives one field two meanings. So `obe` is a
`done` state, and "how much did we deliver" is a separate outcome field if anyone asks for it.

### The config

```toml
[pm.states.story]
todo        = ["planning", "ready"]
in_progress = ["building", "reviewing", "accepted", "packaging"]
done        = ["done", "obe"]
```

`accepted` and `packaging` are `in_progress` because a category is about whether WORK REMAINS,
not whether the outcome is decided (Chris: *"work isn't done if it's being packaged"*). Declared
per grain kind, so a bug's `open` / `fixed` / `closed` is declared the same way. The seed
reproduces today's `LIFECYCLE`, but it is a seed that gets WRITTEN, not a fallback.

The engine keeps three opinions and no more:

1. the category set is `todo`, `in_progress`, `done`;
2. they are ordered `todo < in_progress < done`;
3. every declared state maps to exactly one; none or two is a `ConfigError` at exit 2.

Everything else — how many states, their names, which category, their order — is the project's.

### The table is WRITTEN by `init` and READ every run — never assumed

| | where | what it is |
|---|---|---|
| **the seed** | code | the shipped default table, versioned with the engine |
| **the declaration** | the project's `devkit.toml`, written by `init` | THIS project's states and transitions |
| **the reader** | every run | reads the declaration and does not fall back |

A runtime fallback is the engine keeping its opinion with extra steps, so `init` materializes the
seed into the config, where it is visible and diffable.

#### Hard rule 5 is not an exception to make — it is a rule to split

Rule 5 was written for a read-only linter whose defaults were universal, before `pm` existed. Its
first half (config, never edit the tool) guards against forks and stays; its second half (no
`devkit.toml` behaves like declared defaults) is scoped to the GATES, because a WORKFLOW's states
have no universal default: `init` writes them and a tree without them is refused by name.

#### And a pin bump is where this gets tested

A release that adds a conveyor step adds a transition the consumer's older config lacks;
`adopt`'s `config-updated` step names it, with the seed value to paste.

### Ordering falls out, and it is only over categories

D5's *"is the parent behind its children"* needs only `todo < in_progress < done`, over
categories, never over words; order within a category is presentation. That deletes
`model.py:1030`'s `states.index(status) >= states.index(BUILDING)`.

### What each caller becomes

| today | becomes |
|---|---|
| `pm ready-for feature` — every story `== 'done'` | every story in category `done` |
| — | a story at `packaging` now BLOCKS, because packaging is work |
| `check pm` D2 — `STALLED_IF_ALL_STORIES_DONE` | children all `done`, parent still `todo` |
| `check pm` D5 — `at_or_past(BUILDING)` | child's category > parent's category |
| `ledger.TERMINAL_STATE = 'done'` | the grain kind's `done` category |
| `pm ledger report` dwell columns — one per state | one per category |
| conveyor `stories-done` | category `done`, via `ready-for` |

## 5. What this costs, and why it is not 0.2.0

*History: 0.3.0 was collapsed into 0.2.0 on 2026-09-05 and everything above shipped there.
`also_done` (below) and `feature done --cascade` (§6) are retired and refused by name; `--skip`
(§7) left with D12. Kept as the record of what was rejected.*

The original ruling: thirty-two call sites plus a schema change is a milestone, not a patch.

### The two lines 0.2.0 does take

```toml
[pm]
also_done = ["obe"]     # default: () — more words that mean FINISHED
```

The `done` category with one member enumerated by hand, to be folded into `[pm.states.<kind>]
done` and deleted; the rest was deferred as consumer-visible behaviour change.

## 6. The engine has two verbs, and everything else is declaration

Chris, 2026-09-05: *"It's just a conveyor belt of moving action to action. It's not inference."*

```
move(grain, to_state)          is this transition declared? then write it.
holds(grains, category|state)  are they all there? yes or no, and name who is not.
```

Everything a belt does is a sequence of those plus commands the project named; anything else is
inference, an opinion a project cannot see, change or choose.

### The inference census, measured 2026-09-05

| where | what it infers | becomes |
|---|---|---|
| `model.py:80` `STALLED_IF_ALL_STORIES_DONE` | which states mean a feature has not advanced | `holds(feature, todo)` |
| ~~D2's "advance it"~~ | WITHDRAWN: `ADVANCE_IT` is `checks/pm.py:159`, a gate's job under rule 9 | nothing |
| `pm/cli.py:1524-1557` ledger dispatch snapshot | which states count as open work, keyed on literals | category buckets — a DATA MIGRATION, the keys are in JSONL rows |
| `execlist.py:44-50` `_phase_key` | `seam`, a word about a project's phase vocabulary | declared, or dropped |
| `model.py:1071-1084` `at_or_past(BUILDING)` | ordering by indexing a tuple of words | category order |
| `ledger.py:597` `terminal_state(cfg, kind)` | which single state ends a grain; special-cases bugs | `holds(grain, done)` |
| `pm/cli.py` `feature done --cascade` | which stories to move, and to what | the `feature` belt's declared steps |
| `model.py:979` `review_slug_fallback` | a review record, from a filename glob | a pointer, or a finding |
| `checks/grain_shape.py:167` `_kind_of` | a grain's kind, from path shape | finish declaring it |
| `model.py:1122` `states_without_building` | the state sets D5 cannot place BUILDING in | deleted |

### The price, which the first draft did not name

D5 and D2 report strictly LESS (three positions instead of seven, two instead of three): the
right trade, but a CHANGELOG behaviour change, not an improvement.

### What this buys, and it is the durability argument

A project adds a state, maps it and wires its transitions, and the engine ships nothing, because
it never asks *which word*, only *which category* and *is this move declared*.

### The line this does NOT cross

The engine still refuses facts about the input (a state in no category or two, an undeclared
state, a `move` the table does not permit, a wrong-shaped value): that is reading, not deciding.

## 7. It GATES the SDLC. It does not run it.

Chris, 2026-09-05: *"It shouldn't say, no, you can't do that. It should just say: warning, you're
moving to a closed state, and you have open children."*

### 0.2.0 built refusal where the package's own rule said report

`.claude/rules/pm-execution.md` already said `pm feature reviewing` REPORTS, never refuses.

### The rule, and it has exactly one edge

| about | answer | why |
|---|---|---|
| **the INPUT** — malformed id, undeclared state, transition not in the table, wrong-shaped value | REFUSE, exit 2 | reading, not deciding |
| **the TREE** — open children, no review record, dirty worktree, red gate | REPORT, and proceed | the caller knows whether that is wrong and the engine does not |

```
$ agentic-sdlc close feature 0.2.0/alpha
[feature:stories-done] WARNING — 3 story/ies not in `done`: s1 is building, s2 is
                       reviewing, s3 is planning
[feature] feature 0.2.0/alpha: reviewing -> done  (1 warning)
```

### Why refusing is worse, and it is not a philosophical point

- A tool that refuses gets worked around, invisibly, and then the protocol teaches nothing.
- The engine cannot hold the reason; *why* a feature closed with an open story is intent.
- The gate already exists: `check pm` fails a contradictory tree, in CI and pre-push.

### What this deletes from 0.2.0

- `close story` / `close feature` / `release` / `adopt` stop blocking: they walk, warn, finish.
- `pm ready-for` becomes a read verb whose exit code is information, not a wall.
- The 0.24.0 lesson survives as an ordered list with a loud warning at `review-landed`;
  `--skip <step> --reason` shrinks to a note.

### The one-line test for anything added to this engine later

**Is this the engine reading what the project declared, or deciding what the project should do?**
