---
id: ft-a-guard-declares-its-violation-corpus
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: a guard declares its violation corpus
status: building
reviewed:
depends_on: []
consumed_by: []
changelog: A source-shaped guard now declares the violations it must catch — `CORPUS` (planted input, must it be caught) and `catches()`, its own classifier over one — and `tests/test_guard_corpus.py` derives the roster of AST-shaped guards under `tests/` from source, replays every declared case, and holds the ones declaring nothing as an exact named roster that can only shrink. The shape is `prepare-commit-msg --self-test` plus `check hooks`, one layer over; nothing in the shipped CLI changed.
---

# a guard declares its violation corpus

This suite polices its own source with guards that walk an AST: one walk, one
apply, config through the guards, layers pointing downward, the tool emits and
never executes, every event field derived, no `git` at this checkout. Each one
asserts an EMPTY offender list, and an empty list is also what a reader that
stopped reading produces. 0.5.0 shipped that exact failure: a derived-field
guard walked `ast.Return` in a function whose only return is a bare name, so a
planted `suggested_action` was invisible while the guard reported 4-of-4, and
the count was cited to the orchestrator as proof the property held.

Five of the guards in `tests/test_boundaries.py` already answer this, by hand
and by habit: `OPEN_SPELLINGS`, `EMIT_EXECUTION_SPELLINGS`, `MINTER_SPELLINGS`,
`DOCSTRING_SPELLINGS`, `GIT_SPAWN_SPELLINGS` are planted inputs run through the
real classifier. Nothing knows they exist, nothing counts them, and a guard
written tomorrow with no table looks exactly like a guard whose table passes.

**The hook corpus is the shipped precedent and this follows its shape, not a new
one.** `tools/hooks/prepare-commit-msg` declares its own cases behind
`--self-test`; `check hooks` derives from each hook's TEXT which ones declare a
corpus, replays them, counts them, spells the coverage in words, and calls zero
replays a finding. Here: a guard declares `CORPUS` (planted source, must it be
caught) and `catches()` (its own classifier over one planted source); the gate
derives from each test module's TEXT which guards are AST-shaped and which
declare a corpus, imports and replays every declared one, and holds the
uncovered ones as an exact named roster that can only shrink.

The population is AST-shaped guards — a guard whose grading reaches
`ast.parse`. That is the narrowing this feature makes deliberately, and it is
the shape in the evidence: a syntax classifier can visit the wrong node type
and keep reporting a count, while a byte comparison either matches or does not.
Guards that read shipped text without parsing it are OUTSIDE this census, and
so is a guard reaching a reader in another module, which source in one file
cannot resolve. Both are stated in the module docstring rather than implied —
the same disclosure `check hooks` makes about `_*` and `*.local`.

## Ship criterion

`tests/test_guard_corpus.py` derives the roster of AST-shaped guards under
`tests/` from source, and:

- every guard that declares `CORPUS` + `catches()` has every case replayed, so
  a guard that stops catching its own planted violation turns the suite red by
  name and case;
- a corpus that holds no violation case, or no clean case, is a finding — it is
  the analogue of a hook naming `--self-test` and never printing `SELF-TEST OK`;
- a guard with no corpus is named in an exact `UNCOVERED` roster: a guard
  missing from it fails the gate, and a listed guard that has since gained a
  corpus fails the gate too, so the list can only shrink;
- the census has floors, and the gate that reads the roster is itself an
  AST-shaped guard carrying its own corpus, replayed by itself;
- every AST-shaped guard in `tests/test_boundaries.py` declares a corpus.

Guards in test modules this agent does not own stay on `UNCOVERED`, named, as
the work queue.

## Proof budget

  cases: 5 new (the gate's own module) + 14 corpora declared on existing guards
         (data on the guard, replayed by one of those 5 — not new cases)
  tier: unit (`make unit`) — pure `ast.parse` over snippets and over `tests/`,
        no temp tree, no process, which is rule 10's cheapest tier that can fail
  lands in: `tests/test_guard_corpus.py` (new; joins `UNMARKED_MODULES` in
        `tests/test_shell_mark.py` in sorted position), and `CORPUS`/`catches`
        on the 14 AST-shaped guards in `tests/test_boundaries.py`
  what already covers this: nothing counts corpora. Five guards replay planted
        inputs today (`OPEN_SPELLINGS`, `EMIT_EXECUTION_SPELLINGS`,
        `MINTER_SPELLINGS`, `DOCSTRING_SPELLINGS`, `GIT_SPAWN_SPELLINGS`) and
        their tables stay as the exact expectation; what is missing is that
        nine other guards have none, no gate says so, and a new guard is not
        asked for one. `tests/test_check_hooks.py` proves the same shape one
        layer over, for hooks, and is the design this copies.
  spent: 4 cases in `tests/test_guard_corpus.py`, replaying 155 corpus cases as
        subtests, and NET ZERO new test items — the four same-module cases in
        `TheLedgerAppendIsTheOneException` became fourteen `CORPUS` rows with
        one replayer, which is rule 10's "prove it once". 15 of 30 AST-shaped
        guards declare a corpus; the other 15 are named in `UNCOVERED`. The
        unit tier stayed at 8 s.
