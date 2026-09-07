---
id: "ms-a-move-is-an-event"
kind: milestone
name: a move is an event
status: planning
depends_on: ["ms-0.4.0"]
branch: milestone/0.5.0-a-move-is-an-event
version: 0.5.0
order:
  - "ft-the-tool-emits-and-never-executes"
  - "ft-one-event-shape-serves-three-readers"
  - "ft-a-move-emits-the-breadcrumb-it-prints"
  - "ft-a-rung-has-an-entry-edge"
  - "ft-a-sink-wired-and-silent-is-a-finding"
  - "ft-a-lesson-is-a-row-bound-to-a-grain"
  - "ft-a-lesson-surfaces-where-you-stand"
  - "bg-the-new-verbs-mint-a-compound-id"
---

# 0.5.0 — a move is an event

> ## Northstar: **the conveyor already knows what it just did and what the next rung asks. Today it
> says that once, as English, to whoever happens to be reading stdout.** Say it as a structured
> event instead, and hooks, telemetry and learning stop being three features — they are three
> readers of one stream.

0.4.0 shipped `every-move-breadcrumbs-the-next-step`: every `pm <kind> <status> <id>` write prints,
after the status line, the belt that closes the grain and the checks that belt will ask — read at
runtime from `[pm.states.*]` and from `registry_for(operation)`, never templated. That feature's
**Out of scope** section is this milestone's brief, written before we knew we would need it:

> Hooks. The corpus is opt-in and arming-dependent, so CLI output reaches every consumer and a hook
> reaches some; a `PostToolUse` breadcrumb is a later layer over the same derived sentence, not a
> substitute for it.

This is that later layer. **The sentence does not change. Its carrier does.**

## What changes

An agent driving this conveyor today has to scrape. It runs `pm story reviewing st-x`, reads a line
of prose meant for a human, and infers its next move from the wording. That works until the wording
changes — which rule 6 says is a minor bump, so it will. Meanwhile the harnesses these agents run
inside (Claude Code and its peers) already have the machinery: a subagent finishes and a callback
fires with a payload. **The conveyor is the only part of the loop with no edges to hook.**

Give every rung two, and make both structured:

    enter   pm ready-for <rung> <id>        the entry condition, ALREADY an exit code —
                                            0 ready, 1 not, naming every blocker
    leave   pm <kind> <status> <id>         the move, ALREADY deriving what comes next
            close story|feature <id>        a belt: its checks, then one write
            release <version>

Neither edge is new work. Both already exist, both already compute exactly the payload an agent
needs, and both currently throw it away by rendering it to prose.

## The shape — five decisions, and the first one is load-bearing

**1. The tool EMITS. It never EXECUTES.** Hard rule 2 says this package boots nothing — safe
anywhere, any time, in parallel. A hook the package spawns ends that permanently, and it is the one
property that makes every gate safe to run from a git hook. So a hook here is **not a command the
tool runs**. It is an event the tool WRITES, and a courier the consumer already arms carries it to
whatever wants it. That split is not new either: `cc-ledger-session.sh` and `cc-ledger-subagent.sh`
already do exactly this for transcripts. This milestone gives them more to carry, not a new
mechanism.

**2. The payload is DERIVED or it does not ship.** Straight from 0.4.0, and the same test guards it:
every field traces to `[pm.states.<kind>]`, to `registry_for(operation)`, or to the grain's own
frontmatter. `{"next_checks": ["stories-done", "findings-landed"]}` is the engine reading its own
registry back. `{"suggested_action": "run a review"}` is the engine having an opinion, and rule 9
forbids it. A hardcoded next-step must fail a test, not a review.

**3. One event shape, three readers.** The event is a ledger row — `ledger.jsonl` already exists,
already has row kinds, already routes by the grain that owns it (D1, 0.4.0). Hooks, telemetry and
learning are the same row read by different people:

    kind        who reads it              what it answers
    move        an agent, via a courier   what just happened, what the next rung asks
    dispatch    pm ledger report          what it cost
    lesson      a person at the next move what this tree learned here before

**4. A lesson is a ROW, not a model.** Capture is append-only and bound to a grain and a rule id,
sourced from what the tree already produces: a gate verdict, a review finding, a `--force`
deviation. Recall REPORTS what was recorded for this grain or rule. It never ranks, scores or
recommends.

**5. The sink is declared, and a wired sink that is silent is a finding.** `recording-is-on-or-the-
gate-is-red` (0.4.0) is the precedent: a fail-open courier with no fail-loud counterpart recorded
nothing for the whole of 0.3.0 and nobody could tell. The same trap is waiting here.

## Prior art, and the thing it gets wrong

The unrelated `agentic-sdlc` on PyPI (truongnat, 3.0.0) ships `WorkflowEngine`, `Coordinator`,
`Agent` and a self-learning `Learner`. It is worth reading once, as a boundary marker:

- `WorkflowEngine._execute_step` returns `{"step": …, "action": …, "status": "completed"}`. The
  `action` is a string echoed back, never resolved to anything callable. Every step "completes" and
  nothing runs.
- `Coordinator.start_execution` sets `status: "running"` and executes nothing.
- `Learner` genuinely persists patterns — and `frequency` is initialised to `1`, read on load, used
  to rank recommendations and to compute `confidence = min(frequency / 10.0, 1.0)`, and
  **incremented nowhere in the package**. The confidence is permanently `0.1`. The loop has no
  feedback edge.

**A learning loop that is never read back is decoration.** That is the failure mode this milestone
has to avoid, and it is why capture alone does not satisfy the ship criterion — a lesson has to
surface where somebody is standing (rule 11), or it is `frequency` all over again.

## Ship criterion

Every belt rung emits a structured event at both edges — entry (`ready-for`) and exit (a move or a
belt write) — carrying the grain, the transition, and the next rung's checks, every field derived
from config or from the belt registry. A test asserts no field can be added that is neither.

The tool spawns nothing to deliver it: the sink is declared in `devkit.toml`, the payload is written,
and a courier carries it. `check pm` names a sink that is wired and silent.

A lesson recorded against a grain or a rule id is READ BACK at the next move that touches either —
not stored and forgotten.

An agent can drive a full story-to-close loop from emitted events alone, without parsing one line of
human prose.

## Risks

- **Rule 2 is the whole design, and it is one commit away from being lost.** "Just let the config
  name a command to run" is the obvious next request and it must be refused by name. Record it as a
  decision with its rejected alternative, before anyone asks.
- **Output shapes are contract (rule 6).** Adding an emission is minor; changing the prose the
  breadcrumb already prints is minor too, and both land in the same code path. Consumers grep that
  prose today.
- **A second scoreboard.** A lesson store that drifts from the review records and gate reports it
  was derived from is exactly the duplication V2 and the path-as-schema defect were killed for. The
  row points at its source; it does not restate it.
- **Scope.** Hooks, telemetry and learning are one stream by design, but they are three audiences
  and this milestone could grow the way 0.4.0 did (17 features). The entry and exit edges are the
  spine; lessons ride on them. If the milestone has to shed weight, it sheds lessons and keeps the
  edges — not the reverse.
