---
id: 0.3.0/states-are-categories-not-words
milestone: "0.3.0"
name: Every question the engine asks is asked of a category
status: planning
reviewed:
phase: 1
depends_on: []
consumed_by: []
risk: high
size: l
labels: ["pm", "config", "categories", "conveyor"]
---

# Every question the engine asks is asked of a category

The design is `docs/design/state-categories.md`. **This file is the ENCODING** — the config
shape, and the exact rule for how the conveyor consumes it.

## The three, and they do not grow

```
todo         not started
in_progress  started, not finished
done         finished
```

Chris ruled these a hard opinion. `obe` is a `done` state, not a fourth category — whether work
shipped or was abandoned is an OUTCOME, a different axis, and Jira keeps it in a separate
`resolution` field for exactly this reason.

## ASK BY CATEGORY, WRITE BY NAME

**This is the whole encoding, and it is one sentence because getting it wrong is the failure.**

A conveyor step does two different things with a status and they need two different answers:

- **Asking** — *"is every story finished?"* — is a CATEGORY question. It must be, or the engine
  has an opinion about a word and a project that renames one loses the gate silently.
- **Writing** — *"move this feature to review"* — is a NAME question. A category holds several
  states; `in_progress` here is `building` AND `reviewing`, and "start the review" means exactly
  one of them. **Only the project knows which.**

An engine that asked by name has 0.2.0's bug. An engine that WROTE by category would have to
guess which member, which is worse: it would pick one and be quietly wrong on every tree whose
vocabulary is richer than two words.

## The config

```toml
[pm.states.feature]
todo        = ["planning", "ready"]
in_progress = ["building", "reviewing", "accepted", "packaging"]
done        = ["done", "obe"]

[pm.transitions.feature]
# Which state each conveyor step WRITES. Asking is by category; writing is by
# name, because only this project knows which of its in_progress words means
# "the review has started".
feature-reviewing = "reviewing"
feature-done      = "done"
```

`accepted` and `packaging` are **`in_progress`**: work is not done while it is being packaged.
The first draft had them in `done`, which would have satisfied `features-done` on a feature still
being packaged — the belt above starting while the belt below runs. The rule that catches it: a
category is about whether WORK REMAINS, not about whether the outcome is decided.

**The table is WRITTEN by `init` and READ every run. It is never assumed.** Code holds the SEED;
`init` materializes it into the project's `devkit.toml`; the runtime reads what is there and does
not fall back. A runtime fallback is the engine keeping its opinion with extra steps — the words
stay invisible, so nobody learns they can change them. This is a documented exception to hard
rule 5 and the only one; `docs/design/state-categories.md` argues it, and the refusal when the
section is absent must print the seed to paste rather than just naming what is missing.

## How each conveyor step is encoded

| belt | step | kind | asks / writes |
|---|---|---|---|
| story | `claimed` | AUTOMATIC | **writes** `[pm.transitions.story] claimed` |
| | `narrow-verified` | GATE | — |
| | `committed` | JUDGEMENT | — |
| | `evidence-written` | JUDGEMENT | — |
| | `story-done` | AUTOMATIC | **writes** `[pm.transitions.story] story-done`; verifies category `done` |
| feature | `stories-done` | JUDGEMENT | **asks** every story ∈ `done` |
| | `feature-reviewing` | AUTOMATIC | **writes** `[pm.transitions.feature] feature-reviewing` |
| | `feature-verified` | GATE | — |
| | `review-recorded` | JUDGEMENT | — |
| | `findings-landed` | JUDGEMENT | — |
| | `feature-done` | AUTOMATIC | **writes** `feature-done`; verifies category `done` |
| release | `features-done` | JUDGEMENT | **asks** every feature ∈ `done`, each with a record |
| | `milestone-reviewing` | AUTOMATIC | **writes** `[pm.transitions.milestone] milestone-reviewing` |
| | `milestone-accepted` | AUTOMATIC | **writes** `milestone-accepted` |
| | `milestone-packaging` | AUTOMATIC | **writes** `milestone-packaging` |
| | `milestone-done` | AUTOMATIC | **writes** `milestone-done`; verifies category `done` |

**Every AUTOMATIC status step gets the same two-part shape**: write the name the project declared,
then re-ask the CATEGORY. That is `do()`-never-decides-its-own-outcome, already the driver's rule,
now with the category as the postcondition — so a project whose `feature-done` transition points
at a state it did not put in `done` gets a step that writes and then refuses, naming both.

## What the gates become

| today | becomes |
|---|---|
| `ready-for feature` — every story `== 'done'` | every story ∈ category `done` |
| `check pm` D2 — `STALLED_IF_ALL_STORIES_DONE` | children all `done`, parent still `todo` |
| `check pm` D5 — `at_or_past(BUILDING)` | child's category > parent's category |
| `ledger.TERMINAL_STATE = 'done'` | the grain kind's `done` category |
| `pm ledger report` dwell columns | one per CATEGORY — three, not twelve |

## Ship criterion

1. Three categories, closed. Every declared state maps to exactly one; none or two is exit 2.
2. **No engine question is asked by name.** A test greps `src/` for a state literal outside the
   config layer and fails on one, the way `test_boundaries.py` holds the import graph.
3. **Every transition a conveyor step writes lands in the category that step's postcondition
   asks for**, and `verify --check`-style validation says so before a run starts rather than
   mid-walk.
4. `todo < in_progress < done` is the only ordering, and it is over categories. D5 stops
   indexing a tuple of words.
5. **`init` writes the states and the transitions into `devkit.toml`**, and the runtime reads
   them every run with no fallback. A tree missing the section gets a refusal that prints the
   seed to paste. `adopt`'s `config-updated` is what catches a pin bump that added a step the
   consumer's table has no transition for — a named finding with the value, never a crash
   mid-release.
6. `[pm] also_done` (0.2.0's shim) is read into `[pm.states.<kind>] done` and deleted.

## Risks

1. **A transitions table is a second place a state name is written**, and the whole point is to
   have fewer of those. Mitigated by criterion 3: the table is VALIDATED against the categories,
   so the two cannot disagree silently. Unmitigated, it is a new drift surface.
2. **A project with one `in_progress` word has a transitions table that says nothing.** The
   default must make it invisible, or every consumer carries ceremony for a choice they do not
   have.
3. **Ordering within a category must stay presentation.** The moment a gate cares whether
   `packaging` precedes `done`, the words are load-bearing again and this milestone is undone
   quietly.
