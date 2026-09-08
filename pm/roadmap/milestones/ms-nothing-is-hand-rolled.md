---
id: "ms-nothing-is-hand-rolled"
kind: milestone
name: nothing is hand-rolled
status: planning
depends_on: ["ms-the-rule-reaches-the-work"]
branch: milestone/0.7.0-nothing-is-hand-rolled
version: 0.7.0
changelog:
order:
  - "bg-a-decision-citation-resolves-to-the-wrong-milestone"
  - "bg-the-brief-undercounts-the-coupling-it-argues-from"
  - "ft-the-module-says-what-it-does"
  - "ft-the-suite-is-measured-like-the-source"
---

# 0.7.0 — nothing is hand-rolled

> ## Northstar: **a module says what it does in one true sentence, and the seams the rules already
> require actually exist.** 0.6.0 deferred this split "whole" at the end of a 17-grain milestone.
> That was a call about TIMING, not merit, and the start of a milestone is the only time it is cheap.

**This is the structural milestone.** It is deliberately small in grain count and large in each
grain, because the work is moving code without changing behaviour and that is reviewed as one
changeset or not at all.

## The measurement

**`repo/pm/model.py` is 2,817 lines doing four unrelated jobs**, and its docstring — *"the PM-tree
invariants, single-sourced"* — describes none of them: the SDLC vocabulary (1,070), the frontmatter
store with its cache and byte-exact writer (385), the id grammar (54), and the grain index and pool
layout that IS the work provider (1,308). **`repo/pm/cli.py` is 3,136 lines**: 24 verb bodies
(1,208), 75 module helpers (1,129), 32 constants.

**Three seams are missing and the rules that need them already exist.**

    storage   164 calls into the frontmatter mechanics from 13 modules outside model.py,
              against 71 to the semantic layer — the engine reaches THROUGH the abstraction
              2.3x more often than it uses it. `field_of(path: Path, key)` at 89 sites.
    spawning  16 subprocess sites across 9 modules, and NO "one place" — for rule 2, the
              rule this tree cares most about.
    naming    model.py, driver.py, steps.py, verdict.py, report.py: a reader cannot tell
              from the name which layer they are in.

**The suite is 36,295 lines and 10,830 of them are English** — 30% of `tests/`, against `src/`'s 22%
for prose of all kinds. The essay style is gated in `src/` and leaked into the one root with no
ceiling. Plus 8,075 lines policing our own AST that nobody has sorted, and 5 of 58 modules declaring
a corpus.

## The standard, and it is already in the tree

`core/apply.py` opens *"The one place this package mutates a filesystem."* `core/walk.py` opens
*"The one place this package enumerates a filesystem."* One sentence, exactly true, enforced by
`tests/test_boundaries.py` with a named exemption roster that can only shrink.

**That is the bar. Two files meet it and nothing under `repo/` does.** The fix is not a new idea —
it is two more members of a family that exists.

## What this milestone is NOT

**Not a line-count exercise.** 0.6.0 ruled against line-count gates on files and functions and that
stands. The target is the SIGNATURE and the SENTENCE: a module you can describe in one true line,
and an engine that does not take a `Path` to ask a grain a question. Where a split falls out of that
it falls out; where it does not, nothing moves for tidiness.

**Not `[work]`, and no second backend.** An abstraction with one implementation is a tax with no
payer. What this buys is REACHABILITY — at 89 `Path` call sites a second backend is not expensive,
it is impossible.

**Not the conveyor.** Agents as registered kinds, a phase declaring what it hands an agent, the
transcript harvester, the hand-rolled-verb census — all moved to the pool, where they gate nothing
and are counted. They belong to the milestone where an agent kicks off steps, spawns subagents and
works the framework itself, and that is a different thing to plan entirely.

## The decomposition, which is the other lesson from 0.6.0

**Ten features shipped in 0.6.0 with 0/0 stories**, and `check pm` warned about it on every run. Two
features here carry ten stories between them, because a module split lands one module at a time —
each behaviour-preserving alone, each committable and revertable alone, each with its own AST proof.
A feature that cannot be decomposed is a feature nobody can review.

## Ship criterion

Every module under `src/agentic_sdlc/` opens with one sentence that is exactly true of it, and its
filename says which layer it is in.

The storage layer and the spawn seam are each one module with a stated contract, held there by
`tests/test_boundaries.py`'s existing primitive family and its exemption roster.

No module outside the storage layer and that roster passes a `Path` to ask what a grain says.

`tests/` is measured by the same census as `src/`, with its own ceiling and its own written
argument, and the source-shaped guards are a named set that says what each protects.

**Behaviour preservation is proven mechanically at every landing**, not asserted — the AST
comparison `ft-the-vocabulary-is-constants-not-literals` used. Hard rule 3's byte-exact guarantee is
what is most at risk.

## Risks

- **This is the milestone most able to break rule 3 silently.** The byte-exact frontmatter writer is
  385 lines of hand-rolled I/O and moving it is the whole point. Every landing needs the AST proof
  AND a read of the residual, and a story that cannot show one does not land.
- **"Split it" is a mood, not a criterion.** The ship criterion is a true sentence per module, not a
  line count; a reviewer should reject any split whose only argument is size.
- **Deferring again is the failure mode.** 0.6.0 deferred exactly this with a good reason about
  timing. There is no such reason at the start of a milestone, and if it is deferred a second time
  the honest conclusion is that the tool does not intend to have layers.
