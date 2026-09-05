# The engine should have no opinion about the words

**Written 2026-09-05, from Chris's reading of the SDLC, after a day of building the belts and
getting the state question wrong twice in one session.**

> *"This tool, all the grammar and the states, it actually really shouldn't have an opinion about
> those. It shouldn't care at all. It should just provide the engine and the machinery. And all
> the states should be configurable. … When we review things for readiness and we say, is this
> feature ready to close — what it's not looking for is all stories in `done`. What it's really
> looking for is: is everything in the macro completed column."*

That is correct, and this document is the case for it plus a design. **It is not scheduled for
0.2.0** — the reasoning and the two-line correction 0.2.0 does take are at the end.

---

## 1. The tool currently has an opinion, in thirty-two places

`grep` over `src/agentic_sdlc`, 2026-09-05: **32 reads** of a hardcoded state word, plus bare
`'done'` string literals in `pm/cli.py`. The load-bearing ones:

| where | what it hardcodes |
|---|---|
| `model.py:75-76` | `BUILDING = 'building'`, `REVIEWING = 'reviewing'` |
| `model.py:80` | `STALLED_IF_ALL_STORIES_DONE = LIFECYCLE[:LIFECYCLE.index(REVIEWING)]` |
| `model.py:1030-1042` | *"Is `status` at or past `BUILDING`"* — D5's whole question |
| `ledger.py:589` | `TERMINAL_STATE = 'done'` |
| `ready_for.py:135` | `DONE = model.LIFECYCLE[-1]` |
| `pm/cli.py` ×12 | `model.REVIEWING` and `'done'` in the feature/story close paths |

`[pm] story_states` is configurable — a project may declare any tuple of words. But **every
question the engine asks about those words is asked by NAME**, so a project that renames
`building` to `in-dev` gets a `[pm] checks` D5 that cannot place it and silently stops asking.
`model.py:1080` even has a function for that case, `states D5 cannot place BUILDING in` — the
config is open and the engine's questions are closed, and the code already knows it.

## 2. Today proved it, twice, in one session

**Both of these were mine, hours apart, and both are the same mistake.**

The belt design said *story → feature: every story at `reviewing`*, so `pm ready-for feature`
asked for `reviewing`. Chris corrected it: a story's work is done when it is done — capture it,
say `done`. I changed the predicate to `done`.

**Both are wrong in the identical way.** The question is not "is every story at the word
`reviewing`" and it is not "at the word `done`". It is *"is every story finished"* — and neither
spelling can answer that for a project whose vocabulary is not this one's.

And the `done` version introduced a defect the `reviewing` version did not have: **a story that
was abandoned blocks its feature forever.** `obe`, `wontfix`, `duplicate`, `cancelled` — a story
in any of those is finished, is never going to be `done`, and under today's predicate holds its
parent open permanently. There is no spelling of a single word that fixes that.

## 3. What mature trackers do, and they converge

### Jira — three categories, and the trap is documented

Jira has **hardcoded status *categories*** — `To Do`, `In Progress`, `Done` — and an **unlimited,
user-defined set of statuses**, each mapped to exactly one category. Boards, filters and
automation key off the category. ([Atlassian Community](https://community.atlassian.com/forums/Jira-articles/Jira-Image-of-the-Day-Status-Categories/ba-p/2646552),
[HeroCoders](https://www.herocoders.com/blog/understanding-jira-issue-statuses))

The detail worth the whole document is that **Jira ships the mistake I made as a documented
training problem**:

> *"if the query is `Status = Done`, only one issue is returned even though there are more issues
> that have reached the end of their lifecycle, whereas `statusCategory = Done` returns all
> issues in the green Done status."*
> — [OBSS](https://apps.obss.tech/blog/jira-statuses-categories-custom-workflows)

`status = Done` is `ready-for feature` as I shipped it this morning. Millions of Jira users hit
that, and Atlassian's answer is not "pick a better word" — it is *ask the category*.

### Azure DevOps — four categories, plus Removed

Azure maps every state to `Proposed`, `In Progress`, `Resolved`, `Completed` — **plus `Removed`,
which is separate, and work items in it are hidden from backlogs and boards entirely.**
([Microsoft Learn](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/workflow-and-state-categories?view=azure-devops))

### Linear — five status types

`Backlog`, `Planned`, `Started`, `Completed`, `Canceled`.
([Linear](https://linear.app/changelog/2024-03-19-custom-statuses-for-projects))

### What they agree on, and where they split

1. **The category set is CLOSED and small; the state set is OPEN.** The engine reasons over a
   handful of categories it defines. The project names as many states as it likes and maps each
   to one.
2. **"We did it" and "we stopped doing it" are tracked apart** — but they disagree about WHERE.
   Jira keeps three categories and puts the distinction in a separate `resolution` field; Azure
   and Linear add a category (`Removed`, `Canceled`). §4 takes Jira's side, and says why.

## 4. The design

### Three categories, and they are a HARD opinion

**Chris, 2026-09-05, on reading the first draft of this document, which proposed four:**

> *"The macro states — the to do, the in progress, and the done — I think those are… I'll call
> them hard opinions. Your work can only fall within those three categories. We could invent
> more, but I don't think we should. However, it's the states within the categories, and their
> mapping, that is configurable."*

```
todo         not started
in_progress  started, not finished
done         finished
```

**That is the whole closed set, and it does not grow.** An `n`-category engine is an engine with
no opinion at all, and then every consumer invents its own lattice and nothing generalises —
which is the failure mode `[gates] extra` was designed against one layer down.

### The fourth category this document proposed, and why it was wrong

The first draft had a `dropped` category for `obe` / `wontfix` / `duplicate` / `cancelled`, on
the argument that a rollup counting them as delivered reports a milestone fully shipped when a
third of it was abandoned.

**The argument is right and the conclusion was wrong: that is a DIFFERENT AXIS.** Progress is
`todo → in_progress → done`. Whether the work shipped or was abandoned is an **outcome**, and
folding an outcome into a progress enum gives one field two meanings.

Jira, which has the most mileage on this, does exactly the split: **`Won't Do` is in the `Done`
CATEGORY**, and delivered-vs-not lives in a separate `resolution` field. Azure and Linear went
the other way — `Removed`, `Canceled` — and the tell that it cost them is what Azure then had to
add: work items in `Removed` are **hidden from backlogs and boards**
([Microsoft Learn](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/workflow-and-state-categories?view=azure-devops)).
A category that also means *"do not display this"* is a display rule wearing a state's clothes,
and it is what a conflated axis looks like from the outside.

So: **`obe` is a `done` state.** A feature whose stories are `done`, `done` and `obe` is
unblocked, because all three are finished. If a project later needs "how much did we deliver",
that is an outcome field and a separate design — **not a fourth category, and not in 0.3.0
unless somebody asks for it with a question the three cannot answer.**

### The config

```toml
[pm.states.story]
todo        = ["planning", "ready"]
in_progress = ["building", "reviewing", "accepted", "packaging"]
done        = ["done", "obe"]
```

**`accepted` and `packaging` are `in_progress`.** Chris, 2026-09-05, on the first draft, which
had them in `done`: *"work isn't done if it's being packaged."* Obvious once said, and the draft
had it wrong in the direction that costs something — `features-done` would have been satisfied by
a feature still being packaged, which is the belt above starting while the belt below is still
running. The rule that catches it: **a category is about whether WORK REMAINS, not about whether
the outcome is decided.** An accepted feature has had its verdict; it still has work.

Per grain kind, so a bug's vocabulary (`open` / `fixed` / `closed`) is declared the same way
rather than being the special case it is today. **The seed reproduces today's `LIFECYCLE`
exactly**, so a project that accepts what `init` writes gets 0.2.0's behaviour — but it is a SEED
that gets WRITTEN, not a fallback that gets assumed. See below; this paragraph said the opposite
until the 0.3.0 plan review caught it contradicting its own §4.

The engine keeps three opinions and no more:

1. the category set is `todo`, `in_progress`, `done`;
2. they are ordered `todo < in_progress < done`;
3. **every declared state maps to exactly one.** A state mapped to none, or to two, is a
   `ConfigError` at exit 2 — a fact about the input, and refusing facts about the input is the
   one thing this tool is always allowed to do.

Everything else — how many states, what they are called, which category each sits in, what order
they appear in within it — is the project's.

### The table is WRITTEN by `init` and READ every run — never assumed

**Chris, 2026-09-05:**

> *"The transitions table should come from code. That's the config that I'm talking about. So
> when you init a project, it writes a config. That is the transition table, and that is what
> should be read into code every single time. It should never assume."*

Three roles, and keeping them apart is the design:

| | where | what it is |
|---|---|---|
| **the seed** | code | the shipped default table — one source, versioned with the engine |
| **the declaration** | the project's `devkit.toml`, written by `init` | what THIS project's states and transitions are |
| **the reader** | every run | reads the declaration. **It does not fall back.** |

**A runtime fallback is the engine keeping its opinion with extra steps.** If the table is
invisible when absent, a project never learns it can change it, the shipped words persist by
default forever, and the one thing this milestone exists to remove survives inside a
default-argument.

So `init` MATERIALIZES the seed into the project's config, where it is visible, diffable and
editable, and the runtime reads what is there.

#### Hard rule 5 is not an exception to make — it is a rule to split

**Chris, 2026-09-05:** *"We can update that hard rule five. What was hard rule five trying to
guard against? I'm actually not sure."*

Neither was I, so I went and found it. `git log -S` on the clause: it lands in **`de548ce`, the
FIRST CLAUDE.md this package ever had**, and the rule beside it at the time reads:

> *"**Pure parse, read-only.** No tool boots Godot, writes into the consuming repo, or depends on
> `.godot/` cache state. **The only writes ever performed are stdout/stderr.**"*

That is what rule 5 was written for: **a linter you point at a repo.** In that package, "works
with no config" was not a principle, it was a *property* — the defaults were things like *scan
`tools/`* and *cap prose at N lines*, universal enough to be right anywhere, and a tool that
demanded configuration before it would lint anything would be a worse linter.

**The rule has two halves and only one of them was ever reasoned about:**

| half | what it guards | verdict |
|---|---|---|
| *"per-project variation goes in a config section — never edit the tool"* | **forked tools.** Two consumers each carrying a patched copy that drifts. | **Keep. This is the whole rule.** |
| *"a repo with NO `devkit.toml` behaves byte-identically to one declaring the defaults"* | nothing, once there is a declared workflow. It is a linter-era convenience. | **Scope it to the gates.** |

`pm` did not exist when that sentence was written. The conveyor did not exist this morning. The
second half is a property of gates with universal defaults being applied, unexamined, to a state
machine that has no universal default — because **the states are the project's, and that is the
entire point.**

So rule 5 becomes:

> **5. Config over forks.** Per-project variation goes in the consumer's `devkit.toml` section —
> never "edit the tool". **A GATE works with stock defaults and a repo with no `devkit.toml`
> runs every gate byte-identically to one declaring them.** The WORKFLOW does not: states and
> transitions are the project's declaration of how it works, `init` writes them, and a tree
> without them is refused by name. A default nobody can see is the engine's opinion wearing the
> project's clothes.

Not an exception bolted onto a rule — the rule saying which of the two things it is talking
about, which it never had to before.

#### And a pin bump is where this gets tested

A release that adds a conveyor step adds a transition the consumer's config — written at THEIR
init, at an older version — does not have. **`adopt`'s `config-updated` step owns that**, and it
is the reason that step exists: it is the one place a version's declared surface is compared
against what the tree declares. A new step with no transition must be a named finding there, with
the seed value to paste, and not a crash three steps into a release.

### Ordering falls out, and it is only over categories

D5's *"is the parent behind its children"* needs a partial order, and `todo < in_progress < done`
is the whole of it — **over categories, never over words**. Order *within* a category is
presentation: whether `packaging` precedes `done` is a project's business and no gate's.

That deletes `model.py:1030`'s `states.index(status) >= states.index(BUILDING)`, which is the
line that breaks the moment a project renames a word.

### What each caller becomes

| today | becomes |
|---|---|
| `pm ready-for feature` — every story `== 'done'` | every story in category `done` |
| — | a story at `packaging` now BLOCKS, because packaging is work |
| `check pm` D2 — `STALLED_IF_ALL_STORIES_DONE` | children all `done`, parent still `todo` |
| `check pm` D5 — `at_or_past(BUILDING)` | child's category > parent's category |
| `ledger.TERMINAL_STATE = 'done'` | the grain kind's `done` category |
| `pm ledger report` dwell columns — one per state | one per **category**, so a twelve-state project gets three columns and not twelve |
| conveyor `stories-done` | category `done`, via `ready-for` |

## 5. What this costs, and why it is not 0.2.0

Thirty-two call sites, `pm vocabulary`'s output shape, the ledger's dwell columns and their golden
tables, `check pm`'s D2/D5 predicates, the conveyor's `stories-done`, and a `devkit.toml` schema
change with a compatibility shim for the flat `story_states` tuple. **That is a milestone.**

0.2.0 is at 24 commits with a green suite and a landed release review. Reopening `model.py`'s
state machinery now would invalidate that review and every feature record under it, to ship a
half-migration.

**0.3.0 takes it**, and the design above is the spec.

### The two lines 0.2.0 does take

A story at `obe` blocking its feature forever is a live defect I introduced today, and the fix is
one optional key rather than a schema change:

```toml
[pm]
also_done = ["obe"]     # default: () — more words that mean FINISHED
```

`pm ready-for feature` and the conveyor's `stories-done` ask **"is this state the last one, or
one of `also_done`"** instead of asking for the bare word `done`.

**It is the `done` CATEGORY with one member enumerated by hand.** Not a fourth category, not an
outcome field, and not a design — a list of additional words that mean finished, which is exactly
what 0.3.0's `[pm.states.<kind>] done = [...]` will hold. When that lands, this key is read into
it and deleted.

A project declaring nothing behaves precisely as it does today. A project that abandons a story
stops being blocked by it forever.

**Deliberately NOT in 0.2.0:** the category-keyed rollup, the dwell-column narrowing, D5's
reordering, and `pm vocabulary`'s new shape. Each is a behaviour change a consumer would have to
read about, and shipping them inside a release whose review has already closed would be exactly
the ordering error this milestone made structural.

---

## 6. The engine has two verbs, and everything else is declaration

**Chris, 2026-09-05:**

> *"It's just a conveyor belt of moving action to action. It's not inference. And I think a lot
> of inference is getting put in the middle here between all this. The engine just says: okay,
> you wanna move something from one state to another? That's fine. You wanna check if all things
> are in a particular state? That's fine. This is just Jira being built local."*

That is the whole architecture, and it is smaller than what is currently here.

```
move(grain, to_state)          is this transition declared? then write it.
holds(grains, category|state)  are they all there? yes or no, and name who is not.
```

Two verbs. Everything a belt does is a sequence of those plus commands the project named.
**Anything else the engine does is inference, and inference is the thing to remove** — not
because it is wrong today, but because it is the engine having an opinion that a project cannot
see, cannot change, and did not choose.

### The inference census, measured 2026-09-05

| where | what it infers | becomes |
|---|---|---|
| `model.py:80` `STALLED_IF_ALL_STORIES_DONE` | *which states mean a feature has not advanced* — derived by slicing the LIFECYCLE tuple at `reviewing` | `holds(feature, todo)` |
| ~~D2's "advance it"~~ | **WITHDRAWN.** `ADVANCE_IT` is `checks/pm.py:159` — in the **gate**, not the engine. Rule 9 licenses that exactly: `check` is the thing that fails a contradictory tree and says what would fix it. I attributed a gate's job to the engine. | nothing; never a violation |
| `pm/cli.py:1524-1557` the ledger dispatch snapshot | *which states count as open work* — keys frozen, matched against the literals `building`/`reviewing`. Its own docstring: *"a project with a genuinely renamed vocabulary records empty lists."* | category buckets — **and this is a DATA MIGRATION**, not a rendering change: those keys are already inside JSONL rows in every consumer tree |
| `execlist.py:44-50` `_phase_key` | `seam` — a word the engine knows about a project's phase vocabulary | declared, or dropped |
| `model.py:1071-1084` `at_or_past(BUILDING)` | *ordering, by indexing a tuple of words* | category order, the only order there is |
| `ledger.py:597` `terminal_state(cfg, kind)` | *which single state ends a grain* — and it special-cases bugs | `holds(grain, done)` |
| `pm/cli.py` `feature done --cascade` | *which stories to move, and to what* — the engine picking grains to write | the `feature` belt's steps, declared |
| `model.py:979` `review_slug_fallback` | *a review record, from a filename glob* | a pointer, or a finding |
| `checks/grain_shape.py:167` `_kind_of` | *a grain's kind, from path shape* | already half-declared; finish it |
| `model.py:1122` `states_without_building` | already NAMES the problem in its own name — "the state sets D5 cannot place BUILDING in" | deleted; a category is always placeable |

Nine, after the plan review withdrew one and found three more. None is a bug today. Every one is a place where a project that wanted to work differently
would find the engine had already decided.

### The price, which the first draft did not name

**D5 and D2 report strictly LESS.** D5 today has seven positions to compare (the LIFECYCLE
index); over categories it has three. D2 drops from three to two. The plan review found this, and
it is right that the design was selling a pure gain.

It is the correct trade — a resolution that exists only while nobody renames a word is a
resolution about to be wrong — but it IS a trade, and a consumer whose D5 currently distinguishes
`accepted` from `packaging` will find that it no longer does. **CHANGELOG as a behaviour change,
not as an improvement.**

### What this buys, and it is the durability argument

**You can add a state without the engine changing.** Declare it, put it in a category, wire its
transitions — the engine does not need to know it exists, because the engine never asks *which
word*, only *which category* and *is this move declared*.

That is the property Jira has and the reason its workflow engine outlived every opinion anyone
built on top of it: **the engine is a graph walker over a declaration, and the declaration is the
customer's.** A team adds `Blocked`, maps it to In Progress, wires it in and out — Atlassian
ships nothing.

### The line this does NOT cross

The engine still refuses facts about the input, and that is not inference:

- a state mapped to no category, or two;
- a transition naming a state that is not declared;
- a `move` the table does not permit;
- a config value that is not the shape the key requires.

**Refusing a malformed declaration is the engine reading, not deciding.** The distinction is
whether the engine is answering a question about what the project SAID, or about what the
project SHOULD DO. The first is its job. The second is the thing to keep taking out.

---

## 7. It GATES the SDLC. It does not run it.

**Chris, 2026-09-05, and this is the largest correction in the document:**

> *"This is a thing that just gates the SDLC. It's a thing that gives codification to a thing
> with inference. It doesn't say why something was moved to done. And hell, it doesn't even stop
> you from closing something if it has, say, a feature with open stories. It shouldn't say, no,
> you can't do that. It should just say: warning, you're moving to a closed state, and you have
> open children. That's it. The machine running this figures out what to do about all of that."*

### 0.2.0 built refusal where the package's own rule said report

`.claude/rules/pm-execution.md`, shipped **before** any of today's work:

> *"**`pm feature reviewing` and `pm milestone done` REPORT, never refuse.** Stories not at
> `reviewing`, features not done — the verb names them and does what it was asked. What the tree
> is then left holding is D3/D5's question, asked of the tree."*

The PM CLI has always worked this way. **The conveyor I built today refuses**, and the feature is
literally called `the-release-is-a-conveyor` with the summary *"a resumable step machine that
refuses to advance"*. I built the opposite of the rule sitting in the repo, and named it after
the thing it got wrong.

### The rule, and it has exactly one edge

| about | answer | why |
|---|---|---|
| **the INPUT** — a malformed id, an undeclared state, a transition not in the table, a config value of the wrong shape | **REFUSE**, exit 2 | reading, not deciding. The declaration is malformed and there is nothing to do with it. |
| **the TREE** — open children, no review record, a dirty worktree, a red gate | **REPORT**, and proceed | the engine cannot know whether that is wrong. Descoped? A hotfix? Deliberate? **The caller knows and the engine does not.** |

```
$ agentic-sdlc close feature 0.2.0/alpha
[feature:stories-done] WARNING — 3 story/ies not in `done`: s1 is building, s2 is
                       reviewing, s3 is planning
[feature] feature 0.2.0/alpha: reviewing -> done  (1 warning)
```

It moved. It said why you might not want it to. **You decide.**

### Why refusing is worse, and it is not a philosophical point

- **A tool that refuses gets worked around.** The workaround is invisible, and then the protocol
  teaches nothing. This package already knows that — it is the entire argument for
  `--skip <step> --reason` writing a ledger row, which is the refusal admitting it should not
  have been one.
- **The engine cannot hold the reason.** *Why* a feature closed with an open story is a fact
  about intent. The engine has no access to it, and a machine that blocks on a question it
  cannot ask is asserting an answer.
- **The gate already exists, and it is a different tool.** `check pm` is the thing that FAILS a
  tree whose statuses contradict each other. It runs in CI, it runs pre-push, and it has an exit
  code contract for exactly this. **`pm` moves and reports; `check pm` gates.** I conflated
  them, and the conveyor inherited a job it should never have had.

### What this deletes from 0.2.0

- `close story` / `close feature` / `release` / `adopt` **stop blocking.** They walk, they move,
  they warn, they finish. The step list keeps its whole value — the ORDER is the thing nobody
  could remember, and that is what 0.24.0's release actually got wrong.
- `pm ready-for` becomes a **read verb** whose exit code is information for a caller that wants
  it, not a wall. It already names its blockers; naming them was always the useful half.
- **The 0.24.0 lesson survives.** That release ran its gate before its review because nobody
  knew the order, not because a machine let them. An ordered list with a loud warning at
  `review-landed` fixes the thing that actually broke.
- `--skip <step> --reason` **can go**, or shrinks to a note. It exists to escape a refusal, and
  with nothing to escape it is ceremony. The ledger row it wrote was the honest part; keep that
  as what a warning records.

### The one-line test for anything added to this engine later

**Is this the engine reading what the project declared, or deciding what the project should do?**
The first is its job. The second belongs to the machine running it — which, for this package's
consumers, is an agent with a dispatch, a reviewer, and a human who can be asked.

