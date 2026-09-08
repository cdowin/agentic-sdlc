# The SDLC as an engine — where this goes

Written 2026-09-08 on the research branch, after reading `orca-sdlc-kit`. A direction, not a spec:
nothing here is decided, and the point is to name the seams that already exist before anybody builds
across them.

---

## Part 1 — the 3k-versus-32k question, answered with numbers

The comparison that prompted this: Orca does a lot with 2,924 lines and no tests. We carry 21,519
source and 36,295 test. That gap deserves a real answer rather than a defence.

### 32k is not 32k of test code

| | total | actual code | prose (docstrings + comments) | blank |
|---|---|---|---|---|
| `src/` | 21,519 | **14,000** (65%) | 4,689 (22%) | 2,830 |
| `tests/` | 36,295 | **20,604** (57%) | **10,830 (30%)** | 4,861 |

The real ratio is **20,604 test lines to 14,000 source lines — 1.47:1**. For a tool whose two
cardinal sins are *a gate that misses drift and prints PASS* and *a write that looks legitimate and
is not*, that is on the high side of normal, not absurd.

**The absurdity is real but it is in two specific places, and neither is "too many tests".**

1. **10,830 lines of prose in `tests/` — 30% of the suite.** `tests/` is 19% docstrings and 11%
   comments. The essay style is deliberate in `src/`, where `test_prose_census.py` gates it and
   where the reader is an agent with no memory of last week. Nothing gates it in `tests/`, and the
   style leaked there anyway. That is the single largest, least defensible block of lines in the
   repository.

2. **8,075 lines live in modules that walk our own AST** to police our own source — roughly 22% of
   the suite spent on self-policing rather than on behaviour. Some of that is rule 4 and is the best
   money we spend (`test_guard_corpus.py` found four hollow gates in one milestone). Some of it is
   the tool checking its own homework, and nobody has ever sorted which is which.

### And the comparison flatters them in two ways

- **They do far less.** Orca is one verb and about eight flags. We are ~15 top-level verbs, 19 `pm`
  subverbs, 7 gates and 4 belts. Most of the source gap is surface area, not gold-plating.
- **They stand on a runtime; we are one.** Orca ADE supplies the worktrees, the agent terminals, the
  dispatch records and the run tracking. `flow.mjs` is a *client* of several thousand lines it does
  not ship. Nothing is beneath us.

Their zero tests are not a saving, they are a deferred cost that has already come due once:
`flow.mjs:1556` scores a task with no result payload as `succeeded`, and nothing they ship could
find it.

**The honest conclusion: cut the prose in `tests/`, sort the self-policing from the behaviour, and
stop quoting 36k as if it were all test code. Do not cut the tests.** And see Part 2 — under a
provider architecture, most of that suite stops being "tests for our markdown reader" and becomes
the conformance contract every backend has to pass, which is a much better thing to own.

---

## Part 2 — the engine

The direction, in one sentence: **the SDLC is the engine; everything it touches is a provider it
declares rather than a thing it contains.**

### What already exists, unnamed

Most of this is latent in `devkit.toml` today. The pieces are there; what is missing is a *name for
the seam*, so each reader invents its own way of asking.

| concern | declared today as | reader |
|---|---|---|
| the flow's vocabulary | `[pm.states.<kind>]` | `model.category_of` |
| what a state ASKS on arrival | `[pm.arrive.<kind>.<status>]` — `ask` / `answers` / `have` | `arrive.py` |
| a belt's steps | `[story] steps`, `[feature] steps`, `[release] steps`, `[adopt] steps` | `steps.steps_for()` |
| how to verify | `[verify] story/feature/milestone` → make targets | `verify/rules.py` |
| which gates run | `[checks] all` | `cli.KNOWN_GATES` |
| what to hand an agent | `[dispatch] project` / `contracts` | `dispatch.py` |
| where events go | `[emit] sink` | `emit.py` |
| where the work lives | `[pm] roadmap_dir` | `model.py`, hard-wired to markdown |

**The belts are already the engine Chris is describing.** A belt is a named operation with a
declared step list, an entry condition (`pm ready-for <rung> <id>`, exit 0/1/2, writes nothing) and
an exit condition (run every check, then one write or a clean refusal — that is the D12 shape). That
is "tight configurable steps with entry and exit conditions", shipped, since 0.2.0.

### What is missing

Three things, in the order they hurt.

**1. There is no provider seam for WORK.** `model.py` *is* the markdown backend. There is no
interface a Jira or Linear or GitHub-Issues backend could implement. Everything above it — the
belts, the gates, `ready-for`, the ledger routing — is already backend-agnostic in shape and
backend-coupled in fact.

The seam that wants naming is small and already implied by the code: resolve a grain by id, read a
field, write one field, list children of a parent, and read a parent's `order`. Every gate in
`check pm` is expressible on those five operations. **A `[work]` declaration naming a provider, with
`markdown` as the shipped default, is the change that makes "Jira instead of md" a config line.**

And it reframes the test mass: the ~20k lines of test code that today prove *our markdown reader is
correct* become the **conformance suite a provider must pass to be allowed to call itself one**.
That is the strongest argument available for keeping them, and it only exists if the seam is named.

**2. BUILD and REVIEW have no provider — the operator is the provider.** This is the finding the
Orca comparison landed hardest, and it is measured in our own tree: 0.6.0 closed 22 grains in
4 h 31 m with four dispatched agents, and every brief was hand-written, every slice hand-verified,
every telemetry row hand-typed.

`[verify]` already shows the shape. It does not run tests; it declares *which make target is the
story rung*, and the belt asks for it by name. **`[agents.build]` and `[agents.review]` are the same
declaration for the two steps that currently have a human in them.**

**3. KNOWLEDGE is three unrelated surfaces.** `lesson record`/`lesson show` (an append-only row
bound to a grain and a rule), `pm decide` (a dated heading with its rejected alternative), and the
review records under `[pm] review_dir`. All three answer *"what did we learn and where does it
surface?"*, and each has its own reader. A `[knowledge]` provider is what makes them one thing, and
what would let the answer come from a vector store or a wiki later without any belt knowing.

### The hook point Chris named, concretely

> *"when you go to building, use this agent, shape a prompt this way"*

`[pm.arrive.<kind>.<status>]` is already exactly that table. It already carries three keys — `ask`
(the question), `answers` (both replies, pre-typed), `have` (the capabilities bound to this state).
Today's declaration:

```toml
[pm.arrive.feature.building]
ask     = "what is building this?"
answers = ["--by me", "--by agent <type>"]
have    = { "tools/dev/agent-worktree.sh" = "isolation for parallel work on this grain" }
```

A fourth key is the whole feature:

```toml
dispatch = { role = "developer", agent = "claude", prompt = "briefs/developer.md" }
```

**And it does not break "boots nothing".** The tool RENDERS the dispatch — that is what
`agentic-sdlc dispatch` already does, and what `have:` and `next:` already do at every arrival.
Something else executes it: a shell loop, a CI job, an MCP client, or Orca. `0.5.0/D1` says *the
tool emits; a plugin framework is the rejected alternative* — emitting a **declared, complete**
dispatch is squarely inside that, and it is the difference between the operator writing a brief from
memory and the operator running a line the tree produced.

That is the honest resolution of the Orca tension: **we are not competing with an executor, we are
the thing that should be feeding one.**

### CLI first, MCP later — and why it is nearly free

Every verb here is already `verb --flags → lines on stdout`, with exit codes as contract (0 pass,
1 findings, 2 usage or config). That maps onto MCP tools almost one-to-one: the verb is the tool,
the flags are the schema, and the exit code is the result discriminator. Rule 11's read side — every
read verb names its columns in order, and composition is the shell's job — is the same discipline a
tool schema wants.

**The implication for now is a constraint, not a project:** every verb added between here and there
should stay a pure `stdin/args → stdout/exit-code` function, because that is what makes the MCP
surface a rendering rather than a rewrite.

---

## What this costs, said plainly

A provider seam is not free and the failure mode is well known: an abstraction with exactly one
implementation is a tax with no payer. Three guards worth stating before anyone starts:

- **Two implementations or no interface.** A `[work]` provider with only `markdown` behind it is
  worse than the hard-wired `model.py` we have now. The seam earns its place when a second backend
  passes the conformance suite, and not before.
- **The conformance suite has to come first.** Today's tests assert against markdown specifics in
  places. Sorting behaviour from implementation-detail is most of the work and none of the glamour,
  and it is what turns 20k lines from cost into asset.
- **This is a major.** Hard rule 7: a consumer's Makefile or hook changing to survive is a major
  bump. A `[work]` declaration with a default keeps that at minor; anything that moves `[pm]` keys
  does not.

---

## The order I would do it in

1. **Cut the prose in `tests/`** and sort the AST self-policing from the behaviour tests. Cheapest,
   independent of everything else, and it makes every later measurement honest.
2. **`[ledger] transcripts`** — the harvester from the Orca read. Fixes a measured five-milestone
   defect, ~100 lines, no seam required.
3. **`dispatch` as a fourth key on `[pm.arrive.*]`.** Renders; executes nothing. Turns the
   hand-written brief into a declared one and makes the tree the source of the prompt.
4. **`[knowledge]`** — unify lessons, decisions and review records behind one reader. Smallest of
   the three seams and the one with the least coupling.
5. **`[work]`** — last, and only with a second backend in hand.

Nothing above is committed. Items 1 and 2 are unambiguously worth doing; 3 is the interesting one;
4 and 5 are the ones that need a second implementation before they are anything but a tax.
