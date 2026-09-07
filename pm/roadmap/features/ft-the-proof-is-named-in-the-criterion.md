---
id: ft-the-proof-is-named-in-the-criterion
milestone: ms-0.2.0
name: A criterion names the one case that proves it, and the suite is that set
status: done
reviewed: docs/reviews/2026-09-05-the-proof-is-named-in-the-criterion.md
phase: 7
depends_on: ["ft-the-suite-is-cheap-or-it-declares-itself"]
consumed_by: []
risk: high
size: l
labels: ["tests", "process", "templates", "subtraction"]
kind: feature
---

# A criterion names the one case that proves it, and the suite is that set

**Chris, 2026-09-05:**

> *"I really find it hard to believe there are 1853 tests for this small library. … It's a cardinal
> sin to over test like this. … How do we not let this happen? Are the test reviewers not good
> enough? Are the designs not considering testing and the goals as they go? Is it just 'write a
> feature, slap on some tests'?"*

**Measured, and the last question is the right one.**

| | |
|---|---|
| src executable statements | **7,241** |
| tests executable statements | **13,023** — 1.8x the source |
| hand-written test functions | **1,478** (87 `parametrize` decorators expand to 1,855 cases) |
| ratio | **one test per 4.9 statements of source** |
| **test functions ≤ 10 lines** | **1,037 of 1,478 — 70%** |

Two files hold 260 of them: `test_pm_gate.py` (135) and `test_pm_verbs.py` (125).

## Why it happened, and it is not the reviewers

Four artifacts decide what gets tested here. Grep them for the question nobody asked:

| artifact | what it asks about proving the work |
|---|---|
| `templates/feature.md` | **nothing.** Not one word about tests. |
| `templates/story.md` | `## Acceptance criteria`, and nothing else — no tier, no proof, no budget |
| `SDLC.md`'s review step | no opinion on test count or test cost |
| `reviewer.md`, `verification-reviewer.md` | neither mentioned speed or spawning until 2026-09-05 |

**So yes: structurally it is "write a feature, slap on some tests."** The process asks *what must be
true* and never *what is the cheapest thing that proves it, and how few of those*.

**The reviewers are not the failure.** They are excellent at the thing they were pointed at: every
minor bump in this package has had a pre-release review return NOT RELEASE-SAFE, and each time the
blocker was a false PASS. A reviewer catches what the rules name, and no rule named this — hard
rule 10 was written the day this was measured, two releases late.

**The mechanism is acceptance criteria without a proof.** A criterion says what must be true; it
does not say what demonstrates it. So a builder proving criterion 5 writes as many cases as feels
safe — each one cheap alone, all of them expensive only in aggregate, and nothing downstream ever
asks. That is a commons problem, and commons problems are not solved by asking people to try
harder.

## The ruling this feature proposes

**Chris, 2026-09-05, and this is the selection criterion the whole feature turns on:**

> *"We only test to be useful, not to say we have tests. Tests should only gate something that
> BITES, something that eats up real time. … I actually don't care about 100% test coverage. I
> care about test coverage that bites. It should target modules that are core and called
> frequently, ones that are load bearing. I value rapid iteration and learning over precise
> perfect engineering."*

> **A test earns its place by gating something that BITES. A criterion names the one case that
> proves it, and a case beyond that set justifies itself in review.**

Two halves, and the first is the one that decides what goes:

**Does it bite?** The operational question is *if this test were deleted and the thing it guards
broke, what would that cost?* Three answers mean delete: *"the next run catches it anyway"*,
*"nothing downstream depends on it"*, *"it would be obvious immediately."*

| bites | does not bite |
|---|---|
| rule 4's two cardinal sins — a gate printing PASS over what it did not measure, a write that looks legitimate and is not | a docstring claim, asserted |
| a **load-bearing** module: `core/walk.py`, `core/config.py`, `core/apply.py`, `repo/pm/model.py`, `conveyor/driver.py` — called by everything | prose, naming, and file-layout assertions |
| anything on the path a consumer runs **dozens of times a day**: `close story`, `check all`, the hooks | a grammar's twelfth spelling, where eleven already passed |
| a defect that would ship SILENTLY and be found weeks later | a rule already proven one altitude down |
| **anything that has ever gone red for a real defect** — the evidence is `git log -S` on the assertion, or a finding id in its docstring | coverage added to reach a number |

**And the count is capped at DESIGN time.** 31 stories × ~6 criteria is ~190 cases against 1,478
functions. The gap is what got added because nobody had said how much was enough — not because
anyone was careless.

**What this explicitly gives up**, because it should be said rather than discovered: coverage of
paths that are cheap to break and cheap to notice. That is the trade — iteration and learning over
perfect engineering — and it is only safe because the things that bite are gated hard.

## Phase A — collapse, and it is mechanical (SAFE)

**1,037 functions of ≤10 lines are near-identical single-assert shapes over one setup.** Collapsing
a family into one `parametrize`d function preserves every assertion and every case, and removes
N-1 **fixture entries** — which is the cost, because each function re-enters a tree builder.

**BE HONEST ABOUT WHAT THIS DOES NOT DO:** `parametrize` keeps the collected COUNT. The headline
1,853 barely moves in phase A. What moves is setup work and file length.

- target: 1,478 functions → **~600**
- expected: ~800 fewer fixture entries; the unit tier well under 5 s
- risk: low. An assertion that survives a collapse is the same assertion.

## Phase B — delete, and it needs judgement (AGGRESSIVE, and authorised)

Per module, one question: **which of these assert the same thing?** Chris has authorised
aggression; criterion 4 below is what keeps aggression from becoming damage.

- target: **~1,853 collected cases → 400-600**
- **the question, per module, in order:** does this module BITE — is it load-bearing, called
  often, or a place a defect ships silently? If not, its tests are the first to go wholesale
  rather than case by case. If so, which of its cases would actually catch a real defect?
- the shape to look for: a rule proven at three altitudes where one would fail if any did; a
  refusal matrix enumerating twelve spellings of one grammar; a census asserted in four tests that
  read the same census; anything asserting a docstring rather than a behaviour.
- **the shape to KEEP:** every case that has ever gone red for a real defect. `git log -S` on the
  assertion is the evidence, and a test with a finding id in its docstring is a test that caught
  something. Those are proven to bite; nothing else in the suite is.
- risk: **high, and it is the write-side cardinal sin if done carelessly.** A deleted assertion is
  a gate that stops noticing.

## Phase C — the prevention, which is the actual deliverable

Phase A and B are one-time. This is what stops it recurring:

1. **`templates/story.md` gains `## How this is proven`** — per criterion, the tier and the one
   case. A story that cannot name it has a criterion nobody knows how to demonstrate, which is
   worth finding at design time.
2. **`templates/feature.md` gains a proof budget** — roughly how many cases this feature should
   cost, written before it is built and compared after.
3. **SDLC.md's review step gains the question**, so it is asked once per feature by someone who is
   not the author.
4. **`check budget` grows a census ceiling** beside its duration ceiling: `[tests] budget` may
   declare a maximum case count per tier, and exceeding it is a finding naming the growth. Rule
   4's census, pointed at the suite's own size.

## Ship criteria

1. The unit tier is **under 5 s** and the integration tier **under 30 s** — the two numbers
   criterion 3 of the previous feature did not reach.
2. Collected cases are **under 700**, and the ratio of test statements to source statements is
   **under 1.2** (from 1.80). **The number is a direction, not the goal** — the goal is that what
   remains gates something that bites, and a module that genuinely needs eighty cases keeps
   eighty.
3. **No assertion is deleted without a reason recorded.** Every removal names either the case that
   subsumes it or the reason it proved nothing, in the commit. A diff that only shrinks a number
   is not reviewable.
4. **A deliberately-broken probe still reddens.** For each of the eight `check` gates and each `pm`
   write verb, introduce the defect its tests exist to catch and confirm the REDUCED suite still
   fails. This is the criterion that makes aggression safe, and it is not optional.
5. The story and feature templates ask how a criterion is proven, and `check budget` fails a tier
   whose case count exceeds its declared ceiling.
6. `SDLC.md`'s review step asks it, and `install-sdlc` re-renders.

## Risks

1. **This feature can do more damage than any other in the milestone.** Every other one adds a
   gate; this one removes them. Criterion 4 is the guard and it is worth more than criteria 1-3.
2. **The count is a bad target and it is the one Chris named.** 400-600 is a direction, not a
   quota — a module that genuinely needs 80 cases should keep 80, and a phase that hit the number
   by deleting the hook corpus would have destroyed the thing the number was a proxy for.
3. **Phase A makes phase B harder to review.** Once twelve functions are one parametrized family,
   deleting four rows is a smaller diff and a less visible decision. Do B on the modules that
   matter BEFORE collapsing them, or collapse and then review the rows explicitly.
4. **Phase C is the only part that lasts** and it is the part most likely to be dropped when the
   numbers look good. If phases A and B land and C does not, this is a one-time cleanup and the
   next milestone rebuilds the bloat.
