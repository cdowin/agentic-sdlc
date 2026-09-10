---
id: ft-the-suite-is-measured-like-the-source
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: the suite is measured like the source
status: building
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the suite is measured like the source

The test debt, and the reason it is a feature rather than an afternoon of trimming: **a cut nobody
gates comes back.**

## The measurement

|  | total | code | prose | blank |
|---|---|---|---|---|
| `src/` | 21,519 | 14,000 (65%) | 4,689 (22%) | 2,830 |
| `tests/` | 36,295 | **20,604 (57%)** | **10,830 (30%)** | 4,861 |

The honest ratio is **20,604 lines of test code to 14,000 of source — 1.47:1**, which for a tool
whose cardinal sins are a lying gate and a corrupting write is the high side of normal and is NOT
the problem.

**The problem is that 30% of `tests/` is English** — 19% docstring, 11% comment, against `src/`'s 22%
for both combined. The essay style is deliberate in `src/`, where `test_prose_census.py` gates it and
the reader is an agent with no memory of last week. Nothing measures `tests/`. The style leaked into
the one root with no ceiling and grew there.

**And 8,075 lines live in modules that reach `ast.parse` or `ast.walk`** — ~22% of the suite spent
policing our own source rather than exercising our own behaviour. Some is the best money in the
repository: `test_guard_corpus.py` found four hollow gates during 0.6.0's close. Some is the tool
checking its own homework at a price nobody has ever named. **Nobody knows which is which**, because
the only way to ask is to grep — which is how the number above was produced.

Underneath both: **5 of 58 test modules declare a `CORPUS`**, against ~330 lifetime probe rows for
~1,253 cases. Most of the suite has never been probed either, which is the finding a milestone
review landed against the claim that deterministic gates beat a self-reported verdict. They do — but
more thinly than the claim implies.

## Why a ceiling, and why the measurements become verbs

0.6.0 spent **eight rounds** on the src census and the brief had to say *"no comment trimming to buy
census margin"* out loud because the gate kept demanding it. That fight produced `0.6.0/D7`, which
fixed what the census COUNTS rather than what it allows. The lesson: a number somebody hits is
worthless; a number somebody has to ARGUE is the mechanism.

So `tests/` gets its own declared ceiling with its own written argument, set from the suite AFTER the
rot is out — not before, and not at `src/`'s ratio, because the economics differ.

**And the measurements this feature argues from become askable**, because every number in this file
was hand-rolled with `python3 -` and one of its siblings is already a filed bug: the 0.6.0 brief
said the hard rules were cited "roughly 600" times when the tree says 1,107. A measurement a document
quotes must be one a command produces. Scoped to the censuses THIS milestone needs — not a verb per
afternoon, which would be worse than the `python3 -` that produced it.

**Where prose should GO rather than die.** 0.6.0 established three placements that are not trimming
and they apply unchanged: help text belongs in a `USAGE` constant (a string assignment is code), a
rejected alternative belongs in `pm decide`, and the story of a defect belongs in the grain that
fixed it. A test docstring says what this case pins and why it can fail — it does not retell the
incident.

## Ship criterion

`tests/` is measured by the same census as `src/`, with its own declared ceiling and the per-module
argument for that number written beside it, in the shape 0.4.0/0.5.0/0.6.0's case-count arguments
already use.

The ceiling is set from the suite AFTER the rot is out, and the cut is reported per module rather
than as one number. Nothing in `src/` is trimmed to pay for it.

`0.6.0/D7`'s published-`--help` exclusion is carried across correctly or deliberately not — a test
docstring is not printed as `--help`, so the argument does not transfer, and the difference is
stated rather than assumed.

The source-shaped guards are a NAMED set the code can be asked for rather than a grep, each naming
the property it protects, and each judged in writing: load-bearing, or a second scoreboard for
something a behaviour test already covers.

Every census this feature argues from is a command's output, and the number the 0.6.0 brief got
wrong is corrected from one.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_prose_census.py` (a second root is a parametrize row, not a module) and
    `tests/test_guard_corpus.py` (it already derives the guard roster from source)
  what already covers this: `test_comments_and_docstrings_are_under_a_third_of_the_code` IS this
    feature for one root; `test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling` is the
    guard that stops a ceiling becoming a growth gate and generalises to both roots;
    `test_every_ast_shaped_guard_declares_a_corpus_or_is_named` is the roster half already.

## Out of scope

A line-count target. Being over after removing all rot is a legitimate outcome to STATE, not to
satisfy — the same ruling 0.6.0 made about `CLAUDE.md`.

Deleting tests. The suite is 1.47:1 and defensible; this feature is about the English and about
knowing what the self-policing costs.

A coverage target. `check budget` gates cost and the corpus roster gates probing; a third number
would be cargo.
