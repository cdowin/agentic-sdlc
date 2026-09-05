---
id: 0.3.0/the-belts-report-they-do-not-refuse
milestone: "0.3.0"
name: A belt moves, warns, and finishes — the caller decides
status: planning
reviewed:
phase: 1
depends_on: []
consumed_by: ["0.3.0/states-are-categories-not-words"]
risk: medium
size: m
labels: ["conveyor", "sdlc", "subtraction"]
---

# A belt moves, warns, and finishes — the caller decides

**Chris, 2026-09-05:**

> *"This is a thing that just gates the SDLC. … It doesn't even stop you from closing something
> if it has, say, a feature with open stories. It shouldn't say, no, you can't do that. It should
> just say: warning, you're moving to a closed state, and you have open children. That's it. The
> machine running this figures out what to do about all of that."*

**This is mostly SUBTRACTION**, and it removes something 0.2.0 shipped four days of thinking into.

## What 0.2.0 got wrong, against a rule already in the repo

`.claude/rules/pm-execution.md`, shipped before any of this:

> *"`pm feature reviewing` and `pm milestone done` REPORT, never refuse. Stories not at
> `reviewing`, features not done — the verb names them and does what it was asked."*

The PM CLI has always worked that way. **The conveyor was built to refuse** — and the feature is
named `the-release-is-a-conveyor`, summary *"a resumable step machine that refuses to advance"*.
The opposite of the rule sitting in the same repo, named after the thing it got wrong.

## The rule, one edge

| about | answer |
|---|---|
| the **INPUT** — malformed id, undeclared state, transition not in the table, config of the wrong shape | **REFUSE**, exit 2. Reading, not deciding. |
| the **TREE** — open children, no review record, dirty worktree, red gate | **REPORT**, and proceed. |

The engine cannot know whether an open child is wrong. Descoped? Hotfix? Deliberate? **The caller
knows and the engine does not**, and a machine that blocks on a question it cannot ask is
asserting an answer.

```
[feature:stories-done] WARNING — 3 story/ies not in `done`: s1 is building, …
[feature] feature 0.2.0/alpha: reviewing -> done  (1 warning)
```

## Scope

| thing | action |
|---|---|
| `close story`, `close feature`, `release`, `adopt` | **stop blocking.** Walk, move, warn, finish. |
| step kinds `AUTOMATIC` / `GATE` / `JUDGEMENT` | keep — they say what a step CAN do, which is still true |
| `Answer.no` / `UNVERIFIABLE` halting the walk | **delete.** They become warnings on the transcript. |
| `pm ready-for` | a READ verb. Its exit code is information for a caller that wants it, not a wall. |
| `--skip <step> --reason` | **shrinks or goes.** It exists to escape a refusal; with nothing to escape it is ceremony. The ledger row was the honest half — keep that as what a WARNING records. |
| `check pm` | untouched. **It is the gate.** `pm` moves and reports; `check pm` fails a contradictory tree, in CI and pre-push, with an exit-code contract for exactly this. |

## What is NOT lost, and this is the part to get right

**The 0.24.0 lesson survives.** That release ran `make milestone` before its reviewer because
nobody knew the order — not because a machine permitted it. The ORDER was always the deliverable;
refusal was belt-and-braces added on top. An ordered list with a loud warning at `review-landed`
fixes the thing that actually broke, and `check pm` still fails a tree that lies about itself.

**And a tool that refuses gets worked around, invisibly.** This package already knew that: it is
the whole argument for `--skip --reason` writing a ledger row — the refusal admitting it should
not have been one.

## Ship criterion

1. No belt halts on a fact about the tree. Every such fact is a WARNING on the transcript, named,
   and the walk continues.
2. Every belt's final line **counts its warnings**, so a caller reading one line knows whether to
   look.
3. Facts about the INPUT still refuse at exit 2, and a test holds the line between the two —
   that boundary is the whole design and it is the thing that will erode.
4. `check pm` is unchanged and still fails a contradictory tree. **A test asserts a belt and the
   gate disagree**: the belt moved it, the gate reports it, and that is correct.
5. `pm-execution.md`'s report-never-refuse rule is quoted in the driver's docstring, since the
   driver is what broke it.

## Risks

1. **A warning nobody reads is worse than a refusal.** Criterion 2 is the mitigation and it is
   thin. If the transcript grows past a screen, the warning count is all anyone sees — make that
   line good.
2. **Removing the halt removes the thing that made the belts feel safe**, and the temptation on
   the next incident will be to add a refusal back for one special case. That is how this got
   built the first time. The one-line test: *is the engine reading what the project declared, or
   deciding what it should do?*
