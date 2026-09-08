---
id: ft-a-source-shaped-guard-is-named-as-one
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: a source-shaped guard is named as one
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a source-shaped guard is named as one

The other half of the tech debt, and the half nobody has ever sorted.

## The measurement

**8,075 lines of `tests/` live in modules that reach `ast.parse` or `ast.walk`** — roughly 22% of
the suite, spent policing our own source rather than exercising our own behaviour.

Some of that is the best money in the repository. `tests/test_guard_corpus.py` found four hollow
gates during 0.6.0's close, and `test_boundaries.py` catches a spawn on the hot path before a
reviewer would. Some of it is the tool checking its own homework at a cost nobody has priced.

**Nobody knows which is which**, because the only way to ask is to grep for `ast.parse` — which is
how the number above was produced, by hand, which makes it a row in
`ft-a-hand-rolled-command-is-a-missing-verb`'s census too.

## What already exists to build on

`tests/test_guard_corpus.py` derives the roster of AST-shaped guards FROM SOURCE, replays every
declared `CORPUS`, and holds the ones declaring nothing as an `UNCOVERED` roster that can only
shrink. The mechanism is there. What it does not do is say what the guards COST or what fraction of
the suite they are — it answers "is this guard probed", not "should this guard exist".

And the honest number underneath: **5 of 58 test modules declare a `CORPUS`.** Most of the suite has
never been probed either, which is the finding a milestone review landed against the claim that our
gates are better than an LLM's verdict. They are — but thinner than the claim implies.

## The question this feature answers

For each source-shaped guard: **what property does it protect, and would anything else have caught
that property breaking?** A guard whose property is already covered by a behaviour test is a second
scoreboard. A guard protecting a property nothing else can see — rule 2's no-spawn, rule 9's
no-inference, the derived-field rule — is load-bearing and its cost is worth paying.

That is a judgement per guard, written down, not a rule that can be automated. What CAN be
mechanised is the census: which modules are source-shaped, how many lines, what they claim to
protect, and whether they declare a corpus.

## Ship criterion

The source-shaped guards are a NAMED set the code can be asked for, not a grep — and the set,
its line cost, and its corpus coverage are reportable.

Every guard in the set names the property it protects, in one line, where the guard lives.

Each is judged in writing — load-bearing, or a second scoreboard for a property a behaviour test
already covers — and the ones judged redundant are removed or the judgement is recorded against
them.

The `UNCOVERED` roster's growth is explained rather than assumed: 5 of 58 modules declaring a corpus
is either correct (most modules are not source-shaped) or a gap, and this feature says which.

## Proof budget

  cases: 2
  tier: pyunit
  lands in: `tests/test_guard_corpus.py` — it already derives the roster from source and holds the
    exact-roster assertion; the census is a second question of the same reader
  what already covers this: `test_every_ast_shaped_guard_declares_a_corpus_or_is_named` is the
    roster half already. What has never been asked is what the set COSTS and whether each member
    earns it.

## Out of scope

Deleting a guard because it is expensive. The two cardinal sins are worth real money; this feature
is about knowing the price, not refusing to pay it.

A coverage target. `check budget` gates cost and the corpus roster gates probing; a third number
would be cargo, which is the same ruling 0.6.0 made about a line-count gate on functions.
