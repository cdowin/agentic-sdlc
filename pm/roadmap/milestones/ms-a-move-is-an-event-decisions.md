Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ms-a-move-is-an-event  — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-07 — The tool emits; a plugin framework is the rejected alternative

**A hook is an event this package WRITES. It is never a command this package RUNS.** The sink is
declared in `devkit.toml` — a path, a stream, the ledger — and a courier the consumer arms carries
the payload onward, exactly as `cc-ledger-session.sh` and `cc-ledger-subagent.sh` already carry
transcripts. Nothing new is spawned, imported or initialised by any verb.

**Rejected: a plugin system — an ABC a consumer subclasses, discovered through
`importlib.metadata` entry points, invoked by the belt at each rung.** It is the obvious design, it
is stdlib-only so hard rule 1 survives it, and it is what every framework in this space does. It
still dies on hard rule 2: discovery means *importing consumer code into this process*, and
"boots nothing — safe anywhere, any time, in parallel" is the property that makes every gate here
runnable from a git hook. The moment a plugin is imported, the tool also owns lifecycle, timeouts,
error isolation and shutdown — it has stopped being a reader/writer and become a runtime.

**The rejected alternative has a worked example, and it is the package that owns our name on PyPI.**
`agentic-sdlc` 3.0.0 (truongnat, MIT, unrelated) is aimed at the same target this package is — its
CLI is `init`, `run <workflow>`, `status`, `agent create|list`, `workflow create`, `config
show|set`, `health`, `brain stats|learn`. That is our surface minus the PM tree and minus every
gate. It took the plugin path, and its 3.0.0 is what the plugin path decays into:

- `Plugin(ABC)` with four abstract methods and `PluginRegistry.load_from_entry_points()` handling
  three Python versions' `entry_points()` shapes — real machinery, carefully written.
- **No cross-module call sites.** `PluginRegistry`, `Bridge`, `ModelClient`, `WorkflowEngine`,
  `Coordinator`, `AgentRegistry` and `Learner` are each imported in exactly two places: their own
  subpackage `__init__.py` and the top-level `__all__`. Nothing calls anything.
- **Two execution engines that do not know about each other.** `infrastructure/engine`'s
  `TaskExecutor.execute` really calls `task.func(*args, **kwargs)`;
  `infrastructure/automation`'s `WorkflowEngine._execute_step` takes an `action` STRING and returns
  `{"step": …, "action": …, "status": "completed"}` — a literal. The five lines that would resolve
  one into the other through the registry are the seam, and they are absent.
- `_compat/installer.py` is the fossil record: ~20 real 2.x modules (`api_client`,
  `cost_tracker`, `rate_limiter`, `failover_manager`, `health_checker`, `openai_adapter`,
  `anthropic_adapter`, `ollama_adapter`, plus `self_healing`, `hitl`, `judge`, `observer`) all
  shimmed onto a package that now holds one abstract client. Its own comment says the shims are
  lenient *"to allow legacy tests to be collectable even if members were removed."*

**The lesson is not that they wrote it badly.** It is that the abstract half of a plugin framework
costs nothing to keep and the concrete half costs everything, so a restructure keeps the surface
and sheds the implementation — and *nothing in that architecture can tell you it happened*. A
package of gates cannot lose its implementation quietly; a gate that stops checking prints PASS
over zero files and rule 4 makes that a failure. That asymmetry is the whole argument for staying a
reader/writer.

**What survives from their design:** the *shape* of `brain learn` — a durable lesson store fed by
observed events — which is `ft-a-lesson-is-a-row-bound-to-a-grain` here. What does not survive is
`Learner` itself: `frequency` is set to 1, ranks recommendations, computes `confidence =
min(frequency / 10.0, 1.0)`, and is incremented nowhere, so confidence is permanently `0.1`. Its
`LearningStrategy` base class is never accepted by `Learner` and never subclassed. Capture with no
read-back is decoration — which is why this milestone's ship criterion requires a lesson to surface
at the next move that touches its grain or rule.

**The pressure this decision has to survive is one sentence:** *"just let the config name a command
to run."* It will sound reasonable, it is one commit, and it is the whole of the above.

## D2 — 2026-09-07 — Everything ships in 0.5.0; a 0.4.1 patch is the rejected alternative

**The five bugs ship here, in 0.5.0, and the consumer-facing two run FIRST.** `order` opens with
`the-migration-rewrites-only-quoted-refs` (#7) and `check-pm-reopens-every-file-per-field` (#6),
ahead of every feature — the same shape 0.4.0 used when it put its telemetry pre-work before the
migration, and for the same reason: the riskiest and most-blocking work should be the best-measured
and the earliest, not the tail.

**Rejected: a 0.4.1 carrying #6 and #7 alone, ahead of this milestone.** The argument for it was
real and is recorded here rather than lost: both are open against SHIPPED 0.4.0 and are degrading a
consumer tree right now — #7 quietly turned 36 refs decorative while `check pm` exited 0, and #6
made the narrowest rung on the conveyor slower than that consumer's entire unit tier. Carrying them
in 0.5.0 means that consumer waits for the whole event stream to land before either is fixed,
because `release` refuses while any open bug names the milestone.

It was rejected on cost, deliberately: a patch release is its own belt run — branch, changelog,
version-sync, full gate, PR, merge, tag, artifact proof — and 0.5.0 would then have to adopt its own
patch mid-milestone. Front-loading the two bugs in `order` gets the fix written just as early; what
it does not get is the fix PUBLISHED early. **If the consumer needs it published before 0.5.0 is
ready, the answer is to cut 0.4.1 from those two commits at that point** — the work is sequenced so
that stays possible, and this decision is not a commitment to never do it.

**What this costs, stated plainly:** 0.5.0 is now 7 features, 1 story and 5 bugs, and it cannot ship
until all five bugs close. The milestone's Risks section already says weight is shed from the
lessons half and never from the edges; the bugs are not sheddable at all, because they are open
against released code.

## D3 — 2026-09-07 — Arrival is the primitive; states declare what arriving asks

**There is one event in this system and it is ARRIVAL: a grain reaches a state.** Everything this
milestone has been building — hooks, the fork, dispositions, telemetry, lessons, breadcrumbs — is a
reader of that one event. They were being designed as five mechanisms because nobody had named the
one underneath them.

**The config already declares the nodes. It gains one table: what ARRIVING at each state asks.**

    [pm.states.feature]                     # today — the nodes and their categories
    todo        = ["planning", "ready"]
    in_progress = ["building", "reviewing"]
    done        = ["done", "obe"]

    [pm.arrive.feature.building]            # new — the action tied to the state
    ask     = "what is building this?"
    answers = ["--by me", "--by agent <type>"]

    [pm.arrive.feature.reviewing]
    ask     = "what happens to it?"
    answers = ["--review agent <type>", "--skip review \"<why>\""]

**An arrival does four things, and all four are derived from what the project declared:**

    1  writes the status                        (today)
    2  asks its question, both answers typed    ft-the-conveyor-pushes-back
    3  records the disposition, or `none`       ft-every-edge-carries-a-disposition
    4  emits the event                          ft-one-event-shape-serves-three-readers

The belts are unchanged and sit on top: a belt is its checks, then one write — **and a write is an
arrival**, so a belt's close is an arrival like any other, and a skipped check is that arrival's
disposition.

**DIRECTION IS NOT MODELLED, and that is the point.** The unit is arrival, never the pair
`(from, to)`. `building -> planning` is an arrival at `planning`. A second pass through `building`
asks *"what is building this?"* again — which is the correct question, because it is the question, and
the answer genuinely may have changed. So:

- there is no transition table, and there never will be one. Rule 9 already says the tool has no
  opinion about which state may follow which; making arrival the unit means it never needs one.
- backwards costs nothing to support because it was never a special case.
- a grain that bounces is not an error, it is an arrival log with more rows, which is exactly what a
  reader wants to see.

**Telemetry is passive and reads that log.** Time in a state is the gap between two arrivals on one
grain. Who did the work is an arrival's disposition. What was skipped is an arrival's disposition at
`done`. None of it needs a harness hook, which is the failure this milestone hit: nine dispatches,
zero rows, because the only telemetry path ran through something outside the tree. **A tree that
records its own arrivals knows what it did without asking anyone.** Hook-written rows keep enriching
it — tokens, tool calls — joined on the disposition's `ref`.

**Rejected: modelling transitions as edges with allowed sources.** It is the obvious reading of "state
machine", it makes backwards a special case that needs permission, and it puts the tool in the
business of deciding which move is legitimate — the exact opinion rule 9 forbids. Arrival is
strictly less machinery and strictly more honest: the tree records where things went, not where they
were permitted to go.

## D4 — 2026-09-07 — ready-for has no adopt rung; inventing an entry condition for it is the rejected alternative

**`pm ready-for` takes `story | feature | milestone | tag`, and it will not take `adopt`.** An
adopt BELT exists — `driver.OPERATIONS` names it and `close`'s registry answers for it — so the
absence is a real gap in `ft-a-rung-has-an-entry-edge`'s ship criterion (*"answers for every rung a
belt exists for"*) rather than an oversight, and it is recorded here because a gap nobody wrote
down reads as a bug the next person will "fix".

**The reason is the derivation, run against the adopt list.** `ready-for <rung>` does not hold a
list of conditions: `_entry_condition` composes `[<op>] steps` with `registry_for(<op>)` and
`steps.ENTRY_CONDITIONS`, and asks whatever survives. Run it over `DEFAULT_ADOPT_STEPS` and nothing
survives, for one of two reasons:

- `pin-bumped`, `installables-current` and `config-updated` are the work the bump DOES. They are
  true only AFTER the belt has run, which is the same reason `evidence-written` is not a story
  entry condition.
- `hooks-self-test`, `telemetry-live`, `runner-targets-resolve`, `checks-pass` and `pm-validates`
  are all in `COMMANDABLE` with a `SHIPPED_ACTION`, and an entry condition that runs a command is
  passed over by name: `ready-for` boots nothing (hard rule 2), and a rung that shelled out would
  stop being safe to ask dozens of times a day.

So the derived entry set for `adopt` is EMPTY. `ready_for_story`'s zero-census branch would fire on
every invocation and the verb could only ever exit 1 — *"nothing was asked"* — on every tree, for
every consumer, forever. **A rung that can only answer NOT READY is worse than no rung**: an agent
learns to ignore it, and the ignoring generalises to the three rungs that do work.

**Rejected: writing an adopt entry condition by hand** — *"the pin is behind"*, *"the working tree
is clean"*, *"the current version parses"*. It is one small function, it would make the criterion's
sentence literally true, and it is the rejected alternative because of what it costs. Every other
rung's condition is READ from the belt's own registry, which is why a project that narrows its
`[<op>] steps` gets its own answer back; a hand-written adopt condition would be the one rung whose
question this package DECIDED rather than read — rule 9's edge — and it would answer READY over a
census of nothing the belt will actually ask, which is rule 4's first sin wearing a different hat.

**What ships instead is the ABSENCE, said out loud** (rule 11). `pm ready-for adopt 0.5.0` used to
answer `unknown kind 'adopt'`, which reads as a typo — the exact failure `cli.py`'s
`RETIRED_COMMANDS` handling exists to prevent. The refusal now names `adopt` and says why it has no
entry condition, `ft-a-rung-has-an-entry-edge`'s synopsis no longer advertises the form, and the
feature's `## Out of scope` carries the line.

**What would reopen this:** an adopt check that is decidable up front and runs nothing. `pin-bumped`
becomes one the moment it is split into *"is the pin behind?"* (a read of two version sites, true
before the work) and *"was the pin bumped?"* (the write). If that split ever happens for its own
reasons, `ENTRY_CONDITIONS` gains a name and this rung starts answering — with no change to
`ready_for.py`, which is the point of deriving it.

## D5 — 2026-09-07 — A check has three answers; deleting the check is the rejected alternative

**`--skip <check> "<why>"` is a first-class close, and D12 is revised to say so.** D12's sentence —
*"a belt is its checks, then one write or a clean error"* — stands whole. What changes is what
counts as a check being ANSWERED: a disposition is an answer. The belt still writes exactly one
thing, still names every check on its own line, and still refuses when a check is false and nobody
spoke. `--force` is untouched and keeps its meaning: writing ANYWAY, false checks named, no reason
given, one `deviation` row. The two are different in kind and their rows do not bleed.

    true            the check passed
    dispositioned   the caller answered it: skipped, and why
    false           not true, and nobody said anything — the belt writes nothing

**The hard requirement CAUSED the batching, and that is a measured claim, not a worry.** `close
feature` refused without a review record; a review is expensive; so closing was expensive, so
closing got deferred. Offered *"pay for a review, or file a deviation against yourself"*, an
operator does neither — it opens another grain. This milestone's own build did that thirteen times,
having written the rule down twice. A rule that is written down twice and broken thirteen times is
not a discipline problem; it is a priced-wrong verb.

**A skipped check is not asked.** That is the whole economy: `--skip feature-verified "..."` does
not run the tier, and `--skip review-recorded "..."` does not look for the record. A `skipped:` line
over a question that was asked anyway would save nothing and mean nothing.

**A skip with no reason is REFUSED**, because an unexplained skip IS a deviation and already has a
verb. The reason goes through `ledger.reason_defect` — the same grammar the deviation row's reason
uses, so there is one definition of what a reason is — and a `disposition` row carries it against
the grain forever: `{ts, kind, grain, operation, check, why}`, one row per skipped check, because a
forced write is one act while a disposition is one judgement about one question. **`ts`, not the
grain's `at`**: every reader here — `ledger.read_rows`, `parse_ts`, `pm ledger show`'s sort — keys
the stamp as `ts`, and a second spelling would file every disposition at the beginning of time.

**Which checks are dispositionable is a DECLARATION** — `[<belt>] skippable = ["review-recorded"]`
— and the stock declaration is NOTHING, so a repo with no `devkit.toml` runs today's belt byte for
byte. That is what keeps this inside rule 9: the tool reads what the project declared and has no
opinion about which check is a judgement. `tree-clean` and `on-milestone-branch` are facts about the
world rather than judgements, and **a project that lists one is making a mistake the tool will let
it make**, because that is what rule 9 means. A skip of a check the project did not declare is
refused BY NAME at exit 2, and so is a `skippable` entry naming a check this belt does not run.

**`adopt` takes neither flag.** It is checks-only and says so before its first check: no status, no
row. A `skipped:` line there would be a judgement with nowhere to be recorded, which is the record
this flag exists to make, missing. Both flags are named in its `--help` as the ones it refuses,
rather than left to be discovered by trying them (rule 11).

**Rejected: making review optional by deleting `review-recorded` from the shipped list.** It is the
one-line version, it needs no flag, no config key and no row, and it makes the close as cheap as
this decision does. It is wrong because **then nothing records that a judgement was made.** A tree
with no `review-recorded` check cannot distinguish the feature whose author read the diff and
decided it did not warrant a review from the feature nobody looked at at all — and those are the two
cases a milestone review most needs told apart. The check is not the cost; the check is the
QUESTION, and the answer is what the tree is for. Deleting it deletes the question so that the
absence of an answer stops being visible, which is rule 11's failure with the evidence removed.

**Rejected, second: letting `--force` carry a reason.** One flag, no new row kind, no config. It
fails on the word: a `deviation` row reads as a breach of the belt, and a considered engineering
call filed as a breach is a lie about what happened — the same class of lie as a gate printing PASS
over nothing, pointed at the operator instead of the tree. The two acts want two words because they
are two acts, and a milestone review sweeping *"which closes skipped a review, and why"* needs the
one that is not an admission of guilt.

**What is left for the read side (rule 11):** `pm ledger show <grain>` prints a `disposition` row's
`ts` and `kind` and stops there, because its renderer branches on `status` only — the row is
visible and its `check` and `why` are not. That is a column, not a verb, and it belongs in
`cmd_ledger_show` beside the status branch.

## D6 — 2026-09-07 — One word, two shapes: the skip is folded into the arrival it belongs to

Two agents built two halves of one word and neither would decide alone — correctly. `arrive.py` mints
`{ts, kind: "disposition", grain, state, answer, value}` on every arrival; `driver.py` mints
`{ts, kind: "disposition", grain, operation, check, why}` on every skipped check. Both added a shape
discriminator (`state` present vs `check` present), both pinned it with a test, and both wrote the
same sentence: *whether these should be one row is the milestone's to settle.*

**They fold. One row per arrival, and a skip is a field on it.**

    {ts, kind: "disposition", grain, state, answer, value?,
     skipped: [{check, why}, …]}

D3 is the reason and it is not a preference. *A belt is its checks, then one write — and a write is
an arrival, so a belt's close is an arrival like any other, and a skipped check is that arrival's
disposition.* A `close feature --skip review-recorded "…"` is ONE thing happening: the grain arrived
at `done`, and this is how its question was answered. Two rows describe it as two events, and the
tree then holds two facts where one occurred.

**What folding buys, concretely.** `pm ledger report`'s per-state time is the gap between consecutive
arrival rows on a grain (`ft-time-is-measured-per-state-and-rolls-up`). With one kind and one shape
that is a walk. With two shapes under one kind it is a walk plus a filter — and a filter that a
future reader can forget is rule 4's first sin waiting: it would report a plausible number computed
over the wrong rows, and nothing would say so.

**Rejected: two distinct kinds, `disposition` and `skip`.** It is cheaper than folding, it removes the
collision just as completely, and I nearly took it. It fails on D3: it spells a close as an arrival
PLUS some other kind of event, when the whole point of naming arrival the primitive was that there is
only one event in this system. A second kind is a second scoreboard for the same fact.

**Rejected: leaving the discriminator.** It works, it is tested, and it is what is in the tree right
now. But `disposition` would mean two things depending on which key is present, and every future
reader would have to know that — the exact "one word, two shapes" defect this package deletes
everywhere else.

**Cost, stated plainly:** the belt currently mints skip rows during its check run, before the write.
Folding means collecting them and emitting once, at the arrival. That is a real change to
`driver.py`'s ordering and it is the work this decision buys.
