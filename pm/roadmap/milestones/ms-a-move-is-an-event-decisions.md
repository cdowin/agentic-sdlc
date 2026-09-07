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
