---
id: 0.2.0/the-project-declares-its-flow
milestone: "0.2.0"
name: The states, the transitions and the flow are in the project's config, written by init and read every run
status: planning
reviewed: docs/reviews/2026-09-05-the-project-declares-its-flow.md
phase: 6
depends_on: ["0.2.0/adopt-is-a-conveyor"]
consumed_by: ["0.2.0/every-question-is-asked-of-a-category"]
risk: high
size: l
labels: ["pm", "config", "categories", "transitions", "init", "additive"]
---

# The states, the transitions and the flow are in the project's config

**Cut by the plan audit (Q4) out of four features that could not individually close.**
`states-are-categories-not-words` (the config half), `the-transitions-table-is-published-vocabulary`
and `init-can-append-to-a-config-it-did-not-write` were one config schema wearing three feature
records: the same block, written by the same seed, materialised by the same `init`, appended by the
same append path, read by the same reader, refused by the same two refusals. Four features that
cannot individually close is the shape that parked 26 stories at `reviewing`.

**This feature is ADDITIVE and that is the point of the seam.** After it, a project can read its
own flow out of its own config for the first time, `init` can put it there, `adopt` names it at a
pin bump, and the engine refuses a malformed declaration. **No question the engine asks changes
yet.** The tree is green, the suite is green, and a consumer who reads the CHANGELOG finds a new
config section and no behaviour change. Every behaviour change is the next feature.

## The declaration

```toml
[pm.states.story]
todo        = ["planning", "ready"]
in_progress = ["building", "reviewing", "accepted", "packaging"]
done        = ["done", "obe"]

[pm.transitions.story]
story-building = "building"
story-done     = "done"
```

Three roles, and keeping them apart is the design (`docs/design/state-categories.md` §4):

| | where | what it is |
|---|---|---|
| **the seed** | code | the shipped default table, versioned with the engine |
| **the declaration** | the project's `devkit.toml`, written by `init` | what THIS project's flow is |
| **the reader** | every run | reads the declaration. **It does not fall back.** |

**No fallback, and hard rule 5 has already been split to license it.** A default nobody can see is
the engine's opinion wearing the project's clothes: if the table is invisible when absent, a project
never learns it can change it and the shipped words persist forever inside a default argument.

### The seed reproduces today's `LIFECYCLE` exactly

So a project that accepts what `init` writes gets 0.2.0's behaviour. That is a SEED that gets
WRITTEN, not a fallback that gets assumed, and the difference is the whole feature.

## P1's blocker, which is why the append path is in here rather than beside it

`init.py:158-193` **never overwrites an existing `devkit.toml`**, and `--force` is documented as
never touching it (`init.py:30-32`) — correctly; it is the project's file. `installables/project-devkit.toml`
has **zero uncommented lines**: the seed `init` writes today is entirely commentary.

So no-fallback, as the design states it, is unshippable without two things this feature owns:

1. **`init` materialises a LIVE section**, which changes the seed's commenting convention.
2. **`init` can APPEND a missing section to an existing `devkit.toml`** — the shape
   `_write_gitignore` already has at `init.py:207-247`: appends what is missing, rewrites nothing,
   idempotent on a second run, and refuses whole rather than editing partially (hard rule 3).

Without (2), every existing consumer is refused by a runtime that will not fall back, by a verb
that will not write the section, with nothing in between.

## The step registry is this package's published vocabulary — say it

P6's ruling, and it must be written down rather than implied. `[pm.transitions.<kind>]` has a
**key set the project cannot change**: the keys are the engine's step names, shipped in `steps.py`.
A project cannot invent a step. Presented as pure project declaration, that is the engine's opinion
with a config file in front of it.

Presented honestly it is the Jira shape the design argues for: **the step registry is this package's
published API surface, versioned like the CLI, read at a pin bump through `pm vocabulary`.** The
project declares its flow over a vocabulary the engine publishes. Selecting and ordering from a
closed menu — which `steps.py:73-92` already lets a project do via `[release] steps = [...]` — is
declaring your flow. Naming a step is not deciding what a move means.

**And it must ASK BY CATEGORY, WRITE BY NAME.** A category holds several states, so writing by
category would make the engine guess a member — strictly worse than what is there now.

## `pm vocabulary` is the pin-bump verb and it currently lies

`cli.py:1061-1062`: *"There are no TRANSITIONS to print."* Falsified by this feature. It is how a
consumer discovers a new section at a bump, so P6 makes it load-bearing rather than cosmetic.

## `config-updated` is how an existing consumer survives the bump — and A1 must land first

`adopt`'s `config-updated` is the one place a version's declared surface is compared against what
the tree declares. A new step with no transition must be a **named finding there, with the seed
value to paste**, not a crash three steps into a release.

A1 says the step asks `_config_readers()`'s **six** and reports over a hand-written list of **ten**,
so four sections it names are never asked. **Fix A1 first, in phase 4, by deriving the census from
`_config_readers()`** — then this feature's two new sections get named for free by adding two
readers. Fixed the other way round, it is the double-touch.

## Scope

| thing | action |
|---|---|
| `[pm.states.<kind>]`, `[pm.transitions.<kind>]` | the schema, per grain kind — so a bug's `open`/`fixed`/`closed` stops being a special case |
| the reader | reads the declaration every run. **No fallback.** |
| the two refusals | a state in no category or in two; a transition naming an undeclared state. **Exit 2, always** — reading a malformed declaration, which is the one thing this tool is always allowed to do |
| `installables/project-devkit.toml` | materialises a live section; its commenting convention changes |
| `init` | writes it fresh, and **appends it into a config it did not write** |
| `pm vocabulary` | prints states, categories and transitions; `--json` too |
| `adopt`'s `config-updated` | names the two new sections, on the census A1 derived |
| **every question the engine asks** | **unchanged.** That is the next feature. |

## Ship criterion

1. A fresh `agentic-sdlc pm init` writes `[pm.states.<kind>]` and `[pm.transitions.<kind>]` as
   **live TOML**, and the values reproduce 0.2.0's `LIFECYCLE` byte-for-byte.
2. `init` run against an existing `devkit.toml` **appends only the missing sections**, preserves
   every other byte including line endings, and is a no-op the second time.
3. A state mapped to no category, or to two, and a transition naming an undeclared state, each
   **exit 2** with the offending key named.
4. A tree with no `[pm.states]` is **refused by name, and the refusal prints the command that
   fixes it** — not the seed to hand-paste.
5. `pm vocabulary` prints the categories, the project's states in each, and the transitions;
   `cli.py:1061`'s *"there are no transitions to print"* is gone.
6. `config-updated` names both new sections, and its census number is the number it asked —
   **A1 closed, in phase 4, before this feature starts.**
7. **A test asserts no engine question changed.** The whole suite passes unmodified except for the
   new config's own tests. If a golden file moves, the seam is in the wrong place.

## Risks

1. **The seed's commenting convention change is a bigger blast radius than it looks.** Every
   consumer's next `init` writes live TOML where it wrote comments. Ships with the CHANGELOG entry
   naming it, not as an implementation detail.
2. **The append path is a write into the project's own file**, which is the thing `init` has always
   refused to do. Hard rule 3 is the whole of the mitigation: whole or nothing, idempotent, no
   adjacent reformatting — and `_write_gitignore` is the proven shape rather than a new one.
3. **Criterion 7 is the seam's only proof, and it is the one that will be argued away** under
   pressure to "just fix D2 while we're in here". A behaviour change that lands in this feature
   makes the additive seam a fiction and the next feature unreviewable.
