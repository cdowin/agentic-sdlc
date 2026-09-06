---
id: 0.2.0/every-question-is-asked-of-a-category
milestone: "0.2.0"
name: The engine gets two verbs, and every question in the census is routed through them
status: reviewing
reviewed: docs/reviews/2026-09-05-every-question-is-asked-of-a-category.md
phase: 7
depends_on: ["0.2.0/the-project-declares-its-flow", "0.2.0/the-belt-reports-and-finishes"]
consumed_by: ["0.2.0/the-ledger-rows-carry-categories"]
risk: high
size: l
labels: ["pm", "categories", "engine", "behaviour-change"]
---

# The engine gets two verbs, and every question is routed through them

**This is the behavioural half of the seam, and it is where the northstar is actually delivered.**
The previous feature made the project's flow declarable. This one stops the engine asking about
words.

## The two verbs, which do not exist yet — plan audit Q2

`state-categories.md` §6 states the architecture:

```
move(grain, to_state)          is this transition declared? then write it.
holds(grains, category|state)  are they all there? yes or no, and name who is not.
```

> *"Two verbs. Everything a belt does is a sequence of those plus commands the project named."*

`grep -rn "def move(\|def holds(" src/` finds one hit and it is `core/apply.py`'s file mover.
**The architecture the whole milestone rests on has never been built**, and the inference census
names `holds(...)` as the destination for six of its ten rows without a grain that creates it.

Landed without the verbs, this feature is ten call sites that each grow their own
`category_of(status)` lookup and agree by convention to behave alike. **That is a second scoreboard
with ten columns**, and hard rule 4 is why this repo does not accept them. It is not hypothetical:
P9 found `also_done` landed in `ready_for.py:304,334` and NOT in `model.py:1155`, so
`pm ready-for feature` and `check pm` D2 **disagree today** about whether an `obe` story is
finished. One shim, two call sites, already out of step.

**So the verbs are the deliverable and the census is the acceptance test.** Every row below routes
through `move` or `holds`, or the row is not done.

## The census, and where each row lands

| where | what it infers today | becomes |
|---|---|---|
| `model.py:80` `STALLED_IF_ALL_STORIES_DONE` | which states mean a feature has not advanced, by slicing `LIFECYCLE` at `reviewing` | `holds(stories, done)` and parent in `todo` |
| `model.py:1071-1084` `at_or_past(BUILDING)` | ordering, by indexing a tuple of words | category order, the only order there is |
| `model.py:1122` `states_without_building` | names its own blindness in its own name | **deleted** — a category is always placeable |
| `model.py:1155` `done_n` | the bare literal `'done'`; P9's second call site | `holds` |
| `model.py:305` `also_done` shim | ships `obe` as a default value in code | read into `[pm.states.<kind>] done`, then **deleted** |
| `model.py:995` `building_milestones` | one line serving D8, D9 and D10, hardcoded `'building'` | see the ruling below |
| `ledger.py:597` `terminal_state` | which single state ends a grain, special-casing bugs | `holds(grain, done)` |
| `ready_for.py:135` `DONE = LIFECYCLE[-1]` | the last word means finished | `holds` |
| `pm/cli.py` ×12 + `:621, :692, :876` | `model.REVIEWING` and bare `'done'` in the close paths | `holds` |
| `pm/cli.py` `feature done --cascade` (`:506-567`) | which stories to move, and to what | the `feature` belt's steps, declared |
| `execlist.py:44-50` `_phase_key`, `cli.py:874-880` | `seam` — a word the engine knows about a project's PHASE vocabulary | declared, or dropped |
| `model.py:979` `review_slug_fallback` | a review record, from a filename glob | a pointer, or a finding |
| `checks/grain_shape.py:167-186` `_kind_of` | a grain's kind from path shape; L5's `'stories'`/`'bugs'` literals | finish the half-declared convention |
| `steps.py:824` `_status_at_or_past` | **R4** — the same index comparison, without the guard its later twin has | deleted with `at_or_past` |
| conveyor `stories-done` | the word | `holds`, via `ready-for` |

## The five `check pm` D-rules the plan never listed — P4

D2 and D5 were the two everyone named. The others ask by name too:

| rule | asks by name | where |
|---|---|---|
| D3 | `mstat == 'done'` and `view.status != 'done'` | `checks/pm.py:192` |
| D6 | `mstat == model.BUILDING` | `checks/pm.py:224` — its docstring at `:32` admits it |
| D8 D9 D10 | "the building milestone", via `model.py:995` | one line, three rules |

**`ADVANCE_IT` (`checks/pm.py:159`) stays and is struck from the census.** P2's withdrawal is
right: it is in the GATE, and hard rule 9 licenses `check` to name the repair for a contradiction
it has already proved.

### The ruling D8/D9/D10 need — plan audit Q6

Under three categories, `in_progress` may hold several states **and several milestones**, so *"the
milestone currently being worked"* has no expression. The rule-9 answer costs nothing:

> **D8, D9 and D10 report over EVERY milestone whose status is in `in_progress`.** A tree with
> three gets three answers, which is a true statement about that tree. A project that wants exactly
> one narrows it by declaring one; the engine does not guess which.

That is `holds(milestones, in_progress)` doing its job. The alternative — an `active: true`
frontmatter field — is a schema change, and it belongs in `decisions.md` before this feature is
scoped rather than discovered inside it.

## The price, and the CHANGELOG owes it as a behaviour change

**D5 and D2 report strictly LESS.** D5 today compares seven `LIFECYCLE` positions; over categories
it has three. D2 drops from three states to two. A consumer whose D5 currently distinguishes
`accepted` from `packaging` will find that it no longer does.

It is the correct trade — a resolution that exists only while nobody renames a word is a resolution
about to be wrong — but it **is** a trade, and P7 is right that the design sold it as pure gain.
**CHANGELOG as a behaviour change, not as an improvement.**

## The findings that land here rather than earlier

| id | why it waited |
|---|---|
| R4 | `_status_at_or_past` **is** `at_or_past`; the migration deletes the line the finding is against |
| B1 | `cli.py:71` — and `pm --help` — document *"every story at `reviewing`"* for a verb that asks `done`; the predicate becomes a category here (audit Q9: it is user-visible in the shipped help) |
| B2 | `README.md:103`'s ladder row asks the superseded question |
| B3 | `cli.py:414`'s advisory reports a pre-`f7465c2` set |

## Ship criterion

1. **`move(grain, to_state)` and `holds(grains, category|state)` exist as the engine's two verbs**,
   with their own tests, and `move` refuses an undeclared target state at exit 2.
2. **Every row of the census above routes through one of them.** A test enumerates the census and
   asserts no state literal survives outside the config reader — the census is the acceptance
   criterion, not a to-do list.
3. `also_done`, `at_or_past`, `STALLED_IF_ALL_STORIES_DONE` and `states_without_building` are
   **deleted**, and P9's two-call-site disagreement is gone because there is one call site.
4. D2, D3, D5, D6, D8, D9 and D10 all ask `holds`. D8/D9/D10 report per `in_progress` milestone,
   per the ruling above.
5. A project that renames every state word gets **identical** gate behaviour, and a test proves it
   on a fixture tree with a fully renamed vocabulary (hard rule 8: the fixture is vendored here).
6. The CHANGELOG carries the D2/D5 resolution loss as a **behaviour change**, naming what a
   consumer stops seeing.
7. `pm --help`, `README.md:103` and `cli.py:71`/`:414` all state the category question. B1/B2/B3
   close.

## Risks

1. **Criterion 2 is the only thing standing between this and ten private lookups**, and it is the
   criterion a builder under time pressure will satisfy loosely. Enumerating the census in a test
   is what makes it fail honestly.
2. **The renamed-vocabulary fixture is the whole proof of the northstar** and it does not exist
   yet. Without it, "the engine has no opinion" is an assertion.
3. **`feature done --cascade` becoming declared steps is a scope tail.** It is the one census row
   that is not a predicate rewrite — it moves grains — and it belongs to the `feature` belt. If it
   grows, it splits out rather than stretching this feature.
