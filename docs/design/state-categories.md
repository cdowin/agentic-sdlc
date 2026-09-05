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
in_progress = ["building", "reviewing"]
done        = ["accepted", "packaging", "done", "obe"]
```

Per grain kind, so a bug's vocabulary (`open` / `fixed` / `closed`) is declared the same way
rather than being the special case it is today. **The shipped default maps exactly today's
`LIFECYCLE`**, so a consumer that declares nothing sees no change — rule 5, and the only way this
lands without reddening every tree on the bump.

The engine keeps three opinions and no more:

1. the category set is `todo`, `in_progress`, `done`;
2. they are ordered `todo < in_progress < done`;
3. **every declared state maps to exactly one.** A state mapped to none, or to two, is a
   `ConfigError` at exit 2 — a fact about the input, and refusing facts about the input is the
   one thing this tool is always allowed to do.

Everything else — how many states, what they are called, which category each sits in, what order
they appear in within it — is the project's.

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
