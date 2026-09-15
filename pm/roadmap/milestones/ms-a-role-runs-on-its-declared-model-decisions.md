Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-a-role-runs-on-its-declared-model a role runs on the model it declares — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-15 — an ollama role runs as a separate headless claude process, never inside a hook

A Claude Code session has one provider: `ANTHROPIC_BASE_URL` is per process, and a subagent cannot
be pointed anywhere else. So an `ollama/*` role cannot run in-session. The hook DENIES the in-session
`Agent` spawn, and its reason carries a rendered command that runs the role as its own headless
`claude -p` process with `ANTHROPIC_BASE_URL=http://localhost:11434` and `--model <ollama tag>`.
Ollama ≥0.14 speaks the Anthropic Messages API; 0.34 answered on `/v1/messages` here. The package
RENDERS the command; the orchestrator runs it (the shell composes, rule 11's read side). The command
MUST pin `--strict-mcp-config` and an explicit `--tools` list: probe 2 (milestone file) handed a
local 8B model every globally configured MCP tool, Gmail send included, and it answered about
sending email. That is a safety requirement before it is a performance one.

**Rejected:** Chuzom's shape — the hook calls Ollama itself, runs its own tool loop (60s budget) and
returns the answer as `{"decision":"block","reason":<answer>}`. That makes a hook an agent runtime,
its writes bypass `cc-write-confine`, `cc-commit-pathspec` and the ledger couriers (rule 4's second
sin: a write that looks legitimate and is not), and it breaks rule 2 outright. **Rejected:**
declare-only with no Ollama execution — kept as the fallback if probe 4 fails.

**Open:** `--bare` is what made probe 3 pass, and `--bare` also skips hooks — the guards this
decision chose B to keep. Probe 4 (same command, no `--bare`, `--setting-sources project`) loaded
the hooks and kept the prompt at 3,462 tokens, and still failed: one generation ran five minutes
without a tool call. One run each does not say whether hooks mode or 8B's reliability is the cause.
B stands as the design; whether it WORKS is the revive condition.

## D2 — 2026-09-15 — a Claude role gets its declared model through updatedInput, and an explicit disagreeing model is denied

The routing hook answers the `Agent`/`Task` PreToolUse with `permissionDecision: "allow"` and
`updatedInput` = the tool input with `model` set from the chain (`claude-opus` → `opus`; bare
`claude` sets nothing and inherits). Chuzom's `_emit_model_pin` does exactly this to pin Explore
spawns to haiku — the one Chuzom mechanism taken whole. A caller that PASSED a `model` the table
does not name is denied, naming the declared entry: the declaration is the authority, and a silent
overwrite of an explicit choice is the tool deciding. The agent files' `model:` frontmatter stays
as the stock default for a project with no table, and a table change needs no reinstall.

**Rejected:** rendering `model:` into the agent files at `install-agents` — the table and the
installed files drift the moment one is edited, and `test_install.py` would have to learn a second
source for a line it currently compares byte-for-byte. **Unverified:** `updatedInput` on the
`Agent` tool in this harness; seen in Chuzom's code only.

## D3 — 2026-09-15 — failover walks the declared order at spawn time only, behind one localhost probe

At spawn, walk the chain in declared order and take the first AVAILABLE entry. An `ollama/*` entry
is unavailable when `GET localhost:11434/api/tags` does not answer inside 1s or does not list the
tag (22ms here, measured). Every skipped entry is one named line on the hook's output (rule 11).
A `claude*` entry is always available: nothing this tool can read says a Claude model is near its
limit (D4), so a second Claude entry after a first is unreachable by construction. Chris dropped
them: `developer = ["claude-opus"]`. A chain that ends in `claude-sonnet` after Ollama entries
(`tech-writer`, `pm-operator`) keeps it — that one is reachable.

No mid-run failover, no retry, no judging the answer. **Rejected:** Chuzom's `quality_ok` (under 10
characters, or two refusal phrases, means failed) — a heuristic deciding what an answer means is
rule 9's line. **Rejected:** probing at session start in preflight only — stale by the next spawn.

**Rule 2 amendment, accepted by Chris, lands with the first probe code and not before:** *"one
exception: `core/probe.py` may GET localhost with a ≤1s timeout to ask whether a declared provider
is up; nothing else leaves the process."* The primitive joins `tests/test_boundaries.py` with an
exact allowlist, like `spawn.py`.

## D4 — 2026-09-15 — the quota gate is deferred until a signal exists this tool can honestly read

Chuzom reads `~/.chuzom/usage.json` and refreshes it by pulling the OAuth token out of the macOS
Keychain and calling `api.anthropic.com/api/oauth/usage`. Credential handling and an outbound call
to Anthropic are both outside what a pure-text stdlib tool may do. **Rejected:** a ceiling computed
from our own ledger — the ledger is one repo's rows, a rate limit is the whole account's, so the gate
would print green while the account is red. That is rule 4's first sin, a gate that misses and
prints PASS. Revisit only when Claude Code hands a hook or a file a supported usage signal.

## D5 — 2026-09-15 — the chain grammar is claude, claude-ALIAS and ollama/NAME:TAG, and anything else exits 2

An entry is `claude` (inherit the session model), `claude-<alias>` (an alias the `Agent` tool's
`model` accepts), or `ollama/<name>:<tag>`. An unknown prefix or a non-list value exits 2 naming
the key — a malformed declaration is reading (rule 9). A role key with no installed agent file is a
`check pm` WARN, not a refusal: the table may run ahead of the roster. `default` covers every role
the table does not name. The table is a WORKFLOW key (rule 5): nothing stands behind it, and a
project without it routes nothing — the hook passes every spawn untouched. Parsed in
`core/config.py` like every other value.

## D6 — 2026-09-15 — a new cc-model-route hook reaches the pinned CLI through make and never parses TOML itself

A new `tools/hooks/cc-model-route.sh` on PreToolUse `Agent|Task`, one hook one job — not folded
into `cc-agent-isolation.sh`. It asks `make -s pm ARGS='dispatch --route <role>'` for the resolved
entry, the way `cc-ledger-subagent.sh` already reaches the pinned CLI. The reason is measured: this
machine's `/usr/bin/python3` is 3.9 and has no `tomllib`, and rule 1 exists for exactly that
interpreter. Cost is one make + uv call per spawn — the first story measures it and names it.

## D7 — 2026-09-15 — the ledger's recorded model is the proof the routing held

The ledger already records the model each subagent ACTUALLY ran on, from its transcript
(`src/agentic_sdlc/repo/pm/ledger.py`, the `model` field of a courier row). So: a model column on
`pm ledger report`, and a `check pm` WARN for a row whose model is not in its role's chain. That
WARN is the check on the hook itself — a router that silently stopped routing would otherwise print
nothing. It only works for an out-of-band Ollama run if that process fires the couriers, which is
probe 4's question again.

## D8 — 2026-09-15 — local_routing is a switch in dispatch, absent is off, the environment overrides, and an exhausted chain falls to default

Whether Ollama exists is a fact about the MACHINE, not the project: the laptop has it, CI does not.
So `[dispatch] local_routing = true|false` is the project's default, absent means off (local models
are opt-in, so a copied table never reaches for Ollama), and `GDK_LOCAL_ROUTING=0|1` overrides it
for one shell. Off means every `ollama/*` entry is unavailable, exactly as if the server were down —
one rule for "off", "down" and "not pulled", each skip a named line. The switch sits in `[dispatch]`,
not in `[dispatch.models]`, so the models table stays a pure role → chain map. Turning off ALL
routing, Claude models included, is removing the table; there is no second switch.

An exhausted chain falls to `default`, and says so. **Rejected:** refusing by name when an
all-Ollama chain (`doc-hygiene`, `simplifier`) is exhausted — with a switch, that makes turning local
routing off break two roles.

## D9 — 2026-09-15 — the milestone is parked as backlog, not planned, until a machine makes the wall-clock tolerable

Chris, 2026-09-15: *"Unless I get a substantially more performant machine, this seems like a no-op
right now, but I think eventually in the industry this will become more popular and I want to have
the model/framework/thinking outlined."* On a 16 GB machine the cheapest working configuration took
239s for a two-line edit (probe 3); the only model that fits is 8B, and a 14B model at a working
context froze the machine (probe 1). Free in tokens, ruinous in wall-clock and in the machine
it occupies. So the milestone carries the design and the evidence and no features: no `version:`
(which `pm` reads as BACKLOG, not a finding), no `branch:`, status `planning`.

**Rejected:** building features 1, 2 and 4 now, since they do not depend on Ollama. They are sound,
but without an Ollama role the table only re-declares what the agent files' `model:` frontmatter
already pins, which is a second source for one fact and no new capability. They ship with feature 3
or not at all.
