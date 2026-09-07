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
