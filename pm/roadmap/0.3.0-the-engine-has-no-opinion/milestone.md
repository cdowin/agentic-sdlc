---
id: "0.3.0"
name: the engine has no opinion
status: planning
depends_on: []
branch:
---

# 0.3.0 — the engine has no opinion

**It gates the SDLC. It does not run it.** Chris, 2026-09-05: *"It doesn't even stop you from
closing something if it has a feature with open stories. It shouldn't say, no, you can't do that.
It should just say: warning, you're moving to a closed state, and you have open children. That's
it. The machine running this figures out what to do about all of that."*

Two features, and the second is mostly subtraction:

- **`states-are-categories-not-words`** — three categories, states and transitions declared by
  the project, read every run, never assumed.
- **`the-belts-report-they-do-not-refuse`** — a belt moves, warns and finishes. 0.2.0 built
  refusal into the conveyor against a rule already in this repo
  (`pm-execution.md`: *"REPORT, never refuse"*), and named the feature after the thing it got
  wrong.

**One line decides anything added here later:** *is the engine reading what the project declared,
or deciding what the project should do?* The first is its job. The second belongs to the machine
running it.

**Chris, 2026-09-05, reading the SDLC after a day of building the belts:**

> *"This tool, all the grammar and the states, it actually really shouldn't have an opinion about
> those. It shouldn't care at all. It should just provide the engine and the machinery. … When we
> review things for readiness and we say, is this feature ready to close — what it's not looking
> for is all stories in `done`. What it's really looking for is: is everything in the macro
> completed column."*

The design is `docs/design/state-categories.md`, written with the research behind it. This
milestone builds it.

## The engine has two verbs

Chris, 2026-09-05: *"It's just a conveyor belt of moving action to action. It's not inference.
The engine just says: okay, you wanna move something from one state to another? That's fine. You
wanna check if all things are in a particular state? That's fine. **This is just Jira being built
local.**"*

```
move(grain, to_state)          is this transition declared? then write it.
holds(grains, category|state)  are they all there? yes or no, and name who is not.
```

**Seven places currently infer instead** — `STALLED_IF_ALL_STORIES_DONE`, D2's "advance it",
`at_or_past(BUILDING)`, `terminal_state`, `feature done --cascade`, `review_slug_fallback`,
`_kind_of`. None is a bug today; every one is a decision a project cannot see, change, or
un-choose. The census and the reasoning are in `docs/design/state-categories.md` §6.

## Hard rule 5 splits

Its "works with no `devkit.toml`" half was written in `de548ce` — the FIRST CLAUDE.md — beside a
rule reading *"Pure parse, read-only. The only writes ever performed are stdout/stderr."* It was
written for a LINTER, where universal defaults are right and demanding config before linting
would be worse. `pm` did not exist. The conveyor did not exist.

Gates keep it. **The workflow does not**: states and transitions are the project's declaration,
`init` writes them, and a tree without them is refused by name. A default nobody can see is the
engine's opinion wearing the project's clothes.

## The one-sentence version

**`[pm] story_states` is configurable and every question the engine asks about it is asked BY
NAME** — 32 reads of a hardcoded word across `model.py`, `ledger.py`, `ready_for.py` and
`pm/cli.py`. So a project may rename `building` to `in-dev` and D5 silently stops asking. The
config is open; the engine's questions are closed. They swap.

## What 0.2.0 proved, at its own expense

The belt design said *every story at `reviewing`*, so `ready-for feature` asked for `reviewing`.
Chris corrected it to `done`. **Both are wrong the same way**, and the second introduced a defect
the first did not have: a story at `obe` blocks its feature forever, because no single word can
mean "finished by any route".

Jira ships this exact mistake as a documented training problem — `status = Done` returns one
issue where `statusCategory = Done` returns every issue that finished. The answer is not a better
word.

## What 0.2.0 already took

`[pm] also_done` — an optional list of additional words that mean FINISHED, empty by default.
It is the `done` category with its members enumerated by hand, shipped because a story at `obe`
held its feature open forever and that could not wait. **This milestone reads it into
`[pm.states.<kind>] done` and deletes it.**

## Ship criterion

1. **THREE closed categories — `todo`, `in_progress`, `done` — and an OPEN state set**, each
   state mapped to exactly one. A state mapped to none or to two is exit 2. Chris ruled the
   three a hard opinion: work can only fall in those, and the states within them plus their
   mapping are the configurable part.
2. **No engine question is asked by name.** A test greps `src/` for a hardcoded state literal
   outside the config layer and fails on one, the way `test_boundaries.py` already holds the
   import graph.
3. `todo < in_progress < done` is the only ordering, and it is over CATEGORIES. D5 stops
   indexing a tuple of words.
4. **`obe` is a `done` state, not a fourth category.** The first draft of the design proposed
   one, on the argument that a rollup counting abandoned work as delivered lies. The argument is
   right and the conclusion was not: that is an OUTCOME, a different axis from progress, and
   Jira keeps it in a separate `resolution` field for exactly this reason. Azure took the other
   road and then had to make `Removed` items *hidden from backlogs* — a category that also means
   "do not display this" is a display rule wearing a state's clothes.
5. The shipped default maps exactly 0.2.0's `LIFECYCLE`, so a consumer declaring nothing sees no
   behaviour change — rule 5, and the only way this lands without reddening every tree.
6. `pm ledger report`'s dwell columns are per CATEGORY, so a twelve-state project gets three
   columns rather than twelve.
7. A grain kind's vocabulary is declared the same way as any other — bugs stop being the special
   case they are today.

## Risks

1. **A schema change to `devkit.toml` on a tree that already declares `story_states`.** The flat
   tuple has to keep working, read as a shim, or every consumer edits config on the bump — and
   this package has exactly one release of experience with a deprecation window.
2. **The category set is closed, which is the point and also the constraint.** Jira ships three,
   Azure five, Linear five. A FOURTH here needs a question the three cannot answer, in writing,
   before it is added — and "how much did we deliver" is not that question, because it is an
   outcome field.
3. **Ordering within a category is presentation and must stay that way.** The moment a gate cares
   whether `packaging` precedes `done`, the words are load-bearing again and this milestone has
   been undone quietly.
