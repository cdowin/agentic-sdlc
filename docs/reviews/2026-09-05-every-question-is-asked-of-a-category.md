# Feature review — `0.2.0/every-question-is-asked-of-a-category` — HOLD

Feature-level pass (SDLC.md §0, §6) over phase 7 of `0.2.0`, branch
`milestone/0.2.0-the-conveyor` at `2cccde2`. The feature landed in **`32b20b1`**; the per-kind
seed and the deletion of `[pm.transitions.<kind>]` landed after it in **`1e01518`**, which
narrowed what two of the criteria can mean and widened the criterion-2 test. Both are judged here.

Adversarial by execution, in a copy of this tree at
`/private/tmp/.../scratchpad/scratch-repo` — 40 MB, `.claude/worktrees/` removed, the CLI run as
`uv run -q agentic-sdlc …` from that root. **No file in this checkout was modified except this
record, and no `git` write command was run.**

**The northstar is delivered and the seam through the CLI is not.** Every question the engine
asks about a status really is asked of a category: over the whole package, all 41 modules, exactly
15 seed-word string constants survive and all 15 are in the seed block (`model.py:92`, `:183-200`)
plus the documented `verdict.OPEN` homonym. A full rename of every state word in `devkit.toml`
and in 63 grain files leaves `check pm`, `check all`, `pm list`, `pm ready-for` ×4, `pm validate`
and `pm vocabulary` **byte-identical modulo the words**, at identical exit codes. The refusals all
fire at exit 2 naming the key. The WARN-not-fail posture is exactly as specified.

What is not delivered is the exit-code contract on the one path every existing consumer takes.
A tree that has not declared a flow — every consumer's tree on the day it bumps its pin, before it
runs `pm init` — gets an **uncaught Python traceback at exit 1** from `pm status`, `pm list`,
`pm ready-for`, `pm story|feature|milestone|bug` and `pm ledger report`, carrying the correct
message inside a stack trace at the wrong exit code, while `check pm` on the same tree exits 2
with the same message on one line. That is hard rule 6, and it is decision D11's own ruling
re-broken one module over.

## Blockers

### V1 (BLOCKER) — a tree that declares no flow crashes with a traceback at exit 1; `check pm` exits 2 on the identical tree

`src/agentic_sdlc/repo/pm/cli.py:2229-2236` — `main`'s dispatch guard:

```python
    try:
        return fn(cfg, rest)
    except Refused as err:
        print(f'[pm] REFUSED — {err}', file=sys.stderr)
        return 1
    except (Usage, model.AmbiguousStory) as err:
        print(f'[pm] ERROR — {err}', file=sys.stderr)
        return 2
```

`model.ConfigError` is not in it. The one place `main` does catch it is around `model.load()`
(`cli.py:2204-2207`) — the config **parse**. This feature made the absent-declaration refusal
**lazy**: `_load_flows` returns `{}` for an absent section by design (`model.py:513-516`,
"ABSENT IS ABSENT — an empty dict, never the seed") and `flow_of` (`model.py:686-694`) raises
during the walk, after dispatch, where nothing catches it.

Measured in the scratch copy with every `[pm.states.*]` block stripped and nothing else changed:

| command | exit | what the user sees |
|---|---|---|
| `check pm` | **2** | one line, the message, correct |
| `check all` | **2** | correct |
| `pm status` | **1** | prints `milestone 0.1.0 [planning]`, then a traceback — a partial board and a mid-walk crash |
| `pm list` | **1** | traceback |
| `pm ready-for milestone 0.2.0` | **1** | traceback |
| `pm story building <id>` | **1** | traceback |
| `pm ledger report` | **1** | traceback |
| `pm vocabulary` | 0 | correct — this is the verb that answers the tree the others refuse |

The five tracebacks end at `model.py:692, in flow_of` with the right sentence:
`ConfigError: this tree declares no flow: [pm.states.story] is not in devkit.toml … Run
`agentic-sdlc pm init` to write them`. The message is right; the delivery is a stack trace and
the exit code is `1`, which hard rule 6 reserves for **findings**. A consumer's CI reads
"the gate found things" for what is actually "your config is not readable", and the pre-push
hook that runs `pm` verbs prints a Python traceback to a human who needs one sentence.

Three things make this a blocker rather than a MAJOR:

1. **It is the upgrade path, not an edge.** Every consumer on the previous pin has no
   `[pm.states.*]`. `ada37ae` gave `pm init` the append path so they can fix it — and the verb
   that tells them to run it is the one that crashes first.
2. **Two entry points disagree about the same tree.** `check pm` catches it
   (`checks/pm.py:104`) and exits 2; `pm` does not. Rule 6 calls the exit code a contract.
3. **D11 already ruled on exactly this shape** — *"a `ConfigError` raised by a step's `check()`
   escaped `main` as a traceback at exit 1, hard rule 6's code for FINDINGS"* — and `1abba53`
   fixed it for the conveyor. The pm CLI kept the defect, and this feature is what made the
   refusal reachable there.

**Why no test caught it.** The two flow-less cases,
`tests/test_pm_flow.py:160` (`test_a_tree_declaring_nothing_gets_no_flow_and_is_refused_by_name`)
and `tests/test_pm_flow.py:280`, both call `model.flow_of` / `model.holds` **directly** and assert
the exception is raised. They pass, correctly. The contract they are proving — exit 2 — lives at
the CLI altitude, and no case exercises it there. By contrast the *malformed* cases in the
parametrized block at `tests/test_pm_flow.py:275-300` do reach the CLI and do exit 2 (I confirmed
all seven), because `_load_flows` raises inside `model.load()`, inside the guard. The asymmetry
between "malformed" and "absent" is the whole of the gap.

The fix is one `except model.ConfigError` clause returning 2 beside the two that are there, and a
case that runs one pm verb through `main` on a flow-less tree.

## Non-blocking findings

### V2 (MAJOR) — `pm set <id> status <word>` writes any word at exit 0, and two docstrings this commit wrote say it cannot

`cmd_set` (`src/agentic_sdlc/repo/pm/cli.py:1040-1058`) calls `model.set_field(path, key, value)`
with no `move_defect` check and no ledger stamp. Measured in scratch, on this repo's own tree:

```
$ agentic-sdlc pm set 0.2.0/…/01-each-kind-declares-its-own-states status wombat
[pm] …: status 'building' -> 'wombat'                                      exit 0
$ agentic-sdlc pm set 0.2.0/…/01-each-kind-declares-its-own-states status reviewing
[pm] …: status 'wombat' -> 'reviewing'                                     exit 0
      # `reviewing` is declared for a FEATURE, never for a story, since 1e01518

$ agentic-sdlc pm story wombat 0.2.0/…/01-…                                exit 2
$ agentic-sdlc pm feature wombat …                                         exit 2
$ agentic-sdlc pm bug wombat …                                             exit 2
$ agentic-sdlc pm milestone wombat 0.2.0                                   exit 2
$ agentic-sdlc pm story reviewing 0.2.0/…/01-…                             exit 2
```

The four belt verbs refuse correctly through `_movable` → `move_defect`. `pm set` is the fifth
verb that writes a `status:` line and it asks nothing. Two claims written **by this feature's own
commit** (`git blame` → `32b20b1`) are therefore false as stated:

- `cli.py:3-5` — *"Moves a story/feature/milestone `status:` through code rather than a regex:
  **the verb** validates the value against that grain's DECLARED flow (`model.move_defect`)"*
- `cli.py:358-359` — *"`model.move_defect` is the engine's whole opinion about a move, and
  **every status verb asks it BEFORE resolving the grain**"*

`cmd_bug`'s docstring (`cli.py:390-393`) already knows: *"today only a hand edit or **the untyped
`pm set`** reaches it"*. So the gap is known and the universal claim beside it was still written.

Not a blocker: the resulting file is caught by `check pm` D4 at exit 1 on the next run — measured,
`DRIFT story …: status 'wombat' not in (planning ready building done obe)` — so this is a write
that lies until the next gate, not one that lies permanently. It is still rule 4's write-side
shape (*a diff that looks legitimate and is not*), and `pm set status` additionally leaves **no
ledger row** where every other status verb stamps one (`cli.py:293-300`: *"Every verb below that
CHANGES the tree appends one row"*). Either route `cmd_set`'s `status` key through `_movable` +
`_stamp_status`, or narrow the two claims to name `pm set` as the untyped escape hatch.

`tests/test_pm_verbs.py:605` exercises `set … status done` at exit 0 and no case tries an
undeclared word, so nothing fails today.

### V3 (MAJOR) — `readied()` keys on ORDER WITHIN the `todo` category, and two shipped claims say no gate does

`src/agentic_sdlc/repo/pm/model.py:1635-1640`:

```python
def readied(cfg: PmConfig, kind: str, status: str) -> bool:
    """True when `status` is declared and is past the kind's first `todo`."""
    ...
    return status != flow.by_category[TODO][0]
```

Three `check pm` sites read it — `checks/pm.py:209` (milestone), `:264` (feature), `:282` (story)
— and it gates every READY warning: the missing `branch:`, the empty `## Ship criterion`, the
feature with no stories, the story with no `## Acceptance criteria`.

Measured on this repo's own tree, changing **only** the order of two words inside one category —
no word renamed, no word moved between categories, the mapping identical:

```
todo = ["planning", "ready"]   ->  check pm exit 0,  7 WARN
todo = ["ready", "planning"]   ->  check pm exit 0, 13 WARN
```

The six new lines are every `planning` grain in the tree suddenly reading as "readied":
`WARN milestone 0.1.0 is 'planning' with no branch: — readied …`, and so on.

Two claims in files this feature owns say that cannot happen:

- `model.py:117-119`, `Flow.order`'s docstring — *"Order WITHIN a category is presentation and no
  gate keys on it (design §4: 'whether `packaging` precedes `done` is a project's business and no
  gate's')."*
- `devkit.toml:121`, the project-facing comment above `[pm.states.*]` — *"what order they appear
  in within it — is ours, and **changing a word here changes no code anywhere**."*

This is the shape rule 4 names: an engine opinion surviving under a new name. `work_started` /
`at_or_past(BUILDING)` was `states.index(status) >= states.index(BUILDING)`; `readied` is
`status != by_category[TODO][0]` — the same positional inference, one category narrower, and it
is not in the census, not in `DELETED`, and invisible to `test_no_state_literal_survives_outside_the_seed`
because it indexes a tuple instead of spelling a word.

Two things keep it off the blocker list. It does not produce a false PASS — the warnings are
advisory, the exit code is 0 either way. And it is **disclosed**: `CHANGELOG.md:104-105` states it
plainly (*"a grain that has been readied — past its kind's FIRST `todo` state, under whatever
words the project declared"*), and it was introduced by `33a4f62`, a story of
`the-code-knows-entry-and-exit`, not by this feature. So the behaviour is a decision somebody
made; the two claims that contradict it are the defect. Either amend both claims to say
"except the first `todo` state, which `readied` treats as not-yet-started", or give the project a
way to say which of its `todo` words means that — the engine picking index 0 is the engine
deciding, which is rule 9's line.

### V4 (MINOR) — the census test scans 27 of the package's 41 modules

`tests/test_pm_flow.py:_census_modules()` globs `(SRC/family).glob('*.py')` for `pm`, `checks` and
`verify` — non-recursive — and `test_the_belts_spell_no_state_word` adds `conveyor/`. Fourteen
modules are never scanned:

```
__init__.py  cli.py  core/{__init__,apply,config,makefile,markdown,project,walk}.py
repo/{__init__,gates_extra,init,install}.py  repo/pm/templates/__init__.py
```

I ran the same AST scan over **all 41** and they carry **zero** seed-word string constants today,
so nothing is hidden — the count is the finding, not a survivor. But criterion 2's promise is that
a literal added next year *"is reported as `cli.py:<line>`, not as a count that went from 0 to 1"*,
and a literal added to `repo/init.py` or `core/config.py` would be reported as nothing at all.
`SRC.rglob('*.py')` with the same allowlist costs one character and closes it.

### V5 (MINOR) — criterion 5's vendored twin compares two verbs; four more were never gated

`tests/test_pm_gate.py:1490` (`ARenamedVocabularyGetsTheSameAnswers`) is a strong test — it builds
the stock twin from `tests/fixtures/renamed-vocabulary/` by substitution, asserts the fixture has
not drifted back toward the seed (`test_the_fixture_is_wholly_renamed_and_the_twin_is_wholly_stock`),
and checks that each of D1–D6, D9 and D10 actually fires on the renamed side so two empty
transcripts cannot pass. It compares **`check pm`** and **`pm status`**.

It does not compare `pm list`, `pm ready-for feature|milestone|tag`, or `pm vocabulary`. I measured
all of them myself against this repo's tree with every state word renamed and every grain file
rewritten (see the measurement table below) and they are identical modulo the words at identical
exit codes — so the product is right and the gate is narrower than the criterion. Adding the four
to the existing `_copies()` harness is a loop, not a new fixture.

### V6 (MINOR) — `pm status`'s status column is a magic `8`, and it is the one output the rename moves

`src/agentic_sdlc/repo/pm/cli.py:853`:

```python
f'[{view.status:<8}] stories {view.done_n}/{view.total} done{drift}'
```

Eight is the width of `planning` and `building`. `reviewing` overflows it under the shipped
vocabulary; under a renamed one the shorter words pad out to it. This was the only difference in
my whole rename sweep — 10 of 12 captured outputs byte-identical modulo the words, `pm status` and
`pm status 0.2.0` differing only in trailing spaces inside `[...]`. The twin test accommodates it
by whitespace-squeezing each line (`test_pm_gate.py:1604-1612`) with a comment that calls it
alignment rather than behaviour, which is a fair call. Deriving the width from
`max(len(w) for w in flow.order)` would make the criterion's word "identical" literally true and
delete the exemption.

### V7 (QUESTION) — criterion 1's "refuses an undeclared transition" now means "refuses an undeclared state", and the criterion was never amended

Ship criterion 1 reads *"`move` refuses an undeclared transition at exit 2"*, written against
`state-categories.md` §6's `move(grain, to_state)` — *"is this transition declared? then write
it."* `1e01518` deleted `[pm.transitions.<kind>]` and `model.transition_target` per D12, so there
is no transition to declare. What ships is `move_defect(cfg, kind, to_state)` — *"is the target a
state this project declared?"* — with an explicit docstring saying there is no edge graph and
`D3`/`D4`/`D5` check end state instead. That is a defensible narrowing and it is well argued in
place; measured, it refuses at exit 2 for all four kinds.

Two loose ends: the criterion text in `feature.md:114-116` still says "transition", so a reader
grading this feature from its own record grades it against a contract that was retired, and
`move_defect` is a **predicate** — the write it guards happens in `cli.py`, so the "two verbs"
are one predicate and one census, not the verb pair §6 describes. Worth one amending line in the
feature record at close.

### V8 (NIT) — `_set_status(cfg, path, value)` takes a config it never reads

`cli.py:286-290` accepts `cfg` and uses it only for `cfg.rel(path)` in the failure message. A
signature that carries the config reads as though it validates against it; every caller does the
validating one frame up, and V2 is the caller that does not.

### V9 (NIT) — the replacement for the R4 test dropped its positive assertion

`test_the_r4_site_reads_the_flow_and_spells_no_word` asserted both that `_status_at_or_past` spelled
no word **and** that it read `model.flow_of` and did *not* read `model.LIFECYCLE` / `BUILDING` /
`REVIEWING` / `cfg.milestone_states`. Its replacement, `test_the_belts_spell_no_state_word`, is
wider on scope (all of `conveyor/`, no exceptions, which is the better trade) but keeps only the
negative half. `test_the_seeds_exported_words_have_exactly_the_named_readers` covers the
`model.LIFECYCLE` half for the whole package, so the loss is small — naming it here so a future
reader does not rediscover it as a regression.

## What each criterion was judged by

| # | criterion | verdict | the measurement |
|---|---|---|---|
| 1 | the two verbs exist with their own tests; `move` refuses an undeclared transition at exit 2 | **PASS as amended** | `holds`, `move_defect`, `category_of`, `flow_of`, `in_progress_milestones` all present, `TestHolds` / `TestMove` in `tests/test_pm_flow.py`. `pm story\|feature\|bug\|milestone wombat` → exit 2 naming `[pm.states.<kind>]` and listing what the kind does declare, all four measured. `pm story reviewing <story-id>` → exit 2 (declared for `feature`, not `story`). "Transition" now means "target state" — V7 |
| 2 | every census row routes through one of them; a test asserts no state literal survives outside the config reader | **PASS** | My own AST scan over **all 41** package modules: 15 seed-word string constants, all in the seed (`model.py:92`, `:183-200`) plus `verdict.OPEN`. The shipped census test (`test_no_state_literal_survives_outside_the_seed` + `test_the_belts_spell_no_state_word` + `test_the_seeds_exported_words_have_exactly_the_named_readers`) enumerates `DELETED`, `RETIRED`, `SEED_ASSIGNMENTS` and `SEED_WORD_READERS` and fails by name. `SEED_WORDS` is derived from `DEFAULT_FLOWS` and did **not** narrow under `1e01518`'s per-kind seed — the milestone still holds all seven, so the union is the same 11 words. Scope gap: V4 |
| 3 | `also_done`, `at_or_past`, `STALLED_IF_ALL_STORIES_DONE`, `states_without_building` deleted; P9's two call sites are one | **PASS** | `test_every_symbol_the_census_deleted_is_gone` walks 18 `(module, symbol)` pairs by `importlib` + `hasattr`; ran, green. All six retired `[pm]` keys refuse by name — measured at the CLI: `[pm] also_done was retired and is refused — the `done` category is [pm.states.<kind>] done = [...]`, `[pm] story_states was retired and is refused`, both exit 2 on all five verbs tried. `ready_for.py:318,391,406` and `checks/pm.py:232` now share `model.holds` |
| 4 | D2, D3, D5, D6, D8, D9, D10 all ask `holds`; D8/D9/D10 report per `in_progress` milestone | **PASS** | `checks/pm.py:232` is one `holds(features, done)` feeding both D3's per-feature line and D6's census, with a comment saying why; D2/D3/D5/D6 are `warn(...)` (`:246`, `:294`, `:303`, `:310`), never `report(...)`. `in_progress_milestones` (`model.py:1385-1402`) filters on `category_of(...) == IN_PROGRESS` and every reader loops it. Measured: with **two** milestones in `in_progress` and both missing a `branch:`, `check pm` printed D9 **and** D10 for **each** — four DRIFT lines naming `0.1.0` and `0.2.0` separately, exit 1. D8 named the one that mismatched |
| 5 | a project that renames every state word gets identical gate behaviour, proven on a vendored fixture | **PASS with V6** | My own sweep: 12 `[pm.states.*]` list lines and **63** grain `status:` lines rewritten to `alfa…kilo`, nothing else touched. All 12 captured commands returned **identical exit codes**; 10 of 12 outputs byte-identical after un-mapping — `check pm`, `check all`, `pm list`, `pm validate`, `pm vocabulary`, `pm vocabulary --json`, `pm ready-for feature` ×2, `pm ready-for milestone`, `pm ready-for tag`. The 2 that differed are `pm status` / `pm status 0.2.0`, in trailing spaces inside `[...]` only (V6). Vendored proof: `tests/fixtures/renamed-vocabulary/` (26 files) + `ARenamedVocabularyGetsTheSameAnswers`, which builds the stock twin by substitution and asserts eight rules fire on the renamed side. Gate scope narrower than the criterion: V5 |
| 6 | the CHANGELOG carries the D2/D5 resolution loss as a behaviour change, naming what a consumer stops seeing | **PASS** | `CHANGELOG.md:352-395`, `### Every question is asked of a category`, opening `**Behaviour change.**` and a `**What a consumer STOPS seeing**` list of eight items: D2/D6 no longer firing over an `in_progress` parent (with the correction that **D5 lost nothing**, since its split *is* the `todo` boundary), D8/D9/D10 over every `in_progress` milestone, `feature done --cascade` removed, `ready-for` asking the `done` category, `pm retire` on `fixed`, the six retired keys, `seam` gone from phases |
| 7 | `pm --help`, `README.md:103` and `cli.py:71`/`:414` state the category question; B1/B2/B3 close | **PASS** | B1: shipped `pm --help` opens *"…or done — never of the word"* and its `ready-for` block reads *"every story in the `done` CATEGORY ([pm.states.story] done — `obe` too…)"*. B2: the README ladder row now reads *"is every sibling story in the `done` CATEGORY — by whichever word your flow puts there?"*. B3: the advisory is **deleted**, with the reason in place at `cli.py:592` (*"No advisory about the features left behind (story 03): a write prints only what it wrote"*) |

## The probes the review contract asks for, run directly

| probe | result |
|---|---|
| a category declared empty (`story.done = []`) | **exit 2** on `check pm`, `pm status`, `pm list`, `pm vocabulary`, `pm ready-for` — `[pm.states] story.done must be a string or a non-empty list of strings, got []` |
| a state in **two** categories | **exit 2**, all five — `[pm.states.story] maps 'done' to both 'in_progress' and 'done' — every state maps to exactly one category` |
| leftover `[pm.transitions.story]`, **undeclared** target | **exit 2**, all five — `[pm.transitions.story] was retired and is refused — there is no step-to-state table: a belt writes the FIRST state of its kind's [pm.states.<kind>] done list…` |
| leftover `[pm.transitions.story]`, **declared** target | **exit 2**, all five — the key is refused, not its value |
| bare `[pm.transitions]` | **exit 2**, all five, naming `[pm.transitions]` |
| leftover `[pm] story_states` | **exit 2**, all five — `…was retired and is refused — the vocabulary is [pm.states.story] … Remove the key.` |
| leftover `[pm] also_done` | **exit 2**, all five, naming the `done` list as the replacement |
| a grain holding a word declared nowhere (`status: wombat`) | `check pm` **exit 1**, `DRIFT story …: status 'wombat' not in (planning ready building done obe)` — a finding, not a config error, which is the right side of rule 9 |
| **a story at `in_progress` under a feature at `todo`** | `check pm` **exit 0**, six `WARN` lines each naming **both grains and both categories** (`is 'building' (in_progress) but its feature … is still 'planning' (todo)`), verdict `PASS … 13 warning(s)`, and **SHA-1 of all 9 touched files unchanged** — the gate moved nothing |
| the census grep, accounted for | `grep -rn "'building'\|'reviewing'\|'done'\|'planning'" src/agentic_sdlc --include='*.py'` → **5 hits**: `ledger.py:651` and `model.py:67` are comments; `model.py:92` is `DONE_CATEGORY = 'done'`, the closed **category** set, not a state; `model.py:183-184` is `LIFECYCLE`, the seed. The AST scan over all 41 modules adds only `model.py:190/196/198/199/200` (`obe`, `open`, `fixed`, `closed` in the seed) and `verdict.py:111` (`OPEN`, the review-disposition homonym, a declared exception). Nothing unaccounted for |

## Rule 4 and rule 9, asked directly

- **Is there an engine opinion surviving under a new name?** Yes, one: `readied` (V3), which is
  `at_or_past` re-expressed as "not the first `todo` word". It is disclosed in the CHANGELOG and
  contradicted by two claims in files this feature owns. Everything else the census named is
  genuinely gone — I checked `DEFAULT_MILESTONE_STATES`/`FEATURE`/`STORY`/`BUG`,
  `STALLED_IF_ALL_STORIES_DONE`, `work_started`, `split_blind_vocabularies`, `is_terminal`,
  `building_milestones`, `TERMINAL_STATE`, `terminal_state`, `_needs_state`, `_phase_key`,
  `cmd_feature_reviewing`, `transition_target`, `PUBLISHED_STEPS_NOTE`, `_published_steps` and
  `REOPENS_COLUMN` by import.
- **Is anything automatic?** Two engine choices remain, both keying on within-category order.
  `driver.py:238` writes `by_category[DONE_CATEGORY][0]` — the FIRST `done` state — and that one
  is declared: it is in the retired-transitions refusal message, in `CHANGELOG.md:9`, and the
  project controls it by ordering its own list. `readied` is the same mechanism undeclared (V3).
  `feature done --cascade` — the census row that moved grains — is **removed**, and the
  replacement is the story belt closing each by name, which is the right side of rule 9.
- **Does a gate print PASS over what it did not measure?** No. Every verdict line I saw carried a
  census (`scanned 2 milestone(s), 16 feature(s), 39 story/ies, 6 bug(s), 57 ref(s)`), the
  UNVERIFIABLE ref is reported as UNVERIFIABLE rather than folded into either answer, and the
  renamed-twin test explicitly asserts each rule fires so two empty transcripts cannot compare
  equal.
- **Read side vs. write side.** The read side is clean. The write side has one hole (V2,
  `pm set status`) and it fails loudly on the next `check pm` rather than silently.

## What was NOT verified

- **`make milestone` and `make matrix` were not run** (out of scope by instruction), so: no
  cross-interpreter matrix, no `check budget`, no `[tests]` case/duration ceilings. Rule 10's
  *"a tier that got slower is a finding"* is unmeasured here — this feature adds an AST walk over
  27 modules to the unit tier and I did not time the delta.
- **I ran 252 tests + 312 subtests, my run** — `tests/test_pm_flow.py`, `test_pm_gate.py`,
  `test_pm_verbs.py`, `test_pm_ready_for.py`, `test_pm_ledger_record.py`, 9.54 s, all green. The
  rest of the suite (`make test`, both tiers) I did not run.
- **The conveyor belts were never driven against a renamed vocabulary.** My sweep covered the
  `pm` verbs and `check pm` only; `agentic-sdlc close story`, `release` and `adopt` read
  `flow_of` through `driver.py:238` and I read that line rather than exercising it. The
  renamed-vocabulary fixture carries no conveyor run either.
- **The ledger was not renamed.** My sweep rewrote `[pm.states.*]` and 63 `status:` lines; the
  `ledger.jsonl` rows kept the seed's words in their `from`/`to` fields. That is D7's declared
  boundary (frozen keys stay), so the identical outputs I measured were produced with the ledger
  still spelling stock words — a reader of historical rows was not under test.
- **No consumer repo was touched** (hard rule 8). The flow-less tree in V1 is this tree with
  `[pm.states.*]` stripped, which is the same *shape* a consumer has on pin-bump day, not a real
  consumer.
- **`0.2.0/the-ledger-rows-carry-categories` (phase 8) was not reviewed.** I confirmed only that
  `('pm.cli', '_tree_snapshot')` is a declared `SEED_WORD_READERS` exception with D7 beside it.
- **Line endings.** I did not test a CRLF grain file through the status verbs; hard rule 3's
  byte-preservation claim is covered by existing cases I read but did not re-run in isolation.
- **`pm status`'s per-milestone path and `pm list --kind milestone --category …`** were exercised
  only in their default forms.
- **This record is not scanned by any gate.** `check doc` does not read `docs/reviews/`
  (confirmed: `check doc` reports `5 doc(s)` and this file is not among them). What *was* proven
  about the block below is `verdict.parse()` on this file: one block, `HOLD`, 9 findings, every
  severity and disposition accepted, no `MalformedVerdict`.
- **The feature file was not touched.**
  `pm/roadmap/0.2.0-the-conveyor/features/every-question-is-asked-of-a-category/feature.md` is
  still `status: reviewing` with an empty `reviewed:`; this record is not yet pointed at from the
  tree.
- **One file in the tree moved that I did not edit.**
  `pm/roadmap/0.2.0-the-conveyor/ledger.jsonl` gained 8 append-only rows — two `gate:check` rows
  from the armed Stop hook (`tools/hooks/cc-stop-gate.sh`) and five `test` rows plus one
  `gate:unit` row from my pytest run, which `tests/conftest.py:239-243` records by design. No
  verb was run against this tree to write them and nothing else in the checkout changed. They are
  the same rows any `make unit` here produces; drop them if the milestone's ledger should carry
  only its own work.

Reviewer's token cost: ~230k.

```
verdict: HOLD
| id | severity | disposition |
| V1 | BLOCKER | open |
| V2 | MAJOR | open |
| V3 | MAJOR | open |
| V4 | MINOR | open |
| V5 | MINOR | open |
| V6 | MINOR | open |
| V7 | QUESTION | open |
| V8 | NIT | open |
| V9 | NIT | open |
```
